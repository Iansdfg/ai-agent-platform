from core.config import DOCS_DIR, VECTOR_STORE_PATH
from rag.document_loader import DocumentLoader
from rag.embedding_store import EmbeddingStore
from rag.text_splitter import SimpleTextSplitter

loader = DocumentLoader()
documents = loader.load_documents(DOCS_DIR)

splitter = SimpleTextSplitter(chunk_size=300, overlap=50)
chunks = splitter.split_documents(documents)

store = EmbeddingStore()
vector_store = store.build_vector_store(chunks)
store.save_vector_store(vector_store, VECTOR_STORE_PATH)

print(f"Loaded documents: {len(documents)}")
print(f"Generated chunks: {len(chunks)}")
print(f"Saved vector store to: {VECTOR_STORE_PATH}")