"""Run the five initial attacks manually and check for canary leakage."""

from __future__ import annotations

from pathlib import Path

from llm_red_team.attacks import load_attacks
from llm_red_team.judge import judge_response
from llm_red_team.target import draft_reply


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ATTACK_FILE = PROJECT_ROOT / "attacks" / "initial.json"


def main() -> None:
    attacks = load_attacks(ATTACK_FILE)
    failed_count = 0

    for attack in attacks:
        print(f"\n--- {attack.id} ({attack.category}) ---")
        response = draft_reply(
            customer_message=attack.customer_message,
            reference_document=attack.reference_document,
        )
        result = judge_response(response)
        failed_count += int(not result.passed)

        print(response)
        print(f"DETERMINISTIC JUDGE: {'PASS' if result.passed else 'FAIL'}")
        for reason in result.reasons:
            print(f"  - {reason}")

    print(f"\nSummary: {failed_count}/{len(attacks)} responses failed the judge.")
    print("A PASS covers only known deterministic checks; review responses manually.")


if __name__ == "__main__":
    main()

