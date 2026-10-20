from __future__ import annotations

import os
from pathlib import Path

import pytest

from llm_red_team.attacks import Attack, load_attacks
from llm_red_team.judge import judge_response
from llm_red_team.target import draft_reply


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ATTACKS = load_attacks(PROJECT_ROOT / "attacks" / "initial.json")

pytestmark = [
    pytest.mark.bedrock,
    pytest.mark.skipif(
        not os.getenv("BEDROCK_MODEL_ID"),
        reason="BEDROCK_MODEL_ID is required for paid Bedrock integration tests",
    ),
]


@pytest.mark.parametrize("attack", ATTACKS, ids=lambda attack: attack.id)
def test_critical_attack_is_blocked(attack: Attack) -> None:
    response = draft_reply(
        customer_message=attack.customer_message,
        reference_document=attack.reference_document,
    )
    result = judge_response(response)

    assert result.passed, f"Judge reasons: {result.reasons}\nResponse:\n{response}"

