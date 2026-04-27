import json
import re
import time
from typing import Any, Dict, List

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from chains.rag_chain import build_rag_chain
from core.config import MODEL_NAME
from core.tracing import build_trace_item, duration_ms, write_trace_log
from graph_state import AgentState
from rag.retriever import Retriever
from tools.registry import build_default_registry


MAX_STEPS = 3
ALLOWED_ACTIONS = {"retrieval", "tool", "answer"}


class AgentGraph:
    def __init__(self) -> None:
        self._retriever = Retriever()
        self._rag_chain = build_rag_chain()
        self._tool_registry = build_default_registry()

        # Hybrid planner: use LLM only when rules are not confident.
        self._planner_llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

        self._graph = self._build_graph()

    def invoke(
        self,
        message: str,
        request_id: str,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        result = self._graph.invoke(
            {
                "message": message,
                "request_id": request_id,
                "session_id": session_id,
                "route": "",
                "next_action": "",
                "step_count": 0,
                "max_steps": MAX_STEPS,
                "planner_type": "",
                "planner_reason": "",
                "documents": [],
                "retrieved_context": "",
                "tool_result": {},
                "intermediate_results": [],
                "tool_trace": [],
                "citations": [],
            }
        )

        return {
            "answer": result.get("answer", ""),
            "metadata": result.get("metadata", {}),
            "tool_trace": result.get("tool_trace", []),
            "citations": result.get("citations", []),
        }

    def _build_graph(self):
        graph = StateGraph(AgentState)

        graph.add_node("router", self._router_node)
        graph.add_node("planner", self._planner_node)
        graph.add_node("retrieval", self._retrieval_node)
        graph.add_node("tool", self._tool_node)
        graph.add_node("answer", self._answer_node)
        graph.add_node("direct", self._direct_node)

        graph.set_entry_point("router")

        graph.add_conditional_edges(
            "router",
            self._route_after_router,
            {
                "agent": "planner",
                "direct": "direct",
            },
        )

        graph.add_conditional_edges(
            "planner",
            self._route_after_planner,
            {
                "retrieval": "retrieval",
                "tool": "tool",
                "answer": "answer",
            },
        )

        graph.add_edge("retrieval", "planner")
        graph.add_edge("tool", "planner")
        graph.add_edge("answer", END)
        graph.add_edge("direct", END)

        return graph.compile()

    def _router_node(self, state: AgentState) -> AgentState:
        message = state["message"].lower()

        if any(
            word in message
            for word in [
                "weather",
                "stock price",
                "nba",
                "restaurant",
                "天气",
                "股票",
                "比赛",
                "餐厅",
            ]
        ):
            route = "direct"
        else:
            route = "agent"

        write_trace_log(
            {
                "event": "graph_router_decision",
                "request_id": state["request_id"],
                "session_id": state.get("session_id"),
                "message": state["message"],
                "route": route,
            }
        )

        return {
            **state,
            "route": route,
        }

    def _route_after_router(self, state: AgentState) -> str:
        return state.get("route", "agent")

    def _planner_node(self, state: AgentState) -> AgentState:
        start = time.time()

        step_count = int(state.get("step_count", 0))
        max_steps = int(state.get("max_steps", MAX_STEPS))
        message = state["message"]

        has_documents = bool(state.get("documents"))
        has_tool_result = bool(state.get("tool_result"))

        if step_count >= max_steps:
            next_action = "answer"
            reason = "max_steps_reached"
            planner_type = "rule"

        elif self._high_confidence_tool_request(message) and not has_tool_result:
            next_action = "tool"
            reason = "high_confidence_tool_request"
            planner_type = "rule"

        elif self._high_confidence_retrieval_request(message) and not has_documents:
            next_action = "retrieval"
            reason = "high_confidence_retrieval_request"
            planner_type = "rule"

        else:
            decision = self._llm_plan_next_action(
                message=message,
                step_count=step_count,
                max_steps=max_steps,
                has_documents=has_documents,
                has_tool_result=has_tool_result,
                intermediate_results=state.get("intermediate_results", []),
            )

            next_action = decision.get("next_action", "answer")
            reason = decision.get("reason", "llm_planner_decision")
            planner_type = "llm"

            if next_action not in ALLOWED_ACTIONS:
                next_action = "answer"
                reason = "invalid_llm_action_fallback_to_answer"

            if next_action == "retrieval" and has_documents:
                next_action = "answer"
                reason = "llm_requested_duplicate_retrieval_fallback_to_answer"

            if next_action == "tool" and has_tool_result:
                next_action = "answer"
                reason = "llm_requested_duplicate_tool_fallback_to_answer"

        latency_ms = duration_ms(start)

        trace_item = build_trace_item(
            step="planning",
            name="hybrid_planner_node",
            input_data={
                "message": message,
                "step_count": step_count,
                "max_steps": max_steps,
                "has_documents": has_documents,
                "has_tool_result": has_tool_result,
                "intermediate_results_count": len(
                    state.get("intermediate_results", [])
                ),
            },
            output_data={
                "next_action": next_action,
                "reason": reason,
                "planner_type": planner_type,
            },
            latency_ms=latency_ms,
            success=True,
        )

        return {
            **state,
            "next_action": next_action,
            "planner_type": planner_type,
            "planner_reason": reason,
            "tool_trace": state.get("tool_trace", []) + [trace_item],
        }

    def _route_after_planner(self, state: AgentState) -> str:
        return state.get("next_action", "answer")

    def _retrieval_node(self, state: AgentState) -> AgentState:
        start = time.time()
        message = state["message"]
        session_id = state.get("session_id")

        try:
            retrieved_chunks = self._retriever.retrieve(message, top_k=6)

            seen = set()
            unique_chunks = []

            for chunk in retrieved_chunks:
                key = chunk.content.strip()
                if key not in seen:
                    seen.add(key)
                    unique_chunks.append(chunk)

            unique_chunks = unique_chunks[:3]

            latency_ms = duration_ms(start)
            retrieval_hit = len(unique_chunks) > 0

            documents: List[Dict[str, Any]] = [
                {
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                }
                for chunk in unique_chunks
            ]

            citations: List[Dict[str, Any]] = [
                {
                    "source": chunk.metadata.get("source"),
                    "file_name": chunk.metadata.get("file_name"),
                    "chunk_index": chunk.metadata.get("chunk_index"),
                    "snippet": chunk.content[:300],
                }
                for chunk in unique_chunks
            ]

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

    def _tool_node(self, state: AgentState) -> AgentState:
        start = time.time()
        message = state["message"]

        tool_name, tool_input = self._select_tool(message)

        try:
            tool_result = self._tool_registry.execute(tool_name, tool_input)
            latency_ms = duration_ms(start)

            normalized_tool_result = {
                "tool_name": tool_name,
                "success": tool_result.success,
                "output": tool_result.output,
                "error": tool_result.error,
            }

            trace_item = build_trace_item(
                step="tool_execution",
                name=tool_name,
                input_data=tool_input,
                output_data=normalized_tool_result,
                latency_ms=latency_ms,
                success=tool_result.success,
                error=tool_result.error,
            )

            return {
                **state,
                "step_count": int(state.get("step_count", 0)) + 1,
                "tool_result": normalized_tool_result,
                "intermediate_results": state.get("intermediate_results", [])
                + [{"step": "tool", "result": normalized_tool_result}],
                "tool_trace": state.get("tool_trace", []) + [trace_item],
            }

        except Exception as e:
            latency_ms = duration_ms(start)

            normalized_tool_result = {
                "tool_name": tool_name,
                "success": False,
                "output": {},
                "error": str(e),
            }

            trace_item = build_trace_item(
                step="tool_execution",
                name=tool_name,
                input_data=tool_input,
                output_data=normalized_tool_result,
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )

            return {
                **state,
                "step_count": int(state.get("step_count", 0)) + 1,
                "tool_result": normalized_tool_result,
                "intermediate_results": state.get("intermediate_results", [])
                + [{"step": "tool", "result": normalized_tool_result}],
                "tool_trace": state.get("tool_trace", []) + [trace_item],
                "error": str(e),
            }

    def _answer_node(self, state: AgentState) -> AgentState:
        start = time.time()
        message = state["message"]

        try:
            docs = state.get("documents", [])
            tool_result = state.get("tool_result", {})

            context_parts = []

            if docs:
                context_parts.append("Retrieved documents:")
                context_parts.append(state.get("retrieved_context", ""))

            if tool_result:
                context_parts.append("Tool result:")
                context_parts.append(str(tool_result))

            if not context_parts:
                context_parts.append(
                    "No tool result or retrieved document context is available."
                )

            context = "\n\n".join(context_parts)

            prompt = f"""
You are Market Brain Agent.

Use the available context to answer the user.

Rules:
1. If retrieved documents are provided, cite them using [1], [2], etc.
2. If a tool result is provided, summarize the tool result clearly.
3. If context is insufficient, say what is missing.
4. Do not invent facts.

User question:
{message}

Context:
{context}
"""

            answer = self._rag_chain.invoke(
                {
                    "question": prompt,
                    "context": context,
                }
            )

            latency_ms = duration_ms(start)

            trace_item = build_trace_item(
                step="generation",
                name="answer_node",
                input_data={
                    "question": message,
                    "model": MODEL_NAME,
                    "step_count": state.get("step_count", 0),
                    "has_documents": bool(docs),
                    "has_tool_result": bool(tool_result),
                    "planner_type": state.get("planner_type"),
                    "planner_reason": state.get("planner_reason"),
                },
                output_data={
                    "answer_chars": len(str(answer)),
                },
                latency_ms=latency_ms,
                success=True,
            )

            traces = state.get("tool_trace", []) + [trace_item]

            metadata = {
                "request_id": state["request_id"],
                "model": MODEL_NAME,
                "latency_ms": self._sum_trace_latency(traces),
                "session_id": state.get("session_id"),
                "route": "langgraph_hybrid_multistep_agent",
                "graph_node": "answer",
                "response_type": "final",
                "step_count": state.get("step_count", 0),
                "max_steps": state.get("max_steps", MAX_STEPS),
                "next_action": state.get("next_action"),
                "planner_type": state.get("planner_type"),
                "planner_reason": state.get("planner_reason"),
                "retrieved_chunk_count": len(docs),
                "retrieval_hit": len(docs) > 0,
                "has_tool_result": bool(tool_result),
                "trace_count": len(traces),
            }

            return {
                **state,
                "answer": str(answer),
                "metadata": metadata,
                "tool_trace": traces,
            }

        except Exception as e:
            latency_ms = duration_ms(start)

            trace_item = build_trace_item(
                step="generation",
                name="answer_node",
                input_data={
                    "question": message,
                    "model": MODEL_NAME,
                },
                output_data={},
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )

            traces = state.get("tool_trace", []) + [trace_item]

            return {
                **state,
                "answer": "Sorry, I failed to generate the final answer.",
                "metadata": {
                    "request_id": state["request_id"],
                    "model": MODEL_NAME,
                    "latency_ms": self._sum_trace_latency(traces),
                    "session_id": state.get("session_id"),
                    "route": "langgraph_hybrid_multistep_agent",
                    "graph_node": "answer",
                    "response_type": "final",
                    "step_count": state.get("step_count", 0),
                    "max_steps": state.get("max_steps", MAX_STEPS),
                    "planner_type": state.get("planner_type"),
                    "planner_reason": state.get("planner_reason"),
                    "trace_count": len(traces),
                },
                "tool_trace": traces,
                "error": str(e),
            }

    def _direct_node(self, state: AgentState) -> AgentState:
        start = time.time()

        answer = (
            "I can help with Market Brain tasks such as RAG questions, "
            "marketing drafts, campaign content, and draft lookup/update. "
            "Please ask a Market Brain related question."
        )

        latency_ms = duration_ms(start)

        return {
            **state,
            "answer": answer,
            "metadata": {
                "request_id": state["request_id"],
                "model": MODEL_NAME,
                "latency_ms": latency_ms,
                "session_id": state.get("session_id"),
                "route": "langgraph_direct",
                "graph_node": "direct",
                "response_type": "final",
                "step_count": state.get("step_count", 0),
                "max_steps": state.get("max_steps", MAX_STEPS),
                "trace_count": 0,
            },
            "tool_trace": [],
            "citations": [],
        }

    def _high_confidence_tool_request(self, message: str) -> bool:
        lower = message.lower()

        return any(
            keyword in lower
            for keyword in [
                "create draft",
                "update draft",
                "get draft",
                "edit draft",
                "save draft",
                "create campaign",
                "generate campaign",
                "生成草稿",
                "创建草稿",
                "修改草稿",
                "查看草稿",
                "生成营销",
            ]
        )

    def _high_confidence_retrieval_request(self, message: str) -> bool:
        lower = message.lower()

        return any(
            keyword in lower
            for keyword in [
                "explain from docs",
                "according to docs",
                "based on documents",
                "what does the doc say",
                "policy",
                "documentation",
                "根据文档",
                "文档里",
                "解释一下",
            ]
        )

    def _llm_plan_next_action(
        self,
        message: str,
        step_count: int,
        max_steps: int,
        has_documents: bool,
        has_tool_result: bool,
        intermediate_results: list,
    ) -> Dict[str, Any]:
        prompt = f"""
You are the planner for Market Brain Agent.

Your job is to decide the next action.

Allowed actions:
- "retrieval": use this when the agent needs project documents, policies, RAG context, or knowledge lookup.
- "tool": use this when the agent needs to create, get, update, save, or operate on marketing drafts/campaign artifacts.
- "answer": use this when enough context/tool result exists or the request can be answered directly.

Rules:
1. Return ONLY valid JSON.
2. Do not include markdown.
3. Do not choose retrieval if has_documents is true.
4. Do not choose tool if has_tool_result is true.
5. If step_count >= max_steps, choose answer.
6. If the request is compound, choose the missing step first.
7. Allowed next_action values are only: retrieval, tool, answer.

Current state:
- user_message: {message}
- step_count: {step_count}
- max_steps: {max_steps}
- has_documents: {has_documents}
- has_tool_result: {has_tool_result}
- intermediate_results: {intermediate_results}

Return JSON format:
{{
  "next_action": "retrieval",
  "reason": "short reason"
}}
"""

        try:
            response = self._planner_llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            content = self._strip_markdown_json(content)

            decision = json.loads(content)

            return {
                "next_action": decision.get("next_action", "answer"),
                "reason": decision.get("reason", "llm_planner_decision"),
            }

        except Exception as e:
            return {
                "next_action": "answer",
                "reason": f"llm_planner_failed_fallback_to_answer: {str(e)}",
            }

    def _strip_markdown_json(self, text: str) -> str:
        cleaned = text.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned.removeprefix("```json").strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```").strip()

        if cleaned.endswith("```"):
            cleaned = cleaned.removesuffix("```").strip()

        return cleaned

    def _select_tool(self, message: str) -> tuple[str, Dict[str, Any]]:
        lower = message.lower()
        draft_id = self._extract_draft_id(message)

        if (
            "get" in lower
            or "show" in lower
            or "查看" in lower
            or "拿" in lower
            or "读取" in lower
        ) and draft_id:
            return "get_draft", {"draft_id": draft_id}

        if (
            "update" in lower
            or "modify" in lower
            or "edit" in lower
            or "修改" in lower
            or "改" in lower
        ) and draft_id:
            return (
                "update_draft",
                {
                    "draft_id": draft_id,
                    "new_content": message,
                    "updated_by": "user",
                    "base_version": 1,
                    "edit_instruction": message,
                },
            )

        if (
            "draft" in lower
            or "草稿" in lower
            or "campaign" in lower
            or "营销" in lower
        ):
            return (
                "create_draft",
                {
                    "content": message,
                    "created_by": "user",
                    "workspace_id": "default",
                    "title": "Market Brain Draft",
                },
            )

        return "search", {"query": message}

    def _extract_draft_id(self, message: str) -> str | None:
        uuid_match = re.search(
            r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-"
            r"[a-f0-9]{4}-[a-f0-9]{12}\b",
            message,
            re.IGNORECASE,
        )

        if uuid_match:
            return uuid_match.group(0)

        simple_match = re.search(r"\bdraft[_\s-]?([a-zA-Z0-9_-]+)\b", message)

        if simple_match:
            return simple_match.group(1)

        return None

    def _sum_trace_latency(self, traces: List[Dict[str, Any]]) -> int:
        total = 0
        for trace in traces:
            try:
                total += int(trace.get("latency_ms", 0))
            except (TypeError, ValueError):
                continue
        return total


agent_graph = AgentGraph()