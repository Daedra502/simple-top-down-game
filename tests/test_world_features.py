"""Tests for the new world-feature systems: treasure chests, map obstacles,
the level-100 cap, and the expanded audio engine (themes, monster + minion
voices). ASCII-only output.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random

from main import Game
from src.entities.obstacle import Obstacle
from src.entities.chest import Chest
from src.systems import leveling
from src.audio import sounds


def check(label, cond):
    assert cond, label


def test_level_cap_is_100():
    check("max level raised to 100", leveling.max_level() == 100)
    check("XP is still required at level 99", leveling.xp_to_next(99) > 0)
    check("no XP required at the cap", leveling.xp_to_next(100) == 0)


def test_chest_open_returns_loot_bundle():
    c = Chest(0, 0, copper=10, gold=2, xp=50, loot=2)
    rewards = c.open()
    check("open yields the reward bundle", rewards is not None)
    check("loot count is carried in the bundle", rewards["loot"] == 2)
    check("chest marks itself opened", c.opened)
    check("re-opening yields nothing", c.open() is None)


def test_obstacle_collision_pushes_entities_out():
    rock = Obstacle(0, 0, "rock", radius=30)

    class Dummy:
        x, y = 5.0, 0.0   # inside the rock

    d = Dummy()
    moved = rock.resolve_collision(d, entity_radius=10)
    check("solid obstacle pushes the entity out", moved)
    check("entity ends outside the obstacle",
          (d.x ** 2 + d.y ** 2) ** 0.5 >= 30 + 10 - 1e-6)

    # Non-solid hazards never block movement but do report contact.
    bram = Obstacle(0, 0, "brambles", radius=30)
    check("hazard does not block movement",
          not bram.resolve_collision(Dummy(), entity_radius=10))
    check("hazard reports contact for damage", bram.contact(Dummy(), entity_radius=10))


def test_world_features_spawn_and_cull():
    g = Game(900, 650)
    g.chest_spawn_interval = 0.01     # force a spawn quickly
    for _ in range(120):
        g.update()
    check("chests spawned (capped)", 0 < len(g.world.chests) <= g.max_chests)
    check("obstacles populated to target density",
          len(g.world.obstacles) == g.max_obstacles)


def test_audio_engine_builds_extended_palette():
    rng = random.Random(0)
    for theme in ("field", "dungeon", "town", "boss"):
        wave = sounds.compose_theme(theme, rng)
        check(f"{theme} theme renders audio", len(wave) > 0 and abs(wave).max() <= 1.0)

    for key in sounds._MONSTER_PROFILES:
        for kind in sounds._MONSTER_KINDS:
            check(f"{key} {kind} voice renders",
                  len(sounds.make_monster_sound(key, kind, rng)) > 0)

    for kind, recipe in sounds._MINION_RECIPES.items():
        check(f"minion {kind} cue renders", len(recipe(rng)) > 0)
