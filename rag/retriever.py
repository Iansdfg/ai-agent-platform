from typing import Any, Dict, List

from rag.embedding_store import EmbeddingStore


class RetrievedChunk:
    def __init__(self, content: str, metadata: Dict[str, Any]) -> None:
        self.content = content
        self.metadata = metadata


class Retriever:
    def __init__(self) -> None:
        self._store = EmbeddingStore()
        self._index = self._store.load_index()

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedChunk]:
        llama_retriever = self._index.as_retriever(similarity_top_k=top_k)
        results = llama_retriever.retrieve(query)

        chunks: List[RetrievedChunk] = []

        for result in results:
            node = result.node

            chunks.append(
                RetrievedChunk(
                    content=node.get_content(),
                    metadata=node.metadata or {},
                )
            )

        return chunks