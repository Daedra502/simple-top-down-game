"""Procedural animated player sprite: a hooded battle-mage.

All frames are painted from a small pixel grid at construction time (no external
image assets), then scaled up with nearest-neighbor for a crisp pixel-art look.
The sprite exposes a tiny state machine the Player drives each frame:

    facing: "down" | "up" | "left" | "right"   (left is a mirror of right)
    moving: bool                                (walk cycle vs idle bob)
    casting: float                              (seconds of cast pose remaining)

``surface(dt)`` advances the animation clock and returns the frame to blit.
Everything is cached, so per-frame cost is a dict lookup + the blit.
"""
import pygame

# Palette (kept small and readable; indices used by the pixel maps below).
_C = {
    ".": None,                       # transparent
    "R": (44, 58, 120),              # robe (deep blue)
    "r": (30, 40, 90),               # robe shadow
    "H": (24, 30, 66),              # hood / darkest robe
    "T": (36, 48, 104),              # robe trim highlight
    "F": (28, 24, 40),               # face shadow inside hood
    "E": (120, 220, 255),            # glowing eyes
    "S": (150, 110, 70),             # staff shaft
    "s": (110, 80, 50),              # staff shadow
    "O": (255, 200, 120),            # staff orb / cast flare
    "K": (70, 90, 160),             # boots / hands
    "W": (90, 120, 200),            # highlight
}

# Base 16x20 front-facing pose. Rows are strings of palette keys.
# Designed so leg columns (indices) can be swapped for the walk cycle.
_FRONT = [
    "................",
    ".....HHHHHH.....",
    "....HHHHHHHH....",
    "...HHFFFFFFHH...",
    "...HFFEFFEFFH...",   # glowing eyes
    "...HFFFFFFFFH...",
    "...RRRRRRRRRR...",
    "..RRRTRRRRTRRR..",
    "..RRRRRRRRRRRR..",
    "..KRRRRRRRRRRK..",   # hands at sides
    "..KRRRRRRRRRRK..",
    "...RRRRRRRRRR...",
    "...RRRRRRRRRR...",
    "...RRRRRRRRRR...",
    "...rRRRRRRRRr...",
    "...rRRRRRRRRr...",
    "...rrRRRRRRrr...",
    "...rr.RRRR.rr...",
    "...KK......KK...",   # feet
    "...KK......KK...",
]

_BACK = [
    "................",
    ".....HHHHHH.....",
    "....HHHHHHHH....",
    "...HHHHHHHHHH...",
    "...HHHHHHHHHH...",
    "...HHHHHHHHHH...",
    "...RRRRRRRRRR...",
    "..RRRTRRRRTRRR..",
    "..RRRRRRRRRRRR..",
    "..KRRRRRRRRRRK..",
    "..KRRRRRRRRRRK..",
    "...RRRRRRRRRR...",
    "...RRRRRRRRRR...",
    "...RRRRRRRRRR...",
    "...rRRRRRRRRr...",
    "...rRRRRRRRRr...",
    "...rrRRRRRRrr...",
    "...rr.RRRR.rr...",
    "...KK......KK...",
    "...KK......KK...",
]

_SIDE = [
    "................",
    ".....HHHHH......",
    "....HHHHHHH.....",
    "...HHFFFFFH.....",
    "...HFFEFFFH.....",   # one visible eye
    "...HFFFFFFH.....",
    "...RRRRRRRR.....",
    "..RRRRRRRRRR....",
    "..RRRRRRRRRR.SS.",   # staff on the back/side
    "..KRRRRRRRR.Ss..",
    "...RRRRRRRRSs...",
    "...RRRRRRRRs....",
    "...RRRRRRRR.....",
    "...RRRRRRRR.....",
    "...rRRRRRRr.....",
    "...rRRRRRRr.....",
    "...rrRRRRrr.....",
    "...rr.RR.rr.....",
    "...KK..KK.......",
    "...KK..KK.......",
]


