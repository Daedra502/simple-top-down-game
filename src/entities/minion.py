"""Summoned minion (DESIGN.md Phase 13 -- Summon Skeleton).

A short-lived ally that drifts toward the nearest enemy and periodically deals
damage to it through the shared damage pipeline. Kept intentionally light.
"""
import math
import pygame

from src.core.damage import roll_damage


class Minion:
    def __init__(self, x, y, damage, duration, owner, color=(220, 220, 200)):
        self.x = x
        self.y = y
        self.damage = damage
        self.lifetime = duration
        self.owner = owner          # the player (source for crit/scaling)
        self.color = color
        self.speed = 3.2
        self.attack_range = 36
        self.attack_cd = 0.0
        self.attack_interval = 0.6
        self.size = 12

    @property
    def alive(self):
        return self.lifetime > 0

    def update(self, enemies, dt):
        self.lifetime -= dt
        if self.attack_cd > 0:
            self.attack_cd -= dt

        target = self._nearest(enemies)
        if target is None:
            return None

        dist = math.hypot(target.x - self.x, target.y - self.y)
        if dist > self.attack_range:
            self.x += (target.x - self.x) / dist * self.speed
            self.y += (target.y - self.y) / dist * self.speed
        elif self.attack_cd <= 0:
            self.attack_cd = self.attack_interval
            dmg, _ = roll_damage(self.owner, target, self.damage, "physical")
            return (target, dmg)   # Game applies it so on_death rewards fire
        return None

    def _nearest(self, enemies):
        best, best_d = None, 1e18
        for e in enemies:
            if e.health <= 0:
                continue
            d = math.hypot(e.x - self.x, e.y - self.y)
            if d < best_d:
                best, best_d = e, d
        return best

    def draw(self, surface, cam=(0, 0)):
        pos = (int(self.x - cam[0]), int(self.y - cam[1]))
        pygame.draw.circle(surface, self.color, pos, self.size // 2)
        pygame.draw.circle(surface, (255, 255, 255), pos, self.size // 2, 1)
