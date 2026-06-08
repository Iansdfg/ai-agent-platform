"""
Tool execution node for Market Brain Agent.

Executes tools like draft creation, retrieval, and search.
"""

import re
import time
from typing import Any, Dict

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

    def _select_tool(self, message: str) -> tuple[str, Dict[str, Any]]:
        """Select tool and prepare tool input."""
        lower = message.lower()
        draft_id = self._extract_draft_id(message)

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

    def _extract_draft_id(self, message: str) -> str | None:
        """Extract draft ID from message."""
        # Try to find UUID
        uuid_match = re.search(
            r"\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-"
            r"[a-f0-9]{4}-[a-f0-9]{12}\b",
            message,
            re.IGNORECASE,
        )

        if uuid_match:
            return uuid_match.group(0)

        # Try to find simple draft identifier
        simple_match = re.search(r"\bdraft[_\s-]?([a-zA-Z0-9_-]+)\b", message)

        if simple_match:
            return simple_match.group(1)

        return None


def tool_node(state: AgentState) -> AgentState:
    """Tool execution node entry point."""
    return _get_tool_node().invoke(state)
