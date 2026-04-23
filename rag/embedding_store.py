from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import List

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LCDocument

from core.config import EMBEDDING_MODEL_NAME, OPENAI_API_KEY
from rag.text_splitter import Chunk


class EmbeddingStore:
    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set")

        self._embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL_NAME,
            api_key=OPENAI_API_KEY,
        )

    def build_vector_store(self, chunks: List[Chunk]) -> FAISS:
        lc_docs = self._to_langchain_documents(chunks)
        return FAISS.from_documents(lc_docs, self._embeddings)

    def save_vector_store(self, vector_store: FAISS, save_dir: str) -> None:
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        vector_store.save_local(save_dir)

    def load_vector_store(self, save_dir: str) -> FAISS:
        return FAISS.load_local(
            save_dir,
            self._embeddings,
            allow_dangerous_deserialization=True,
        )

    def _to_langchain_documents(self, chunks: List[Chunk]) -> List[LCDocument]:
        return [
            LCDocument(
                page_content=chunk.content,
                metadata=chunk.metadata,
            )
            for chunk in chunks
        ]