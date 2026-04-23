# AI Agent Platform

## Day 8 - Agent Orchestration

This repo now includes a minimal learning module that demonstrates a production-shaped
agent orchestration flow without a real LLM dependency.

What it shows:
- a planner agent that creates a structured plan
- two executor agents: `research_agent` and `math_agent`
- an explicit tool call through `learning_notes_tool`
- a simple agent loop that routes each step and collects structured results

Run the example:

```bash
ai-env/bin/python services/day8_orchestration.py
```

What to look for in the output:
- `plan.steps` shows how the planner decomposed the task
- `steps_completed` shows each executor result
- `tool_calls` makes the tool usage easy to trace
