from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    metadata: Dict[str, Any]
    tool_trace: List[Dict[str, Any]] = []
    citations: List[Dict[str, Any]] = []