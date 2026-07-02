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
        min_dist = self.radius + entity_radius
        # Squared-distance early-out avoids the sqrt on the common no-overlap
        # case (this runs for every mover x every solid, every frame).
        d2 = dx * dx + dy * dy
        if d2 >= min_dist * min_dist:
            return False
        dist = math.sqrt(d2)
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
        # Shares the world's prop painter so obstacle silhouettes match the
        # cosmetic props scattered across the ground.
        from src.systems.world.props import draw_prop
        draw_prop(surface, self.shape, self.color,
                  int(self.x - cam[0]), int(self.y - cam[1]), self.radius)
