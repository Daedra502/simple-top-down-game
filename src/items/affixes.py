"""Affix rolling for armor and jewelry (DESIGN.md Phase 6).

Affixes are defined in data/affixes.json (R5). A roll picks N affixes (N by
rarity) without replacement, weighted by ``weight`` and restricted to the item's
slot category, then rolls a value scaled by item level (ilvl).
"""
import random

from src.core.data_loader import load_json

# How many affixes each rarity rolls (keyed by ItemRarity.value).
AFFIX_COUNT_BY_RARITY = {0: 1, 1: 2, 2: 3, 3: 4}

_RESIST_SUFFIX = "_resistance"


def _pool():
    return load_json("affixes.json")


def affix_count(rarity_value):
    return AFFIX_COUNT_BY_RARITY.get(rarity_value, 1)


def is_resistance_stat(stat):
    return stat.endswith(_RESIST_SUFFIX)


def resistance_element(stat):
    """'fire_resistance' -> 'fire' (matches ElementType strings)."""
    return stat[: -len(_RESIST_SUFFIX)]


def roll_affixes(slot_category, ilvl, rarity_value):
    """Return a list of rolled affixes: {id, stat, value, label, is_percent}."""
    pool = _pool()
    candidates = [(aid, a) for aid, a in pool.items()
                  if slot_category in a["slots"]]
    n = min(affix_count(rarity_value), len(candidates))

    rolled = []
    remaining = candidates[:]
    for _ in range(n):
        weights = [a["weight"] for _, a in remaining]
        idx = random.choices(range(len(remaining)), weights=weights)[0]
        aid, a = remaining.pop(idx)

        value = random.uniform(a["min"], a["max"]) + a["per_ilvl"] * ilvl
        if a.get("is_int"):
            value = int(round(value))
        else:
            value = round(value, 3)

        rolled.append({
            "id": aid,
            "stat": a["stat"],
            "value": value,
            "label": a.get("label", aid),
            "is_percent": not a.get("is_int", False),
        })
    return rolled
