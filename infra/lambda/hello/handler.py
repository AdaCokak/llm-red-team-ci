"""Handler for the minimal CDK learning Lambda."""

from __future__ import annotations

from typing import Any


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Return a small response without calling any external service."""

    return {
        "statusCode": 200,
        "body": "hello from CDK",
        "requestId": getattr(context, "aws_request_id", None),
    }

