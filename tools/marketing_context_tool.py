import json
from pathlib import Path
from typing import Any, Dict

from tools.base import BaseTool, ToolResult


class GetMarketingContextTool(BaseTool):
    name = "get_marketing_context"
    description = (
        "Return current product inventory, product benefits, inventory status, "
        "and active campaign details for marketing content generation."
    )

    def __init__(self) -> None:
        self._context_path = (
            Path(__file__).resolve().parents[1] / "data" / "marketing_context.json"
        )

    def run(self, tool_input: Dict[str, Any]) -> ToolResult:
        try:
            raw_context = json.loads(self._context_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return ToolResult(
                success=False,
                output={},
                error=f"Marketing context file not found: {self._context_path}",
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                output={},
                error=f"Marketing context file is invalid JSON: {e}",
            )

        products = raw_context.get("products", [])

        return ToolResult(
            success=True,
            output={
                "source": "local_mock_marketing_context",
                "query": tool_input.get("query", ""),
                "inventory_last_updated": raw_context.get("inventory_last_updated"),
                "current_product_inventory": products,
                "product_names": [
                    product.get("name") for product in products if product.get("name")
                ],
                "product_benefits": {
                    product.get("name"): product.get("benefits", [])
                    for product in products
                    if product.get("name")
                },
                "inventory_status": {
                    product.get("name"): product.get("inventory_status")
                    for product in products
                    if product.get("name")
                },
                "active_campaign": raw_context.get("active_campaign", {}),
            },
        )
