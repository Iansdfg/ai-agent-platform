import time
from typing import Any, Dict, List

from chains.rag_chain import build_rag_chain
from core.config import MODEL_NAME
from rag.retriever import Retriever


class Orchestrator:
    def __init__(self) -> None:
        self._retriever = Retriever()
        self._rag_chain = build_rag_chain()

    def handle_chat(
        self,
        message: str,
        request_id: str,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        start_time = time.time()

        retrieved_chunks = self._retriever.retrieve(message, top_k=3)
        retrieval_hit = len(retrieved_chunks) > 0

        if retrieval_hit:
            retrieved_context = "\n\n".join(
                [
                    f"[Source {index + 1}]\n"
                    f"file_name: {chunk.metadata.get('file_name')}\n"
                    f"source: {chunk.metadata.get('source')}\n"
                    f"chunk_index: {chunk.metadata.get('chunk_index')}\n"
                    f"content:\n{chunk.content}"
                    for index, chunk in enumerate(retrieved_chunks)
                ]
            )
        else:
            retrieved_context = (
                "No relevant context was retrieved from the vector store. "
                "Answer honestly and say when the available project documents "
                "do not contain enough information."
            )

        answer = self._rag_chain.invoke(
            {
                "question": message,
                "context": retrieved_context,
            }
        )

        citations: List[Dict[str, Any]] = [
            {
                "source": chunk.metadata.get("source"),
                "file_name": chunk.metadata.get("file_name"),
                "chunk_index": chunk.metadata.get("chunk_index"),
                "snippet": chunk.content[:300],
            }
            for chunk in retrieved_chunks
        ]

        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "answer": answer,
            "metadata": {
                "request_id": request_id,
                "model": MODEL_NAME,
                "latency_ms": latency_ms,
                "session_id": session_id,
                "route": "langchain_rag",
                "response_type": "final",
                "top_k": 3,
                "retrieval_hit": retrieval_hit,
                "retrieved_chunk_count": len(retrieved_chunks),
            },
            "tool_trace": [],
            "citations": citations,
        }