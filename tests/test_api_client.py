import json
from unittest.mock import Mock, patch

import pytest

from llm_red_team.api_client import TargetApiError, invoke_api
from llm_red_team.target import ConversationTurn, TargetConfigurationError


def _credentials() -> Mock:
    credentials = Mock()
    credentials.get_frozen_credentials.return_value = Mock(
        access_key="key", secret_key="secret", token=None
    )
    return credentials


@patch("llm_red_team.api_client.URLLib3Session")
@patch("llm_red_team.api_client.boto3.Session")
def test_invoke_api_signs_and_parses_response(session: Mock, https: Mock) -> None:
    session.return_value.get_credentials.return_value = _credentials()
    response = Mock()
    response.status_code = 200
    response.content = json.dumps(
        {
            "reply": "Safe reply",
            "usage": {"input_tokens": 4, "output_tokens": 2, "latency_ms": 15},
            "stop_reason": "end_turn",
        }
    ).encode()
    https.return_value.send.return_value = response

    result = invoke_api(
        "Hello",
        None,
        (ConversationTurn("assistant", "Earlier"),),
        api_url="https://example.execute-api.us-east-1.amazonaws.com/v1/draft",
    )

    assert result.text == "Safe reply"
    assert result.input_tokens == 4
    request = https.return_value.send.call_args.args[0]
    assert request.headers["Authorization"].startswith("AWS4-HMAC-SHA256")


def test_invoke_api_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TARGET_API_URL", raising=False)
    with pytest.raises(TargetConfigurationError, match="TARGET_API_URL"):
        invoke_api("Hello", None, ())
