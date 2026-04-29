import importlib
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient


def load_app(api_key: str | None):
    if api_key is None:
        env = {k: v for k, v in os.environ.items() if k != "APP_API_KEY"}
    else:
        env = {**os.environ, "APP_API_KEY": api_key}

    with patch.dict(os.environ, env, clear=True):
        import core.config
        import core.auth
        import app

        importlib.reload(core.config)
        importlib.reload(core.auth)
        return importlib.reload(app).app


class AuthTests(unittest.TestCase):
    def test_healthcheck_is_public(self):
        client = TestClient(load_app(api_key=None))

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_protected_endpoint_fails_closed_without_configured_key(self):
        client = TestClient(load_app(api_key=None))

        response = client.get("/tools")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            "API key authentication is not configured",
        )

    def test_protected_endpoint_rejects_missing_key(self):
        client = TestClient(load_app(api_key="secret"))

        response = client.get("/tools")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid or missing API key")

    def test_chat_endpoint_rejects_missing_key_before_agent_invocation(self):
        client = TestClient(load_app(api_key="secret"))

        response = client.post("/chat", json={"message": "hello"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid or missing API key")

    def test_tool_execution_endpoint_rejects_missing_key_before_execution(self):
        client = TestClient(load_app(api_key="secret"))

        response = client.post("/tools/create_draft", json={"content": "draft"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid or missing API key")

    def test_protected_endpoint_rejects_invalid_key(self):
        client = TestClient(load_app(api_key="secret"))

        response = client.get("/tools", headers={"X-API-Key": "wrong"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid or missing API key")

    def test_protected_endpoint_accepts_valid_key(self):
        client = TestClient(load_app(api_key="secret"))

        response = client.get("/tools", headers={"X-API-Key": "secret"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("tools", response.json())


if __name__ == "__main__":
    unittest.main()
