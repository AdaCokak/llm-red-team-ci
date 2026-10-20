"""Attack-suite execution and report generation."""

from __future__ import annotations

import json
import os
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Sequence

from llm_red_team.attacks import Attack
from llm_red_team.judge import judge_response
from llm_red_team.llm_judge import judge_fuzzy
from llm_red_team.target import ConversationTurn, TargetResponse, invoke_reply


Invoker = Callable[[str, str | None, Sequence[ConversationTurn]], TargetResponse]


@dataclass(frozen=True)
class AttackResult:
    attack_id: str
    source_id: str
    category: str
    severity: str
    language: str
    mutation: str | None
    status: str
    deterministic_reasons: tuple[str, ...]
    llm_verdict: str | None
    llm_confidence: float | None
    llm_reason: str | None
    responses: tuple[str, ...]
    input_tokens: int
    output_tokens: int
    latency_ms: int
    stop_reasons: tuple[str | None, ...]
    error: str | None


def direct_invoker(
    message: str,
    document: str | None,
    history: Sequence[ConversationTurn],
) -> TargetResponse:
    return invoke_reply(message, document, history=history)


def run_attack(
    attack: Attack,
    *,
    invoker: Invoker | None = None,
    use_llm_judge: bool = False,
) -> AttackResult:
    history: list[ConversationTurn] = []
    responses: list[str] = []
    reasons: list[str] = []
    input_tokens = 0
    output_tokens = 0
    latency_ms = 0
    stop_reasons: list[str | None] = []

    selected_invoker = invoker or direct_invoker
    try:
        for index, message in enumerate(attack.messages):
            result = selected_invoker(
                message,
                attack.reference_document if index == 0 else None,
                tuple(history),
            )
            responses.append(result.text)
            input_tokens += result.input_tokens
            output_tokens += result.output_tokens
            latency_ms += result.latency_ms
            stop_reasons.append(result.stop_reason)
            reasons.extend(judge_response(result.text).reasons)
            history.extend(
                [
                    ConversationTurn("user", message),
                    ConversationTurn("assistant", result.text),
                ]
            )

        llm_result = judge_fuzzy(attack, responses[-1]) if use_llm_judge else None
        return AttackResult(
            attack_id=attack.id,
            source_id=attack.source_id,
            category=attack.category,
            severity=attack.severity,
            language=attack.language,
            mutation=attack.mutation,
            status="fail" if reasons else "pass",
            deterministic_reasons=tuple(dict.fromkeys(reasons)),
            llm_verdict=llm_result.verdict if llm_result else None,
            llm_confidence=llm_result.confidence if llm_result else None,
            llm_reason=llm_result.reason if llm_result else None,
            responses=tuple(responses),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            stop_reasons=tuple(stop_reasons),
            error=None,
        )
    except Exception as error:
        return AttackResult(
            attack_id=attack.id,
            source_id=attack.source_id,
            category=attack.category,
            severity=attack.severity,
            language=attack.language,
            mutation=attack.mutation,
            status="error",
            deterministic_reasons=(),
            llm_verdict=None,
            llm_confidence=None,
            llm_reason=None,
            responses=tuple(responses),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            stop_reasons=tuple(stop_reasons),
            error=f"{type(error).__name__}: {error}",
        )


def _git_sha() -> str:
    if os.getenv("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_report(results: Sequence[AttackResult]) -> dict[str, object]:
    statuses = Counter(result.status for result in results)
    categories = Counter(result.category for result in results if result.status != "pass")
    languages = Counter(result.language for result in results if result.status != "pass")
    critical_failures = sum(
        result.severity == "critical" and result.status in {"fail", "error"}
        for result in results
    )
    return {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "target_model_id": os.getenv("BEDROCK_MODEL_ID"),
        "guardrail_enabled": bool(os.getenv("BEDROCK_GUARDRAIL_ID")),
        "summary": {
            "total": len(results),
            "passed": statuses["pass"],
            "failed": statuses["fail"],
            "errors": statuses["error"],
            "critical_failures": critical_failures,
            "input_tokens": sum(result.input_tokens for result in results),
            "output_tokens": sum(result.output_tokens for result in results),
            "failed_by_category": dict(categories),
            "failed_by_language": dict(languages),
        },
        "results": [asdict(result) for result in results],
    }


def write_report(report: dict[str, object], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"red-team-{stamp}.json"
    markdown_path = output_dir / f"red-team-{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = report["summary"]
    assert isinstance(summary, dict)
    lines = [
        "# LLM red-team report",
        "",
        f"- Git SHA: `{report['git_sha']}`",
        f"- Total: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        f"- Errors: {summary['errors']}",
        f"- Critical failures: {summary['critical_failures']}",
        f"- Tokens: {summary['input_tokens']} input / {summary['output_tokens']} output",
        "",
        "| Attack | Category | Language | Mutation | Status | LLM judge |",
        "|---|---|---|---|---|---|",
    ]
    for item in report["results"]:
        assert isinstance(item, dict)
        lines.append(
            f"| {item['attack_id']} | {item['category']} | {item['language']} | "
            f"{item['mutation'] or '-'} | {item['status']} | {item['llm_verdict'] or '-'} |"
        )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, markdown_path


def should_fail_build(report: dict[str, object]) -> bool:
    summary = report["summary"]
    assert isinstance(summary, dict)
    return int(summary["critical_failures"]) > 0
