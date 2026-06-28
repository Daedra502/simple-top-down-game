"""Procedural skill icons (UI art).

Each active skill in data/skills.json gets a small, recognizable emblem drawn
with pygame primitives -- no external art assets required. The emblem symbolizes
the skill's purpose: a flame for Fireball, a frozen shard for Ice Shard, a bolt
for Chain Lightning, and so on. Icons are rendered once and cached per
(skill_id, size) so the skill bar can blit them every frame cheaply.
"""
import pygame

# Soft fallback palette if a skill id is unknown.
_DEFAULT_COLOR = (200, 200, 220)

_icon_cache = {}


def _shade(color, factor):
    """Lighten (factor>1) or darken (factor<1) an RGB color, clamped to 0..255."""
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def _draw_fireball(surf, s, color):
    cx, cy = s // 2, int(s * 0.55)
    # Outer flame body
    pygame.draw.circle(surf, color, (cx, cy), int(s * 0.30))
    pygame.draw.circle(surf, _shade(color, 1.4), (cx, cy + int(s * 0.05)), int(s * 0.18))
    # Flickering tongue rising off the top
    tip = [(cx, int(s * 0.10)), (cx - int(s * 0.16), cy),
           (cx + int(s * 0.16), cy)]
    pygame.draw.polygon(surf, color, tip)
    pygame.draw.circle(surf, (255, 245, 200), (cx, cy + int(s * 0.06)), int(s * 0.07))


def _draw_ice_shard(surf, s, color):
    cx = s // 2
    # A tall crystalline shard (diamond) with an inner highlight.
    pts = [(cx, int(s * 0.10)), (int(s * 0.70), int(s * 0.45)),
           (cx, int(s * 0.90)), (int(s * 0.30), int(s * 0.45))]
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, _shade(color, 0.6), pts, 2)
    pygame.draw.line(surf, (240, 250, 255), (cx, int(s * 0.16)),
                     (cx, int(s * 0.84)), 2)


def _draw_lightning(surf, s, color):
    # Classic zig-zag bolt.
    pts = [(int(s * 0.55), int(s * 0.08)), (int(s * 0.30), int(s * 0.50)),
           (int(s * 0.47), int(s * 0.50)), (int(s * 0.40), int(s * 0.92)),
           (int(s * 0.72), int(s * 0.42)), (int(s * 0.52), int(s * 0.42)),
           (int(s * 0.62), int(s * 0.08))]
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, _shade(color, 1.4), pts, 1)


def _draw_arc_slash(surf, s, color):
    # Crescent sweep -- two arcs forming a blade slash.
    rect = pygame.Rect(int(s * 0.12), int(s * 0.12), int(s * 0.76), int(s * 0.76))
    for w, shade in ((4, 1.0), (2, 1.5)):
        pygame.draw.arc(surf, _shade(color, shade), rect, 0.6, 2.6, w)
    # Motion ticks along the sweep
    pygame.draw.line(surf, color, (int(s * 0.20), int(s * 0.30)),
                     (int(s * 0.10), int(s * 0.22)), 2)
    pygame.draw.line(surf, color, (int(s * 0.80), int(s * 0.30)),
                     (int(s * 0.90), int(s * 0.22)), 2)


def _draw_poison_nova(surf, s, color):
    cx, cy = s // 2, s // 2
    # Expanding toxic rings.
    for r, shade in ((int(s * 0.38), 0.6), (int(s * 0.26), 0.9)):
        pygame.draw.circle(surf, _shade(color, shade), (cx, cy), r, 2)
    pygame.draw.circle(surf, color, (cx, cy), int(s * 0.12))
    # Three venom droplets flung outward.
    for dx, dy in ((-0.30, -0.18), (0.30, -0.18), (0.0, 0.34)):
        pygame.draw.circle(surf, _shade(color, 1.3),
                           (int(cx + dx * s), int(cy + dy * s)), max(2, int(s * 0.06)))


def _draw_meteor(surf, s, color):
    # Falling rock with a fiery trail from top-left to bottom-right.
    for i, shade in enumerate((0.5, 0.8)):
        off = i * int(s * 0.08)
        pygame.draw.line(surf, _shade(color, shade),
                         (int(s * 0.12) + off, int(s * 0.10)),
                         (int(s * 0.55), int(s * 0.55)), 3)
    cx, cy = int(s * 0.66), int(s * 0.68)
    pygame.draw.circle(surf, _shade(color, 0.8), (cx, cy), int(s * 0.22))
    pygame.draw.circle(surf, color, (cx, cy), int(s * 0.16))
    pygame.draw.circle(surf, (255, 240, 200), (cx - 2, cy - 2), int(s * 0.06))


def _draw_blink(surf, s, color):
    # Two stacked chevrons suggesting a teleport dash.
    for off, shade in ((0.0, 0.6), (0.22, 1.0)):
        x = int(s * (0.30 + off))
        pts = [(x, int(s * 0.25)), (x + int(s * 0.20), int(s * 0.50)),
               (x, int(s * 0.75))]
        pygame.draw.lines(surf, _shade(color, shade), False, pts, 3)
    # Dashed motion trail
    for i in range(3):
        x = int(s * 0.12) + i * int(s * 0.07)
        pygame.draw.line(surf, color, (x, s // 2), (x + int(s * 0.04), s // 2), 2)


def _draw_skeleton(surf, s, color):
    cx = s // 2
    # Skull cranium
    pygame.draw.circle(surf, color, (cx, int(s * 0.42)), int(s * 0.26))
    # Jaw
    jaw = pygame.Rect(int(s * 0.36), int(s * 0.55), int(s * 0.28), int(s * 0.20))
    pygame.draw.rect(surf, color, jaw, border_radius=3)
    # Eye sockets + nasal cavity
    eye = _shade(color, 0.25)
    pygame.draw.circle(surf, eye, (int(s * 0.40), int(s * 0.42)), int(s * 0.07))
    pygame.draw.circle(surf, eye, (int(s * 0.60), int(s * 0.42)), int(s * 0.07))
    pygame.draw.polygon(surf, eye, [(cx, int(s * 0.46)),
                                    (cx - int(s * 0.04), int(s * 0.54)),
                                    (cx + int(s * 0.04), int(s * 0.54))])


# Map each skill id to its drawing routine.
_DRAWERS = {
    "fireball": _draw_fireball,
    "ice_shard": _draw_ice_shard,
    "chain_lightning": _draw_lightning,
    "arc_slash": _draw_arc_slash,
    "poison_nova": _draw_poison_nova,
    "meteor": _draw_meteor,
    "blink": _draw_blink,
    "summon_skeleton": _draw_skeleton,
}


def render_skill_icon(skill_id, size, color=None):
    """Return a cached, per-pixel-alpha Surface with the skill's emblem."""
    key = (skill_id, size)
    cached = _icon_cache.get(key)
    if cached is not None:
        return cached

    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    drawer = _DRAWERS.get(skill_id)
    col = color or _DEFAULT_COLOR
    if drawer is not None:
        drawer(surf, size, col)
    else:
        # Unknown skill: draw its first initial as a simple glyph.
        pygame.draw.circle(surf, col, (size // 2, size // 2), int(size * 0.30), 2)
    _icon_cache[key] = surf
    return surf


def has_icon(skill_id):
    return skill_id in _DRAWERS
