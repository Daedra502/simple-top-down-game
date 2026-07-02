"""Tests for the pixel-art spell projectile visuals: trail tracking, element
styling, and clean rendering of every element. ASCII-only output.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.spells.spells import Projectile


def check(label, cond):
    assert cond, label


def test_projectile_builds_a_bounded_trail():
    p = Projectile(0, 0, 100, 0, 5, 10, (255, 120, 30), radius=8)
    for _ in range(20):
        p.update()
    check("trail is populated", len(p._trail) > 0)
    check("trail length is capped", len(p._trail) <= Projectile._TRAIL_LEN)
    check("projectile advanced along its heading", p.x > 0)


def test_projectile_tracks_heading_angle():
    p = Projectile(0, 0, 0, 100, 5, 10, (200, 200, 200))  # aimed straight down
    p.update()
    import math
    check("angle points downward", abs(p.angle - math.pi / 2) < 0.2)


def test_every_element_renders_clean():
    surf = pygame.Surface((200, 200))
    for elem, col in (("fire", (255, 120, 30)), ("cold", (120, 200, 245)),
                      ("lightning", (255, 245, 130)), ("physical", (180, 180, 190))):
        p = Projectile(100, 100, 300, 100, 5, 10, col, radius=8)
        p.element_type = elem
        for _ in range(4):
            p.update()
        p.draw(surf, cam=(0, 0))
    check("all element projectiles drew without error", True)


def test_default_element_is_neutral():
    p = Projectile(0, 0, 1, 0, 5, 10, (150, 150, 150))
    check("defaults to physical/neutral styling", p.element_type == "physical")
