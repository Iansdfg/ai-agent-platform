from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    metadata: Dict[str, Any]
    tool_trace: List[Any] = Field(default_factory=list)
    citations: List[Any] = Field(default_factory=list)
