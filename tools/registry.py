from typing import Dict, Any

from tools.search_docs import SearchDocsTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools = {
            "search_docs": SearchDocsTool(),
        }

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in self._tools.values()
        ]

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return self._tools[tool_name].run(**tool_input)