from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import BaseModel


class ToolResult(BaseModel):
    success: bool
    output: Dict[str, Any]
    error: str | None = None


class BaseTool(ABC):
    name: str
    description: str

    @abstractmethod
    def run(self, tool_input: Dict[str, Any]) -> ToolResult:
        pass

    def to_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
        }