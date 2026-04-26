import time
from typing import Any, Dict, List

from chains.rag_chain import build_rag_chain
from core.config import MODEL_NAME
from core.tracing import build_trace_item, duration_ms, write_trace_log
from rag.retriever import Retriever
from router import QueryRouter
from tools.registry import build_default_registry


class Orchestrator:
    def __init__(self) -> None:
        self._retriever = Retriever()
        self._rag_chain = build_rag_chain()
        self._router = QueryRouter()
        self._tool_registry = build_default_registry()

        # session_id -> [{"role": "user", "content": "..."}, ...]
        self._memory: Dict[str, List[Dict[str, str]]] = {}

    def _get_history(self, session_id: str | None) -> List[Dict[str, str]]:
        if not session_id:
            return []
        return self._memory.get(session_id, [])

    def _append_history(self, session_id: str | None, role: str, content: str) -> None:
        if not session_id:
            return

        if session_id not in self._memory:
            self._memory[session_id] = []

        self._memory[session_id].append(
            {
                "role": role,
                "content": content,
            }
        )

        self._memory[session_id] = self._memory[session_id][-10:]

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        if not history:
            return "No previous conversation history."

        return "\n".join(
            [
                f"{msg['role']}: {msg['content']}"
                for msg in history[-6:]
            ]
        )

    def handle_chat(
        self,
        message: str,
        request_id: str,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        total_start = time.time()
        tool_trace: List[Dict[str, Any]] = []

        history = self._get_history(session_id)
        history_text = self._format_history(history)

        # Step 1: Router
        routing_start = time.time()

        route_decision = self._router.route(
            query=message,
            history=history,
        )

        tool_trace.append(
            build_trace_item(
                step="routing",
                name="query_router",
                input_data={
                    "query": message,
                    "session_id": session_id,
                    "history_message_count": len(history),
                },
                output_data=route_decision.model_dump(),
                latency_ms=duration_ms(routing_start),
                success=True,
            )
        )

        # Step 2A: Tool route
        if route_decision.route == "tool":
            tool_start = time.time()

            try:
                if not route_decision.tool_name:
                    raise ValueError("Router selected tool route but tool_name is missing.")

                tool_result = self._tool_registry.execute(
                    route_decision.tool_name,
                    route_decision.tool_input,
                )

                tool_latency_ms = duration_ms(tool_start)

                tool_trace.append(
                    build_trace_item(
                        step="tool_execution",
                        name=route_decision.tool_name,
                        input_data=route_decision.tool_input,
                        output_data={
                            "success": tool_result.success,
                            "output": tool_result.output,
                            "error": tool_result.error,
                        },
                        latency_ms=tool_latency_ms,
                        success=tool_result.success,
                        error=tool_result.error,
                    )
                )

                if tool_result.success:
                    answer = (
                        f"Tool `{route_decision.tool_name}` executed successfully.\n\n"
                        f"Result:\n{tool_result.output}"
                    )
                else:
                    answer = (
                        f"Tool `{route_decision.tool_name}` failed: "
                        f"{tool_result.error}"
                    )

            except Exception as e:
                answer = f"Tool execution failed: {str(e)}"

                tool_trace.append(
                    build_trace_item(
                        step="tool_execution",
                        name=route_decision.tool_name or "unknown_tool",
                        input_data=route_decision.tool_input,
                        output_data={},
                        latency_ms=duration_ms(tool_start),
                        success=False,
                        error=str(e),
                    )
                )

            self._append_history(session_id, "user", message)
            self._append_history(session_id, "assistant", answer)

            result = {
                "answer": answer,
                "metadata": {
                    "request_id": request_id,
                    "model": MODEL_NAME,
                    "latency_ms": duration_ms(total_start),
                    "session_id": session_id,
                    "route": "tool",
                    "router_reason": route_decision.reason,
                    "router_confidence": route_decision.confidence,
                    "tool_name": route_decision.tool_name,
                    "response_type": "final",
                    "trace_count": len(tool_trace),
                    "memory_enabled": session_id is not None,
                    "history_message_count_before": len(history),
                    "history_message_count_after": len(self._get_history(session_id)),
                },
                "tool_trace": tool_trace,
                "citations": [],
            }

            write_trace_log(
                {
                    "event": "agent_request_completed",
                    "request_id": request_id,
                    "session_id": session_id,
                    "message": message,
                    "metadata": result["metadata"],
                    "tool_trace": tool_trace,
                }
            )

            return result

        # Step 2B: Direct route
        if route_decision.route == "direct":
            llm_start = time.time()

            try:
                direct_question = (
                    f"Conversation history:\n{history_text}\n\n"
                    f"Current user question:\n{message}"
                )

                answer = self._rag_chain.invoke(
                    {
                        "question": direct_question,
                        "context": (
                            "No retrieval is needed for this query. "
                            "Answer directly and concisely."
                        ),
                    }
                )

                tool_trace.append(
                    build_trace_item(
                        step="generation",
                        name="direct_llm",
                        input_data={
                            "question": message,
                            "session_id": session_id,
                            "history_message_count": len(history),
                            "model": MODEL_NAME,
                        },
                        output_data={
                            "answer_chars": len(str(answer)),
                        },
                        latency_ms=duration_ms(llm_start),
                        success=True,
                    )
                )

            except Exception as e:
                answer = (
                    "Sorry, I failed to generate a direct answer because "
                    "the LLM chain raised an error."
                )

                tool_trace.append(
                    build_trace_item(
                        step="generation",
                        name="direct_llm",
                        input_data={
                            "question": message,
                            "session_id": session_id,
                            "history_message_count": len(history),
                            "model": MODEL_NAME,
                        },
                        output_data={},
                        latency_ms=duration_ms(llm_start),
                        success=False,
                        error=str(e),
                    )
                )

            self._append_history(session_id, "user", message)
            self._append_history(session_id, "assistant", str(answer))

            result = {
                "answer": answer,
                "metadata": {
                    "request_id": request_id,
                    "model": MODEL_NAME,
                    "latency_ms": duration_ms(total_start),
                    "session_id": session_id,
                    "route": "direct",
                    "router_reason": route_decision.reason,
                    "router_confidence": route_decision.confidence,
                    "response_type": "final",
                    "trace_count": len(tool_trace),
                    "memory_enabled": session_id is not None,
                    "history_message_count_before": len(history),
                    "history_message_count_after": len(self._get_history(session_id)),
                },
                "tool_trace": tool_trace,
                "citations": [],
            }

            write_trace_log(
                {
                    "event": "agent_request_completed",
                    "request_id": request_id,
                    "session_id": session_id,
                    "message": message,
                    "metadata": result["metadata"],
                    "tool_trace": tool_trace,
                }
            )

            return result

        # Step 2C: RAG route
        retrieval_start = time.time()

        try:
            retrieval_query = f"{history_text}\n\nCurrent user question: {message}"

            retrieved_chunks = self._retriever.retrieve(retrieval_query, top_k=3)
            retrieval_latency_ms = duration_ms(retrieval_start)
            retrieval_hit = len(retrieved_chunks) > 0

            tool_trace.append(
                build_trace_item(
                    step="retrieval",
                    name="faiss_retriever",
                    input_data={
                        "query": message,
                        "session_id": session_id,
                        "history_message_count": len(history),
                        "top_k": 3,
                    },
                    output_data={
                        "retrieval_hit": retrieval_hit,
                        "retrieved_chunk_count": len(retrieved_chunks),
                        "sources": [
                            {
                                "source": chunk.metadata.get("source"),
                                "file_name": chunk.metadata.get("file_name"),
                                "chunk_index": chunk.metadata.get("chunk_index"),
                            }
                            for chunk in retrieved_chunks
                        ],
                    },
                    latency_ms=retrieval_latency_ms,
                    success=True,
                )
            )

        except Exception as e:
            retrieval_latency_ms = duration_ms(retrieval_start)
            retrieved_chunks = []
            retrieval_hit = False

            tool_trace.append(
                build_trace_item(
                    step="retrieval",
                    name="faiss_retriever",
                    input_data={
                        "query": message,
                        "session_id": session_id,
                        "history_message_count": len(history),
                        "top_k": 3,
                    },
                    output_data={},
                    latency_ms=retrieval_latency_ms,
                    success=False,
                    error=str(e),
                )
            )

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

        question_with_history = (
            f"Conversation history:\n{history_text}\n\n"
            f"Current user question:\n{message}"
        )

        llm_start = time.time()

        try:
            answer = self._rag_chain.invoke(
                {
                    "question": question_with_history,
                    "context": retrieved_context,
                }
            )

            tool_trace.append(
                build_trace_item(
                    step="generation",
                    name="rag_chain_llm",
                    input_data={
                        "question": message,
                        "session_id": session_id,
                        "history_message_count": len(history),
                        "context_chars": len(retrieved_context),
                        "model": MODEL_NAME,
                    },
                    output_data={
                        "answer_chars": len(str(answer)),
                    },
                    latency_ms=duration_ms(llm_start),
                    success=True,
                )
            )

        except Exception as e:
            answer = (
                "Sorry, I failed to generate an answer because "
                "the LLM chain raised an error."
            )

            tool_trace.append(
                build_trace_item(
                    step="generation",
                    name="rag_chain_llm",
                    input_data={
                        "question": message,
                        "session_id": session_id,
                        "history_message_count": len(history),
                        "context_chars": len(retrieved_context),
                        "model": MODEL_NAME,
                    },
                    output_data={},
                    latency_ms=duration_ms(llm_start),
                    success=False,
                    error=str(e),
                )
            )

        self._append_history(session_id, "user", message)
        self._append_history(session_id, "assistant", str(answer))

        citations: List[Dict[str, Any]] = [
            {
                "source": chunk.metadata.get("source"),
                "file_name": chunk.metadata.get("file_name"),
                "chunk_index": chunk.metadata.get("chunk_index"),
                "snippet": chunk.content[:300],
            }
            for chunk in retrieved_chunks
        ]

        result = {
            "answer": answer,
            "metadata": {
                "request_id": request_id,
                "model": MODEL_NAME,
                "latency_ms": duration_ms(total_start),
                "session_id": session_id,
                "route": "rag",
                "router_reason": route_decision.reason,
                "router_confidence": route_decision.confidence,
                "response_type": "final",
                "top_k": 3,
                "retrieval_hit": retrieval_hit,
                "retrieved_chunk_count": len(retrieved_chunks),
                "trace_count": len(tool_trace),
                "memory_enabled": session_id is not None,
                "history_message_count_before": len(history),
                "history_message_count_after": len(self._get_history(session_id)),
            },
            "tool_trace": tool_trace,
            "citations": citations,
        }

        write_trace_log(
            {
                "event": "agent_request_completed",
                "request_id": request_id,
                "session_id": session_id,
                "message": message,
                "metadata": result["metadata"],
                "tool_trace": tool_trace,
            }
        )

        return result