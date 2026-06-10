"""
Direct response node for Market Brain Agent.

Handles out-of-domain queries with canned response.
"""

import time

from core.config import MODEL_NAME
from core.logging import log_event
from core.tracing import duration_ms
from state.agent_state import AgentState


def direct_node(state: AgentState) -> AgentState:
    """
    Return safe canned response for out-of-domain queries.
    
    This node handles queries that don't belong to Market Brain domain.
    """
    start = time.time()

    answer = (
        "I can help with Market Brain tasks such as RAG questions, "
        "marketing drafts, campaign content, and draft lookup/update. "
        "Please ask a Market Brain related question."
    )

    latency_ms = duration_ms(start)

    log_event(
        "eval_process_direct_completed",
        request_id=state["request_id"],
        session_id=state.get("session_id"),
        step_count=state.get("step_count", 0),
        latency_ms=latency_ms,
    )

    return {
        **state,
        "answer": answer,
        "metadata": {
            "request_id": state["request_id"],
            "model": MODEL_NAME,
            "latency_ms": latency_ms,
            "session_id": state.get("session_id"),
            "route": "langgraph_direct",
            "graph_node": "direct",
            "response_type": "final",
            "step_count": state.get("step_count", 0),
            "max_steps": state.get("max_steps", 3),
            "trace_count": 0,
            "token_usage": {"input": 0, "output": 0},
        },
        "tool_trace": [],
        "citations": [],
    }
