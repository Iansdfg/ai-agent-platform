from typing import Any, Dict

from tools.base import BaseTool, ToolResult


class SearchTool(BaseTool):
    name = "search"
    description = "Search local knowledge base for simple keyword matches."

    def __init__(self) -> None:
        self._documents = [
            {
                "title": "RAG",
                "content": "RAG retrieves relevant documents before calling the LLM.",
            },
            {
                "title": "Agent",
                "content": "An agent can reason, choose tools, execute actions, and produce answers.",
            },
            {
                "title": "Tool Registry",
                "content": "A tool registry lets the agent discover and execute tools by name.",
            },
        ]

    def run(self, tool_input: Dict[str, Any]) -> ToolResult:
        query = str(tool_input.get("query", "")).lower().strip()

        if not query:
            return ToolResult(success=False, output={}, error="Missing query")

        matches = [
            doc for doc in self._documents
            if query in doc["title"].lower() or query in doc["content"].lower()
        ]

        return ToolResult(
            success=True,
            output={
                "query": query,
                "matches": matches,
                "count": len(matches),
            },
        )