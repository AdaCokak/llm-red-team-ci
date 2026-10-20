"""Attack-case loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Attack:
    """One known attack used as a security regression case."""

    id: str
    category: str
    severity: str
    customer_message: str
    reference_document: str | None


def load_attacks(path: Path) -> list[Attack]:
    """Load attacks from JSON and reject malformed or duplicate cases."""

    raw_attacks = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_attacks, list) or not raw_attacks:
        raise ValueError("Attack file must contain a non-empty JSON list.")

    required_fields = {
        "id",
        "category",
        "severity",
        "customer_message",
        "reference_document",
    }
    attacks: list[Attack] = []
    seen_ids: set[str] = set()

    for index, item in enumerate(raw_attacks):
        if not isinstance(item, dict):
            raise ValueError(f"Attack at index {index} must be a JSON object.")

        missing = required_fields - item.keys()
        extra = item.keys() - required_fields
        if missing or extra:
            raise ValueError(
                f"Attack at index {index} has missing fields {sorted(missing)} "
                f"and extra fields {sorted(extra)}."
            )

        attack = Attack(**item)
        if attack.id in seen_ids:
            raise ValueError(f"Duplicate attack ID: {attack.id}")
        if attack.severity not in {"low", "medium", "high", "critical"}:
            raise ValueError(f"Invalid severity for {attack.id}: {attack.severity}")
        if not attack.customer_message.strip():
            raise ValueError(f"Attack {attack.id} has an empty customer message.")

        seen_ids.add(attack.id)
        attacks.append(attack)

    return attacks

