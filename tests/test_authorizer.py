import unittest

from authorizer import extract_bearer_token, is_authorized


class AuthorizerTests(unittest.TestCase):
    def test_extract_bearer_token_is_case_insensitive(self):
        self.assertEqual(
            extract_bearer_token({"authorization": "Bearer abc123"}),
            "abc123",
        )

    def test_missing_scheme_is_rejected(self):
        self.assertEqual(extract_bearer_token({"Authorization": "abc123"}), "")

    def test_constant_time_authorization_helper(self):
        self.assertTrue(is_authorized("same-token", "same-token"))
        self.assertFalse(is_authorized("wrong", "same-token"))
        self.assertFalse(is_authorized("", "same-token"))


if __name__ == "__main__":
    unittest.main()
