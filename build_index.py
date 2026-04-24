from core.config import DOCS_DIR
from rag.document_loader import DocumentLoader
from rag.embedding_store import EmbeddingStore

loader = DocumentLoader()
documents = loader.load_documents(DOCS_DIR)

store = EmbeddingStore()
index = store.build_index(documents)

print(f"Indexed documents into PostgreSQL vector DB")