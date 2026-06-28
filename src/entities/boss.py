"""Rift boss entity (DESIGN.md Phase 5).

A boss is a large, data-driven Enemy (data/bosses.json). It reuses Enemy's
chase AI, attack, and draw logic; only construction differs (boss stats + GR
scaling). On death the game's rift-boss handler grants big, scaled rewards and
-- in a normal rift -- a Rift Keystone.
"""
import pygame
import random
import math

from src.entities.enemy import Enemy
from src.systems.ailments import AilmentManager
from src.core.data_loader import load_json


def boss_keys():
    """All boss ids in the pool."""
    return list(load_json("bosses.json").keys())


class Boss(Enemy):
    """A scaled boss built from a bosses.json row."""

    def __init__(self, x, y, boss_key, hp_mult=1.0, dmg_mult=1.0, reward_mult=1.0):
        data = load_json("bosses.json")[boss_key]

        # Bypass Enemy.__init__ (which reads enemies.json); set boss fields here
        # and inherit Enemy's behavior methods.
        from src.entities.entity import Entity
        Entity.__init__(self, x, y, int(data["max_health"] * hp_mult))

        self.boss_key = boss_key
        self.enemy_type = None
        self.name = data["name"]
        self.theme = data.get("theme")
        self.abilities = list(data.get("abilities", []))
        self.is_boss = True
        self.progress_value = 0  # bosses don't fill the rift bar

        # Phase 12 fields (Boss bypasses Enemy.__init__, so set them here).
        self.family = None
        self.resistances = {}
        self.tier = "boss"
        self.is_elite = False
        self.elite_affixes = []
        self.behaviors = {}
        self.cc_immune = False
        self.is_treasure_goblin = False
        self.loot_drops = 1
        self._behavior_timer = 0.0

        self.width = data["width"]
        self.height = data["height"]
        self.color = tuple(data["color"])
        self.damage = int(data["damage"] * dmg_mult)
        self.speed = data["speed"]

        self.experience_reward = int(data["xp_reward"] * reward_mult)
        self.money_reward = {
            coin: int(amount * reward_mult)
            for coin, amount in data["money"].items()
        }

        self.elemental_effects = AilmentManager(self)

        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.center = (self.x, self.y)

        # AI state (same fields Enemy.update expects)
        self.target = None
        self.ai_timer = 0
        self.attack_cooldown = 0
        self.wander_direction = random.uniform(0, 2 * math.pi)

        # Blink AI: rift bosses teleport near the player every 20-30s so the
        # fight stays mobile and they can't be permanently kited.
        self.teleport_interval = random.uniform(20.0, 30.0)
        self.teleport_timer = self.teleport_interval
        self.teleport_flash = 0.0   # >0 briefly after a blink, for a visual cue

    def maybe_teleport(self, player, dt):
        """Tick the blink timer; on expiry, jump to a random ring around player.

        Returns True on the frame a teleport happens. Lands 180-360px from the
        player (off melee range but on-screen) and rerolls the next interval.
        """
        if self.teleport_flash > 0:
            self.teleport_flash = max(0.0, self.teleport_flash - dt)

        self.teleport_timer -= dt
        if self.teleport_timer > 0:
            return False

        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(180.0, 360.0)
        self.x = player.x + math.cos(angle) * dist
        self.y = player.y + math.sin(angle) * dist
        self.rect.center = (self.x, self.y)

        self.teleport_interval = random.uniform(20.0, 30.0)
        self.teleport_timer = self.teleport_interval
        self.teleport_flash = 0.45
        return True
