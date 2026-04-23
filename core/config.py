import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "AI Agent Platform"
MODEL_NAME = "gpt-4o-mini"
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-small")
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "rag_store")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")