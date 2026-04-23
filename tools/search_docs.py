from typing import Dict, Any, List

from core.config import VECTOR_STORE_PATH
from rag.retriever import Retriever


class SearchDocsTool:
    name = "search_docs"
    description = "Search indexed local documents and return top relevant chunks with metadata."

    def __init__(self) -> None:
        self._retriever = Retriever(VECTOR_STORE_PATH)

    def run(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        chunks = self._retriever.retrieve(query, top_k=top_k)

        items: List[Dict[str, Any]] = []
        citations: List[Dict[str, Any]] = []

        for chunk in chunks:
            item = {
                "content": chunk.content,
                "source": chunk.metadata.get("source"),
                "file_name": chunk.metadata.get("file_name"),
                "chunk_index": chunk.metadata.get("chunk_index"),
            }
            items.append(item)
            citations.append(
                {
                    "source": chunk.metadata.get("source"),
                    "file_name": chunk.metadata.get("file_name"),
                    "chunk_index": chunk.metadata.get("chunk_index"),
                }
            )

        return {
            "query": query,
            "results": items,
            "citations": citations,
        }