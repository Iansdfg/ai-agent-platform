"""Day 8 learning module: minimal agent orchestration with tool use.

This file is intentionally small and beginner-friendly:
- A planner agent decides which executor should handle each step.
- Two executor agents return structured outputs.
- One executor performs an explicit tool call that is easy to trace.
- A simple loop runs until the planner has no work left.

Run:
    ai-env/bin/python services/day8_orchestration.py
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Records one tool invocation so the orchestration path is visible."""

    tool_name: str
    tool_input: str
    tool_output: str


class ExecutionStep(BaseModel):
    """One planned unit of work for an executor agent."""

    step_id: str
    description: str
    executor: str


class PlannerOutput(BaseModel):
    """The planner returns a queue of structured steps."""

    objective: str
    steps: List[ExecutionStep]


class AgentResult(BaseModel):
    """Executors respond with structured output for easy downstream handling."""

    agent_name: str
    step_id: str
    summary: str
    output: str
    tool_calls: List[ToolCall] = Field(default_factory=list)


class OrchestrationResult(BaseModel):
    """Final run artifact produced by the agent loop."""

    objective: str
    plan: PlannerOutput
    steps_completed: List[AgentResult]
    final_answer: str


class LearningNotesTool:
    """A tiny local tool that stands in for search, RAG, or an API call."""

    def __init__(self) -> None:
        self._notes: Dict[str, str] = {
            "agent orchestration": (
                "Agent orchestration is the coordination layer that decides "
                "which agent should do which task and in what order."
            ),
            "tool use": (
                "Tool use means an agent leaves pure text generation and calls "
                "a function, API, retriever, or database to get grounded data."
            ),
            "planner": (
                "A planner breaks a user objective into smaller steps and "
                "routes each step to the right executor."
            ),
        }

    def run(self, query: str) -> str:
        normalized_query = query.lower().strip()
        return self._notes.get(
            normalized_query,
            "No local note found. In a real system, this could query search or RAG.",
        )


class PlannerAgent:
    """Deterministic planner used for learning before adding an LLM."""

    def create_plan(self, objective: str) -> PlannerOutput:
        steps: List[ExecutionStep] = [
            ExecutionStep(
                step_id="step-1",
                description="Explain agent orchestration using the learning notes tool.",
                executor="research_agent",
            ),
            ExecutionStep(
                step_id="step-2",
                description="Count how many executor agents are in this demo.",
                executor="math_agent",
            ),
        ]

        return PlannerOutput(objective=objective, steps=steps)


class ResearchAgent:
    """Executor that gathers grounded information by calling a tool."""

    def __init__(self, learning_notes_tool: LearningNotesTool) -> None:
        self._learning_notes_tool = learning_notes_tool

    def run(self, step: ExecutionStep) -> AgentResult:
        # The tool call is explicit so a learner can see the exact handoff.
        tool_output = self._learning_notes_tool.run("agent orchestration")
        tool_call = ToolCall(
            tool_name="learning_notes_tool",
            tool_input="agent orchestration",
            tool_output=tool_output,
        )

        return AgentResult(
            agent_name="research_agent",
            step_id=step.step_id,
            summary="Used the local learning notes tool to gather background.",
            output=tool_output,
            tool_calls=[tool_call],
        )


class MathAgent:
    """Executor that handles a small deterministic task."""

    def run(self, step: ExecutionStep) -> AgentResult:
        executor_count = 2
        return AgentResult(
            agent_name="math_agent",
            step_id=step.step_id,
            summary="Computed the number of executor agents in the demo.",
            output=f"This demo has {executor_count} executor agents.",
        )


class Day8AgentOrchestrator:
    """Simple agent loop that plans, dispatches, and collects results."""

    def __init__(self) -> None:
        learning_notes_tool = LearningNotesTool()
        self._planner = PlannerAgent()
        self._executors = {
            "research_agent": ResearchAgent(learning_notes_tool),
            "math_agent": MathAgent(),
        }

    def run(self, objective: str) -> OrchestrationResult:
        plan = self._planner.create_plan(objective)
        remaining_steps = list(plan.steps)
        completed_steps: List[AgentResult] = []

        # This loop is the orchestration engine:
        # pull the next step, route it to the right agent, store the result.
        while remaining_steps:
            next_step = remaining_steps.pop(0)
            executor = self._executors[next_step.executor]
            result = executor.run(next_step)
            completed_steps.append(result)

        final_answer = self._build_final_answer(completed_steps)
        return OrchestrationResult(
            objective=objective,
            plan=plan,
            steps_completed=completed_steps,
            final_answer=final_answer,
        )

    @staticmethod
    def _build_final_answer(completed_steps: List[AgentResult]) -> str:
        research_summary = next(
            (step.output for step in completed_steps if step.agent_name == "research_agent"),
            "",
        )
        math_summary = next(
            (step.output for step in completed_steps if step.agent_name == "math_agent"),
            "",
        )

        return f"{research_summary}\n{math_summary}"


def main() -> None:
    objective = "Teach me the basics of planner-driven agent orchestration."
    orchestrator = Day8AgentOrchestrator()
    result = orchestrator.run(objective)
    if hasattr(result, "model_dump_json"):
        print(result.model_dump_json(indent=2))
    else:
        print(result.json(indent=2))


if __name__ == "__main__":
    main()
