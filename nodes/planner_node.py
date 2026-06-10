"""
Planner node for Market Brain Agent.

Implements hybrid planning: rule-based first, LLM fallback for ambiguous cases.
"""

import json
import time
from typing import Any, Dict, List, Optional

from langchain_openai import ChatOpenAI

from core.config import MODEL_NAME
from core.tracing import build_trace_item, duration_ms
from state.agent_state import AgentState


MAX_STEPS = 3
ALLOWED_ACTIONS = {"retrieval", "tool", "answer"}


# Lazy initialization
_planner = None


def _get_planner_node():
    """Lazy initialization of PlannerNode."""
    global _planner
    if _planner is None:
        _planner = PlannerNode()
    return _planner


class PlannerNode:
    """Hybrid planner for multi-step agent reasoning."""

    def __init__(self) -> None:
        self._llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

    def invoke(self, state: AgentState) -> AgentState:
        """
        Plan the next action based on message, step count, and available context.
        
        Returns updated state with next_action, planner_type, and planner_reason.
        """
        start = time.time()

        step_count = int(state.get("step_count", 0))
        max_steps = int(state.get("max_steps", MAX_STEPS))
        message = state["message"]

        has_documents = bool(state.get("documents"))
        has_tool_result = bool(state.get("tool_result"))

        # Rule 1: Max steps reached
        if step_count >= max_steps:
            next_action = "answer"
            reason = "max_steps_reached"
            planner_type = "rule"

        # Rule 2: High confidence tool request
        elif self._high_confidence_tool_request(message) and not has_tool_result:
            next_action = "tool"
            reason = "high_confidence_tool_request"
            planner_type = "rule"

        # Rule 3: High confidence retrieval request
        elif self._high_confidence_retrieval_request(message) and not has_documents:
            next_action = "retrieval"
            reason = "high_confidence_retrieval_request"
            planner_type = "rule"

        # Fallback: LLM planner
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

            # Validate LLM action
            if next_action not in ALLOWED_ACTIONS:
                next_action = "answer"
                reason = "invalid_llm_action_fallback_to_answer"

            # Prevent duplicate retrieval
            if next_action == "retrieval" and has_documents:
                next_action = "answer"
                reason = "llm_requested_duplicate_retrieval_fallback_to_answer"

            # Prevent duplicate tool execution
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
                "intermediate_results_count": len(state.get("intermediate_results", [])),
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

    def _high_confidence_tool_request(self, message: str) -> bool:
        """Detect high-confidence tool requests."""
        lower = message.lower()
        keywords = [
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
        return (
            any(keyword in lower for keyword in keywords)
            or self._marketing_content_generation_request(lower)
        )

    def _marketing_content_generation_request(self, lower_message: str) -> bool:
        """Detect requests that need current marketing/product context."""
        generation_keywords = [
            "promotional email",
            "marketing email",
            "promo copy",
            "product copy",
            "write an email about our products",
            "email for pet owners",
            "pet owners",
        ]
        product_context_keywords = [
            "our products",
            "product",
            "products",
            "inventory",
            "campaign",
            "discount",
            "cta",
        ]

        if any(keyword in lower_message for keyword in generation_keywords):
            return True

        asks_to_write = any(
            keyword in lower_message
            for keyword in ["write", "draft", "generate", "create"]
        )
        mentions_email_or_copy = any(
            keyword in lower_message
            for keyword in ["email", "copy", "content", "promotion", "promo"]
        )
        mentions_business_context = any(
            keyword in lower_message for keyword in product_context_keywords
        )

        return asks_to_write and mentions_email_or_copy and mentions_business_context

    def _high_confidence_retrieval_request(self, message: str) -> bool:
        """Detect high-confidence retrieval requests."""
        lower = message.lower()
        keywords = [
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
        return any(keyword in lower for keyword in keywords)

    def _llm_plan_next_action(
        self,
        message: str,
        step_count: int,
        max_steps: int,
        has_documents: bool,
        has_tool_result: bool,
        intermediate_results: list,
    ) -> Dict[str, Any]:
        """Use LLM to decide next action when rules are uncertain."""
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
            response = self._llm.invoke(prompt)
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
        """Remove markdown code blocks from JSON."""
        cleaned = text.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned.removeprefix("```json").strip()

        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```").strip()

        if cleaned.endswith("```"):
            cleaned = cleaned.removesuffix("```").strip()

        return cleaned


def planner_node(state: AgentState) -> AgentState:
    """Planner node entry point."""
    return _get_planner_node().invoke(state)
