from typing import Any, Dict
from urllib.parse import urlparse

import requests

from tools.base import BaseTool, ToolResult


class HttpTool(BaseTool):
    name = "http_get"
    description = "Fetch JSON data from allowed HTTP domains."

    def __init__(self) -> None:
        self._allowed_domains = {
            "httpbin.org",
            "api.github.com",
        }

    def run(self, tool_input: Dict[str, Any]) -> ToolResult:
        url = str(tool_input.get("url", "")).strip()

        if not url:
            return ToolResult(success=False, output={}, error="Missing url")

        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            return ToolResult(success=False, output={}, error="Only http/https URLs are allowed")

        if parsed.netloc not in self._allowed_domains:
            return ToolResult(
                success=False,
                output={},
                error=f"Domain not allowed: {parsed.netloc}",
            )

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            return ToolResult(
                success=True,
                output={
                    "url": url,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("content-type"),
                    "text": response.text[:1000],
                },
            )

        except requests.RequestException as e:
            return ToolResult(success=False, output={}, error=str(e))