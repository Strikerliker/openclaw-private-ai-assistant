from __future__ import annotations

import os
from typing import Protocol


class ModelProvider(Protocol):
    def generate(self, *, system: str, user: str, context: str) -> str: ...


class DeterministicProvider:
    """Offline provider used to demonstrate the control flow without external inference."""

    def generate(self, *, system: str, user: str, context: str) -> str:
        del system
        if not context.strip():
            return (
                "I do not have approved context for that request. Use the escalation path "
                "instead of making an unverified change."
            )
        compact = " ".join(context.strip().split())
        return (
            "Based on the approved context: "
            f"{compact[:900]}"
            " Keep the action within the documented authorization boundary and escalate if "
            "the requested change exceeds that boundary."
        )


class BedrockProvider:
    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or os.getenv("MODEL_ID", "amazon.nova-lite-v1:0")

    def generate(self, *, system: str, user: str, context: str) -> str:
        import boto3

        client = boto3.client("bedrock-runtime")
        prompt = (
            "Use only the approved context below. If the context is insufficient, say so and "
            "recommend escalation. Do not invent tool results, credentials, approvals, or system state.\n\n"
            f"APPROVED CONTEXT:\n{context}\n\nUSER REQUEST:\n{user}"
        )
        result = client.converse(
            modelId=self.model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 700, "temperature": 0.1},
        )
        blocks = result.get("output", {}).get("message", {}).get("content", [])
        text = "".join(
            str(block.get("text", ""))
            for block in blocks
            if isinstance(block, dict) and block.get("text")
        ).strip()
        if not text:
            raise RuntimeError("Amazon Bedrock returned an empty response.")
        return text


def build_provider() -> ModelProvider:
    mode = os.getenv("PROVIDER_MODE", "deterministic").strip().lower()
    if mode == "bedrock":
        return BedrockProvider()
    return DeterministicProvider()
