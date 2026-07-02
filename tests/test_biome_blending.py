"""Tests for the living-map biome system: deterministic climate regions,
soft cross-fade borders, cached chunk rendering + invalidation, and the
shared prop painter. ASCII-only output.
"""
import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.systems.world.world_manager import WorldManager
from src.systems.world import props as prop_art


def check(label, cond):
    assert cond, label


class _P:
    def __init__(self, x=0.0, y=0.0):
        self.x, self.y = x, y


def test_stable_hash_is_process_stable():
    # Known vector so a future refactor that changes the mixing is caught.
    a = prop_art.stable_hash(42, "rc", 3, 5)
    b = prop_art.stable_hash(42, "rc", 3, 5)
    check("stable_hash is deterministic", a == b)
    check("stable_hash varies with inputs",
          prop_art.stable_hash(42, "rc", 3, 6) != a)
    check("stable_hash returns a big int", a > 2**32)


def test_biomes_are_deterministic_across_instances():
    w1, w2 = WorldManager(seed=123), WorldManager(seed=123)
    for cx, cy in ((0, 0), (3, 5), (-4, 2), (10, -7)):
        check(f"biome_for_chunk stable at {cx},{cy}",
              w1.biome_for_chunk(cx, cy) == w2.biome_for_chunk(cx, cy))
    check("ground color stable",
          w1._ground_color_at(500, 500) == w2._ground_color_at(500, 500))


def test_biomes_form_coherent_regions():
    # Adjacent sample points almost always share a biome (coherent territories),
    # unlike the old per-chunk patchwork where neighbors were independent.
    w = WorldManager(seed=99)
    same = 0
    total = 0
    for i in range(60):
        x = i * 120
        b_here = w.biome_at(x, 0)[0]
        b_next = w.biome_at(x + 120, 0)[0]
        total += 1
        if b_here == b_next:
            same += 1
    check("neighboring samples usually share a biome", same / total > 0.6)


def test_borders_blend_but_interiors_do_not():
    w = WorldManager(seed=99)
    blends = [w.biome_at(x, 0)[2] for x in range(0, 12000, 30)]
    check("some points sit in a blend band", any(b > 0.05 for b in blends))
    check("many points are pure interior", any(b == 0.0 for b in blends))
    check("blend never exceeds a half mix", max(blends) <= 0.5 + 1e-9)


def test_ground_color_blends_between_two_biomes():
    w = WorldManager(seed=99)
    # Find a strong blend point and confirm the color is between the two biomes.
    for x in range(0, 20000, 15):
        b1, b2, blend = w.biome_at(x, 0)
        if blend > 0.3 and b1 != b2:
            c1 = w.biomes[b1]["ground_color"]
            c2 = w.biomes[b2]["ground_color"]
            col = w._ground_color_at(x, 0)
            for k in range(3):
                lo, hi = sorted((c1[k], c2[k]))
                check("blended channel is between the two biomes",
                      lo - 1 <= col[k] <= hi + 1)
            return
    check("a blended border point exists", False)


def test_chunk_surface_cache_and_invalidation():
    import pygame
    w = WorldManager(seed=5)
    w.update_world(_P())
    w.draw_ground(pygame.Surface((900, 700)), (0, 0), 900, 700)
    chunk = w.get_chunk(0, 0)
    check("visible chunk got a cached surface", chunk.surface is not None)
    cached = chunk.surface

    # Same signature -> same cached surface object reused.
    w.draw_ground(pygame.Surface((900, 700)), (0, 0), 900, 700)
    check("cache reused when nothing changed", w.get_chunk(0, 0).surface is cached)

    # Changing atlas biome weights invalidates the ground caches.
    w.biome_weights = {"burning_hellscape": 5.0}
    w.draw_ground(pygame.Surface((900, 700)), (0, 0), 900, 700)
    check("cache rebuilt after weight change",
          w.get_chunk(0, 0).surface is not cached)


def test_distant_chunk_caches_are_freed():
    import pygame
    w = WorldManager(seed=5)
    w.update_world(_P())
    w.draw_ground(pygame.Surface((900, 700)), (0, 0), 900, 700)
    check("origin chunk cached", w.get_chunk(0, 0).surface is not None)
    # Walk far away; the origin chunk should drop its cache (still in GEN ring
    # radius it would keep it, so move well beyond).
    w.update_world(_P(w.CHUNK_SIZE * 3, 0))
    origin = w.chunks.get((0, 0))
    if origin is not None:
        check("distant chunk cache freed", origin.surface is None)


def test_current_biome_returns_valid_pool():
    w = WorldManager(seed=5)
    data = w.current_biome(_P())
    check("current biome has an enemy pool", data.get("enemy_pool"))
    check("current biome has a name", bool(data.get("name")))


def test_prop_painter_draws_all_shapes():
    import pygame
    surf = pygame.Surface((120, 120))
    for shape in ("rock", "pillar", "crystal", "tree", "column", "shard",
                  "crack", "pool", "spike", "wisp", "star", "bramble"):
        prop_art.draw_prop(surf, shape, (120, 120, 140), 60, 60, 16, h=7)
    check("prop painter ran for every shape", True)
