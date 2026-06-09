import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

APP_NAME = "AI Agent Platform"
MODEL_NAME = "gpt-4o-mini"
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APP_API_KEY = os.getenv("APP_API_KEY")


def _build_postgres_url(
    driver: str,
    user: str,
    password: str,
    host: str,
    port: int,
    database: str,
    sslmode: str | None = None,
) -> str:
    query = f"?sslmode={sslmode}" if sslmode else ""
    return (
        f"postgresql+{driver}://"
        f"{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}{query}"
    )


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "agent_platform")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_SSLMODE = os.getenv("DB_SSLMODE")

DATABASE_URL = os.getenv("DATABASE_URL") or _build_postgres_url(
    driver="psycopg2",
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    sslmode=DB_SSLMODE,
)

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-small")
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "rag_store")
DOCS_DIR = os.getenv("DOCS_DIR", "docs")

RAG_DB_HOST = os.getenv("RAG_DB_HOST", DB_HOST)
RAG_DB_PORT = int(os.getenv("RAG_DB_PORT", str(DB_PORT)))
RAG_DB_NAME = os.getenv("RAG_DB_NAME", DB_NAME)
RAG_DB_USER = os.getenv("RAG_DB_USER", DB_USER)
RAG_DB_PASSWORD = os.getenv("RAG_DB_PASSWORD", DB_PASSWORD)
RAG_DB_SSLMODE = os.getenv("RAG_DB_SSLMODE", DB_SSLMODE or "")
RAG_TABLE_NAME = os.getenv("RAG_TABLE_NAME", "documents")
RAG_EMBED_DIM = int(os.getenv("RAG_EMBED_DIM", "1536"))

RAG_DATABASE_URL = os.getenv("RAG_DATABASE_URL") or _build_postgres_url(
    driver="psycopg2",
    user=RAG_DB_USER,
    password=RAG_DB_PASSWORD,
    host=RAG_DB_HOST,
    port=RAG_DB_PORT,
    database=RAG_DB_NAME,
    sslmode=RAG_DB_SSLMODE or None,
)
RAG_ASYNC_DATABASE_URL = os.getenv("RAG_ASYNC_DATABASE_URL") or _build_postgres_url(
    driver="asyncpg",
    user=RAG_DB_USER,
    password=RAG_DB_PASSWORD,
    host=RAG_DB_HOST,
    port=RAG_DB_PORT,
    database=RAG_DB_NAME,
)
