import os
import tempfile
import unittest

from memory import InMemoryStore, SqliteMemoryStore


class MemoryTests(unittest.TestCase):
    def test_in_memory_recent_is_session_scoped(self):
        store = InMemoryStore()
        store.append("session-a", "user", "one")
        store.append("session-b", "user", "other")
        store.append("session-a", "assistant", "two")

        messages = store.recent("session-a", limit=5)
        self.assertEqual([item.content for item in messages], ["one", "two"])

    def test_sqlite_store_persists_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "memory.db")
            first = SqliteMemoryStore(path)
            first.append("session-1", "user", "hello")
            first.append("session-1", "assistant", "hi")

            second = SqliteMemoryStore(path)
            messages = second.recent("session-1", limit=2)
            self.assertEqual([item.role for item in messages], ["user", "assistant"])
            self.assertEqual(messages[-1].content, "hi")


if __name__ == "__main__":
    unittest.main()
