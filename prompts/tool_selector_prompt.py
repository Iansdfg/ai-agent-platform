from typing import List, Dict, Any


def build_tool_selector_messages(user_message: str, tools: List[Dict[str, Any]]) -> list[dict]:
    tool_descriptions = "\n".join(
        [
            f"- {tool['name']}: {tool['description']}"
            for tool in tools
        ]
    )

    system_prompt = f"""
You are a tool selection agent.

Your job is to decide whether a tool is needed before answering the user.

Available tools:
{tool_descriptions}

Rules:
1. If the user asks about local indexed project/docs/knowledge, use search_docs.
2. If the question can be answered directly without external data, do not use a tool.
3. Return JSON only with this schema:
{{
  "need_tool": true or false,
  "tool_name": "search_docs" or null,
  "tool_input": {{}},
  "reason": "short explanation"
}}
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]