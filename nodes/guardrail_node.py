"""
Guardrail node for Market Brain Agent.

Validates and enforces safety constraints on planner decisions.
"""

import time

from core.tracing import build_trace_item, duration_ms
from state.agent_state import AgentState


ALLOWED_ACTIONS = {"retrieval", "tool", "answer"}
MAX_STEPS = 3


def guardrail_node(state: AgentState) -> AgentState:
    """
    Validate and enforce guardrails on planner decision.
    
    Responsibilities:
    - Validate next_action is one of retrieval/tool/answer
    - Enforce max_steps limit
    - Prevent duplicate retrieval when documents exist
    - Prevent duplicate tool execution when tool_result exists
    """
    start = time.time()

    next_action = state.get("next_action", "answer")
    step_count = int(state.get("step_count", 0))
    max_steps = int(state.get("max_steps", MAX_STEPS))
    has_documents = bool(state.get("documents"))
    has_tool_result = bool(state.get("tool_result"))

    original_action = next_action
    guardrail_triggered = False
    violation_reason = ""

    # Check 1: Validate next_action is allowed
    if next_action not in ALLOWED_ACTIONS:
        next_action = "answer"
        guardrail_triggered = True
        violation_reason = f"invalid_action_{original_action}"

    # Check 2: Enforce max_steps
    if step_count >= max_steps:
        next_action = "answer"
        guardrail_triggered = True
        violation_reason = "max_steps_reached"

    # Check 3: Prevent duplicate retrieval
    if next_action == "retrieval" and has_documents:
        next_action = "answer"
        guardrail_triggered = True
        violation_reason = "duplicate_retrieval_prevention"

    # Check 4: Prevent duplicate tool execution
    if next_action == "tool" and has_tool_result:
        next_action = "answer"
        guardrail_triggered = True
        violation_reason = "duplicate_tool_execution_prevention"

    latency_ms = duration_ms(start)

    trace_item = build_trace_item(
        step="guardrail",
        name="action_guardrail",
        input_data={
            "next_action": original_action,
            "step_count": step_count,
            "max_steps": max_steps,
            "has_documents": has_documents,
            "has_tool_result": has_tool_result,
        },
        output_data={
            "next_action": next_action,
            "guardrail_triggered": guardrail_triggered,
            "violation_reason": violation_reason,
        },
        latency_ms=latency_ms,
        success=True,
    )

    return {
        **state,
        "next_action": next_action,
        "tool_trace": state.get("tool_trace", []) + [trace_item],
    }
