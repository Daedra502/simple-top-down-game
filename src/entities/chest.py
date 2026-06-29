import math

import pygame


class Chest(pygame.sprite.Sprite):
    """Treasure chest that can be opened for money, XP and (via the game) loot.

    Drawn camera-relative like the other world entities. Unopened chests pulse a
    soft golden glow so they read as a reward beacon across the map; opened ones
    go dark. ``radius`` is used for proximity opening and culling.
    """

    def __init__(self, x, y, copper=0, silver=0, gold=0, diamond=0, xp=0,
                 loot=0):
        super().__init__()

        self.x = x
        self.y = y
        self.width = 30
        self.height = 30
        self.radius = 18

        # Rewards
        self.copper = copper
        self.silver = silver
        self.gold = gold
        self.diamond = diamond
        self.xp_reward = xp
        self.loot = loot          # number of equipment drops (granted by the game)

        self.opened = False
        self._pulse = 0.0         # animates the unopened glow

        # Sprite surface (kept for MapManager compatibility / rect math).
        self.image = pygame.Surface((self.width, self.height))
        self.color = (200, 150, 50)
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.center = (self.x, self.y)

    def update(self, dt):
        """Advance the idle glow animation (no-op once opened)."""
        if not self.opened:
            self._pulse = (self._pulse + dt * 3.0) % (2 * math.pi)

    def open(self):
        """Open the chest, returning its reward bundle (None if already open)."""
        if not self.opened:
            self.opened = True
            self.color = (100, 75, 25)
            self.image.fill(self.color)
            return {
                'copper': self.copper,
                'silver': self.silver,
                'gold': self.gold,
                'diamond': self.diamond,
                'xp': self.xp_reward,
                'loot': self.loot,
            }
        return None

    def draw(self, surface, cam=(0, 0)):
        """Draw the chest at its world position, offset by the camera."""
        cx = int(self.x - cam[0])
        cy = int(self.y - cam[1])

        if not self.opened:
            # Pulsing golden aura so loot is visible from a distance.
            glow = int(22 + 8 * math.sin(self._pulse))
            aura = pygame.Surface((glow * 2, glow * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (255, 215, 90, 70), (glow, glow), glow)
            surface.blit(aura, (cx - glow, cy - glow))

        w, h = self.width, self.height
        base = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        body = self.color
        lid = tuple(min(255, c + 40) for c in body)
        band = (90, 60, 20) if not self.opened else (60, 45, 18)

        pygame.draw.rect(surface, body, base)
        pygame.draw.rect(surface, lid, (base.x, base.y, w, h // 2))     # lid
        pygame.draw.rect(surface, band, (cx - 3, base.y, 6, h))         # latch
        pygame.draw.rect(surface, (20, 20, 20), base, 2)               # outline
