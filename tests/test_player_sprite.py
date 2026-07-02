"""Tests for the procedural animated player sprite (hooded battle-mage) and its
integration into the Player (facing, cast pose, draw). ASCII-only output.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.entities.player_sprite import PlayerSprite
from src.entities.player import Player


def check(label, cond):
    assert cond, label


def test_all_frames_generated():
    sp = PlayerSprite(target_size=20)
    for facing in ("down", "up", "left", "right"):
        check(f"{facing} idle frame exists", sp.idle[facing].get_width() > 0)
        check(f"{facing} cast frame exists", sp.cast[facing].get_width() > 0)
        check(f"{facing} has a 4-frame walk cycle", len(sp.walk[facing]) == 4)


def test_frame_selection_by_state():
    sp = PlayerSprite(target_size=20)
    # Casting beats moving.
    surf, _ = sp.frame("down", moving=True, casting=0.2, dt=0.016)
    check("cast pose used while casting", surf is sp.cast["down"])
    # Moving (not casting) picks a walk frame.
    surf, _ = sp.frame("right", moving=True, casting=0.0, dt=0.016)
    check("walk frame used while moving", surf in sp.walk["right"])
    # Idle returns an idle frame and a small bob offset over time.
    bobs = set()
    for _ in range(40):
        _, bob = sp.frame("down", moving=False, casting=0.0, dt=0.1)
        bobs.add(bob)
    check("idle produces a breathing bob", bobs == {0, 1})


def test_player_facing_follows_velocity():
    p = Player(0, 0)
    p.velocity_x, p.velocity_y = 5, 0
    p.update(dt=0.016)
    check("faces right", p.facing == "right")
    p.velocity_x, p.velocity_y = 0, -5
    p.update(dt=0.016)
    check("faces up", p.facing == "up")
    p.velocity_x, p.velocity_y = -5, 1
    p.update(dt=0.016)
    check("dominant axis wins (left)", p.facing == "left")


def test_cast_pose_decays():
    p = Player(0, 0)
    p.notify_cast(0.25)
    check("cast pose armed", p._cast_pose == 0.25)
    for _ in range(20):
        p.update(dt=0.016)
    check("cast pose decays to zero", p._cast_pose == 0.0)


def test_player_draw_runs_headless():
    p = Player(300, 300)
    surf = pygame.Surface((640, 480))
    p.update(dt=0.016)
    p.draw(surf, cam=(150, 150))   # no exception = pass
    check("player draw ran", True)
