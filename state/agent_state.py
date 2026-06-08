from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    """
    Represents the state of the Market Brain Agent throughout its execution.
    
    Fields:
    - message: User input message
    - request_id: Unique request identifier
    - session_id: Optional session identifier
    - route: Router decision (agent or direct)
    - next_action: Planner decision (retrieval, tool, answer)
    - step_count: Current execution step
    - max_steps: Maximum allowed steps
    - planner_type: Type of planner used (rule or llm)
    - planner_reason: Reason for planner decision
    - documents: Retrieved documents
    - retrieved_context: Formatted retrieved context
    - tool_result: Result from tool execution
    - intermediate_results: Step-by-step results
    - answer: Final generated answer
    - metadata: Response metadata
    - tool_trace: Detailed execution trace
    - citations: Document citations
    - error: Optional error message
    """
    
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
