"""Phase 11 tests: endless streaming world, chunks, biomes, seeded determinism.

ASCII-only output. Run: python test_phase11_world.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.systems.world import WorldManager
from main import Game

passed = 0
failed = 0


def check(label, cond):
    global passed, failed
    if cond:
        passed += 1
        print("  [PASS] " + label)
    else:
        failed += 1
        print("  [FAIL] " + label)


class P:
    def __init__(self, x, y):
        self.x = x
        self.y = y


print("PHASE 11 -- Endless Rift World")

w = WorldManager(seed=12345)
check("world is unbounded", w.bounded is False)
check("world pre-generates chunks around origin", w.loaded_chunk_count() > 0)
check("10 biomes available", len(w.biome_ids) == 10)

# Chunk coordinates map correctly
check("chunk_coord at origin is (0,0)", w.chunk_coord(10, 10) == (0, 0))
check("chunk_coord crosses to next chunk",
      w.chunk_coord(w.CHUNK_SIZE + 5, 0) == (1, 0))

# Deterministic biome from seed: same seed -> same biome for a chunk
b_a = WorldManager(seed=777).biome_for_chunk(3, -2)
b_b = WorldManager(seed=777).biome_for_chunk(3, -2)
b_c = WorldManager(seed=778).biome_for_chunk(3, -2)
check("same seed gives same biome for a chunk", b_a == b_b)
check("different seed can give different worlds", isinstance(b_c, str))

# Streaming: as the player moves, new chunks generate and far ones unload
p = P(0, 0)
w.update_world(p)
near = w.loaded_chunk_count()
p.x = w.CHUNK_SIZE * 20  # walk far away
w.update_world(p)
far = w.loaded_chunk_count()
check("chunk count stays bounded while streaming",
      far <= (2 * w.GEN_RADIUS + 1) ** 2 + (2 * w.UNLOAD_RADIUS + 1) ** 2)
check("old origin chunk unloaded after moving far", (0, 0) not in w.chunks)
check("new region generated around the player",
      w.chunk_coord(p.x, p.y) in w.chunks)

# Biomes actually vary across the world (sample a line of chunks)
names = {w.get_chunk(cx, 0).biome_data["name"] for cx in range(-30, 30)}
check("multiple biomes appear across the world", len(names) >= 5)

# In-game: player can travel a long distance with no map swap / clamp
g = Game()
start_biome = g.world.current_biome(g.player)["name"]
seen = set()
for _ in range(1500):
    g.dt = 1 / 60
    g.player.velocity_x = 7
    g.player.velocity_y = 3
    g.update()
    seen.add(g.world.current_biome(g.player)["name"])
check("player travels far past old map bounds", g.player.x > 5000)
check("biome changes as the player travels", len(seen) >= 3)
check("rift progression continues in the open world", g.rift.type in ("normal", "greater"))
check("enemies stream in around the player", len(g.world.enemies) > 0)

# Seed survives save/load so the world is reproducible
g.save_game(0)
seed_before = g.world.seed
g2 = Game()
g2.load_game(0)
check("world seed persists across save/load", g2.world.seed == seed_before)
if os.path.exists("saves/save_slot_0.json"):
    os.remove("saves/save_slot_0.json")
    try:
        os.rmdir("saves")
    except OSError:
        pass

print("\n%d passed, %d failed" % (passed, failed))
raise SystemExit(1 if failed else 0)
