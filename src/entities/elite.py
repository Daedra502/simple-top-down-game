"""Elite/tiered enemy construction (DESIGN.md Phase 12).

An "EliteEnemy" is just a normal data-driven Enemy with a *tier* (Normal..Elite)
and a set of *elite affixes* applied on top. Tier scales hp/damage/size/color;
affixes layer extra hp plus behaviors (regen, lifesteal, reflect, cc-immunity,
teleport, and on-death novas). Behaviors are stored as data on the enemy and run
by Enemy.update (self-contained ones) or the Game (ones needing world context).
"""
import pygame

from src.entities.enemy import Enemy
from src.core.data_loader import load_json


def _blend(base, tint, t=0.5):
    if tint is None:
        return base
    return tuple(int(base[i] + (tint[i] - base[i]) * t) for i in range(3))


def _rebuild_sprite(enemy):
    enemy.width = max(8, int(enemy.width))
    enemy.height = max(8, int(enemy.height))
    enemy.image = pygame.Surface((enemy.width, enemy.height))
    enemy.image.fill(enemy.color)
    enemy.rect = enemy.image.get_rect()
    enemy.rect.center = (enemy.x, enemy.y)


def build_enemy(enemy_type, tier="normal", affix_ids=None):
    """Create an Enemy of the given tier with the given elite affixes applied."""
    affix_ids = affix_ids or []
    tiers = load_json("spawn_director.json")["tiers"]
    affix_data = load_json("elite_affixes.json")

    e = Enemy(0, 0, enemy_type)
    e.tier = tier

    tcfg = tiers.get(tier, tiers["normal"])
    e.max_health = int(e.max_health * tcfg["hp"])
    e.health = e.max_health
    e.damage = int(e.damage * tcfg["damage"])
    e.width = int(e.width * tcfg["size"])
    e.height = int(e.height * tcfg["size"])
    e.color = _blend(e.color, tcfg.get("tint"))

    on_death = []
    for aid in affix_ids:
        a = affix_data.get(aid)
        if not a:
            continue
        e.elite_affixes.append(aid)
        e.max_health = int(e.max_health * a.get("hp", 1.0))
        e.health = e.max_health
        e.color = _blend(e.color, a.get("tint"), 0.45)

        if a.get("cc_immune"):
            e.cc_immune = True
        if "regen" in a:
            e.behaviors["regen"] = max(e.behaviors.get("regen", 0), a["regen"])
        if "lifesteal" in a:
            e.behaviors["lifesteal"] = a["lifesteal"]
        if "reflect" in a:
            e.behaviors["reflect"] = a["reflect"]
        if "teleport" in a:
            e.behaviors["teleport"] = a["teleport"]
        if "on_death" in a:
            on_death.append(a["on_death"])

    if on_death:
        e.behaviors["on_death"] = on_death

    e.is_elite = tier in ("champion", "elite") or bool(affix_ids)
    _rebuild_sprite(e)
    return e
