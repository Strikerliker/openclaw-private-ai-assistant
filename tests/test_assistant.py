import unittest

from assistant import process_message, validate_message, validate_session_id
from memory import InMemoryStore


class RecordingProvider:
    def __init__(self):
        self.calls = []

    def generate(self, *, system, user, context):
        self.calls.append({"system": system, "user": user, "context": context})
        return "Grounded answer from approved context."


class AssistantTests(unittest.TestCase):
    def test_safe_request_uses_approved_context(self):
        memory = InMemoryStore()
        provider = RecordingProvider()
        result = process_message(
            "demo-session",
            "What is the approved process for an access request?",
            memory=memory,
            provider=provider,
        )
        self.assertEqual(result.status, "ok")
        self.assertFalse(result.approval_required)
        self.assertEqual(result.tools_used, ["knowledge_lookup"])
        self.assertEqual(len(provider.calls), 1)
        self.assertIn("least-privilege", provider.calls[0]["context"])

    def test_high_risk_request_requires_approval_without_model_execution(self):
        memory = InMemoryStore()
        provider = RecordingProvider()
        result = process_message(
            "demo-session",
            "Please grant admin access to the production system",
            memory=memory,
            provider=provider,
        )
        self.assertEqual(result.status, "approval_required")
        self.assertTrue(result.approval_required)
        self.assertEqual(provider.calls, [])
        self.assertIn("escalation_template", result.tools_used)

    def test_incident_request_adds_escalation(self):
        result = process_message(
            "incident-123",
            "We may have a malware incident on a workstation",
            memory=InMemoryStore(),
            provider=RecordingProvider(),
        )
        self.assertIn("escalation_template", result.tools_used)
        self.assertIn("escalation policy", result.answer)

    def test_validation_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            validate_session_id("x")
        with self.assertRaises(ValueError):
            validate_message("   ")


if __name__ == "__main__":
    unittest.main()