def _paint(grid, px):
    """Render a pixel grid (list of strings) into a Surface scaled by px."""
    h = len(grid)
    w = len(grid[0])
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(grid):
        for x, key in enumerate(row):
            col = _C.get(key)
            if col is not None:
                surf.set_at((x, y), col)
    if px != 1:
        surf = pygame.transform.scale(surf, (w * px, h * px))
    return surf


def _shift_feet(grid, dx):
    """Return a copy of a grid with the two foot rows shifted for a walk step."""
    out = list(grid)
    for i in (18, 19):
        row = list(grid[i])
        # Move the left foot block (cols 3-4) and right foot (cols 10-11).
        base = [" "] * len(row)
        for x, ch in enumerate(row):
            if ch in ("K", "k"):
                nx = min(len(row) - 1, max(0, x + dx))
                base[nx] = ch
        # keep non-foot chars, overlay feet
        merged = list(grid[i])
        for x, ch in enumerate(merged):
            if ch in ("K", "k"):
                merged[x] = "."
        for x, ch in enumerate(base):
            if ch in ("K", "k"):
                merged[x] = ch
        out[i] = "".join(merged)
    return out


def _sway(grid, dx):
    """Shift the hem rows sideways to suggest robe sway during the walk."""
    out = list(grid)
    for i in (14, 15, 16, 17):
        row = grid[i]
        if dx < 0:
            out[i] = row[-dx:] + "." * (-dx)
        elif dx > 0:
            out[i] = "." * dx + row[:-dx]
    return out


def _with_cast(grid, side=False):
    """Add a glowing orb/flare near the mage's hand for the cast pose."""
    out = list(grid)
    # Front/back: raise a hand and flare on the right side (col ~12-13, row 9).
    ry = 9
    row = list(out[ry])
    for x in (12, 13):
        if x < len(row):
            row[x] = "O"
    out[ry] = "".join(row)
    row2 = list(out[8])
    for x in (12, 13):
        if x < len(row2):
            row2[x] = "O"
    out[8] = "".join(row2)
    return out


class PlayerSprite:
    """Builds and serves the animated frames for the player character."""

    WALK_FPS = 8.0
    IDLE_FPS = 2.0

    def __init__(self, target_size=24):
        # Scale the 16x20 art so its height matches target visual size.
        px = max(1, round(target_size / 20 * 1.6))
        self.px = px

        # Walk cycle: 4 poses (contact, passing, contact-opposite, passing).
        def cycle(base, mirror=False):
            frames = [
                _paint(_sway(_shift_feet(base, -1), -1), px),
                _paint(base, px),
                _paint(_sway(_shift_feet(base, 1), 1), px),
                _paint(base, px),
            ]
            if mirror:
                frames = [pygame.transform.flip(f, True, False) for f in frames]
            return frames

        self.walk = {
            "down": cycle(_FRONT),
            "up": cycle(_BACK),
            "right": cycle(_SIDE),
            "left": cycle(_SIDE, mirror=True),
        }
        # Idle: base pose + a 1px "breathing" bob handled at blit time.
        self.idle = {
            "down": _paint(_FRONT, px),
            "up": _paint(_BACK, px),
            "right": _paint(_SIDE, px),
            "left": pygame.transform.flip(_paint(_SIDE, px), True, False),
        }
        # Cast poses per facing.
        self.cast = {
            "down": _paint(_with_cast(_FRONT), px),
            "up": _paint(_with_cast(_BACK), px),
            "right": _paint(_with_cast(_SIDE), px),
            "left": pygame.transform.flip(_paint(_with_cast(_SIDE), px), True, False),
        }

        self.clock = 0.0

    @property
    def size(self):
        return self.idle["down"].get_size()

    def frame(self, facing, moving, casting, dt):
        """Advance the clock and return (surface, y_bob) for the current state."""
        self.clock += dt
        if casting > 0:
            return self.cast.get(facing, self.cast["down"]), 0
        if moving:
            idx = int(self.clock * self.WALK_FPS) % 4
            return self.walk[facing][idx], 0
        # Idle breathing bob: 0 or 1px on a slow cycle.
        bob = 1 if int(self.clock * self.IDLE_FPS) % 2 else 0
        return self.idle.get(facing, self.idle["down"]), bob
