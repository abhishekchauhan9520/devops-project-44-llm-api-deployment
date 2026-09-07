import os
import unittest

os.environ["REQUIRE_API_KEY"] = "true"
os.environ["SERVICE_API_KEY"] = "test-key"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["RATE_LIMIT_RPM"] = "2"

from fastapi.testclient import TestClient
from app.main import app


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_ready(self):
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)

    def test_auth_required(self):
        response = self.client.post("/v1/chat", json={"prompt": "hello"})
        self.assertEqual(response.status_code, 401)

    def test_chat_mock_provider(self):
        response = self.client.post("/v1/chat", headers={"X-API-Key": "test-key", "X-Client-Id": "client-a"}, json={"prompt": "hello"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["provider"], "mock")
        self.assertIn("output", body)
        self.assertIn("usage", body)

    def test_prompt_length_validation(self):
        response = self.client.post("/v1/chat", headers={"X-API-Key": "test-key", "X-Client-Id": "client-b"}, json={"prompt": "x" * 12001})
        self.assertEqual(response.status_code, 422)

    def test_model_output_limit_validation(self):
        response = self.client.post("/v1/chat", headers={"X-API-Key": "test-key", "X-Client-Id": "client-c"}, json={"prompt": "hello", "max_output_tokens": 2048})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
