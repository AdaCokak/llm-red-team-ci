from llm_red_team.attacks import Attack
from llm_red_team.runner import build_report, run_attack, should_fail_build
from llm_red_team.target import TargetResponse


ATTACK = Attack(
    id="test-attack",
    source_id="test-attack",
    category="direct_prompt_injection",
    severity="critical",
    language="en",
    messages=("attack",),
    reference_document=None,
)


def _response(text: str) -> TargetResponse:
    return TargetResponse(text, "model", "us-east-1", 10, 4, 20, "end_turn")


def test_safe_result_does_not_fail_build() -> None:
    result = run_attack(ATTACK, invoker=lambda *args: _response("I cannot do that."))
    report = build_report([result])

    assert result.status == "pass"
    assert should_fail_build(report) is False


def test_canary_leak_fails_build() -> None:
    result = run_attack(ATTACK, invoker=lambda *args: _response("ZEBRA-7731"))
    report = build_report([result])

    assert result.status == "fail"
    assert should_fail_build(report) is True

def test_invocation_error_fails_closed() -> None:
    def fail(*args):
        raise TimeoutError("model timed out")

    result = run_attack(ATTACK, invoker=fail)
    report = build_report([result])

    assert result.status == "error"
    assert should_fail_build(report) is True

