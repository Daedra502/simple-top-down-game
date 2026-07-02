"""Shared decorative prop painter for the streaming world.

One place that knows how to draw every ground-prop silhouette (rocks, pillars,
crystals, twisted trees, ice shards, lava cracks, ruined columns, pools,
spikes, wisps, star flecks). Used by the chunk ground renderer for biome and
layout props and by map obstacles, so the shapes can't drift apart between
systems.

All functions are deterministic: variation comes from the caller-supplied
hash value ``h``, never from ``random``.
"""
import math
import zlib

import pygame


def stable_hash(*parts):
    """Process-stable FNV-1a mix of ints/strings.

    Python's built-in ``hash`` randomizes string hashes per process
    (PYTHONHASHSEED), which would reshuffle the world's cosmetics between
    launches of the same save. World-gen randomness must go through this.
    """
    acc = 2166136261
    for p in parts:
        if isinstance(p, str):
            p = zlib.crc32(p.encode("utf-8"))
        p = int(p) & 0xFFFFFFFFFFFFFFFF
        while True:
            acc = ((acc ^ (p & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFFFFFFFFFF
            p >>= 32
            if not p:
                break
    return acc


def shade(color, delta):
    """Lighten (+) or darken (-) a color, clamped to [0, 255]."""
    return tuple(max(0, min(255, c + delta)) for c in color)


def draw_prop(surface, shape, color, x, y, size, h=0):
    """Draw one prop silhouette centered at (x, y) with 'radius' ``size``."""
    hi = shade(color, 30)
    lo = shade(color, -35)

    if shape == "pillar":
        rect = (x - size // 2, y - size, size, size * 2)
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, hi, rect, 2)

    elif shape == "crystal":
        pts = [(x, y - size), (x + size * 2 // 3, y), (x, y + size),
               (x - size * 2 // 3, y)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, hi, pts, 2)
        pygame.draw.line(surface, hi, (x, y - size + 3), (x, y + size - 3), 1)

    elif shape == "tree":
        # Twisted, bare tree: trunk with a lean + a few crooked branches.
        lean = (h % 9) - 4
        top = (x + lean, y - size * 2)
        pygame.draw.line(surface, lo, (x, y + size // 2), top, max(2, size // 5))
        for k in range(3):
            bh = hash((h, k))
            ang = math.radians(200 + (bh % 140))
            bx = x + lean * (k + 1) // 3
            by = y - size // 2 - k * size // 2
            ex = bx + int(math.cos(ang) * size * 0.9)
            ey = by + int(math.sin(ang) * size * 0.9)
            pygame.draw.line(surface, lo, (bx, by), (ex, ey), 2)

    elif shape == "column":
        # Broken ruin column: fluted shaft with a toppled capital.
        ch = size + (h % max(1, size))          # broken at varying heights
        rect = (x - size // 2, y - ch, size, ch)
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, hi, rect, 2)
        pygame.draw.line(surface, lo, (x - size // 2 + 2, y - ch),
                         (x - size // 2 + 2, y), 1)
        pygame.draw.rect(surface, hi, (x - size // 2 - 3, y - 4, size + 6, 4))

    elif shape == "shard":
        # Ice shard: tall thin triangle with a glint.
        w = max(3, size // 2)
        pts = [(x, y - size * 2), (x + w, y), (x - w, y)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, hi, pts, 1)
        pygame.draw.line(surface, shade(color, 60), (x, y - size * 2), (x - 1, y - size), 1)

    elif shape == "crack":
        # Glowing fissure: jagged polyline.
        px, py = x - size, y
        for k in range(4):
            ch = hash((h, k))
            nx = px + size // 2 + (ch % max(1, size // 2))
            ny = py + ((ch // 7) % (size)) - size // 2
            pygame.draw.line(surface, color, (px, py), (nx, ny), 3)
            pygame.draw.line(surface, hi, (px, py), (nx, ny), 1)
            px, py = nx, ny

    elif shape == "pool":
        rect = pygame.Rect(x - size, y - size // 2, size * 2, size)
        pygame.draw.ellipse(surface, color, rect)
        pygame.draw.ellipse(surface, lo, rect, 2)
        pygame.draw.ellipse(surface, hi,
                            (x - size // 2, y - size // 5, size, size // 3), 1)

    elif shape == "spike":
        pts = [(x - size // 2, y + size // 2), (x + size // 2, y + size // 2),
               (x + (h % 5) - 2, y - size)]
        pygame.draw.polygon(surface, color, pts)
        pygame.draw.polygon(surface, lo, pts, 1)

    elif shape == "wisp":
        pygame.draw.circle(surface, shade(color, -10), (x, y), size // 2)
        pygame.draw.circle(surface, color, (x, y), max(2, size // 4))
        pygame.draw.circle(surface, hi, (x - size // 6, y - size // 6),
                           max(1, size // 8))

    elif shape == "star":
        pygame.draw.line(surface, color, (x - size // 2, y), (x + size // 2, y), 1)
        pygame.draw.line(surface, color, (x, y - size // 2), (x, y + size // 2), 1)
        pygame.draw.circle(surface, hi, (x, y), 1)

    elif shape == "bramble":
        pygame.draw.circle(surface, color, (x, y), size)
        for a in range(0, 360, 45):
            ex = x + int(math.cos(math.radians(a)) * size)
            ey = y + int(math.sin(math.radians(a)) * size)
            pygame.draw.line(surface, lo, (x, y), (ex, ey), 2)

    else:  # rock
        pygame.draw.circle(surface, color, (x, y), max(2, size // 2))
        pygame.draw.circle(surface, hi, (x, y), max(2, size // 2), 1)
