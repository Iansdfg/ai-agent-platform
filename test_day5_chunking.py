from rag.document_loader import DocumentLoader
from rag.text_splitter import SimpleTextSplitter

loader = DocumentLoader()
documents = loader.load_documents("docs")

splitter = SimpleTextSplitter(chunk_size=80, overlap=20)
chunks = splitter.split_documents(documents)

print(f"Loaded documents: {len(documents)}")
print(f"Generated chunks: {len(chunks)}")
print()

for i, chunk in enumerate(chunks):
    print(f"Chunk {i}")
    print(chunk.metadata)
    print(chunk.content)
    print("-" * 60)