"""Leveling & progression system (DESIGN.md Phase 3).

XP curve and per-level growth live in data/tuning.json (R5), not in code, so the
Phase 10 balance pass has a single place to tune. The player's level / XP /
skill-point state stays on the Player object (the save anchor for Phase 10).
"""
from src.core.data_loader import load_json


def _cfg():
    return load_json("tuning.json")


def max_level():
    return _cfg()["xp"]["max_level"]


def xp_to_next(level):
    """XP required to advance *from* the given level. 0 at/above max level."""
    xp = _cfg()["xp"]
    if level >= xp["max_level"]:
        return 0
    return int(xp["base"] * (level ** xp["exponent"]))


def gain_xp(player, amount):
    """Add XP and process any resulting level-ups. Returns levels gained."""
    player.experience += amount
    levels_gained = 0

    need = xp_to_next(player.level)
    while need > 0 and player.experience >= need:
        player.experience -= need
        _level_up(player)
        levels_gained += 1
        need = xp_to_next(player.level)

    player.xp_to_level = xp_to_next(player.level)
    return levels_gained


def _level_up(player):
    """Advance one level: grant a point, grow core stats, restore resources, cue."""
    player.level += 1
    player.skill_points += 1

    # Core-stat growth modifies the base stats (the source of truth).
    for stat, value in _cfg()["per_level"].items():
        player.stats.base[stat] = player.stats.base.get(stat, 0) + value
    player.recompute()

    # Level-up fully restores health and mana.
    player.health = player.max_health
    player.mana = player.max_mana

    # Feedback cue: anyone (the HUD) can listen.
    if hasattr(player, "on_level_up"):
        player.on_level_up.fire(player.level)
