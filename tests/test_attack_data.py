from pathlib import Path

from llm_red_team.attacks import load_attacks


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_initial_attack_library_is_valid() -> None:
    attacks = load_attacks(PROJECT_ROOT / "attacks" / "initial.json")

    assert len(attacks) == 5
    assert len({attack.id for attack in attacks}) == len(attacks)
    assert all(attack.severity == "critical" for attack in attacks)

