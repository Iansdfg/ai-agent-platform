from dataclasses import dataclass
from typing import Any, Dict, List

from rag.document_loader import Document


@dataclass
class Chunk:
    content: str
    metadata: Dict[str, Any]


class SimpleTextSplitter:
    def __init__(self, chunk_size: int = 300, overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if overlap < 0:
            raise ValueError("overlap must be >= 0")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def split_documents(self, documents: List[Document]) -> List[Chunk]:
        chunks: List[Chunk] = []

        for doc in documents:
            doc_chunks = self._split_single_document(doc)
            chunks.extend(doc_chunks)

        return chunks

    def _split_single_document(self, document: Document) -> List[Chunk]:
        text = document.content
        chunks: List[Chunk] = []

        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunk_metadata = {
                    **document.metadata,
                    "chunk_index": chunk_index,
                    "start_char": start,
                    "end_char": end,
                }

                chunks.append(
                    Chunk(
                        content=chunk_text,
                        metadata=chunk_metadata,
                    )
                )

            if end == len(text):
                break

            start = end - self.overlap
            chunk_index += 1

        return chunks