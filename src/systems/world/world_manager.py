"""Infinite streaming world manager (DESIGN.md Phase 11).

Replaces the fixed MapManager (R4) with a chunk grid generated deterministically
from a seed as the player moves. There is no map swap and no loading screen: the
player walks through world space, chunks around them stream in, and far chunks
unload. Rift progression is unchanged (the boss spawns near the player).

This class is the "current playfield" the Game talks to: it holds the global
``enemies`` list, updates them, and draws the biome ground under the camera.
``bounded = False`` tells entities not to clamp to a fixed map size.
"""
import math
import random

from src.core.data_loader import load_json
from src.systems.world.chunk import Chunk
from src.systems.world import props as prop_art


class WorldManager:
    CHUNK_SIZE = 768
    GEN_RADIUS = 2      # generate a (2*r+1)^2 block of chunks around the player
    UNLOAD_RADIUS = 3   # unload chunks farther than this (in chunk units)

    # Biome regions: one climate cell spans REGION_CHUNKS chunks per side; each
    # cell has a jittered center and a weighted biome, and ground is sampled by
    # nearest center (Worley) so biomes form coherent territories instead of a
    # per-chunk patchwork. Where the two nearest centers are almost equidistant
    # the ground colors cross-fade, giving wide natural transition bands.
    REGION_CHUNKS = 3
    SUBTILE = 96        # ground sampling resolution inside a chunk (8x8)
    EDGE_BAND = 0.22    # normalized border width where biomes blend

    bounded = False     # infinite world: entities don't clamp to bounds

    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randint(0, 2_000_000_000)
        self.biomes = load_json("biomes.json")
        self.biome_ids = list(self.biomes.keys())

        self.chunks = {}        # (cx, cy) -> Chunk
        self.enemies = []       # global, near the player
        self.chests = []        # treasure chests near the player (Game-spawned)
        self.obstacles = []     # solid/hazard map obstacles near the player
        self.biome_weights = {}  # atlas-driven biome bias (Phase 15)
        self.layout = None      # active map layout config (Phase 18)
        self._ground_sig = None  # (layout name, weights) the caches were built for

        self._ensure_started()

    # --- chunk math -------------------------------------------------------
    def chunk_coord(self, x, y):
        return (int(math.floor(x / self.CHUNK_SIZE)),
                int(math.floor(y / self.CHUNK_SIZE)))

    # --- climate regions ---------------------------------------------------
    def _region_size(self):
        return self.REGION_CHUNKS * self.CHUNK_SIZE

    def _region_center(self, rx, ry):
        """Deterministic jittered center point of a climate cell (pixels)."""
        h = prop_art.stable_hash(self.seed, "rc", rx, ry)
        jx = (h % 1000) / 1000.0
        jy = ((h // 1000) % 1000) / 1000.0
        size = self._region_size()
        return ((rx + 0.15 + 0.7 * jx) * size, (ry + 0.15 + 0.7 * jy) * size)

    def _region_biome(self, rx, ry):
        """Weighted biome roll per climate cell (atlas bias, Phase 15)."""
        weights = [self.biome_weights.get(b, 1.0) for b in self.biome_ids]
        total = sum(weights)
        roll = (prop_art.stable_hash(self.seed, "rb", rx, ry) % 1_000_000) / 1_000_000 * total
        acc = 0.0
        for biome, w in zip(self.biome_ids, weights):
            acc += w
            if roll < acc:
                return biome
        return self.biome_ids[-1]

    def biome_at(self, x, y):
        """Sample the climate field at a world point.

        Returns (nearest biome id, second biome id, blend) where blend rises
        from 0 deep inside a region to ~0.5 exactly on a border.
        """
        size = self._region_size()
        rx0 = int(math.floor(x / size))
        ry0 = int(math.floor(y / size))
        best = second = None
        d1 = d2 = float("inf")
        for rx in range(rx0 - 1, rx0 + 2):
            for ry in range(ry0 - 1, ry0 + 2):
                cx, cy = self._region_center(rx, ry)
                d = (x - cx) ** 2 + (y - cy) ** 2
                if d < d1:
                    second, d2 = best, d1
                    best, d1 = (rx, ry), d
                elif d < d2:
                    second, d2 = (rx, ry), d
        b1 = self._region_biome(*best)
        b2 = self._region_biome(*second)   # 3x3 search always yields a runner-up
        d1, d2 = math.sqrt(d1), math.sqrt(d2)
        edge = (d2 - d1) / (d2 + d1 + 1e-9)   # 0 on the border, ~1 at the center
        blend = 0.0
        if edge < self.EDGE_BAND and b2 != b1:
            blend = 0.5 * (1.0 - edge / self.EDGE_BAND)
        return b1, b2, blend

    def biome_for_chunk(self, cx, cy):
        """Dominant biome of a chunk: the climate field at the chunk center."""
        x = (cx + 0.5) * self.CHUNK_SIZE
        y = (cy + 0.5) * self.CHUNK_SIZE
        return self.biome_at(x, y)[0]

    def get_chunk(self, cx, cy):
        chunk = self.chunks.get((cx, cy))
        if chunk is None:
            chunk = self.generate_chunk(cx, cy)
        return chunk

    def generate_chunk(self, cx, cy):
        bid = self.biome_for_chunk(cx, cy)
        chunk = Chunk(cx, cy, self.CHUNK_SIZE, bid, self.biomes[bid])
        self.chunks[(cx, cy)] = chunk
        return chunk

    def _ensure_started(self):
        # Pre-generate the block around the origin (player spawn).
        for dx in range(-self.GEN_RADIUS, self.GEN_RADIUS + 1):
            for dy in range(-self.GEN_RADIUS, self.GEN_RADIUS + 1):
                self.generate_chunk(dx, dy)

    # --- streaming --------------------------------------------------------
    def update_world(self, player):
        """Generate chunks around the player and unload distant ones."""
        pcx, pcy = self.chunk_coord(player.x, player.y)

        for dx in range(-self.GEN_RADIUS, self.GEN_RADIUS + 1):
            for dy in range(-self.GEN_RADIUS, self.GEN_RADIUS + 1):
                key = (pcx + dx, pcy + dy)
                chunk = self.chunks.get(key) or self.generate_chunk(*key)
                chunk.discovered = True

        for key, chunk in list(self.chunks.items()):
            dist = max(abs(key[0] - pcx), abs(key[1] - pcy))
            if dist > self.UNLOAD_RADIUS:
                del self.chunks[key]
            elif dist > self.GEN_RADIUS and chunk.surface is not None:
                chunk.surface = None    # free off-screen ground caches

    def current_biome(self, player):
        cx, cy = self.chunk_coord(player.x, player.y)
        return self.get_chunk(cx, cy).biome_data

    def loaded_chunk_count(self):
        return len(self.chunks)

    def get_info(self, player):
        return {
            "name": self.current_biome(player)["name"],
            "enemies_remaining": len(self.enemies),
            "chunks_loaded": len(self.chunks),
        }

    # --- entity update (Map-compatible) -----------------------------------
    def update(self, player, dt=1.0 / 60.0):
        alive = []
        for enemy in self.enemies:
            if enemy.health > 0:
                enemy.update(player, self, dt)
            if enemy.health > 0:
                alive.append(enemy)
        self.enemies = alive

    # --- rendering --------------------------------------------------------
    def _ground_color_at(self, x, y):
        """Blended ground color of the climate field at a world point."""
        b1, b2, blend = self.biome_at(x, y)
        c1 = self.biomes[b1]["ground_color"]
        c2 = self.biomes[b2]["ground_color"]
        return tuple(int(a + (b - a) * blend) for a, b in zip(c1, c2))

    def _cache_signature(self):
        layout_name = (self.layout or {}).get("name", "")
        return (layout_name, tuple(sorted(self.biome_weights.items())))

    def draw_ground(self, surface, cam, screen_w, screen_h):
        """Blit cached, pre-rendered chunk ground for the visible view.

        Each chunk's ground (blended sub-tiles + texture speckle + biome and
        layout props) is rendered once into a Surface and cached on the chunk;
        per frame this is just a handful of blits. Caches are rebuilt when the
        map layout or atlas biome weights change, and freed as chunks stream
        out (update_world) so memory stays bounded.
        """
        sig = self._cache_signature()
        if sig != self._ground_sig:
            self._ground_sig = sig
            for chunk in self.chunks.values():
                chunk.surface = None

        cam_x, cam_y = cam
        cx0, cy0 = self.chunk_coord(cam_x, cam_y)
        cx1, cy1 = self.chunk_coord(cam_x + screen_w, cam_y + screen_h)

        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1):
                chunk = self.get_chunk(cx, cy)
                if chunk.surface is None:
                    chunk.surface = self._render_chunk(chunk)
                surface.blit(chunk.surface, (chunk.px - cam_x, chunk.py - cam_y))

    def _render_chunk(self, chunk):
        """Render one chunk's ground into a cached Surface (called rarely)."""
        import pygame
        size = self.CHUNK_SIZE
        surf = pygame.Surface((size, size))

        # Blended ground sub-tiles with a touch of deterministic shade jitter.
        sub = self.SUBTILE
        n = size // sub
        for ty in range(n):
            for tx in range(n):
                wx = chunk.px + tx * sub + sub / 2
                wy = chunk.py + ty * sub + sub / 2
                col = self._ground_color_at(wx, wy)
                jitter = (prop_art.stable_hash(self.seed, "j", int(wx), int(wy)) % 7) - 3
                col = prop_art.shade(col, jitter)
                surf.fill(col, (tx * sub, ty * sub, sub, sub))

        # Texture speckle in the biome's accent color.
        biome = self.biomes[chunk.biome_id]
        speck = tuple(biome.get("speckle", prop_art.shade(chunk.ground_color, 18)))
        for i in range(70):
            h = prop_art.stable_hash(self.seed, "spk", chunk.world_x, chunk.world_y, i)
            x = h % size
            y = (h // size) % size
            surf.fill(prop_art.shade(speck, -(h % 25)), (x, y, 2, 2))

        # Signature biome props, then layout props on top.
        for spec in biome.get("props", []):
            self._scatter_props(surf, chunk, spec["shape"], tuple(spec["color"]),
                                spec.get("density", 2), spec.get("size", 14),
                                salt=spec["shape"])
        layout = self.layout
        if layout and layout.get("prop_density", 0) > 0:
            self._scatter_props(surf, chunk, layout.get("prop_shape", "rock"),
                                tuple(layout.get("prop_color", [80, 80, 80])),
                                layout.get("prop_density", 1) * 4,
                                layout.get("prop_size", 14),
                                salt=layout.get("name", ""))
        return surf

    def _scatter_props(self, surf, chunk, shape, color, density, size, salt):
        """Deterministically scatter one prop type across a chunk surface."""
        margin = size * 2 + 4    # keep silhouettes inside the cached surface
        span = self.CHUNK_SIZE - margin * 2
        for i in range(int(density)):
            h = prop_art.stable_hash(self.seed, "prop", chunk.world_x, chunk.world_y, salt, i)
            x = margin + (h % 1000) / 1000.0 * span
            y = margin + ((h // 1000) % 1000) / 1000.0 * span
            prop_art.draw_prop(surf, shape, color, int(x), int(y), size, h=h)
