"""Phase 3 tests: XP curve, level-ups, stat growth, skill points, cue event.

ASCII-only output. Run: python test_phase3_leveling.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.entities.player import Player
from src.systems import leveling


def check(label, cond):
    assert cond, label


def test_phase3_leveling():
    print("PHASE 3 -- Leveling & Progression")

    # Data-driven XP curve
    check("xp_to_next(1) == 100", leveling.xp_to_next(1) == 100)
    check("curve is data-driven (matches base*level**exp)",
          leveling.xp_to_next(7) == int(100 * 7 ** 1.3))
    check("xp_to_next at cap is 0", leveling.xp_to_next(leveling.max_level()) == 0)

    # A single level-up grants the right things
    p = Player(0, 0)
    hp0, mp0, dmg0 = p.max_health, p.max_mana, p.damage
    cues = []
    p.on_level_up.subscribe(lambda lv: cues.append(lv))

    p.add_experience(leveling.xp_to_next(1))  # exactly one level
    check("reached level 2", p.level == 2)
    check("granted 1 skill point", p.skill_points == 1)
    check("max_health grew by 10", p.max_health == hp0 + 10)
    check("max_mana grew by 5", p.max_mana == mp0 + 5)
    check("damage grew by 1", p.damage == dmg0 + 1)
    check("health restored to full", p.health == p.max_health)
    check("mana restored to full", p.mana == p.max_mana)
    check("on_level_up fired once with new level", cues == [2])

    # XP rolls over; multiple level-ups in one grant
    p2 = Player(0, 0)
    levels = p2.add_experience(10 ** 6)
    check("bulk XP grants many levels", levels >= 10 and p2.level == 1 + levels)
    check("skill points match levels gained", p2.skill_points == levels)

    # Hard cap
    p3 = Player(0, 0)
    p3.add_experience(10 ** 9)
    check("cannot exceed max level", p3.level == leveling.max_level())
    check("xp_to_level is 0 at cap", p3.xp_to_level == 0)
