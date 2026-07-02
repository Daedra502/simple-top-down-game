# Living Map, Animated Hero, UI Cleanup, Code Health

Date: 2026-07-01
Status: approved (user chose: build all four parts, order A-D; hero style =
hooded battle-mage)

## A. Living map — biome blending + cosmetics

Problem: `WorldManager.biome_for_chunk` hashes each chunk independently, so
biomes form an uncorrelated patchwork with hard edges.

Design: seeded climate regions with soft borders.
- A coarse region lattice (REGION_SIZE = 3 chunks ≈ 2300px). Each region cell
  gets a deterministic jittered center point and a biome rolled from the
  atlas-weighted distribution (same weighting semantics as today).
- Ground is sampled per 96px sub-tile (8x8 per chunk): the sub-tile takes the
  biome of the nearest region center (Worley/Voronoi); when the second-nearest
  center is nearly as close, the two biomes' ground colors cross-fade, giving
  wide, natural transition bands.
- Determinism: everything derives from (seed, cell coords); atlas weight
  changes re-color the world exactly as before (cache cleared on weight/layout
  change).
- `chunk.biome_id` = sample at the chunk center (spawn pools/current_biome
  unchanged in shape).
- Performance: each chunk renders its ground once into a cached
  `pygame.Surface` (sub-tiles + speckle texture + props); `draw_ground` blits
  cached surfaces. Cache invalidated when layout or biome weights change.
  The black per-chunk border line is removed.
- Per-biome cosmetics: `data/biomes.json` gains a `props` list per biome
  (shape id + color + density + size). A shared prop painter
  (`src/systems/world/props.py`) draws all shapes (rock, pillar, crystal,
  ice shard, lava crack, tree, column, wisp, star, pool, spike) and is used
  for both biome props and the existing layout props — removing the
  duplicated silhouette code.

## B. Animated hero (procedural pixel-art battle-mage)

- `src/entities/player_sprite.py`: builds all frames at init from a 16x20
  pixel grid (no external assets): deep-blue hooded robe, glowing eyes,
  staff on the back; scaled with nearest-neighbor to the player's size.
- Animations: 4-frame walk cycle (leg alternation + robe sway) in 4 facings
  (left = mirrored right); 2-frame idle breathing; cast pose (arm extended,
  warm hand flare) held ~0.25s after casting.
- Player tracks facing from velocity and exposes `notify_cast()`; `draw()`
  blits the current frame. `player.image`/`rect` stay for collisions.

## C. UI cleanup

- Top HUD: fix overlapping lines (wallet/keystone row collision, biome row)
  by laying the left-of-minimap block on a fixed row grid.
- Skill bar: keep cooldown sweep + numeric timer; tooltips (hover) must show
  accurate name, level, damage, mana cost and cooldown for every skill.
- Minimap: framed panel labeled "Map", biome-colored explored trail, player
  marker, enemy dots, pylon markers.
- Escape menu (standard): Resume / Audio sliders / Save-Load / Controls /
  Quit with a confirm dialog (Y/N + buttons); Esc backs out one level at a
  time (submenu -> pause -> game).

## D. Code health (apply prior review findings)

- Bramble hazard damage now applies armor damage reduction like melee (via
  one shared player-damage helper used by melee/bramble/elite paths).
- Obstacle spawns enforce minimum separation from other obstacles and
  chests; collision loop iterates solids only with a squared-distance
  early-out.
- Minions are pushed out of solid obstacles like the player/enemies.
- Spawn ring minimum distance uses the camera half-diagonal + margin so
  chests/obstacles never pop into view.
- Chest aura surfaces cached by glow radius (no per-frame allocation); dead
  Chest sprite state (image/rect/radius) removed.

## Testing

Per part: A) region determinism, blending continuity (adjacent sub-tiles
differ by bounded color delta), cache invalidation, current_biome still
returns a valid pool; B) frames generated for all facings/states, draw runs
headless; C) HUD rows non-overlapping (rect math), tooltip content matches
skills.json, quit-confirm flow; D) armor applied to bramble damage, obstacle
separation respected, minions resolved, ring min >= half-diagonal.
