import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_ollama import OllamaEmbeddings

logger = logging.getLogger(__name__)
load_dotenv()

class Config:
    def __init__(self):

        # AWS S3
        self.aws_bucket_name:str = os.getenv('AWS_S3_BUCKET')
        self.aws_profile:str = os.getenv('AWS_PROFILE')
        self.aws_region:str = os.getenv('AWS_REGION', 'us-east-1')

        # Postgres
        self.psql_host:str = os.getenv('PSQL_HOST')
        self.psql_port:str = os.getenv('PSQL_PORT')
        self.psql_database:str = os.getenv('PSQL_DATABASE')
        self.psql_user:str = os.getenv('PSQL_USER')
        self.psql_password:str = os.getenv('PSQL_PASSWORD')
        self.psql_connection_string: str = self._get_postgres_connection_string()

        # Langsmith
        self.langsmith_api_key:str = os.getenv('LANGSMITH_API_KEY')
        self.langsmith_tracing:str = os.getenv('LANGSMITH_TRACING')

        # # Pinecone Vector Database
        # self.pinecone_api_key:str = os.getenv('PINECONE_API_KEY')
        # self.pinecone_index_name: str = os.getenv('PINECONE_INDEX_NAME')
        # self.pinecone_region: str = os.getenv('PINECONE_REGION')

        # Embedding
        self.embedding_provider: str = os.getenv('EMBEDDING_PROVIDER')
        self.embedding_model: Embeddings = self._get_embeddings()
        self.embedding_dimension: int = self._get_embedding_dimension()

        # Project Root
        self.project_root = self._get_project_root()

    # Helper function to get project paths
    def _get_project_root(self) -> Path:
        """Get the root directory of this project"""
        current_file = Path(__file__)
        parent_directory = current_file
        project_root = parent_directory.parent
        return project_root

    def _get_postgres_connection_string(self) -> str:
        """Build PostgreSQL connection string for langchain-postgres."""
        return (
            f"postgresql+psycopg://{self.psql_user}:{self.psql_password}"
            f"@{self.psql_host}:{self.psql_port}/{self.psql_database}"
        )

    def _get_embedding_dimension(self) -> int:
        """Get the dimension size for the configured embedding provider."""
        dimensions = {
            'gemini': 768,  # text-embedding-004
            'ollama': 768,  # nomic-embed-text default
        }
        return dimensions.get(self.embedding_provider.lower(), 768)

    def _get_embeddings(self) -> Embeddings:
        """
        Get embeddings based on configured provider.

        Supports: OpenAI, Google Gemini, Ollama
        Returns the appropriate embedding model instance.
        """
        provider = self.embedding_provider
        model = os.getenv('EMBEDDING_MODEL')

        match provider:
            case 'gemini':
                logger.info(f"Using Google Gemini embeddings: {model}")
                return GoogleGenerativeAIEmbeddings(
                    model=model,
                    google_api_key=os.getenv('GEMINI_API_KEY')
                )

            case 'ollama':
                logger.info(f"Using Ollama embeddings: {model}")
                return OllamaEmbeddings(
                    model=model,
                )

            case _:
                raise ValueError(
                    f"Unknown embedding provider: {provider}. "
                    f"Supported: 'gemini', 'ollama'"
                )

config = Config()

