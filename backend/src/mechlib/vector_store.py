import logging
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_postgres import PGVectorStore

from backend.config import config
from backend.src.mechlib.s3_store import S3_StoreManager

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """
    Use PGVectorStore (langchain-postgres) to manage Vector Database operations for images.

    Migration from deprecated PGVector to new PGVectorStore implementation.
    Uses single-table design for better performance and simpler management.

    Methods:
    - add_documents: Add Documents to Vector Database as Embeddings
    - search: Semantic search for images, returns gallery HTML
    """

    TABLE_NAME = "mechlib_images"

    def __init__(self):
        """Initialize PGVectorStore with connection and embeddings."""
        from langchain_postgres import PGEngine

        # Create engine from connection string
        self.engine = PGEngine.from_connection_string(
            url=config.psql_connection_string
        )

        # Initialize table if it doesn't exist
        self._init_table()

        # Create vector store
        self.vector_store = PGVectorStore.create_sync(
            engine=self.engine,
            embedding_service=config.embedding_model,
            table_name=self.TABLE_NAME,
        )

        logger.info(f"Initialized PGVectorStore with table '{self.TABLE_NAME}'")

    def _init_table(self):
        """Initialize the vectorstore table with proper schema."""
        try:
            self.engine.init_vectorstore_table(
                table_name=self.TABLE_NAME,
                vector_size=config.embedding_dimension,
            )
            logger.info(f"Table '{self.TABLE_NAME}' initialized with vector size {config.embedding_dimension}")
        except Exception as e:
            # Table might already exist, which is fine
            logger.debug(f"Table initialization: {e}")


    def add_documents(self, docs: List[Document]):
        if not docs:
            logger.warning('No docs to add')

        logger.info(f'Adding {len(docs)} docs to vector store...')
        ids = self.vector_store.add_documents(docs)
        logger.info(f'Successfully added {len(ids)} documents')


    # def _get_embedding_dimension(provider: str) -> int:
    #     """Get the dimension size for each embedding provider. """
    #     dimensions = {
    #         'openai': 1536,  # text-embedding-3-small
    #         'gemini': 768,  # text-embedding-004
    #         'ollama': 768,  # nomic-embed-text
    #     }
    #     return dimensions.get(provider.lower(), 1536)


    def search(self):

        results = self.vector_store.similarity_search(
            query= 'find images of comp products with bayonet features',
            k=3
        )
        s3_client = S3_StoreManager()
        # logger.info(results)
        image_urls = []
        for doc in results:
            url = s3_client.generate_presigned_url(
                s3_uri=doc.metadata.get('s3_uri')
            )
            image_urls.append(url)


        # Generate image HTML
        images_html = '\n'.join([
            f'        <div class="gallery-item">\n'
            f'            <img src="{url}" alt="{doc.metadata.get("filename", "Image")}">\n'
            f'        </div>'
            for url, doc in zip(image_urls, results)
        ])

        # Read template and substitute images
        template_path = Path('./templates/gallery.html')
        template = template_path.read_text()
        html = template.replace('{{IMAGES}}', images_html)

        # Save to local file
        gallery_path = Path('gallery.html')
        gallery_path.write_text(html)

        print(f"✅ Gallery created at {gallery_path.absolute()}")
        print(f"📖 Open in browser: file://{gallery_path.absolute()}")
        return gallery_path


