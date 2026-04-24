from llama_index.core import VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from core.config import OPENAI_API_KEY

class EmbeddingStore:
    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")

        self._embed_model = OpenAIEmbedding(api_key=OPENAI_API_KEY)

        self._vector_store = PGVectorStore.from_params(
            database="rag_db",
            host="localhost",
            password="postgres",
            port=5432,
            user="postgres",
            table_name="documents",
            embed_dim=1536,
        )

    def build_index(self, documents):
        return VectorStoreIndex.from_documents(
            documents,
            embed_model=self._embed_model,
            vector_store=self._vector_store,
        )

    def load_index(self):
        return VectorStoreIndex.from_vector_store(
            self._vector_store,
            embed_model=self._embed_model,
        )
