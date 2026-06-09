from llama_index.core import Document as LlamaDocument
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

from core.config import (
    EMBEDDING_MODEL_NAME,
    OPENAI_API_KEY,
    RAG_DB_HOST,
    RAG_DB_NAME,
    RAG_DB_PASSWORD,
    RAG_DB_PORT,
    RAG_DB_USER,
    RAG_EMBED_DIM,
    RAG_ASYNC_DATABASE_URL,
    RAG_DATABASE_URL,
    RAG_TABLE_NAME,
)


class EmbeddingStore:
    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")

        self._embed_model = OpenAIEmbedding(
            model=EMBEDDING_MODEL_NAME,
            api_key=OPENAI_API_KEY,
        )

        self._vector_store = PGVectorStore.from_params(
            connection_string=RAG_DATABASE_URL,
            async_connection_string=RAG_ASYNC_DATABASE_URL,
            database=RAG_DB_NAME,
            host=RAG_DB_HOST,
            password=RAG_DB_PASSWORD,
            port=RAG_DB_PORT,
            user=RAG_DB_USER,
            table_name=RAG_TABLE_NAME,
            embed_dim=RAG_EMBED_DIM,
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
