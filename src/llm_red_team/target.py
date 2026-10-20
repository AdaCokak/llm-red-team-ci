"""Amazon Bedrock target shared by local tests and the deployed Lambda."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Sequence

import boto3

from llm_red_team.policy import (
    CANARY,
    SYSTEM_PROMPT,
    render_untrusted_content,
    render_user_content,
)


class TargetConfigurationError(RuntimeError):
    """Raised when required target configuration is missing."""


@dataclass(frozen=True)
class ConversationTurn:
    role: str
    text: str


@dataclass(frozen=True)
class TargetResponse:
    text: str
    model_id: str
    region: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    stop_reason: str | None


def _to_bedrock_messages(
    history: Sequence[ConversationTurn],
    customer_message: str,
    reference_document: str | None,
    *,
    selectively_guard: bool,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for turn in history:
        if turn.role not in {"user", "assistant"}:
            raise ValueError(f"Unsupported conversation role: {turn.role}")
        text = render_user_content(turn.text) if turn.role == "user" else turn.text
        messages.append({"role": turn.role, "content": [{"text": text}]})

    if selectively_guard:
        current_content: list[dict[str, Any]] = [
            {"text": "Draft a reply to the customer using the information below."},
            {
                "guardContent": {
                    "text": {
                        "text": render_untrusted_content(customer_message, reference_document),
                        "qualifiers": ["guard_content"],
                    }
                }
            },
        ]
    else:
        current_content = [{"text": render_user_content(customer_message, reference_document)}]
    messages.append({"role": "user", "content": current_content})
    return messages


def invoke_reply(
    customer_message: str,
    reference_document: str | None = None,
    *,
    history: Sequence[ConversationTurn] = (),
    model_id: str | None = None,
    region: str | None = None,
    guardrail_identifier: str | None = None,
    guardrail_version: str | None = None,
) -> TargetResponse:
    """Invoke Bedrock with optional conversation history and Guardrail."""

    selected_model = model_id or os.getenv("BEDROCK_MODEL_ID")
    selected_region = region or os.getenv("AWS_REGION", "us-east-1")
    selected_guardrail = guardrail_identifier or os.getenv("BEDROCK_GUARDRAIL_ID")
    selected_guardrail_version = guardrail_version or os.getenv("BEDROCK_GUARDRAIL_VERSION")

    if not selected_model:
        raise TargetConfigurationError(
            "BEDROCK_MODEL_ID is not set. Use an ID returned by your account's "
            "Bedrock inference-profile or foundation-model listing."
        )
    if bool(selected_guardrail) != bool(selected_guardrail_version):
        raise TargetConfigurationError(
            "BEDROCK_GUARDRAIL_ID and BEDROCK_GUARDRAIL_VERSION must be set together."
        )

    request: dict[str, Any] = {
        "modelId": selected_model,
        "system": [{"text": SYSTEM_PROMPT}],
        "messages": _to_bedrock_messages(
            history,
            customer_message,
            reference_document,
            selectively_guard=bool(selected_guardrail),
        ),
        "inferenceConfig": {"maxTokens": 300, "temperature": 0},
    }
    if selected_guardrail and selected_guardrail_version:
        request["guardrailConfig"] = {
            "guardrailIdentifier": selected_guardrail,
            "guardrailVersion": selected_guardrail_version,
            "trace": "enabled",
        }

    client = boto3.client("bedrock-runtime", region_name=selected_region)
    started = time.perf_counter()
    response = client.converse(**request)
    elapsed_ms = round((time.perf_counter() - started) * 1000)

    content_blocks = response["output"]["message"]["content"]
    text_blocks = [block["text"] for block in content_blocks if "text" in block]
    if not text_blocks:
        raise RuntimeError("Bedrock returned no text content.")

    usage = response.get("usage", {})
    return TargetResponse(
        text="\n".join(text_blocks).strip(),
        model_id=selected_model,
        region=selected_region,
        input_tokens=int(usage.get("inputTokens", 0)),
        output_tokens=int(usage.get("outputTokens", 0)),
        latency_ms=elapsed_ms,
        stop_reason=response.get("stopReason"),
    )


def draft_reply(
    customer_message: str,
    reference_document: str | None = None,
    *,
    model_id: str | None = None,
    region: str | None = None,
) -> str:
    """Compatibility wrapper for a single-turn, unguarded text response."""

    return invoke_reply(
        customer_message,
        reference_document,
        model_id=model_id,
        region=region,
    ).text

