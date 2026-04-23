from langchain_openai import ChatOpenAI

from core.config import MODEL_NAME, OPENAI_API_KEY
from prompts.chat_prompt import build_chat_prompt


class LLMService:
    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model=MODEL_NAME,
            api_key=OPENAI_API_KEY,
            temperature=0
        )

    def generate_response(self, user_message: str, retrieved_context: str | None = None) -> str:
        messages = build_chat_prompt(user_message, retrieved_context=retrieved_context)
        response = self._llm.invoke(messages)
        return response.content