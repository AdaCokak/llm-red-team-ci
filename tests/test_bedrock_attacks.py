from __future__ import annotations

import os
from pathlib import Path

import pytest

from llm_red_team.attacks import Attack, load_attacks
from llm_red_team.runner import run_attack


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ATTACKS = load_attacks(PROJECT_ROOT / "attacks" / "catalog.json")

pytestmark = [
    pytest.mark.bedrock,
    pytest.mark.skipif(
        not os.getenv("BEDROCK_MODEL_ID"),
        reason="BEDROCK_MODEL_ID is required for paid Bedrock integration tests",
    ),
]


@pytest.mark.parametrize("attack", ATTACKS, ids=lambda attack: attack.id)
def test_critical_attack_is_blocked(attack: Attack) -> None:
    result = run_attack(attack)

    assert result.status == "pass", (
        f"Reasons: {result.deterministic_reasons}\n"
        f"Error: {result.error}\n"
        f"Responses: {result.responses}"
    )

