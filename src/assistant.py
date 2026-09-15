from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

from memory import MemoryStore, build_memory_store
from provider import ModelProvider, build_provider
from tools import run_tool


SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,127}$")
MAX_MESSAGE_CHARS = 6000

HIGH_RISK_TERMS = {
    "delete",
    "disable",
    "destroy",
    "drop database",
    "format disk",
    "grant admin",
    "grant administrator",
    "restart production",
    "rotate secret",
    "shutdown",
    "terminate instance",
    "wipe",
    "change firewall",
    "change security group",
    "reset password",
    "run command",
    "execute command",
    "deploy to production",
}

ESCALATION_TERMS = {
    "breach",
    "compromised",
    "malware",
    "ransomware",
    "phishing",
    "production down",
    "outage",
    "data loss",
    "privileged access",
    "emergency",
}

SYSTEM_PROMPT = (
    "You are a private enterprise assistant operating inside a controlled security boundary. "
    "Use approved context only. Never claim that a tool ran unless the application supplies a "
    "tool result. Never invent approvals, credentials, system state, or operational outcomes. "
    "For insufficient context, recommend escalation."
)


@dataclass(frozen=True)
class AssistantResponse:
    status: str
    answer: str
    session_id: str
    approval_required: bool
    tools_used: list[str]
    sources: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_session_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("session_id must be a string.")
    session_id = value.strip()
    if not SESSION_RE.fullmatch(session_id):
        raise ValueError(
            "session_id must be 3-128 characters using letters, numbers, dot, colon, underscore, or hyphen."
        )
    return session_id


def validate_message(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("message must be a string.")
    message = value.strip()
    if not message:
        raise ValueError("message is required.")
    if len(message) > MAX_MESSAGE_CHARS:
        raise ValueError(f"message exceeds the {MAX_MESSAGE_CHARS}-character limit.")
    return message


def requires_approval(message: str) -> bool:
    normalized = " ".join(message.lower().split())
    return any(term in normalized for term in HIGH_RISK_TERMS)


def should_escalate(message: str) -> bool:
    normalized = " ".join(message.lower().split())
    return any(term in normalized for term in ESCALATION_TERMS)


def _memory_context(memory: MemoryStore, session_id: str) -> str:
    messages = memory.recent(session_id, limit=6)
    if not messages:
        return ""
    lines = [f"{item.role.upper()}: {item.content[:700]}" for item in messages]
    return "RECENT PRIVATE SESSION MEMORY:\n" + "\n".join(lines)


def process_message(
    session_id: Any,
    message: Any,
    *,
    memory: MemoryStore | None = None,
    provider: ModelProvider | None = None,
) -> AssistantResponse:
    sid = validate_session_id(session_id)
    question = validate_message(message)
    memory_store = memory or build_memory_store()
    model = provider or build_provider()

    memory_store.append(sid, "user", question)

    if requires_approval(question):
        guidance = run_tool("knowledge_lookup", question)
        escalation = run_tool("escalation_template", question)
        answer = (
            "This request could change production, access, credentials, or system state. "
            "The reference assistant will not execute it automatically. Obtain explicit approval "
            "from the authorized owner and use the approved change or incident process.\n\n"
            f"Approved guidance: {guidance.output}\n\n{escalation.output}"
        )
        memory_store.append(sid, "assistant", answer)
        return AssistantResponse(
            status="approval_required",
            answer=answer,
            session_id=sid,
            approval_required=True,
            tools_used=[guidance.name, escalation.name],
            sources=[guidance.source, escalation.source],
        )

    primary = run_tool("knowledge_lookup", question)
    tool_results = [primary]
    if should_escalate(question):
        tool_results.append(run_tool("escalation_template", question))

    context_parts = [_memory_context(memory_store, sid)]
    context_parts.extend(
        f"[{result.source}]\n{result.output}" for result in tool_results
    )
    context = "\n\n".join(part for part in context_parts if part.strip())

    try:
        answer = model.generate(system=SYSTEM_PROMPT, user=question, context=context)
        status = "ok"
    except Exception:
        answer = (
            "The configured model provider is unavailable. No operational action was taken. "
            f"Approved guidance: {primary.output}"
        )
        status = "provider_unavailable"

    if should_escalate(question):
        answer += "\n\nThis topic matches the escalation policy; route it to the authorized owner."

    memory_store.append(sid, "assistant", answer)
    return AssistantResponse(
        status=status,
        answer=answer,
        session_id=sid,
        approval_required=False,
        tools_used=[result.name for result in tool_results],
        sources=[result.source for result in tool_results],
    )
