"""API Gateway Lambda handler for the deployed target."""

from __future__ import annotations

import json
from typing import Any

from llm_red_team.target import ConversationTurn, TargetConfigurationError, invoke_reply


MAX_MESSAGE_CHARS = 8_000
MAX_DOCUMENT_CHARS = 20_000
MAX_HISTORY_TURNS = 10


def _response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload),
    }


def _parse_history(value: Any) -> list[ConversationTurn]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > MAX_HISTORY_TURNS:
        raise ValueError(f"history must be a list with at most {MAX_HISTORY_TURNS} turns")

    turns: list[ConversationTurn] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"role", "text"}:
            raise ValueError("each history item must contain only role and text")
        role = item["role"]
        text = item["text"]
        if role not in {"user", "assistant"} or not isinstance(text, str) or not text.strip():
            raise ValueError("history roles must be user/assistant with non-empty text")
        if len(text) > MAX_MESSAGE_CHARS:
            raise ValueError("history text is too long")
        turns.append(ConversationTurn(role=role, text=text))
    return turns


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    del context
    try:
        payload = json.loads(event.get("body") or "{}")
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")

        message = payload.get("message")
        document = payload.get("reference_document")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("message must be a non-empty string")
        if len(message) > MAX_MESSAGE_CHARS:
            raise ValueError("message is too long")
        if document is not None and not isinstance(document, str):
            raise ValueError("reference_document must be a string or null")
        if document is not None and len(document) > MAX_DOCUMENT_CHARS:
            raise ValueError("reference_document is too long")

        result = invoke_reply(
            message,
            document,
            history=_parse_history(payload.get("history")),
        )
        return _response(
            200,
            {
                "reply": result.text,
                "usage": {
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "latency_ms": result.latency_ms,
                },
                "stop_reason": result.stop_reason,
            },
        )
    except (ValueError, json.JSONDecodeError) as error:
        return _response(400, {"error": str(error)})
    except TargetConfigurationError as error:
        return _response(500, {"error": str(error)})
    except Exception:
        return _response(502, {"error": "target invocation failed"})
