import logging
from pathlib import Path
from typing import List

from langchain_core.documents import Document

from langchain_pinecone import PineconeVectorStore


from config import config
from src.s3_store import S3_StoreManager

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """
    Use Pinecone Langchain to manage Vector Database operations for images
    https://docs.pinecone.io/integrations/langchain

    get_embeddings: Get embedding LLMs
    :arg
    :return embedding: Embedding

    add_documents: Add Documents to Vector Database as Embeddings and get list of IDs of added docs
    :arg docs: List[Documents]
    :return ids: List[str]

    search_images: Find images in Pinecone with semantic query
    :arg
    :return images: list[str]
    Query a question using LLM (RAG)

    """
    def __init__(self):
        # Initialize Embeddings and Dimension (more dimension more context per embedding)
        # self.dimension = self._get_embedding_dimension()

        # Initialize Pinecone vector store
        self.vector_store = PineconeVectorStore(
            pinecone_api_key= config.pinecone_api_key,
            index_name= config.pinecone_index_name,
            embedding=config.embedding_model
        )



    def add_documents(self, docs: List[Document]) -> List[str]:
        if not docs:
            logger.warning('No docs to add')
            return []

        logger.info(f'Adding {len(docs)} docs to vector store...')
        ids = self.vector_store.add_documents(docs)
        logger.info(f'Successfully added {len(ids)} documents')

        return ids


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
                s3_uri=doc.metadata.get('s3_uri'),
                expiration=3600
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


