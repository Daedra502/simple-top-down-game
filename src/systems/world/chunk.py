"""A single streamed world chunk (DESIGN.md Phase 11).

Chunks describe a square region of the infinite world: which biome it is, its
ground tint, and slots for per-chunk content (events/portals/structures) that
later phases fill. Enemies are managed globally near the player by the spawn
director, so ``enemies`` here stays empty for now.
"""


class Chunk:
    def __init__(self, cx, cy, size, biome_id, biome_data):
        self.chunk_id = f"{cx}_{cy}"
        self.world_x = cx          # chunk-grid coordinate (not pixels)
        self.world_y = cy
        self.size = size
        self.biome_id = biome_id
        self.biome_data = biome_data

        # Pixel-space bounds of this chunk in world coordinates.
        self.px = cx * size
        self.py = cy * size

        self.tiles = None          # reserved for a future tile grid
        self.enemies = []          # director-managed globally for now
        self.events = []           # Phase 12 dynamic events
        self.portals = []
        self.structures = []
        self.discovered = False

    @property
    def ground_color(self):
        return tuple(self.biome_data["ground_color"])

    def world_rect(self):
        return (self.px, self.py, self.size, self.size)
