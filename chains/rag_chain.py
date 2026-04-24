from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from core.config import MODEL_NAME, OPENAI_API_KEY


def build_rag_chain():
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are a helpful AI assistant. "
                    "Answer using the provided retrieved context when relevant. "
                    "If the context does not contain enough information, say so honestly."
                ),
            ),
            (
                "human",
                (
                    "User question:\n{question}\n\n"
                    "Retrieved context:\n{context}"
                ),
            ),
        ]
    )

    llm = ChatOpenAI(
        model=MODEL_NAME,
        api_key=OPENAI_API_KEY,
        temperature=0,
    )

    return prompt | llm | StrOutputParser()