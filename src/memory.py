from __future__ import annotations

import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MemoryMessage:
    role: str
    content: str
    created_at: float


class MemoryStore(Protocol):
    def append(self, session_id: str, role: str, content: str) -> None: ...

    def recent(self, session_id: str, limit: int = 8) -> list[MemoryMessage]: ...


class InMemoryStore:
    def __init__(self) -> None:
        self._messages: dict[str, list[MemoryMessage]] = {}

    def append(self, session_id: str, role: str, content: str) -> None:
        self._messages.setdefault(session_id, []).append(
            MemoryMessage(role=role, content=content, created_at=time.time())
        )

    def recent(self, session_id: str, limit: int = 8) -> list[MemoryMessage]:
        if limit <= 0:
            return []
        return list(self._messages.get(session_id, [])[-limit:])


class SqliteMemoryStore:
    """Small local-only store used for the self-hosted demo."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, id)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def append(self, session_id: str, role: str, content: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, time.time()),
            )

    def recent(self, session_id: str, limit: int = 8) -> list[MemoryMessage]:
        if limit <= 0:
            return []
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (session_id, int(limit)),
            ).fetchall()
        rows.reverse()
        return [MemoryMessage(role=row[0], content=row[1], created_at=row[2]) for row in rows]


class DynamoMemoryStore:
    """DynamoDB-backed private memory for AWS deployments."""

    def __init__(self, table_name: str) -> None:
        if not table_name:
            raise ValueError("table_name is required")
        import boto3

        self.table = boto3.resource("dynamodb").Table(table_name)

    def append(self, session_id: str, role: str, content: str) -> None:
        now = time.time()
        message_id = f"{int(now * 1_000_000):020d}#{uuid.uuid4().hex}"
        self.table.put_item(
            Item={
                "session_id": session_id,
                "message_id": message_id,
                "role": role,
                "content": content,
                "created_at": str(now),
            }
        )

    def recent(self, session_id: str, limit: int = 8) -> list[MemoryMessage]:
        if limit <= 0:
            return []
        from boto3.dynamodb.conditions import Key

        result = self.table.query(
            KeyConditionExpression=Key("session_id").eq(session_id),
            ScanIndexForward=False,
            Limit=int(limit),
        )
        items = list(result.get("Items", []))
        items.reverse()
        return [
            MemoryMessage(
                role=str(item.get("role", "unknown")),
                content=str(item.get("content", "")),
                created_at=float(item.get("created_at", "0")),
            )
            for item in items
        ]


def build_memory_store() -> MemoryStore:
    backend = os.getenv("MEMORY_BACKEND", "memory").strip().lower()
    if backend == "dynamodb":
        return DynamoMemoryStore(os.getenv("MEMORY_TABLE", ""))
    if backend == "sqlite":
        return SqliteMemoryStore(os.getenv("SQLITE_PATH", "/tmp/openclaw.db"))
    return InMemoryStore()
