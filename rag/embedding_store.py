from llama_index.core import Document as LlamaDocument
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from core.config import OPENAI_API_KEY


class EmbeddingStore:
    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")

        self._embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=OPENAI_API_KEY,
        )

        self._vector_store = PGVectorStore.from_params(
            database="rag_db",
            host="localhost",
            password="postgres",
            port=5432,
            user="postgres",
            table_name="documents",
            embed_dim=1536,
        )

        self._storage_context = StorageContext.from_defaults(
            vector_store=self._vector_store
        )

    def build_index(self, documents):
        llama_docs = [
            LlamaDocument(
                text=doc.content,
                metadata=doc.metadata,
            )
            for doc in documents
        ]

        return VectorStoreIndex.from_documents(
            llama_docs,
            storage_context=self._storage_context,
            embed_model=self._embed_model,
        )

    def load_index(self):
        return VectorStoreIndex.from_vector_store(
            self._vector_store,
            embed_model=self._embed_model,
        )