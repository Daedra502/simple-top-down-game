"""Phase 15 tests: ascendancy specialization + keystones, atlas world-shaping.

ASCII-only output. Run: python test_phase15_endgame.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.progression.ascendancy import AscendancyManager, UNLOCK_LEVEL
from src.progression.atlas import AtlasManager
from src.entities.enemy import Enemy, EnemyType
from main import Game


def check(label, cond):
    assert cond, label


def test_phase15_endgame(test_slot):
    print("PHASE 15 -- Ascendancy & Atlas")

    # Ascendancy is gated by level and permanent
    a = AscendancyManager()
    check("4 ascendancy classes exist", len(a.available_classes()) == 4)
    check("cannot choose below unlock level", a.choose("berserker", UNLOCK_LEVEL - 1) is False)
    check("can choose at unlock level", a.choose("berserker", UNLOCK_LEVEL) is True)
    check("choice is permanent (cannot re-choose)", a.choose("elementalist", 50) is False)

    # Points accrue at milestones; allocation follows the in-tree edges
    a2 = AscendancyManager()
    a2.choose("berserker", 50)
    check("points available at level 50", a2.points_available(50) > 0)
    check("entry node (no edges) allocatable", a2.allocate("bs_core", 50))
    check("cannot allocate a disconnected node", not a2.allocate("bs_glass", 50))  # needs bs_speed
    check("connected node allocatable", a2.allocate("bs_speed", 50))
    check("now the keystone node is reachable", a2.allocate("bs_glass", 50))

    # Keystone: Glass Cannon (+100% damage, -50% max HP) via the Stats layer
    g = Game()
    g.player.add_experience(10 ** 9)
    g.ascendancy.choose("berserker", g.player.level)
    for n in ("bs_core", "bs_speed", "bs_glass"):
        g.ascendancy.allocate(n, g.player.level)
    base_hp = g.player.stats.base["max_health"]
    g.recompute_player_stats()
    check("Glass Cannon halves max HP", g.player.max_health < base_hp)
    check("Glass Cannon roughly doubles damage",
          g.player.damage >= int(g.player.stats.base["damage"] * 1.8))

    # Keystone: Eternal Flame -> player's burns never expire
    g2 = Game()
    g2.player.add_experience(10 ** 9)
    g2.ascendancy.choose("elementalist", g2.player.level)
    for n in ("em_core", "em_burn", "em_eternal"):
        g2.ascendancy.allocate(n, g2.player.level)
    g2.recompute_player_stats()
    check("Eternal Flame flag set on player", g2.player.eternal_flame is True)
    victim = Enemy(0, 0, EnemyType.LICH)
    victim.elemental_effects.apply_burn(g2.player)
    check("Eternal Flame burns never expire",
          victim.elemental_effects.active["burn"]["remaining"] > 1000)

    # Keystone: Overcharged -> shock stacks uncapped
    g3 = Game()
    g3.player.add_experience(10 ** 9)
    g3.ascendancy.choose("riftwalker", g3.player.level)
    for n in ("rw_core", "rw_void", "rw_charge"):
        g3.ascendancy.allocate(n, g3.player.level)
    g3.recompute_player_stats()
    e = Enemy(0, 0, EnemyType.LICH)
    for _ in range(20):
        e.elemental_effects.apply_shock(g3.player)
    check("Overcharged removes the shock stack cap",
          e.elemental_effects.active["shock"]["stacks"] > 5)

    # Atlas: points from GR clears, neighbor-rule allocation, world-shaping effects
    at = AtlasManager()
    check("atlas root is free + pre-allocated", "atlas_start" in at.allocated)
    check("cannot allocate without points", not at.allocate("atlas_loot"))
    at.add_points(3)
    check("connected atlas node allocatable", at.allocate("atlas_loot"))
    check("atlas effects aggregate (loot quality)", at.get_effects()["loot_quality"] > 0)
    at.allocate("atlas_elites")
    check("atlas effects aggregate (elite density)", at.get_effects()["elite_density"] > 0)
    at.allocate("atlas_fire")
    check("atlas biome weight shapes the world",
          at.get_effects()["biome_weight"].get("burning_hellscape", 1) > 1)

    # Atlas influences the generated world in-game
    g4 = Game()
    g4.atlas.add_points(2)
    g4.atlas.allocate("atlas_fire")
    g4.recompute_player_stats()  # pushes biome weights into the world
    check("biome weights propagate to the world generator",
          g4.world.biome_weights.get("burning_hellscape", 1) > 1)

    # GR clears fund the atlas
    g5 = Game()
    pts0 = g5.atlas.points
    g5.rift.open_greater(5)
    g5.rift.begin_boss()
    boss = type("B", (), {"is_boss": True, "experience_reward": 1, "money_reward": {},
                          "x": 0, "y": 0, "behaviors": {}})()
    g5._on_rift_boss_killed(boss)
    check("clearing a Greater Rift grants an atlas point", g5.atlas.points == pts0 + 1)

    # Everything persists across save/load
    g6 = Game()
    g6.player.add_experience(10 ** 9)
    g6.ascendancy.choose("necromancer", g6.player.level)
    g6.ascendancy.allocate("nc_core", g6.player.level)
    g6.atlas.add_points(2)
    g6.atlas.allocate("atlas_events")
    g6.save_game(test_slot)
    g7 = Game()
    g7.load_game(test_slot)
    check("ascendancy class persists", g7.ascendancy.chosen == "necromancer")
    check("ascendancy nodes persist", "nc_core" in g7.ascendancy.allocated)
    check("atlas allocation persists", "atlas_events" in g7.atlas.allocated)
