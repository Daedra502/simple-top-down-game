"""Static map obstacles (rocks, pillars, crystals, bramble).

Obstacles add navigational intrigue: solid ones block movement so the player
must path around them (cover to kite enemies behind, chokepoints to funnel a
swarm), while ``hazard`` types deal light contact damage. They are spawned near
the player by the streaming world and culled when far away, mirroring how the
spawn director manages enemies. Purely server-side geometry -- cheap circles.
"""
import math

import pygame


# type id -> (fill color, solid?, hazard contact damage, draw shape)
OBSTACLE_TYPES = {
    "rock":    {"color": (90, 90, 95),   "solid": True,  "damage": 0,  "shape": "rock"},
    "pillar":  {"color": (120, 110, 95), "solid": True,  "damage": 0,  "shape": "pillar"},
    "crystal": {"color": (120, 90, 200), "solid": True,  "damage": 0,  "shape": "crystal"},
    "brambles": {"color": (70, 110, 60), "solid": False, "damage": 4,  "shape": "bramble"},
}


class Obstacle:
    def __init__(self, x, y, kind="rock", radius=26):
        self.x = x
        self.y = y
        self.kind = kind if kind in OBSTACLE_TYPES else "rock"
        spec = OBSTACLE_TYPES[self.kind]
        self.radius = radius
        self.color = spec["color"]
        self.solid = spec["solid"]
        self.damage = spec["damage"]      # contact damage per second for hazards
        self.shape = spec["shape"]

    def resolve_collision(self, entity, entity_radius):
        """Push a circular entity out of a solid obstacle. Returns True if moved.

        Works on anything exposing ``x``/``y`` (player or enemy); the caller
        passes the entity's collision radius. No-op for non-solid hazards.
        """
        if not self.solid:
            return False
        dx = entity.x - self.x
        dy = entity.y - self.y
        dist = math.hypot(dx, dy)
        min_dist = self.radius + entity_radius
        if dist >= min_dist:
            return False
        if dist == 0:                      # exactly centered: shove in a default dir
            dx, dy, dist = 1.0, 0.0, 1.0
        push = (min_dist - dist)
        entity.x += dx / dist * push
        entity.y += dy / dist * push
        if hasattr(entity, "rect"):
            entity.rect.center = (entity.x, entity.y)
        return True

    def contact(self, entity, entity_radius):
        """True if a hazard obstacle is overlapping the entity (for damage)."""
        if self.solid or self.damage <= 0:
            return False
        return math.hypot(entity.x - self.x, entity.y - self.y) < self.radius + entity_radius

    def draw(self, surface, cam=(0, 0)):
        cx = int(self.x - cam[0])
        cy = int(self.y - cam[1])
        r = self.radius
        shade = tuple(min(255, c + 35) for c in self.color)
        if self.shape == "pillar":
            rect = (cx - r // 2, cy - r, r, r * 2)
            pygame.draw.rect(surface, self.color, rect)
            pygame.draw.rect(surface, shade, rect, 2)
        elif self.shape == "crystal":
            pts = [(cx, cy - r), (cx + r * 2 // 3, cy), (cx, cy + r), (cx - r * 2 // 3, cy)]
            pygame.draw.polygon(surface, self.color, pts)
            pygame.draw.polygon(surface, shade, pts, 2)
        elif self.shape == "bramble":
            # A ragged hazard: a few spiky spokes around a dark core.
            pygame.draw.circle(surface, self.color, (cx, cy), r)
            for a in range(0, 360, 45):
                ex = cx + int(math.cos(math.radians(a)) * r)
                ey = cy + int(math.sin(math.radians(a)) * r)
                pygame.draw.line(surface, (40, 70, 35), (cx, cy), (ex, ey), 2)
        else:  # rock
            pygame.draw.circle(surface, self.color, (cx, cy), r)
            pygame.draw.circle(surface, shade, (cx, cy), r, 2)
            pygame.draw.circle(surface, (40, 40, 45), (cx, cy), r, 1)
