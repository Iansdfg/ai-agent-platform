import json
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class AgentDecision(BaseModel):
    action: Literal["retrieve", "tool", "answer", "stop"]
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


DECISION_PROMPT = """
You are a hybrid multi-step agent planner.

Choose exactly one action:
- retrieve: use RAG/document retrieval
- tool: call an allowed tool
- answer: enough context exists, produce final answer
- stop: unsafe, unrelated, or impossible request

Allowed tools:
{available_tools}

Current state:
{state}

User message:
{message}

Return ONLY valid JSON:
{{
  "action": "retrieve|tool|answer|stop",
  "tool_name": null,
  "tool_args": {{}},
  "reason": "short reason"
}}
"""


def decide_next_step(llm_service, message: str, state: Dict[str, Any], available_tools: list[str]) -> AgentDecision:
    prompt = DECISION_PROMPT.format(
        message=message,
        state=json.dumps(state, ensure_ascii=False),
        available_tools=", ".join(available_tools),
    )

    raw = llm_service.generate_text(prompt)

    try:
        decision = AgentDecision(**json.loads(raw))
    except Exception:
        return AgentDecision(
            action="answer",
            reason="LLM returned invalid JSON. Fallback to final answer.",
        )

    if decision.action == "tool" and decision.tool_name not in available_tools:
        return AgentDecision(
            action="stop",
            reason=f"Tool {decision.tool_name} is not allowed.",
        )

    return decision