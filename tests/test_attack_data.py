from pathlib import Path

from llm_red_team.attacks import load_attacks


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATALOG = PROJECT_ROOT / "attacks" / "catalog.json"


def test_attack_catalog_expands_to_fifty_cases() -> None:
    seeds = load_attacks(CATALOG, include_mutations=False)
    attacks = load_attacks(CATALOG)

    assert len(seeds) == 30
    assert len(attacks) == 50
    assert len({attack.id for attack in attacks}) == len(attacks)
    assert all(attack.severity == "critical" for attack in attacks)


def test_catalog_covers_required_categories_and_turkish() -> None:
    attacks = load_attacks(CATALOG)

    assert {attack.category for attack in attacks} >= {
        "direct_prompt_injection",
        "indirect_prompt_injection",
        "jailbreak_role_play",
        "system_prompt_leakage",
        "encoded_prompt_injection",
    }
    assert sum(attack.language == "tr" for attack in attacks) >= 6
    assert sum(attack.mutation == "base64" for attack in attacks) == 10
    assert sum(attack.mutation == "multi_turn" for attack in attacks) == 10


def test_multi_turn_mutations_have_two_messages() -> None:
    attacks = load_attacks(CATALOG)
    variants = [attack for attack in attacks if attack.mutation == "multi_turn"]

    assert variants
    assert all(len(attack.messages) == 2 for attack in variants)

