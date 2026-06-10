"""
Router node for Market Brain Agent.

Determines whether a query belongs to Market Brain domain or should be handled directly.
"""

from core.logging import log_event
from core.tracing import write_trace_log
from state.agent_state import AgentState


AGENT_KEYWORDS = [
    "market brain",
    "rag",
    "campaign",
    "draft",
    "document",
    "docs",
    "policy",
    "marketing",
    "草稿",
    "营销",
    "文档",
]

DIRECT_KEYWORDS = [
    "weather",
    "stock price",
    "stock",
    "nba",
    "restaurant",
    "天气",
    "股票",
    "比赛",
    "餐厅",
]


def router_node(state: AgentState) -> AgentState:
    """
    Route the query to either agent mode or direct mode.
    
    Agent mode: Market Brain domain queries requiring multi-step reasoning.
    Direct mode: Out-of-domain queries with canned response.
    """
    message = state["message"].lower()

    # Check for direct keywords (out-of-domain)
    if any(word in message for word in DIRECT_KEYWORDS):
        route = "direct"
    # Check for agent keywords or default to agent
    else:
        route = "agent"

    write_trace_log(
        {
            "event": "graph_router_decision",
            "request_id": state["request_id"],
            "session_id": state.get("session_id"),
            "message": state["message"],
            "route": route,
        }
    )

    log_event(
        "eval_process_router_completed",
        request_id=state["request_id"],
        session_id=state.get("session_id"),
        route=route,
    )

    return {
        **state,
        "route": route,
    }
