"""
Tool execution node for Market Brain Agent.

Executes tools like draft creation, retrieval, and search.
"""

import re
import time
from typing import Any, Dict

from core.logging import log_event
from core.tracing import build_trace_item, duration_ms
from state.agent_state import AgentState
from tools.registry import build_default_registry


# Lazy initialization
_tool = None


def _get_tool_node():
    """Lazy initialization of ToolNode."""
    global _tool
    if _tool is None:
        _tool = ToolNode()
    return _tool


class ToolNode:
    """Tool execution and selection."""

    def __init__(self) -> None:
        self._tool_registry = build_default_registry()

    def invoke(self, state: AgentState) -> AgentState:
        """
        Select and execute tool based on message.
        
        Tool selection:
        - get_draft: if message asks get/show/read and contains draft_id
        - update_draft: if message asks update/modify/edit and contains draft_id
        - get_marketing_context: if message asks for marketing/product email or copy
        - create_draft: if message mentions draft/campaign/草稿/营销
        - search: default fallback
        """
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

            log_event(
                "eval_process_tool_completed",
                request_id=state["request_id"],
                session_id=state.get("session_id"),
                step_count=int(state.get("step_count", 0)) + 1,
                tool_name=tool_name,
                success=tool_result.success,
                latency_ms=latency_ms,
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

            log_event(
                "eval_process_tool_failed",
                request_id=state["request_id"],
                session_id=state.get("session_id"),
                step_count=int(state.get("step_count", 0)) + 1,
                tool_name=tool_name,
                latency_ms=latency_ms,
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

    def _select_tool(self, message: str) -> tuple[str, Dict[str, Any]]:
        """Select tool and prepare tool input."""
        lower = message.lower()
        draft_id = self._extract_draft_id(message)

        if self._product_faq_shipping_request(lower):
            return "search", {"query": message}

        # Tool: get_draft
        if (
            any(
                keyword in lower
                for keyword in ["get", "show", "查看", "拿", "读取"]
            )
        ) and draft_id:
            return "get_draft", {"draft_id": draft_id}

        # Tool: update_draft
        if (
            any(
                keyword in lower
                for keyword in ["update", "modify", "edit", "修改", "改"]
            )
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

        # Tool: get_marketing_context
        if self._marketing_content_generation_request(lower):
            return (
                "get_marketing_context",
                {
                    "query": message,
                    "workspace_id": "default",
                },
            )

        # Tool: create_draft
        if any(
            keyword in lower
            for keyword in ["draft", "草稿", "campaign", "营销"]
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

        # Default: search
        return "search", {"query": message}

    def _product_faq_shipping_request(self, lower_message: str) -> bool:
        """Detect product FAQ/shipping requests that should not mutate drafts."""
        product_faq_terms = [
            "product faq",
            "order tracking",
            "standard shipping",
            "expedited shipping",
            "tracking is provided",
        ]
        shipping_terms = [
            "shipping",
            "ships",
            "order ships",
            "tracking",
            "checkout",
        ]

        return any(term in lower_message for term in product_faq_terms + shipping_terms)

    def _marketing_content_generation_request(self, lower_message: str) -> bool:
        """Detect content generation that needs current product/campaign context."""
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

    def _extract_draft_id(self, message: str) -> str | None:
        """Extract draft ID from message."""
        uuid_match = re.search(
            r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-"
            r"[a-f0-9]{4}-[a-f0-9]{12}\b",
            message,
            re.IGNORECASE,
        )

        if uuid_match:
            return uuid_match.group(0)

        explicit_match = re.search(
            r"\b(?:draft_id|draft id|draft-id)\s*[:=]?\s*([a-zA-Z0-9_-]+)\b",
            message,
            re.IGNORECASE,
        )

        if explicit_match:
            return explicit_match.group(1)

        return None


def tool_node(state: AgentState) -> AgentState:
    """Tool execution node entry point."""
    return _get_tool_node().invoke(state)
