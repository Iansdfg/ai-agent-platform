import json
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from core.config import MODEL_NAME, OPENAI_API_KEY
from prompts.tool_selector_prompt import build_tool_selector_messages
from schemas import ToolDecision


class LLMService:
    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model=MODEL_NAME,
            api_key=OPENAI_API_KEY,
            temperature=0,
        )

    def decide_tool(self, user_message: str, tools: list[dict]) -> ToolDecision:
        messages = build_tool_selector_messages(user_message, tools)
        response = self._llm.invoke(messages)
        content = str(response.content).strip()

        try:
            data = json.loads(content)
            return ToolDecision(**data)
        except Exception:
            return ToolDecision(
                need_tool=False,
                tool_name=None,
                tool_input={},
                reason="fallback: invalid tool decision json",
            )

    def generate_response(
        self,
        user_message: str,
        retrieved_context: Optional[str] = None,
    ) -> str:
        messages = [
            SystemMessage(
                content=(
                    "You are a helpful AI assistant. "
                    "Use the retrieved context when it is relevant. "
                    "If the context does not contain enough information, say so honestly."
                )
            ),
            HumanMessage(
                content=(
                    f"User question:\n{user_message}\n\n"
                    f"Retrieved context:\n{retrieved_context or 'No retrieved context.'}"
                )
            ),
        ]

        response = self._llm.invoke(messages)
        return str(response.content)

    def generate_final_answer(
        self,
        user_message: str,
        retrieved_context: Optional[str] = None,
        tool_result: Optional[str] = None,
    ) -> str:
        context_parts = []

        if retrieved_context:
            context_parts.append(f"Retrieved context:\n{retrieved_context}")

        if tool_result:
            context_parts.append(f"Tool result:\n{tool_result}")

        combined_context = "\n\n".join(context_parts) or "No extra context."

        return self.generate_response(
            user_message=user_message,
            retrieved_context=combined_context,
        )