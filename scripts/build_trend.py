"""Build a compact cross-commit trend from saved JSON reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_reports(input_dir: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for path in input_dir.rglob("red-team-*.json"):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            key = (str(report["created_at"]), str(report["git_sha"]))
            if key not in seen:
                reports.append(report)
                seen.add(key)
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            continue
    return sorted(reports, key=lambda report: str(report["created_at"]))


def render_trend(reports: list[dict[str, Any]]) -> str:
    lines = [
        "# Red-team trend",
        "",
        "| Run | Commit | Passed | Failed | Errors | Critical rate |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for report in reports:
        summary = report["summary"]
        total = int(summary["total"])
        critical = int(summary["critical_failures"])
        rate = (critical / total * 100) if total else 0
        lines.append(
            f"| {str(report['created_at'])[:19]} | `{str(report['git_sha'])[:8]}` | "
            f"{summary['passed']} | {summary['failed']} | {summary['errors']} | {rate:.1f}% |"
        )
    if not reports:
        lines.append("| No reports yet | - | - | - | - | - |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("reports"))
    parser.add_argument("--output", type=Path, default=Path("reports/trend.md"))
    args = parser.parse_args()

    reports = load_reports(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_trend(reports), encoding="utf-8")
    print(f"Trend report: {args.output} ({len(reports)} runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
