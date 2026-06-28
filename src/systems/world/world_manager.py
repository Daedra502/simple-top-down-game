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


class WorldManager:
    CHUNK_SIZE = 768
    GEN_RADIUS = 2      # generate a (2*r+1)^2 block of chunks around the player
    UNLOAD_RADIUS = 3   # unload chunks farther than this (in chunk units)

    bounded = False     # infinite world: entities don't clamp to bounds

    def __init__(self, seed=None):
        self.seed = seed if seed is not None else random.randint(0, 2_000_000_000)
        self.biomes = load_json("biomes.json")
        self.biome_ids = list(self.biomes.keys())

        self.chunks = {}        # (cx, cy) -> Chunk
        self.enemies = []       # global, near the player
        self.chests = []        # reserved (per-chunk structures come later)
        self.biome_weights = {}  # atlas-driven biome bias (Phase 15)
        self.layout = None      # active map layout config (Phase 18)

        self._ensure_started()

    # --- chunk math -------------------------------------------------------
    def chunk_coord(self, x, y):
        return (int(math.floor(x / self.CHUNK_SIZE)),
                int(math.floor(y / self.CHUNK_SIZE)))

    def biome_for_chunk(self, cx, cy):
        """Deterministic biome from (seed, cx, cy), biased by atlas weights.

        Stays deterministic for a fixed (seed, weights) so streaming/saves are
        reproducible; the atlas changes which biomes the world favors (Phase 15).
        """
        weights = [self.biome_weights.get(b, 1.0) for b in self.biome_ids]
        total = sum(weights)
        roll = (hash((self.seed, cx, cy)) % 1_000_000) / 1_000_000 * total
        acc = 0.0
        for biome, w in zip(self.biome_ids, weights):
            acc += w
            if roll < acc:
                return biome
        return self.biome_ids[-1]

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

        for key in list(self.chunks):
            if max(abs(key[0] - pcx), abs(key[1] - pcy)) > self.UNLOAD_RADIUS:
                del self.chunks[key]

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
    def draw_ground(self, surface, cam, screen_w, screen_h):
        """Draw biome-tinted ground for every chunk overlapping the view."""
        cam_x, cam_y = cam
        cx0, cy0 = self.chunk_coord(cam_x, cam_y)
        cx1, cy1 = self.chunk_coord(cam_x + screen_w, cam_y + screen_h)

        import pygame
        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1):
                chunk = self.get_chunk(cx, cy)
                sx = chunk.px - cam_x
                sy = chunk.py - cam_y
                rect = pygame.Rect(sx, sy, self.CHUNK_SIZE, self.CHUNK_SIZE)
                pygame.draw.rect(surface, chunk.ground_color, rect)
                # subtle chunk border so biome transitions are visible
                pygame.draw.rect(surface, (0, 0, 0), rect, 1)
                self._draw_chunk_props(surface, pygame, cx, cy, sx, sy)

    def _draw_chunk_props(self, surface, pygame, cx, cy, sx, sy):
        """Scatter decorative props for the active map layout (Phase 18).

        Props are deterministic per (seed, chunk, layout) so the world looks
        stable as it streams, and purely cosmetic -- they give each layout a
        distinct silhouette (rocks, pillars, crystals) without affecting paths.
        """
        layout = self.layout
        if not layout:
            return
        density = layout.get("prop_density", 0.0)
        if density <= 0:
            return
        count = int(density * 4)
        color = tuple(layout.get("prop_color", [80, 80, 80]))
        size = layout.get("prop_size", 14)
        shape = layout.get("prop_shape", "rock")
        layout_name = layout.get("name", "")
        for i in range(count):
            h = hash((self.seed, cx, cy, i, layout_name))
            ox = (h % 1000) / 1000.0 * self.CHUNK_SIZE
            oy = ((h // 1000) % 1000) / 1000.0 * self.CHUNK_SIZE
            x, y = int(sx + ox), int(sy + oy)
            shade = tuple(min(255, c + 25) for c in color)
            if shape == "pillar":
                pygame.draw.rect(surface, color, (x - size // 3, y - size, size // 1.5 * 1, size * 2))
                pygame.draw.rect(surface, shade, (x - size // 3, y - size, size // 1.5 * 1, size * 2), 1)
            elif shape == "crystal":
                pts = [(x, y - size), (x + size // 2, y), (x, y + size), (x - size // 2, y)]
                pygame.draw.polygon(surface, color, pts)
                pygame.draw.polygon(surface, shade, pts, 1)
            else:  # rock
                pygame.draw.circle(surface, color, (x, y), size // 2)
                pygame.draw.circle(surface, shade, (x, y), size // 2, 1)
