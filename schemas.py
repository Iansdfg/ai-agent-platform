from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    metadata: Dict[str, Any]
    tool_trace: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)


class ToolDecision(BaseModel):
    need_tool: bool
    tool_name: Optional[str] = None
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class ToolTraceItem(BaseModel):
    tool_name: str
    tool_input: Dict[str, Any] = Field(default_factory=dict)
    tool_output: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = 0
    success: bool = True
    error: Optional[str] = None


class RouteDecision(BaseModel):
    route: str  # "rag" | "tool" | "direct"
    reason: str = ""
    confidence: float = 0.0
    matched_rules: List[str] = Field(default_factory=list)
    tool_name: Optional[str] = None
    tool_input: Dict[str, Any] = Field(default_factory=dict)