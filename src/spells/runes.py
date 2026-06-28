"""Rune system (DESIGN.md Phase 14).

Runes are composable cast-plan transforms. A skill's base cast plan (Phase 13)
is passed through each equipped rune, so combinations stack -- e.g. Fireball +
Added Projectiles + Chain + Meteor Conversion turns a single bolt into a chaining
meteor barrage ("Meteor Shower") with no new skill.
"""
from src.core.data_loader import load_json

MAX_RUNE_SLOTS = 3


def load_runes():
    return load_json("runes.json")


def _apply_one(plan, effects):
    for key, val in effects.items():
        if key == "add_projectiles":
            plan["count"] = plan.get("count", 1) + val
        elif key == "pierce":
            plan["pierce"] = plan.get("pierce", 0) + val
        elif key == "chain":
            plan["chain"] = plan.get("chain", 0) + val
        elif key == "return":
            plan["return"] = True
        elif key == "orbit":
            plan["orbit"] = True
        elif key == "auto_target":
            plan["auto_target"] = True
        elif key == "cast_on_kill":
            plan["cast_on_kill"] = True
        elif key == "convert_element":
            plan["element"] = val
        elif key == "radius_mult":
            if "radius" in plan:
                plan["radius"] = plan["radius"] * (1 + val)
            if "aoe_radius" in plan:
                plan["aoe_radius"] = plan["aoe_radius"] * (1 + val)
        elif key == "damage_mult":
            plan["damage"] = plan.get("damage", 0) * (1 + val)
        elif key == "extra_nova":
            plan["extra_nova"] = max(plan.get("extra_nova", 0), val)
        elif key == "lingering":
            plan["lingering"] = val
        elif key == "convert_aoe":
            # Transform a projectile into a targeted AoE (e.g. Meteor Conversion).
            plan["kind"] = "aoe"
            plan["at"] = "target"
            plan["aoe_radius"] = max(plan.get("aoe_radius", 0), val)
    return plan


def apply_runes(plan, rune_ids):
    """Run the plan through every equipped rune, in order."""
    if not rune_ids:
        return plan
    runes = load_runes()
    for rid in rune_ids:
        rune = runes.get(rid)
        if rune:
            _apply_one(plan, rune.get("effects", {}))
    return plan
