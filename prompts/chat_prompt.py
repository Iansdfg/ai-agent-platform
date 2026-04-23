from typing import List, Optional


def build_chat_prompt(user_message: str, retrieved_context: Optional[str] = None) -> list[tuple[str, str]]:
    system_prompt = (
        "You are a helpful AI assistant. "
        "Answer clearly and concisely. "
        "Use the provided context when it is relevant. "
        "If the answer is not in the context, say so honestly."
    )

    if retrieved_context:
        human_prompt = (
            f"User question:\n{user_message}\n\n"
            f"Retrieved context:\n{retrieved_context}"
        )
    else:
        human_prompt = user_message

    return [
        ("system", system_prompt),
        ("human", human_prompt),
    ]