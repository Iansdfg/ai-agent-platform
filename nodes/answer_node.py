"""
Answer generation node for Market Brain Agent.

Generates final answer using retrieved documents and tool results.
"""

import time
from typing import Any, Dict, List

from core.config import MODEL_NAME
from core.tracing import build_trace_item, duration_ms
from chains.rag_chain import build_rag_chain
from state.agent_state import AgentState


# Lazy initialization
_answer = None


def _get_answer_node():
    """Lazy initialization of AnswerNode."""
    global _answer
    if _answer is None:
        _answer = AnswerNode()
    return _answer


class AnswerNode:
    """Generate final answer using RAG chain."""

    def __init__(self) -> None:
        self._rag_chain = build_rag_chain()

    def invoke(self, state: AgentState) -> AgentState:
        """
        Generate final answer from message and context.
        
        Rules:
        - Use retrieved documents if available (cite as [1], [2], etc.)
        - Use tool result if available
        - Say what is missing if context is insufficient
        - Do not invent facts
        """
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

            if self._has_marketing_context(tool_result):
                answer = self._generate_marketing_content_answer(
                    message=message,
                    marketing_context=tool_result.get("output", {}),
                )
            else:
                prompt = f"""
You are Market Brain Agent.

Use the available context to answer the user.

Rules:
1. If retrieved documents are provided, cite them using [1], [2], etc.
2. If a tool result is provided, summarize the tool result clearly.
3. If the tool result contains product inventory or campaign data, use it as
   grounding context for marketing content and do not ask the user for product
   details already present in the tool result.
4. If context is insufficient, say what is missing.
5. Do not invent facts.

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
                "max_steps": state.get("max_steps", 3),
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
                    "max_steps": state.get("max_steps", 3),
                    "planner_type": state.get("planner_type"),
                    "planner_reason": state.get("planner_reason"),
                    "trace_count": len(traces),
                },
                "tool_trace": traces,
                "error": str(e),
            }

    def _sum_trace_latency(self, traces: List[Dict[str, Any]]) -> int:
        """Sum latency across all trace items."""
        total = 0
        for trace in traces:
            try:
                total += int(trace.get("latency_ms", 0))
            except (TypeError, ValueError):
                continue
        return total

    def _has_marketing_context(self, tool_result: Dict[str, Any]) -> bool:
        return (
            tool_result.get("tool_name") == "get_marketing_context"
            and bool(tool_result.get("success"))
            and bool(tool_result.get("output", {}).get("current_product_inventory"))
        )

    def _generate_marketing_content_answer(
        self,
        message: str,
        marketing_context: Dict[str, Any],
    ) -> str:
        products = marketing_context.get("current_product_inventory", [])
        campaign = marketing_context.get("active_campaign", {})

        in_stock_products = [
            product for product in products
            if product.get("inventory_status") in {"in_stock", "low_stock"}
        ]
        featured_products = in_stock_products[:2] or products[:2]

        product_lines = []
        for product in featured_products:
            benefits = product.get("benefits", [])
            benefit_text = benefits[0] if benefits else "supports everyday pet care"
            inventory_status = product.get("inventory_status", "available")
            product_lines.append(
                f"{product.get('name')} ({inventory_status}): {benefit_text}"
            )

        discount = campaign.get("discount")
        cta = campaign.get("cta") or "Shop now"
        campaign_name = campaign.get("name") or "Pet Care Essentials"
        end_date = campaign.get("end_date")

        offer_sentence = (
            f"For a limited time, enjoy {discount}."
            if discount else
            "For a limited time, stock up on customer favorites."
        )
        date_sentence = f" Offer ends {end_date}." if end_date else ""
        product_sentence = " ".join(product_lines)

        return (
            f"Subject: {campaign_name} for happier, healthier pets\n\n"
            "Hi there,\n\n"
            "Give your pet care routine a fresh upgrade with practical essentials "
            f"chosen for pet owners. {product_sentence} {offer_sentence}"
            f"{date_sentence}\n\n"
            f"{cta}."
        )


def answer_node(state: AgentState) -> AgentState:
    """Answer generation node entry point."""
    return _get_answer_node().invoke(state)
