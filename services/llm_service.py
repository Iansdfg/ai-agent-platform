import json

from langchain_openai import ChatOpenAI

from core.config import MODEL_NAME, OPENAI_API_KEY
from prompts.chat_prompt import build_chat_prompt
from prompts.tool_selector_prompt import build_tool_selector_messages
from schemas import ToolDecision


class LLMService:
    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model=MODEL_NAME,
            api_key=OPENAI_API_KEY,
            temperature=0
        )

    def decide_tool(self, user_message: str, tools: list[dict]) -> ToolDecision:
        messages = build_tool_selector_messages(user_message, tools)
        response = self._llm.invoke(messages)
        content = response.content.strip()

        try:
            data = json.loads(content)
            return ToolDecision(**data)
        except Exception:
            # fallback: if parsing fails, do direct answer path
            return ToolDecision(
                need_tool=False,
                tool_name=None,
                tool_input={},
                reason="fallback: invalid tool decision json"
            )

    def generate_final_answer(
        self,
        user_message: str,
        retrieved_context: str | None = None,
        tool_result: str | None = None,
    ) -> str:
        extra_context = ""

        if retrieved_context:
            extra_context += f"\n\nRetrieved context:\n{retrieved_context}"

        if tool_result:
            extra_context += f"\n\nTool result:\n{tool_result}"

        messages = build_chat_prompt(
            user_message,
            retrieved_context=extra_context if extra_context else None
        )
        response = self._llm.invoke(messages)
        return response.content