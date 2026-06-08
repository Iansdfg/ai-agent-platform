"""
Retrieval node for Market Brain Agent.

Retrieves relevant documents from vector store using FAISS.
"""

import time
from typing import Any, Dict, List

from core.tracing import build_trace_item, duration_ms
from rag.retriever import Retriever
from state.agent_state import AgentState


# Lazy initialization
_retrieval = None


def _get_retrieval_node():
    """Lazy initialization of RetrievalNode."""
    global _retrieval
    if _retrieval is None:
        _retrieval = RetrievalNode()
    return _retrieval


class RetrievalNode:
    """Document retrieval using FAISS vector store."""

    def __init__(self) -> None:
        self._retriever = Retriever()

    def invoke(self, state: AgentState) -> AgentState:
        """
        Retrieve relevant documents for the user message.
        
        Retrieves top_k=6, deduplicates by content, keeps top 3 unique.
        """
        start = time.time()
        message = state["message"]
        session_id = state.get("session_id")

        try:
            retrieved_chunks = self._retriever.retrieve(message, top_k=6)

            # Deduplicate by content
            seen = set()
            unique_chunks = []

            for chunk in retrieved_chunks:
                key = chunk.content.strip()
                if key not in seen:
                    seen.add(key)
                    unique_chunks.append(chunk)

            # Keep top 3 unique
            unique_chunks = unique_chunks[:3]

            latency_ms = duration_ms(start)
            retrieval_hit = len(unique_chunks) > 0

            # Format documents
            documents: List[Dict[str, Any]] = [
                {
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                }
                for chunk in unique_chunks
            ]

            # Format citations
            citations: List[Dict[str, Any]] = [
                {
                    "source": chunk.metadata.get("source"),
                    "file_name": chunk.metadata.get("file_name"),
                    "chunk_index": chunk.metadata.get("chunk_index"),
                    "snippet": chunk.content[:300],
                }
                for chunk in unique_chunks
            ]

            # Format retrieved context
            if retrieval_hit:
                retrieved_context = "\n\n".join(
                    [
                        f"[{index + 1}]\n"
                        f"file_name: {chunk.metadata.get('file_name')}\n"
                        f"source: {chunk.metadata.get('source')}\n"
                        f"chunk_index: {chunk.metadata.get('chunk_index')}\n"
                        f"content:\n{chunk.content}"
                        for index, chunk in enumerate(unique_chunks)
                    ]
                )
            else:
                retrieved_context = (
                    "No relevant context was retrieved from the vector store."
                )

            trace_item = build_trace_item(
                step="retrieval",
                name="faiss_retriever",
                input_data={
                    "query": message,
                    "session_id": session_id,
                    "top_k": 6,
                    "deduped_top_k": 3,
                },
                output_data={
                    "retrieval_hit": retrieval_hit,
                    "retrieved_chunk_count": len(unique_chunks),
                    "raw_retrieved_chunk_count": len(retrieved_chunks),
                },
                latency_ms=latency_ms,
                success=True,
            )

            intermediate_result = {
                "step": "retrieval",
                "retrieval_hit": retrieval_hit,
                "retrieved_chunk_count": len(unique_chunks),
            }

            return {
                **state,
                "step_count": int(state.get("step_count", 0)) + 1,
                "documents": documents,
                "retrieved_context": retrieved_context,
                "citations": citations,
                "intermediate_results": state.get("intermediate_results", [])
                + [intermediate_result],
                "tool_trace": state.get("tool_trace", []) + [trace_item],
            }

        except Exception as e:
            latency_ms = duration_ms(start)

            trace_item = build_trace_item(
                step="retrieval",
                name="faiss_retriever",
                input_data={
                    "query": message,
                    "session_id": session_id,
                    "top_k": 6,
                },
                output_data={},
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )

            return {
                **state,
                "step_count": int(state.get("step_count", 0)) + 1,
                "documents": [],
                "retrieved_context": "Retrieval failed.",
                "citations": [],
                "intermediate_results": state.get("intermediate_results", [])
                + [{"step": "retrieval", "success": False, "error": str(e)}],
                "tool_trace": state.get("tool_trace", []) + [trace_item],
                "error": str(e),
            }


def retrieval_node(state: AgentState) -> AgentState:
    """Retrieval node entry point."""
    return _get_retrieval_node().invoke(state)
