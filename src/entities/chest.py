import math

import pygame


class Chest:
    """Treasure chest that can be opened for money, XP and (via the game) loot.

    Drawn camera-relative like the other world entities. Unopened chests pulse a
    soft golden glow so they read as a reward beacon; opened ones go dark.
    """

    # Pre-rendered aura surfaces shared by every chest, keyed by glow radius.
    # The pulse only visits ~17 integer radii, so this caps allocations at a
    # handful of small surfaces for the whole game instead of one per frame.
    _AURA_CACHE = {}

    def __init__(self, x, y, copper=0, silver=0, gold=0, diamond=0, xp=0,
                 loot=0):
        self.x = x
        self.y = y
        self.width = 30
        self.height = 30

        # Rewards
        self.copper = copper
        self.silver = silver
        self.gold = gold
        self.diamond = diamond
        self.xp_reward = xp
        self.loot = loot          # number of equipment drops (granted by the game)

        self.opened = False
        self._pulse = 0.0         # animates the unopened glow
        self.color = (200, 150, 50)

    def update(self, dt):
        """Advance the idle glow animation (no-op once opened)."""
        if not self.opened:
            self._pulse = (self._pulse + dt * 3.0) % (2 * math.pi)

    def open(self):
        """Open the chest, returning its reward bundle (None if already open)."""
        if not self.opened:
            self.opened = True
            self.color = (100, 75, 25)
            return {
                'copper': self.copper,
                'silver': self.silver,
                'gold': self.gold,
                'diamond': self.diamond,
                'xp': self.xp_reward,
                'loot': self.loot,
            }
        return None

    @classmethod
    def _aura(cls, glow):
        """Return a cached golden aura surface of the given radius."""
        surf = cls._AURA_CACHE.get(glow)
        if surf is None:
            surf = pygame.Surface((glow * 2, glow * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 215, 90, 70), (glow, glow), glow)
            cls._AURA_CACHE[glow] = surf
        return surf

    def draw(self, surface, cam=(0, 0)):
        """Draw the chest at its world position, offset by the camera."""
        cx = int(self.x - cam[0])
        cy = int(self.y - cam[1])

        if not self.opened:
            # Pulsing golden aura (cached per radius) so loot reads at a distance.
            glow = int(22 + 8 * math.sin(self._pulse))
            surface.blit(self._aura(glow), (cx - glow, cy - glow))

        w, h = self.width, self.height
        base = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        body = self.color
        lid = tuple(min(255, c + 40) for c in body)
        band = (90, 60, 20) if not self.opened else (60, 45, 18)

        pygame.draw.rect(surface, body, base)
        pygame.draw.rect(surface, lid, (base.x, base.y, w, h // 2))     # lid
        pygame.draw.rect(surface, band, (cx - 3, base.y, 6, h))         # latch
        pygame.draw.rect(surface, (20, 20, 20), base, 2)               # outline
