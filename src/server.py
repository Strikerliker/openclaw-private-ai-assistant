from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from assistant import process_message
from memory import build_memory_store
from provider import build_provider
from tools import approved_tool_names


HOST = os.getenv("OPENCLAW_HOST", "127.0.0.1")
PORT = int(os.getenv("OPENCLAW_PORT", "8080"))
LOCAL_API_TOKEN = os.getenv("LOCAL_API_TOKEN", "")
MEMORY = build_memory_store()
PROVIDER = build_provider()


def token_ok(headers: Any) -> bool:
    if not LOCAL_API_TOKEN:
        return False
    value = str(headers.get("Authorization", "")).strip()
    if not value.lower().startswith("bearer "):
        return False
    provided = value[7:].strip()
    return bool(provided) and hmac.compare_digest(
        provided.encode("utf-8"), LOCAL_API_TOKEN.encode("utf-8")
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "OpenClawPrivateAssistant/1.0"

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path != "/health":
            self._json(404, {"error": "not_found"})
            return
        self._json(
            200,
            {
                "status": "ok",
                "service": "openclaw-private-ai-assistant",
                "approved_tools": approved_tool_names(),
            },
        )

    def do_POST(self) -> None:
        if self.path != "/v1/chat":
            self._json(404, {"error": "not_found"})
            return
        if not LOCAL_API_TOKEN:
            self._json(503, {"error": "server_not_configured"})
            return
        if not token_ok(self.headers):
            self._json(401, {"error": "unauthorized"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536:
                raise ValueError("Request body size is invalid.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            result = process_message(
                payload.get("session_id"),
                payload.get("message"),
                memory=MEMORY,
                provider=PROVIDER,
            )
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": "invalid_request", "message": str(exc)})
            return
        except Exception:
            self._json(500, {"error": "assistant_unavailable"})
            return

        self._json(202 if result.approval_required else 200, result.to_dict())

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep local logs to method/path/status metadata; request bodies are never logged here.
        super().log_message(fmt, *args)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"OpenClaw Private AI Assistant listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
