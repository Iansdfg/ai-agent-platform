import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/agent_platform",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS drafts (
            id UUID PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            campaign_id TEXT,
            segment_id TEXT,
            customer_id TEXT,
            title TEXT,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_by TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            version INT NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS draft_versions (
            id UUID PRIMARY KEY,
            draft_id UUID NOT NULL REFERENCES drafts(id),
            version INT NOT NULL,
            content TEXT NOT NULL,
            edited_by TEXT NOT NULL,
            edit_instruction TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS draft_events (
            id UUID PRIMARY KEY,
            draft_id UUID NOT NULL,
            actor_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """))