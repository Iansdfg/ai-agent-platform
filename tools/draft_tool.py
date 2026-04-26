from typing import Any, Dict

from services.draft_service import (
    DraftNotFound,
    DraftService,
    DraftVersionConflict,
)
from tools.base import BaseTool, ToolResult


class CreateDraftTool(BaseTool):
    name = "create_draft"
    description = "Create and persist a marketing draft."

    def __init__(self) -> None:
        self._service = DraftService()

    def run(self, tool_input: Dict[str, Any]) -> ToolResult:
        content = str(tool_input.get("content", "")).strip()
        created_by = str(tool_input.get("created_by", "system")).strip()
        workspace_id = str(tool_input.get("workspace_id", "default")).strip()

        if not content:
            return ToolResult(success=False, output={}, error="Missing content")

        result = self._service.create_draft(
            content=content,
            created_by=created_by,
            workspace_id=workspace_id,
            title=tool_input.get("title"),
            campaign_id=tool_input.get("campaign_id"),
            segment_id=tool_input.get("segment_id"),
            customer_id=tool_input.get("customer_id"),
        )

        return ToolResult(success=True, output=result)


class GetDraftTool(BaseTool):
    name = "get_draft"
    description = "Get a draft by draft_id."

    def __init__(self) -> None:
        self._service = DraftService()

    def run(self, tool_input: Dict[str, Any]) -> ToolResult:
        draft_id = str(tool_input.get("draft_id", "")).strip()

        if not draft_id:
            return ToolResult(success=False, output={}, error="Missing draft_id")

        try:
            result = self._service.get_draft(draft_id)
            return ToolResult(success=True, output=result)
        except DraftNotFound as e:
            return ToolResult(success=False, output={}, error=str(e))


class UpdateDraftTool(BaseTool):
    name = "update_draft"
    description = "Update a draft with optimistic locking."

    def __init__(self) -> None:
        self._service = DraftService()

    def run(self, tool_input: Dict[str, Any]) -> ToolResult:
        draft_id = str(tool_input.get("draft_id", "")).strip()
        new_content = str(tool_input.get("new_content", "")).strip()
        updated_by = str(tool_input.get("updated_by", "system")).strip()
        edit_instruction = str(tool_input.get("edit_instruction", "")).strip()

        try:
            base_version = int(tool_input.get("base_version"))
        except (TypeError, ValueError):
            return ToolResult(success=False, output={}, error="Missing or invalid base_version")

        if not draft_id:
            return ToolResult(success=False, output={}, error="Missing draft_id")

        if not new_content:
            return ToolResult(success=False, output={}, error="Missing new_content")

        try:
            result = self._service.update_draft(
                draft_id=draft_id,
                new_content=new_content,
                updated_by=updated_by,
                base_version=base_version,
                edit_instruction=edit_instruction,
            )
            return ToolResult(success=True, output=result)

        except (DraftNotFound, DraftVersionConflict) as e:
            return ToolResult(success=False, output={}, error=str(e))