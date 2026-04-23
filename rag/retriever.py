from dataclasses import dataclass
from typing import Any, Dict, List

from rag.embedding_store import EmbeddingStore


@dataclass
class RetrievedChunk:
    content: str
    metadata: Dict[str, Any]


class Retriever:
    def __init__(self, vector_store_path: str) -> None:
        self._store = EmbeddingStore()
        self._vector_store = self._store.load_vector_store(vector_store_path)

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedChunk]:
        results = self._vector_store.similarity_search(query, k=top_k)

        unique_results: List[RetrievedChunk] = []
        seen = set()

        for doc in results:
            dedupe_key = (
                doc.metadata.get("source"),
                doc.metadata.get("chunk_index"),
            )

            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            unique_results.append(
                RetrievedChunk(
                    content=doc.page_content,
                    metadata=doc.metadata,
                )
            )

        return unique_results