import json
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import text

from db import SessionLocal


class DraftVersionConflict(Exception):
    pass


class DraftNotFound(Exception):
    pass


class DraftService:
    def create_draft(
        self,
        content: str,
        created_by: str,
        workspace_id: str = "default",
        title: Optional[str] = None,
        campaign_id: Optional[str] = None,
        segment_id: Optional[str] = None,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        draft_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())

        with SessionLocal() as db:
            with db.begin():
                db.execute(
                    text("""
                    INSERT INTO drafts (
                        id, workspace_id, campaign_id, segment_id, customer_id,
                        title, content, status, created_by, updated_by, version
                    )
                    VALUES (
                        :id, :workspace_id, :campaign_id, :segment_id, :customer_id,
                        :title, :content, 'draft', :created_by, :created_by, 1
                    )
                    """),
                    {
                        "id": draft_id,
                        "workspace_id": workspace_id,
                        "campaign_id": campaign_id,
                        "segment_id": segment_id,
                        "customer_id": customer_id,
                        "title": title,
                        "content": content,
                        "created_by": created_by,
                    },
                )

                db.execute(
                    text("""
                    INSERT INTO draft_versions (
                        id, draft_id, version, content, edited_by, edit_instruction
                    )
                    VALUES (
                        :id, :draft_id, 1, :content, :edited_by, :edit_instruction
                    )
                    """),
                    {
                        "id": version_id,
                        "draft_id": draft_id,
                        "content": content,
                        "edited_by": created_by,
                        "edit_instruction": "initial draft",
                    },
                )

                db.execute(
                    text("""
                    INSERT INTO draft_events (
                        id, draft_id, actor_id, event_type, metadata
                    )
                    VALUES (
                        :id, :draft_id, :actor_id, 'draft_created', CAST(:metadata AS JSONB)
                    )
                    """),
                    {
                        "id": event_id,
                        "draft_id": draft_id,
                        "actor_id": created_by,
                        "metadata": json.dumps({"version": 1}),
                    },
                )

        return {
            "draft_id": draft_id,
            "version": 1,
            "content": content,
            "status": "draft",
        }

    def get_draft(self, draft_id: str) -> Dict[str, Any]:
        with SessionLocal() as db:
            row = db.execute(
                text("""
                SELECT id, workspace_id, campaign_id, segment_id, customer_id,
                       title, content, status, created_by, updated_by,
                       version, created_at, updated_at
                FROM drafts
                WHERE id = :id
                """),
                {"id": draft_id},
            ).mappings().first()

        if not row:
            raise DraftNotFound(f"Draft not found: {draft_id}")

        return dict(row)

    def update_draft(
        self,
        draft_id: str,
        new_content: str,
        updated_by: str,
        base_version: int,
        edit_instruction: str,
    ) -> Dict[str, Any]:
        new_version = base_version + 1
        version_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())

        with SessionLocal() as db:
            with db.begin():
                result = db.execute(
                    text("""
                    UPDATE drafts
                    SET content = :content,
                        version = version + 1,
                        updated_by = :updated_by,
                        updated_at = NOW()
                    WHERE id = :id
                      AND version = :base_version
                    """),
                    {
                        "id": draft_id,
                        "content": new_content,
                        "updated_by": updated_by,
                        "base_version": base_version,
                    },
                )

                if result.rowcount == 0:
                    existing = db.execute(
                        text("SELECT id FROM drafts WHERE id = :id"),
                        {"id": draft_id},
                    ).first()

                    if not existing:
                        raise DraftNotFound(f"Draft not found: {draft_id}")

                    raise DraftVersionConflict(
                        "Draft was updated by someone else. Reload before editing."
                    )

                db.execute(
                    text("""
                    INSERT INTO draft_versions (
                        id, draft_id, version, content, edited_by, edit_instruction
                    )
                    VALUES (
                        :id, :draft_id, :version, :content, :edited_by, :edit_instruction
                    )
                    """),
                    {
                        "id": version_id,
                        "draft_id": draft_id,
                        "version": new_version,
                        "content": new_content,
                        "edited_by": updated_by,
                        "edit_instruction": edit_instruction,
                    },
                )

                db.execute(
                    text("""
                    INSERT INTO draft_events (
                        id, draft_id, actor_id, event_type, metadata
                    )
                    VALUES (
                        :id, :draft_id, :actor_id, 'draft_updated', CAST(:metadata AS JSONB)
                    )
                    """),
                    {
                        "id": event_id,
                        "draft_id": draft_id,
                        "actor_id": updated_by,
                        "metadata": json.dumps({
                            "base_version": base_version,
                            "new_version": new_version,
                            "edit_instruction": edit_instruction,
                        }),
                    },
                )

        return {
            "draft_id": draft_id,
            "version": new_version,
            "content": new_content,
            "status": "draft",
        }