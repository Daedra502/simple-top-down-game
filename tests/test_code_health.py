"""Tests for the code-health pass: shared player-damage path (armor applies to
bramble hazards), solids-only obstacle collision with minions included,
obstacle spawn separation, off-screen ring spawns, and the cached chest aura.
ASCII-only output.
"""
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from main import Game
from src.entities.obstacle import Obstacle
from src.entities.chest import Chest


def check(label, cond):
    assert cond, label


def test_damage_player_applies_armor_to_physical_only():
    g = Game(900, 650)
    # Force known mitigation: some armor, no resistances.
    g.player.armor_damage_reduction = lambda: 0.5
    g.player.resistances = {}
    g.player.health = g.player.max_health = 1000

    before = g.player.health
    dealt = g._damage_player(100, 'physical')
    check("physical damage halved by 50% armor", abs(dealt - 50) < 1e-6)
    check("physical damage actually applied", abs((before - g.player.health) - 50) < 1e-6)

    # Fire ignores armor (armor is physical mitigation only).
    g.player.health = 1000
    dealt_fire = g._damage_player(100, 'fire')
    check("fire damage ignores armor", abs(dealt_fire - 100) < 1e-6)


def test_bramble_hazard_uses_armor():
    g = Game(900, 650)
    g.player.armor_damage_reduction = lambda: 0.5
    g.player.resistances = {}
    g.player.health = g.player.max_health = 1000
    # Drop a bramble right on the player and force the hazard tick.
    g.world.obstacles = [Obstacle(g.player.x, g.player.y, "brambles", radius=30)]
    g._hazard_tick = 0.0
    g._resolve_obstacle_collisions()
    dmg_taken = 1000 - g.player.health
    # Bramble base damage is 4; with 50% armor it should be ~2, not 4.
    check("bramble damage was mitigated by armor", 0 < dmg_taken < 4)


def test_obstacle_collision_includes_minions():
    g = Game(900, 650)

    class Dummy:
        def __init__(self, x, y):
            self.x, self.y = x, y
            self.size = 10
    m = Dummy(5.0, 0.0)
    g.minions = [m]
    g.world.obstacles = [Obstacle(0.0, 0.0, "rock", radius=30)]
    g.world.enemies = []
    g._resolve_obstacle_collisions()
    check("minion pushed out of the solid rock",
          math.hypot(m.x, m.y) >= 30 + 10 - 1e-3)


def test_obstacle_collision_skips_non_solids_for_movers():
    # A bramble (non-solid) must never displace a mover.
    g = Game(900, 650)

    class Dummy:
        x, y, size = 5.0, 0.0, 10
    d = Dummy()
    g.minions = [d]
    g.world.enemies = []
    g.world.obstacles = [Obstacle(0.0, 0.0, "brambles", radius=30)]
    g._hazard_tick = 999  # don't apply damage this call
    g._resolve_obstacle_collisions()
    check("non-solid hazard did not move the minion", (d.x, d.y) == (5.0, 0.0))


def test_obstacle_spawns_keep_their_distance():
    g = Game(900, 650)
    g.world.obstacles = []
    g.world.chests = []
    for _ in range(g.max_obstacles * 3):
        g._spawn_obstacle()
    obs = g.world.obstacles
    for i in range(len(obs)):
        for j in range(i + 1, len(obs)):
            d = math.hypot(obs[i].x - obs[j].x, obs[i].y - obs[j].y)
            check("obstacles never overlap", d > obs[i].radius + obs[j].radius)


def test_ring_spawns_are_off_screen():
    g = Game(1200, 800)
    half_diag = math.hypot(g.width, g.height) / 2
    for _ in range(200):
        x, y = g._ring_spawn_point()
        d = math.hypot(x - g.player.x, y - g.player.y)
        check("spawn point is beyond the visible half-diagonal", d >= half_diag)


def test_chest_aura_surfaces_are_cached():
    Chest._AURA_CACHE.clear()
    c = Chest(0, 0)
    a1 = Chest._aura(20)
    a2 = Chest._aura(20)
    check("same radius returns the same cached surface", a1 is a2)
    check("cache holds one entry for one radius", len(Chest._AURA_CACHE) == 1)
    Chest._aura(24)
    check("distinct radius adds one entry", len(Chest._AURA_CACHE) == 2)


def test_chest_open_still_returns_bundle():
    c = Chest(0, 0, copper=10, loot=2)
    bundle = c.open()
    check("open returns rewards", bundle and bundle["loot"] == 2)
    check("re-open returns None", c.open() is None)
    check("no dead sprite state remains",
          not hasattr(c, "image") and not hasattr(c, "rect"))
