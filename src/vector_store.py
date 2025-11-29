import logging
from typing import List, Dict, Any

from langchain_core.documents import Document

from langchain_pinecone import PineconeVectorStore


from config import config

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





