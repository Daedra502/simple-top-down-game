# Passive Skill Tree Redesign — PoE2-style Radial Web

Date: 2026-07-01
Status: approved (user chose: decompose the larger request, tree first; ~250-350
nodes; all six archetype regions; auto-refund old saves; generator-script approach)

## Goal

Replace the 79-node hand-placed passive tree with a ~300-node organized radial
web in the style of Path of Exile 2: root at center, themed regions as angular
slices, travel spokes, wheels of minors around notables, keystones at the rim,
and ring-road links between adjacent regions.

## Approach

A build-time generator (`tools/build_skill_tree.py`) computes the layout from a
hand-authored region spec and emits `data/skill_tree.json` in the existing
schema (`name/pos/tier/cost/color/bonuses/edges`). Runtime code (allocation
rules, rendering, stat aggregation) is unchanged except for small UI quality
additions. Re-running the script regenerates the tree deterministically.

## Structure

- Root ("Life Force", free) at (600, 400) — same center as today so the
  overlay opens on it.
- Six slices: Fire, Cold, Lightning, Sorcery/Speed (double-width), Summoner,
  Defense/Blood. Eight spokes leave the root (Sorcery/Speed owns three:
  `mana_1`, `dmg_1`, `speed_1`).
- Rings: gateway (~r90), travel (~r150-270), wheel band (~r330), rim travel
  (~r450), rim notables (~r510), keystones (~r570).
- Each slice: travel spokes, 2+ wheels (ring of minors + a notable on the
  wheel), a rim notable, and a keystone. Ring-road arcs connect adjacent
  spokes at two radii so builds can travel between regions.

## Compatibility contract (tests + keystones)

Preserved node IDs and adjacencies:
- Root-adjacent: `fire_1`, `mana_1`, `dmg_1`, `lightning_1`, `speed_1` (plus
  new gateways `cold_1`, `minion_1`, `blood_1`).
- Chains: `fire_1-fire_2-fire_3-fire_key`; `mana_1-mana_2-mana_3`;
  `dmg_1-dmg_2-dmg_3`; `speed_1-move_1-move_2-move_notable`;
  `speed_1-atk_1-atk_2-atk_notable` (with `move_1` NOT adjacent to root, so
  `speed_1` stays a cut vertex for the move chain).
- `hybrid_ld` bridge keystone adjacent to `lightning_1` and `dmg_1`.
- `hpregen_notable` exists (Defense slice).
- `KEYSTONE_NODES` mapping unchanged: mechanical keystones stay on `fire_key`
  (Elemental Focus), `mana_3` (Spell Echo), `dmg_3` (Omnivamp), `hybrid_ld`
  (Projectile Mastery). New keystones in other slices are stat bundles only.

## Stat vocabulary

Only keys the game already consumes: `STAT_EFFECT_KEYS` (+ `_increase`
variants), spell keys (`spell_damage`, `fire_damage`, `lightning_damage`,
`frostbolt_damage`, `fireball_damage`), ailment keys, `minion_damage_increase`,
`projectile_count/speed`, `life_leech`. New wiring (small): tree-granted
`fire/cold/lightning/physical_resistance` keys merge into `player.resistances`
(capped 75) inside `Game.recompute_player_stats` for the Defense slice.

## Saves

`apply_save` already re-allocates saved nodes connectivity-safely and drops
unknown/unreachable ones; it now also refunds one skill point per dropped node.

## UI

- Mouse-wheel zoom on the tree overlay (`SkillTreeUI.zoom`, applied in
  draw/hover/click transforms), clamped ~0.4-1.6.
- Initial view centered on the root; region name labels drawn faintly at each
  slice's mid-angle.

## Validation & tests

Generator validates: unique IDs, edges reference existing nodes, whole graph
connected from root, minimum node spacing, and prints tier counts. New pytest
module asserts: node count in 250-350, connectivity, required legacy IDs +
adjacency contract, keystone mapping intact, and save-load point refund.
