from typing import Any, Dict

from tools.base import BaseTool, ToolResult


class LearningNotesTool(BaseTool):
    name = "learning_notes"
    description = "Search local learning notes about agent, RAG, and tool use concepts."

    def __init__(self) -> None:
        self._notes = {
            "agent orchestration": (
                "Agent orchestration is the coordination layer that decides "
                "which agent or tool should handle each task and in what order."
            ),
            "tool use": (
                "Tool use means an agent calls an external function, API, retriever, "
                "database, or service instead of only generating text."
            ),
            "rag": (
                "RAG retrieves relevant external context first, then injects that "
                "context into the LLM prompt to produce a grounded answer."
            ),
        }

    def run(self, tool_input: Dict[str, Any]) -> ToolResult:
        query = str(tool_input.get("query", "")).lower().strip()

        if not query:
            return ToolResult(
                success=False,
                output={},
                error="Missing required input: query",
            )

        result = self._notes.get(
            query,
            "No local note found. In a real system, this could call RAG or search.",
        )

        return ToolResult(
            success=True,
            output={
                "query": query,
                "result": result,
            },
        )