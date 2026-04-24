from typing import Dict, List

from tools.base import BaseTool, ToolResult
from tools.learning_notes_tool import LearningNotesTool
from tools.search_tool import SearchTool
from tools.http_tool import HttpTool

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, tool_name: str) -> BaseTool:
        if tool_name not in self._tools:
            raise ValueError(f"Tool not found: {tool_name}")
        return self._tools[tool_name]

    def list_tools(self) -> List[dict]:
        return [tool.to_schema() for tool in self._tools.values()]

    def execute(self, tool_name: str, tool_input: dict) -> ToolResult:
        tool = self.get(tool_name)
        return tool.run(tool_input)


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(LearningNotesTool())
    registry.register(SearchTool())
    registry.register(HttpTool())
    return registry