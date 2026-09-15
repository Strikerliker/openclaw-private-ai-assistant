import json
import unittest

import app


class AppTests(unittest.TestCase):
    def event(self, method, path, body=None):
        return {
            "rawPath": path,
            "requestContext": {"http": {"method": method, "path": path}},
            "body": None if body is None else json.dumps(body),
        }

    def test_health_route(self):
        result = app.lambda_handler(self.event("GET", "/health"), None)
        self.assertEqual(result["statusCode"], 200)
        payload = json.loads(result["body"])
        self.assertEqual(payload["status"], "ok")
        self.assertIn("knowledge_lookup", payload["approved_tools"])

    def test_chat_route_returns_grounded_response(self):
        result = app.lambda_handler(
            self.event(
                "POST",
                "/v1/chat",
                {
                    "session_id": "demo-session",
                    "message": "What is the approved access process?",
                },
            ),
            None,
        )
        self.assertEqual(result["statusCode"], 200)
        payload = json.loads(result["body"])
        self.assertEqual(payload["status"], "ok")
        self.assertIn("knowledge_lookup", payload["tools_used"])

    def test_high_risk_chat_returns_202(self):
        result = app.lambda_handler(
            self.event(
                "POST",
                "/v1/chat",
                {
                    "session_id": "demo-session",
                    "message": "Please delete the production database",
                },
            ),
            None,
        )
        self.assertEqual(result["statusCode"], 202)
        self.assertTrue(json.loads(result["body"])["approval_required"])

    def test_invalid_body_returns_400(self):
        event = self.event("POST", "/v1/chat")
        event["body"] = "not-json"
        result = app.lambda_handler(event, None)
        self.assertEqual(result["statusCode"], 400)


if __name__ == "__main__":
    unittest.main()
