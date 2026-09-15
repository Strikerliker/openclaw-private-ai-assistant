from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ToolResult:
    name: str
    output: str
    source: str


ToolHandler = Callable[[str], ToolResult]


APPROVED_GUIDANCE = {
    "access": (
        "Access changes require an approved ticket, a named business or system owner, "
        "least-privilege scope, and documented expiration or review criteria. Privileged "
        "access should use a separate administrative identity where supported."
    ),
    "incident": (
        "For a suspected security incident, preserve evidence, record the affected identity "
        "and system, note timestamps and observed indicators, avoid destructive remediation, "
        "and escalate through the approved incident-response path."
    ),
    "change": (
        "Production changes should have an approved change record, implementation plan, "
        "validation steps, rollback criteria, owner, and maintenance window before execution."
    ),
    "backup": (
        "Before a high-impact configuration or data change, verify a recent recoverable backup "
        "or snapshot and confirm the restoration owner and rollback procedure."
    ),
}


def knowledge_lookup(query: str) -> ToolResult:
    normalized = query.lower()
    best_key = "change"
    best_score = -1
    for key, text in APPROVED_GUIDANCE.items():
        terms = {key, *text.lower().replace(",", "").replace(".", "").split()}
        score = sum(1 for token in normalized.split() if token in terms)
        if score > best_score:
            best_key = key
            best_score = score
    return ToolResult(
        name="knowledge_lookup",
        output=APPROVED_GUIDANCE[best_key],
        source=f"approved-guidance:{best_key}",
    )


def escalation_template(query: str) -> ToolResult:
    summary = " ".join(query.strip().split())[:240]
    return ToolResult(
        name="escalation_template",
        output=(
            "Escalation record:\n"
            f"- Request summary: {summary or 'Not provided'}\n"
            "- Affected system/service: capture before escalation\n"
            "- Business impact: capture before escalation\n"
            "- Timestamp and requester identity: capture before escalation\n"
            "- Evidence/error details: attach without exposing secrets\n"
            "- Requested action: route to the authorized system, security, or operations owner"
        ),
        source="approved-template:escalation",
    )


TOOL_REGISTRY: dict[str, ToolHandler] = {
    "knowledge_lookup": knowledge_lookup,
    "escalation_template": escalation_template,
}


def run_tool(name: str, argument: str) -> ToolResult:
    handler = TOOL_REGISTRY.get(name)
    if handler is None:
        raise ValueError(f"Tool '{name}' is not approved.")
    return handler(argument)


def approved_tool_names() -> list[str]:
    return sorted(TOOL_REGISTRY)
