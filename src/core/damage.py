"""Damage pipeline -- the single path every damage source routes through.

Pipeline stages (DESIGN.md Phase 2): base -> source modifiers (crit) ->
target amplifiers (shock; Vulnerable in Phase 7) -> resistances -> final.

The incoming ``base`` is expected to already include the source's flat damage
assembly (e.g. ``Player.get_spell_damage``); this stage adds the multiplicative
layers so values are never double-counted.
"""
import random

from src.core.data_loader import load_json

# Minimum damage so a hit always registers something.
MIN_DAMAGE = 1


def _ailment_cfg():
    return load_json("ailments.json")


def _target_amplifiers(source, target, element, dmg):
    """Apply shock, Vulnerable, and shatter multipliers from the target's state."""
    effects = getattr(target, "elemental_effects", None)
    if effects is None:
        return dmg

    # Shock increases all damage taken.
    if hasattr(effects, "get_shock_amplification"):
        dmg *= effects.get_shock_amplification()

    cfg = _ailment_cfg()

    # Vulnerable: +15% base (+ source's gear/tree Increased Vulnerable Damage).
    if hasattr(effects, "is_vulnerable") and effects.is_vulnerable():
        base = cfg["vulnerable"]["bonus_damage"]
        extra = getattr(source, "increased_vulnerable_damage", 0.0)
        dmg *= (1.0 + base + extra)

    # Shatter (Phase 9): frozen targets take bonus hit damage.
    if hasattr(effects, "is_frozen") and effects.is_frozen():
        dmg *= (1.0 + cfg.get("combos", {}).get("shatter_bonus", 0.0))

    return dmg


def roll_damage(source, target, base, element="physical"):
    """Compute final damage for one hit. Returns ``(final_damage, is_crit)``."""
    dmg = float(base)

    # --- source modifiers: critical strike ---
    crit_chance = getattr(source, "crit_chance", 0.0)
    crit_damage = getattr(source, "crit_damage", 1.5)
    is_crit = random.random() < crit_chance
    if is_crit:
        dmg *= crit_damage

    # --- target amplifiers (shock / Vulnerable / shatter) ---
    dmg = _target_amplifiers(source, target, element, dmg)

    # --- resistances ---
    if hasattr(target, "get_resistance"):
        resist_pct = target.get_resistance(element)  # 0..100
        dmg *= max(0.1, 1.0 - resist_pct / 100.0)

    return max(MIN_DAMAGE, dmg), is_crit


def apply_ailment_damage(target, amount, element="fire"):
    """Apply damage-over-time through the pipeline so resists + Vulnerable apply.

    Returns True if the tick killed the target.
    """
    dmg = float(amount)
    effects = getattr(target, "elemental_effects", None)
    cfg = _ailment_cfg()

    if effects is not None and hasattr(effects, "is_vulnerable") and effects.is_vulnerable():
        dmg *= (1.0 + cfg["vulnerable"]["bonus_damage"])
        # Burning + Vulnerable multiplies DoT (Phase 9 combo).
        if element == "fire":
            dmg *= cfg.get("combos", {}).get("burn_vulnerable_mult", 1.0)

    if hasattr(target, "get_resistance"):
        dmg *= max(0.1, 1.0 - target.get_resistance(element) / 100.0)

    return target.take_damage(max(MIN_DAMAGE, dmg))
