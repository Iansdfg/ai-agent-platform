from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    message: str
    request_id: str
    session_id: Optional[str]

    route: str
    next_action: str

    step_count: int
    max_steps: int

    planner_type: str
    planner_reason: str

    documents: List[Dict[str, Any]]
    retrieved_context: str
    tool_result: Dict[str, Any]
    intermediate_results: List[Dict[str, Any]]

    answer: str
    metadata: Dict[str, Any]
    tool_trace: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]

    error: Optional[str]