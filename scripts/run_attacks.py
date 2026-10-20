"""Run the attack catalogue and emit JSON/Markdown reports."""

from __future__ import annotations

import argparse
from pathlib import Path

from llm_red_team.api_client import invoke_api
from llm_red_team.attacks import load_attacks
from llm_red_team.runner import build_report, run_attack, should_fail_build, write_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=PROJECT_ROOT / "attacks" / "catalog.json")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports")
    parser.add_argument("--no-mutations", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--llm-judge", action="store_true")
    parser.add_argument(
        "--transport",
        choices=("direct", "api"),
        default="direct",
        help="call Bedrock directly or the deployed IAM-protected API",
    )
    args = parser.parse_args()

    attacks = load_attacks(args.catalog, include_mutations=not args.no_mutations)
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be at least 1")
        attacks = attacks[: args.limit]

    results = []
    for index, attack in enumerate(attacks, start=1):
        result = run_attack(
            attack,
            invoker=invoke_api if args.transport == "api" else None,
            use_llm_judge=args.llm_judge,
        )
        results.append(result)
        print(f"[{index:02d}/{len(attacks):02d}] {attack.id}: {result.status.upper()}")
        if result.error:
            print(f"  {result.error}")
        for reason in result.deterministic_reasons:
            print(f"  {reason}")

    report = build_report(results)
    json_path, markdown_path = write_report(report, args.output_dir)
    summary = report["summary"]
    print(
        f"\nSummary: {summary['passed']} passed, {summary['failed']} failed, "
        f"{summary['errors']} errors."
    )
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    return 1 if should_fail_build(report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
