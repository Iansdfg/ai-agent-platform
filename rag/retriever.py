from typing import List

from rag.embedding_store import EmbeddingStore


class RetrievedChunk:
    def __init__(self, content, metadata):
        self.content = content
        self.metadata = metadata


class Retriever:
    def __init__(self) -> None:
        self._store = EmbeddingStore()
        self._index = self._store.load_index()

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedChunk]:
        retriever = self._index.as_retriever(similarity_top_k=top_k)
        results = retriever.retrieve(query)

        return [
            RetrievedChunk(node.get_content(), node.metadata)
            for node in results
        ]
