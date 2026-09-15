import unittest

from tools import approved_tool_names, run_tool


class ToolTests(unittest.TestCase):
    def test_registry_contains_only_expected_read_only_tools(self):
        self.assertEqual(approved_tool_names(), ["escalation_template", "knowledge_lookup"])

    def test_knowledge_lookup_returns_approved_source(self):
        result = run_tool("knowledge_lookup", "How should privileged access be approved?")
        self.assertEqual(result.name, "knowledge_lookup")
        self.assertTrue(result.source.startswith("approved-guidance:"))
        self.assertIn("least-privilege", result.output)

    def test_unapproved_tool_is_rejected(self):
        with self.assertRaises(ValueError):
            run_tool("shell", "rm -rf /")


if __name__ == "__main__":
    unittest.main()
