import json

from llm_red_team import lambda_handler
from llm_red_team.target import TargetResponse


def test_lambda_rejects_missing_message() -> None:
    response = lambda_handler.lambda_handler({"body": "{}"}, None)

    assert response["statusCode"] == 400
    assert "message" in json.loads(response["body"])["error"]


def test_lambda_returns_sanitized_target_response(monkeypatch) -> None:
    monkeypatch.setattr(
        lambda_handler,
        "invoke_reply",
        lambda *args, **kwargs: TargetResponse(
            text="Safe reply",
            model_id="test-model",
            region="us-east-1",
            input_tokens=10,
            output_tokens=3,
            latency_ms=25,
            stop_reason="end_turn",
        ),
    )
    response = lambda_handler.lambda_handler(
        {"body": json.dumps({"message": "Where is my order?"})},
        None,
    )
    payload = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert payload["reply"] == "Safe reply"
    assert payload["usage"]["input_tokens"] == 10
    assert "model_id" not in payload


def test_lambda_hides_internal_exception(monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("sensitive AWS detail")

    monkeypatch.setattr(lambda_handler, "invoke_reply", fail)
    response = lambda_handler.lambda_handler(
        {"body": json.dumps({"message": "Hello"})},
        None,
    )

    assert response["statusCode"] == 502
    assert "sensitive AWS detail" not in response["body"]

