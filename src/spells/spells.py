import pygame
import math


def _shade(color, delta):
    return tuple(max(0, min(255, c + delta)) for c in color)


class Projectile(pygame.sprite.Sprite):
    """Spell projectile with a pixel-art, element-styled look + fading trail.

    The silhouette matches the game's blocky pixel aesthetic: fire flickers as a
    stacked flame, cold flies as a crystalline shard, lightning as a jagged
    cross, and anything else as a glowing orb. A short trail of fading pixel
    motes streams behind it. ``element_type`` selects the style and is set by the
    caster right after construction (defaults to a neutral orb).
    """

    _TRAIL_LEN = 7

    def __init__(self, x, y, target_x, target_y, speed, damage, color, radius=5, lifetime=300):
        super().__init__()

        self.x = x
        self.y = y
        self.damage = damage
        self.lifetime = lifetime
        self.max_lifetime = lifetime

        # Calculate direction
        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx**2 + dy**2)

        if distance > 0:
            self.velocity_x = (dx / distance) * speed
            self.velocity_y = (dy / distance) * speed
        else:
            self.velocity_x = 0
            self.velocity_y = 0

        # Graphics / animation state
        self.radius = radius
        self.color = color
        self.element_type = "physical"      # set by the caster; picks the style
        self.angle = math.atan2(self.velocity_y, self.velocity_x)
        self._frame = 0
        self._trail = []                    # recent (x, y) world positions

        # A tiny collision surface is retained for any sprite-group / rect users.
        self.image = pygame.Surface((radius * 2, radius * 2))
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.center = (self.x, self.y)

    def update(self):
        """Update projectile position, trail and lifetime."""
        self._trail.append((self.x, self.y))
        if len(self._trail) > self._TRAIL_LEN:
            self._trail.pop(0)
        self.x += self.velocity_x
        self.y += self.velocity_y
        if self.velocity_x or self.velocity_y:
            self.angle = math.atan2(self.velocity_y, self.velocity_x)
        self.lifetime -= 1
        self._frame += 1
        self.rect.center = (self.x, self.y)

    def is_alive(self):
        """Check if projectile is still alive."""
        return self.lifetime > 0

    def draw(self, surface, cam=(0, 0)):
        """Draw the fading trail then the element-styled pixel-art head."""
        # Trail: fading motes, oldest = smallest/dimmest.
        n = len(self._trail)
        for i, (tx, ty) in enumerate(self._trail):
            frac = (i + 1) / (n + 1)
            sz = max(1, int(self.radius * frac * 0.8))
            sx = int(tx - cam[0]) - sz
            sy = int(ty - cam[1]) - sz
            mote = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            col = _shade(self.color, 20)
            pygame.draw.rect(mote, (*col, int(150 * frac)), (0, 0, sz * 2, sz * 2))
            surface.blit(mote, (sx, sy))

        cx = int(self.x - cam[0])
        cy = int(self.y - cam[1])
        r = self.radius
        elem = self.element_type
        pulse = (self._frame // 3) % 2

        if elem == "fire":
            self._draw_fire(surface, cx, cy, r, pulse)
        elif elem == "cold":
            self._draw_cold(surface, cx, cy, r)
        elif elem == "lightning":
            self._draw_lightning(surface, cx, cy, r, pulse)
        else:
            self._draw_orb(surface, cx, cy, r)

    # --- per-element pixel silhouettes ------------------------------------
    def _draw_orb(self, surface, cx, cy, r):
        pygame.draw.rect(surface, _shade(self.color, -40),
                         (cx - r, cy - r, r * 2, r * 2))
        pygame.draw.rect(surface, self.color, (cx - r + 1, cy - r + 1, r * 2 - 2, r * 2 - 2))
        pygame.draw.rect(surface, _shade(self.color, 70), (cx - r // 2, cy - r // 2, r, r))

    def _draw_fire(self, surface, cx, cy, r, pulse):
        # Stacked flame: dark red base, orange body, yellow flickering core.
        base = (200, 60, 20)
        pygame.draw.rect(surface, base, (cx - r, cy - r + pulse, r * 2, r * 2 - pulse))
        pygame.draw.rect(surface, (255, 140, 30),
                         (cx - r + 1, cy - r + 1, r * 2 - 2, r * 2 - 3))
        core = r - 1 - pulse
        if core > 0:
            pygame.draw.rect(surface, (255, 230, 120), (cx - core, cy - core, core * 2, core * 2))

    def _draw_cold(self, surface, cx, cy, r):
        # Crystalline shard: a diamond with a bright inner glint.
        pts = [(cx, cy - r - 1), (cx + r, cy), (cx, cy + r + 1), (cx - r, cy)]
        pygame.draw.polygon(surface, (120, 200, 245), pts)
        pygame.draw.polygon(surface, (215, 245, 255), pts, 1)
        pygame.draw.line(surface, (235, 250, 255), (cx, cy - r), (cx, cy + r), 1)

    def _draw_lightning(self, surface, cx, cy, r, pulse):
        # Jagged spark: a bright cross that flickers thickness each frame.
        col = (255, 245, 130) if pulse else (255, 255, 200)
        w = r + 1
        pygame.draw.line(surface, col, (cx - w, cy), (cx + w, cy), 2)
        pygame.draw.line(surface, col, (cx, cy - w), (cx, cy + w), 2)
        pygame.draw.line(surface, (255, 255, 255), (cx - w // 2, cy - w // 2),
                         (cx + w // 2, cy + w // 2), 1)

class Spell:
    """Base spell class."""
    
    def __init__(self, name, damage, projectile_color):
        self.name = name
        self.damage = damage
        self.projectile_color = projectile_color
    
    def cast(self, x, y, target_x, target_y):
        """Cast the spell and return a projectile."""
        raise NotImplementedError

class Fireball(Spell):
    """Fireball spell - high damage, medium speed."""
    
    def __init__(self):
        super().__init__("Fireball", 25, (255, 100, 0))
        self.speed = 6
        self.radius = 8
    
    def cast(self, x, y, target_x, target_y):
        """Create a fireball projectile."""
        return Projectile(x, y, target_x, target_y, self.speed, self.damage, 
                         self.projectile_color, self.radius, 400)

class FrostBolt(Spell):
    """Frost Bolt spell - medium damage, fast speed, slows enemies."""
    
    def __init__(self):
        super().__init__("Frost Bolt", 18, (100, 200, 255))
        self.speed = 8
        self.radius = 6
        self.slow_duration = 60
    
    def cast(self, x, y, target_x, target_y):
        """Create a frost bolt projectile."""
        return Projectile(x, y, target_x, target_y, self.speed, self.damage,
                         self.projectile_color, self.radius, 350)

class LightningStrike(Spell):
    """Lightning Strike spell - high damage, very fast, hits multiple targets."""
    
    def __init__(self):
        super().__init__("Lightning Strike", 30, (255, 255, 100))
        self.speed = 12
        self.radius = 5
    
    def cast(self, x, y, target_x, target_y):
        """Create a lightning projectile."""
        return Projectile(x, y, target_x, target_y, self.speed, self.damage,
                         self.projectile_color, self.radius, 300)

# Create instances of each spell
SPELLS = {
    0: Fireball(),
    1: FrostBolt(),
    2: LightningStrike()
}
