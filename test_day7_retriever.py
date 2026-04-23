from core.config import VECTOR_STORE_PATH
from rag.retriever import Retriever

retriever = Retriever(VECTOR_STORE_PATH)

query = "What is the return policy?"
results = retriever.retrieve(query, top_k=3)

print(f"Query: {query}")
print(f"Results: {len(results)}")
print()

for i, item in enumerate(results):
    print(f"Result {i + 1}")
    print(item.metadata)
    print(item.content)
    print("-" * 60)