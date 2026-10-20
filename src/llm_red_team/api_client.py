"""SigV4 client for the IAM-protected deployed target API."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import HTTPClientError
from botocore.httpsession import URLLib3Session

from llm_red_team.target import ConversationTurn, TargetConfigurationError, TargetResponse


class TargetApiError(RuntimeError):
    """Raised when the deployed target rejects or cannot process a request."""


def invoke_api(
    message: str,
    document: str | None,
    history: Sequence[ConversationTurn],
    *,
    api_url: str | None = None,
    region: str | None = None,
) -> TargetResponse:
    """Call API Gateway with the current AWS identity using Signature Version 4."""

    selected_url = api_url or os.getenv("TARGET_API_URL")
    selected_region = region or os.getenv("AWS_REGION", "us-east-1")
    if not selected_url:
        raise TargetConfigurationError(
            "TARGET_API_URL is not set. Use the TargetApiUrl CDK stack output."
        )

    body = json.dumps(
        {
            "message": message,
            "reference_document": document,
            "history": [
                {"role": turn.role, "text": turn.text}
                for turn in history
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")

    session = boto3.Session()
    credentials = session.get_credentials()
    if credentials is None:
        raise TargetConfigurationError("No AWS credentials are available for API signing.")

    aws_request = AWSRequest(
        method="POST",
        url=selected_url,
        data=body,
        headers={"content-type": "application/json"},
    )
    SigV4Auth(credentials.get_frozen_credentials(), "execute-api", selected_region).add_auth(
        aws_request
    )
    prepared = aws_request.prepare()
    try:
        response = URLLib3Session(timeout=40).send(prepared)
    except HTTPClientError as error:
        raise TargetApiError(f"Target API request failed: {error}") from error

    if response.status_code >= 400:
        detail = response.content.decode("utf-8", errors="replace")
        raise TargetApiError(
            f"Target API returned HTTP {response.status_code}: {detail}"
        )
    payload: Any = json.loads(response.content)

    if not isinstance(payload, dict) or not isinstance(payload.get("reply"), str):
        raise TargetApiError("Target API returned an invalid response body.")
    usage = payload.get("usage", {})
    if not isinstance(usage, dict):
        usage = {}
    return TargetResponse(
        text=payload["reply"],
        model_id="deployed-api",
        region=selected_region,
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
        latency_ms=int(usage.get("latency_ms", 0)),
        stop_reason=payload.get("stop_reason"),
    )
