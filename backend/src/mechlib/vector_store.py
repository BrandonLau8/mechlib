import logging
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_postgres import PGVectorStore

from config import config
from .s3_store import S3_StoreManager

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

        # Add full-text search for hybrid search
        self._init_fulltext_search()

    def _init_fulltext_search(self):
        """Add full-text search column and index for keyword search."""
        import psycopg

        conn = None
        cur = None
        try:
            # psycopg needs postgresql:// not postgresql+psycopg://
            conn_string = config.psql_connection_string.replace('postgresql+psycopg://', 'postgresql://')
            conn = psycopg.connect(conn_string)
            cur = conn.cursor()

            # Add search_vector column
            cur.execute(f"""
                ALTER TABLE {self.TABLE_NAME}
                ADD COLUMN IF NOT EXISTS search_vector tsvector;
            """)

            # Create/replace trigger function
            cur.execute(f"""
                CREATE OR REPLACE FUNCTION {self.TABLE_NAME}_search_update()
                RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := to_tsvector('english',
                        COALESCE(NEW.langchain_metadata->>'description', '') || ' ' ||
                        COALESCE(NEW.langchain_metadata->>'brand', '') || ' ' ||
                        COALESCE(NEW.langchain_metadata->>'person', '') || ' ' ||
                        COALESCE(NEW.langchain_metadata->>'project', '') || ' ' ||
                        COALESCE(NEW.langchain_metadata->>'materials', '') || ' ' ||
                        COALESCE(NEW.langchain_metadata->>'process', '') || ' ' ||
                        COALESCE(NEW.langchain_metadata->>'mechanism', '')
                    );
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            # Drop and recreate trigger
            cur.execute(f"""
                DROP TRIGGER IF EXISTS {self.TABLE_NAME}_search_trigger ON {self.TABLE_NAME};
            """)
            cur.execute(f"""
                CREATE TRIGGER {self.TABLE_NAME}_search_trigger
                BEFORE INSERT OR UPDATE ON {self.TABLE_NAME}
                FOR EACH ROW EXECUTE FUNCTION {self.TABLE_NAME}_search_update();
            """)

            # Update existing rows
            cur.execute(f"""
                UPDATE {self.TABLE_NAME}
                SET search_vector = to_tsvector('english',
                    COALESCE(langchain_metadata->>'description', '') || ' ' ||
                    COALESCE(langchain_metadata->>'brand', '') || ' ' ||
                    COALESCE(langchain_metadata->>'person', '') || ' ' ||
                    COALESCE(langchain_metadata->>'project', '') || ' ' ||
                    COALESCE(langchain_metadata->>'materials', '') || ' ' ||
                    COALESCE(langchain_metadata->>'process', '') || ' ' ||
                    COALESCE(langchain_metadata->>'mechanism', '')
                )
                WHERE search_vector IS NULL;
            """)

            # Create GIN index for fast full-text search
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.TABLE_NAME}_search_idx
                ON {self.TABLE_NAME} USING GIN(search_vector);
            """)

            conn.commit()
            logger.info("Full-text search enabled for hybrid search")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.debug(f"Full-text search setup: {e}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()


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


    def hybrid_search(self, query: str, k: int = 10, keyword_weight: float = 0.5):
        """
        Hybrid search combining keyword (full-text) and semantic (vector) search.

        Args:
            query: Search query
            k: Number of results to return
            keyword_weight: Weight for keyword search (0.0-1.0).
                           0.5 = equal weight, 1.0 = keyword only, 0.0 = semantic only

        Returns:
            List of (Document, combined_score) tuples, sorted by score (lower is better)
        """
        from collections import defaultdict

        # Get more results from each search to ensure good coverage
        fetch_k = k * 3

        # Get semantic search results (cosine distance: 0=identical, 2=opposite)
        semantic_results = self.vector_store.similarity_search_with_score(query, k=fetch_k)

        # Build filename -> (doc, semantic_rank, distance) mapping
        semantic_map = {}
        for rank, (doc, distance) in enumerate(semantic_results, start=1):
            filename = doc.metadata.get('filename')
            if filename:
                semantic_map[filename] = (doc, rank, distance)

        # Get keyword search results
        keyword_filenames = self._keyword_search(query, k=fetch_k)
        keyword_set = set(keyword_filenames)

        # Combine keyword and semantic scores
        # Strategy: Use semantic distances but boost keyword matches
        hybrid_scores = {}

        # Process all semantic results
        for filename, (doc, rank, distance) in semantic_map.items():
            base_distance = distance

            # Apply keyword boost if this file has a keyword match
            if filename in keyword_set:
                keyword_rank = keyword_filenames.index(filename) + 1
                # Reduce distance based on keyword match (better rank = more reduction)
                keyword_boost = 0.3 * (1 / keyword_rank)  # Up to 0.3 reduction
                final_distance = max(0.0, base_distance - keyword_boost)
            else:
                final_distance = base_distance

            hybrid_scores[filename] = {'doc': doc, 'distance': final_distance}

        # Add keyword-only results (not in semantic results)
        for filename in keyword_filenames:
            if filename not in hybrid_scores and filename in semantic_map:
                doc, _, distance = semantic_map[filename]
                # Keyword match with poor semantic gets boosted
                final_distance = max(0.0, distance - 0.3)
                hybrid_scores[filename] = {'doc': doc, 'distance': final_distance}

        # Sort by distance (lower = better) and return
        sorted_results = sorted(
            [(item['doc'], item['distance']) for item in hybrid_scores.values()],
            key=lambda x: x[1]
        )

        return sorted_results[:k]

    def _keyword_search(self, query: str, k: int):
        """Perform keyword search and return list of filenames."""
        import psycopg

        conn_string = config.psql_connection_string.replace('postgresql+psycopg://', 'postgresql://')
        conn = psycopg.connect(conn_string)
        cur = conn.cursor()

        try:
            cur.execute(f"""
                SELECT langchain_metadata->>'filename', ts_rank(search_vector, plainto_tsquery('english', %s)) as rank
                FROM {self.TABLE_NAME}
                WHERE search_vector @@ plainto_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s;
            """, (query, query, k))

            results = [row[0] for row in cur.fetchall() if row[0]]
            return results
        finally:
            cur.close()
            conn.close()

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


