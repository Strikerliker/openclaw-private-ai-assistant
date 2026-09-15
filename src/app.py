from __future__ import annotations

import json
from typing import Any

from assistant import process_message
from tools import approved_tool_names


SERVICE_NAME = "openclaw-private-ai-assistant"


def response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json",
            "cache-control": "no-store",
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
        },
        "body": json.dumps(body),
    }


def parse_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body")
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Request body must be valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Request body must be a JSON object.")
    return parsed


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    del context
    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})
    method = str(http.get("method", event.get("httpMethod", ""))).upper()
    path = str(event.get("rawPath") or http.get("path") or event.get("path") or "")

    if method == "GET" and path == "/health":
        return response(
            200,
            {
                "status": "ok",
                "service": SERVICE_NAME,
                "approved_tools": approved_tool_names(),
            },
        )

    if method != "POST" or path != "/v1/chat":
        return response(404, {"error": "not_found"})

    try:
        payload = parse_body(event)
        result = process_message(
            payload.get("session_id"),
            payload.get("message"),
        )
    except ValueError as exc:
        return response(400, {"error": "invalid_request", "message": str(exc)})
    except Exception:
        return response(
            500,
            {
                "error": "assistant_unavailable",
                "message": "The private assistant could not process the request.",
            },
        )

    status_code = 202 if result.approval_required else 200
    return response(status_code, result.to_dict())
