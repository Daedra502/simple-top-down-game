"""Phase 14 tests: rune modifiers compose to transform skills.

ASCII-only output. Run: python test_phase14_runes.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.spells.runes import apply_runes, load_runes, MAX_RUNE_SLOTS
from src.entities.enemy import Enemy, EnemyType
from main import Game


def check(label, cond):
    assert cond, label


def test_phase14_runes(test_slot):
    print("PHASE 14 -- Skill Modification & Rune System")

    runes = load_runes()
    check("rune catalog covers all modifier types",
          {runes[r]["modifier_type"] for r in runes} >= {"projectile", "area", "element", "behavior"})

    # Pure transform tests on a plan
    base = {"kind": "projectile", "count": 1, "radius": 8, "aoe_radius": 0,
            "damage": 100, "element": "fire"}
    check("added projectiles increases count",
          apply_runes(dict(base), ["added_projectiles"])["count"] == 3)
    check("element conversion changes element",
          apply_runes(dict(base), ["to_shock"])["element"] == "lightning")
    check("pierce flag is added", apply_runes(dict(base), ["pierce"])["pierce"] == 2)
    check("chain flag is added", apply_runes(dict(base), ["chain"])["chain"] == 3)
    check("larger radius scales radius",
          apply_runes(dict(base), ["larger_radius"])["radius"] > base["radius"])
    mc = apply_runes(dict(base), ["meteor_conversion"])
    check("meteor conversion turns projectile into AoE", mc["kind"] == "aoe" and mc["aoe_radius"] > 0)

    # Composition: Fireball + added projectiles + chain + meteor conversion = Meteor Shower
    g = Game()
    fb = g.skills.get("fireball")
    fb.equip_rune("added_projectiles")
    fb.equip_rune("chain")
    fb.equip_rune("meteor_conversion")
    plan = fb.cast_plan(g.player, g.player.x + 100, g.player.y)
    check("composed runes transform the skill (kind -> aoe)", plan["kind"] == "aoe")
    check("composed runes stack (count + chain present)",
          plan.get("count", 0) >= 3 and plan.get("chain", 0) >= 3)

    # Slot cap
    check("rune slots are capped", len(fb.runes) == MAX_RUNE_SLOTS)
    check("equipping past the cap fails", fb.equip_rune("pierce") is False)
    check("cannot equip the same rune twice", g.skills.get("ice_shard").equip_rune("to_ice")
          and not g.skills.get("ice_shard").equip_rune("to_ice"))

    # Runtime: pierce keeps a projectile alive through a hit
    g2 = Game()
    cl = g2.skills.get("chain_lightning")
    cl.equip_rune("pierce")
    g2.player.mana = 999
    g2._execute_cast(cl.cast_plan(g2.player, g2.player.x + 100, g2.player.y), cl)
    proj = g2.projectiles[-1]
    proj.x, proj.y = g2.player.x + 200, g2.player.y
    e = Enemy(proj.x, proj.y, EnemyType.LICH)
    e.resistances = {}
    g2.world.enemies.append(e)
    pierce_before = proj.pierce
    g2.update_projectiles(g2.world)
    check("piercing projectile survives a hit", proj in g2.projectiles)
    check("pierce count decremented on hit", proj.pierce == pierce_before - 1)

    # Runtime: lingering ground deals damage over time
    g3 = Game()
    pn = g3.skills.get("poison_nova")
    pn.equip_rune("lingering_ground")
    g3.player.mana = 999
    g3._execute_cast(pn.cast_plan(g3.player, g3.player.x, g3.player.y), pn)
    check("lingering ground spawns a zone", len(g3.ground_zones) == 1)
    victim = Enemy(g3.player.x, g3.player.y, EnemyType.LICH)
    victim.resistances = {}
    g3.world.enemies.append(victim)
    hp0 = victim.health
    g3.dt = 0.5
    g3._update_ground_zones()
    check("standing in lingering ground deals damage", victim.health < hp0)

    # Runes persist across save/load
    g4 = Game()
    g4.skills.get("meteor").equip_rune("larger_radius")
    g4.save_game(test_slot)
    g5 = Game()
    g5.load_game(test_slot)
    check("equipped runes persist across save/load",
          "larger_radius" in g5.skills.get("meteor").runes)
