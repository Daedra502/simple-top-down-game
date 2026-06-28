# ARPG Design & Build Plan

A pseudocode-pass design document for evolving the existing top-down pygame ARPG into an
endless, save-driven, Diablo-3 + Path-of-Exile-2 hybrid. This is **logic and structure**,
not finished Python. Build phases **strictly in order**.

---

## STEP 0 — Existing Project Analysis

### What exists today

**Entry point / loop** — [main.py](main.py): single `Game` class. Classic fixed-timestep
loop: `handle_events() → handle_input() → update() → draw()` at 60 FPS via
`clock.tick(60)`. A frame delta of `0.016` is **hardcoded** in many `update()` calls
instead of being measured — a correctness smell once timing matters.

**Entities** — OOP, `pygame.sprite.Sprite` subclasses:
- [src/entities/player.py](src/entities/player.py) `Player`: position, `health/max_health`,
  `mana/max_mana`, `mana_regen`, `damage`, `attack_speed`, leveling
  (`level`, `experience`, `xp_to_level`, `skill_points`, `max_level=50`), a 4-tier wallet
  (copper/silver/gold/diamond), wand upgrades, and a bag of keystone flags. Damage math lives
  in `get_spell_damage()`.
- [src/entities/enemy.py](src/entities/enemy.py) `Enemy`: 8 hardcoded types via a big
  `if/elif` on `EnemyType`; chase/wander AI; `experience_reward` + `money_reward`.
- [src/entities/chest.py](src/entities/chest.py) `Chest`.

**Systems** — [src/systems/combat.py](src/systems/combat.py) `CombatSystem` (physical +
`apply_elemental_damage` with status hooks) and `CollisionSystem` (circle/rect). Note:
`CollisionSystem` is **defined twice** (here and in `collision.py`) — dead duplication.

**Spells** — [src/spells/](src/spells/): `SPELLS`, gem/modifier system, `skill_tree.py`
(graph of `SkillNode`s with prerequisites/children, allocation rules, `get_active_effects()`),
`keystones.py`, `elements.py` (`ElementType`, `ElementalEffectManager`: burn/freeze/shock/poison).

**Items** — [src/items/](src/items/): `Item` (rarity, slot, flat `stats` dict),
`ItemFactory`, `Inventory`/`EquipmentSlots`/`ItemManager`, set bonuses, synergistic items.

**UI** — [src/ui/](src/ui/): health bars, resource panel, damage numbers, skill bar,
skill-tree overlay, character sheet.

**Maps** — [src/maps/map_manager.py](src/maps/map_manager.py): 8 **fixed**, fully
pre-generated `Map` objects in a linear `map_progression` list. Win = clear all 8.

**Save** — **none.** No serialization seam anywhere.

### Architectural style

Modular OOP, package-per-domain (`entities/spells/items/systems/ui/maps`), single `Game`
god-object orchestrating. Mostly data-light: tuning values are scattered as **literals**
inside class bodies (enemy stats in `if/elif`, XP curve in `get_xp_requirement`, skill costs,
node bonuses). **Commit to this structure** — it's clean enough to grow. We extend packages;
we do not rewrite.

### Refactors required before/within the build (with payoff)

| # | Refactor | Why it fights an endless save-driven ARPG | Payoff |
|---|----------|-------------------------------------------|--------|
| R1 | **`Stats` aggregator** on player (Phase 2/4) | Stats are mutated in-place from many places (`_apply_skill_tree_effects`, set bonuses, wand); base values get clobbered (`max_health = 100 + …`). No single source of truth → gear+tree+ailments can't stack predictably. | One recompute funnel; every later system writes to data, reads effective. |
| R2 | **Data-drive enemies** (Phase 1/5/12) | `if/elif` over 8 types can't scale to bosses, GR tiers, elite affixes, biome pools. | New enemies/bosses become JSON rows, not code. |
| R3 | **Real frame delta `dt`** | Hardcoded `0.016` breaks regen/DoT/cooldowns the moment FPS varies; cooldowns count *frames* not seconds. | Time-correct ailments, regen, attack-speed gating. |
| R4 | **Replace `MapManager` with a streaming world** (Phase 5/11) | Fixed maps + "clear 8 to win" is the opposite of endless. No serialization seam. | Infinite rifts + chunk streaming + saveable world. |
| R5 | **Central tuning data module** (`data/`) | Literals everywhere make a balance pass impossible. | All curves in one place (Phase 10). |
| R6 | **De-dupe `CollisionSystem`** | Two definitions drift. | One owner in `systems/collision.py`. |

### Concrete extension points (where phases hook in)

- `Game.update()` — add `dt`, world streaming, rift progress, director ticks.
- `Player` — gains a `Stats` object (R1); existing `add_experience`, wallet, skill flags stay.
- `Enemy.__init__` — swap `if/elif` for `EnemyDefinition` lookup (R2); `on_death` hook.
- `CombatSystem.apply_*` — becomes the single **damage pipeline** every source routes through.
- `SkillTree` — already a graph with `get_active_effects()`; feed it into `Stats` (R1).
- `ItemManager` — already aggregates; add affix rolls + feed `Stats`.
- `MapManager` — retired behind a `RiftManager`/`WorldManager` (R4) implementing the same
  "give me the current playfield" interface so `Game` barely changes.

---

## Proposed module / file layout

```
main.py                      # Game loop (extended, not replaced)
data/                        # NEW — all tuning is data (R5)
  enemies.json               # base enemy + boss-pool rows         (P1,P5,P12)
  affixes.json               # gear affix pool + weights           (P6)
  skill_tree.json            # passive nodes/edges                 (P4)
  ailments.json              # burn/freeze/shock/vulnerable        (P7,P8,P9)
  skills.json                # active skills + level curves        (P13)
  runes.json                 # skill modifiers                     (P14)
  biomes.json                # biome definitions                   (P11)
  ascendancy.json atlas.json # endgame trees                       (P15)
  tuning.json                # XP curve, GR scaling, drop rates    (P10)
src/
  core/
    stats.py                 # Stats aggregator (R1)               (P2,P4,P6)
    damage.py                # damage pipeline                     (P2,P7,P8)
    save.py                  # serialize/deserialize player+world  (P10)
    rng.py                   # seeded RNG for reproducible worlds
  entities/
    player.py enemy.py chest.py
    boss.py                  # boss-pool entity                    (P5)
    elite.py                 # tier + elite-affix wrapper          (P12)
  systems/
    combat.py collision.py
    leveling.py              # XP curve + level-up                 (P3)
    rift.py                  # normal + greater rift state machine (P5)
    spawn_director.py        # dynamic population                  (P12)
    world/                   # streaming world                     (P11)
      world_manager.py chunk.py biome.py
    ailments.py              # vulnerable + elemental ailments     (P7,P8,P9)
  spells/                    # existing tree/elements +
    active_skills.py runes.py                                     # (P13,P14)
  progression/
    ascendancy.py atlas.py                                        # (P15)
  items/                     # + affix roller                      (P6)
  ui/                        # + rift bars, GR picker, save menu
```

---

# PHASES 1–10 (core game)

## PHASE 1 — Foundation & Health Bars
**Goal:** Player + data-driven enemies live in the loop with scaling health bars.
**Dependencies:** Step 0.

**Pseudocode**
```
class Entity:                      # shared base extracted from Player/Enemy
    hp, max_hp, x, y, stats
    on_death = Event()             # hook so XP/loot/orbs attach later (P3,P5,P7)
    def take_damage(amount):
        hp = max(0, hp - amount)
        if hp == 0: die()
    def die():
        on_death.fire(self)        # listeners added by later phases

class HealthBar:
    def draw(surface, entity, anchor):       # anchor = entity or HUD-fixed
        frac = entity.hp / entity.max_hp
        draw back_bar
        draw fill_bar scaled by frac
        color = lerp(green→yellow→red, frac) # (purple override added in P7)
```
**Data shapes** — `enemies.json` row (see Data Shapes §). Enemy `__init__` reads the row
instead of `if/elif` (R2).
**Integration:** `Enemy`/`Player` extend `Entity`; reuse existing draw. `EnemyHealthBar` in
[src/ui/health_bars.py](src/ui/health_bars.py) generalized to `HealthBar`.
**Done when:** entities render, move, take damage, die, fire `on_death`, show scaling bars;
player bar also pinned in HUD.

## PHASE 2 — Combat Core & Resources
**Goal:** One damage pipeline + a `Stats` source of truth.
**Dependencies:** P1.

**Pseudocode**
```
class Stats:                       # R1 — base + layered modifiers
    base = {...}                   # from class/level
    layers = {tree:{}, gear:{}, ailment:{}}   # filled by P4,P6,P7
    def get(stat): return combine(base, all layers)   # +flat then *increase
    def recompute(): cache effective values; clamp hp/mana to new max

def damage_pipeline(source, target, base, element, tags):   # core/damage.py
    dmg = base
    dmg *= (1 + source.stats.get(element+'_increase'))
    dmg *= crit_roll(source.stats)                          # P6 gear
    dmg *= vulnerable_mult(target)                          # P7
    dmg -= target.resistance(element)                       # capped %
    target.take_damage(dmg)
    return dmg

Player.update(dt):                 # R3 real dt
    regen_tick: hp += stats.get('hp_regen')*dt; mana += stats.get('mana_regen')*dt
    attack_gate -= dt
def try_attack(): if attack_gate<=0 and mana>=cost: spend; attack_gate = 1/stats.get('attack_speed')
```
**Data shapes:** stat keys centralized; gold already exists on `Player`.
**Integration:** retire `get_spell_damage`/`_apply_skill_tree_effects` into `Stats`+pipeline.
`CombatSystem.apply_*` delegates to `damage_pipeline`.
**Done when:** attacks consume mana, regen ticks per-second, attack speed throttles, gold
gained/spent — all reading one `Stats`.

## PHASE 3 — Leveling & Progression
**Goal:** Kills grow the character and grant skill points.
**Dependencies:** P2.

**Pseudocode**
```
# systems/leveling.py
def xp_to_next(level): return tuning.xp.base * level ** tuning.xp.exp   # data (R5)
def gain_xp(player, amount):
    player.experience += amount
    while player.experience >= xp_to_next(player.level):
        player.experience -= xp_to_next(player.level)
        level_up(player)
def level_up(player):
    player.level += 1
    player.skill_points += 1
    player.stats.base.apply(tuning.per_level)   # +hp,+mana,+core
    player.stats.recompute(); player.hp=max_hp; player.mana=max_mana
    fire feedback cue (flash + sound + floating text)
# enemy.on_death subscriber (registered here): gain_xp(player, enemy.xp_reward)
```
**Integration:** subscribe to `Entity.on_death` from P1; move `Player.add_experience` logic
here. `level/experience/skill_points` already the save anchor.
**Done when:** kills grant XP; leveling raises stats + awards points with a clear cue.

## PHASE 4 — PoE2-Style Passive Tree
**Goal:** Path-based passive graph that defines build identity and feeds `Stats`.
**Dependencies:** P3, P2.

**Pseudocode**  *(existing `skill_tree.py` already does most of this — move node data to JSON)*
```
load tree from skill_tree.json → {nodes:{id:{pos,type,cost,bonuses,edges[]}}}
def can_allocate(node): node not allocated and any(neighbor allocated)   # PoE2 rule
def allocate(node):
    if points >= cost and can_allocate(node):
        points -= cost; allocated.add(node); StatAggregator.recompute()
class StatAggregator:              # writes player.stats.layers['tree']
    def recompute(): sum bonuses over allocated nodes → tree layer → stats.recompute()
# render: draw edges, nodes (color by type/allocatable), hit-test click→nearest node
```
Must include nodes for: move speed, attack speed, attack damage (+ clustered minor→notable),
hp regen, mana regen, skill mods/synergies.
**Integration:** `SkillTree.get_active_effects()` → `stats.layers['tree']`. Reuse
`SkillTreeUI`. Allocation already path-checked via prerequisites; switch to neighbor rule.
**Done when:** points spend along connected paths; move/attack speed/damage change live.

## PHASE 5 — Rift & Greater Rift System *(core endgame)*
**Goal:** Normal rifts → keystones → player-chosen Greater Rifts that scale.
**Dependencies:** P1–P4.

**Pseudocode**
```
# systems/rift.py
class Rift:
    type: NORMAL|GREATER; gr_level; progress=0; threshold; boss_spawned=False
    bar_color = YELLOW if NORMAL else PURPLE
def on_enemy_killed(enemy):
    rift.progress += enemy.progress_value
    if rift.progress >= rift.threshold and not boss_spawned:
        spawn boss = pick(BOSS_POOL_10); scale_for_rift(boss, rift); boss_spawned=True
boss.on_death subscriber:
    grant big XP+gold * reward_mult(rift)
    if rift.NORMAL: drop RiftKeystone into inventory
    else: drop scaled loot (P6)

# GR scaling (data-driven, tuning.json)
def scale_for_rift(e, rift):
    e.max_hp *= hp_mult(rift.gr_level); e.damage *= dmg_mult(rift.gr_level)
def hp_mult(L):  return tuning.gr.hp_base ** L          # e.g. 1.08**L
def reward_mult(L): return 1 + tuning.gr.reward_k * L

# open-GR flow
choose gr_level in 1..100 → consume 1 RiftKeystone → new Rift(GREATER, gr_level)
```
**Data shapes:** boss row, keystone item, GR config (see §). Boss pool = 10 JSON rows.
**Integration:** replaces map "clear→exit→next". `on_enemy_killed` subscribes to P1 `on_death`.
Bars are new UI. Keystones live in existing `Inventory`.
**Done when:** clear normal (yellow)→boss→keystone→pick GR 1–100→GR (purple)→boss rewards
scale to level.

## PHASE 6 — Itemization: Armor & Jewelry
**Goal:** Gear that stacks build stats.
**Dependencies:** P2, P4.

**Pseudocode**
```
# items/affix_roller.py, data/affixes.json
def roll_item(slot, ilvl, rarity):
    n = affix_count(rarity)
    pick n affixes weighted by ilvl from pool; roll value in [min,max] scaled by ilvl
    return Item(slot, rarity, affixes)
def equip(item): unequip slot; stats.layers['gear'] = sum(all equipped affixes); recompute
```
Affix pool must cover: crit chance, crit damage, status radius, cooldown reduction, attack
speed, attack damage, mana/hp regen, increased hp, increased mana, elemental+physical
resistances, increased Vulnerable damage (feeds P7).
**Integration:** extend `ItemFactory`→affix rolls; `StatAggregator` now sums
base+tree+gear. Drop rate scales with rift/GR level (P5/P10).
**Done when:** equipping changes aggregated stats; crit/CDR/regen/resist read from gear.

## PHASE 7 — Vulnerable Status
**Goal:** A debuff that rewards setup and feeds the loot loop.
**Dependencies:** P5, P6.

**Pseudocode**
```
# systems/ailments.py
def apply_vulnerable(enemy): enemy.vuln = Timer(data.vulnerable.duration)  # refresh resets
def vulnerable_mult(enemy):
    if enemy.vuln.active:
        return 1 + 0.15 + source.stats.get('increased_vulnerable_damage')   # gear P6
    return 1.0
HealthBar color: if enemy.vuln.active → PURPLE override (P1)
enemy.on_death / on_hit: if vuln and roll < orb_chance:
    drop ProgressOrb(type = rift.type)        # yellow in normal, purple in GR
on_orb_pickup: rift.progress += orb.value     # pushes matching bar (P5)
```
**Integration:** `vulnerable_mult` is a stage in P2 pipeline. Orb type matches `Rift.type`.
**Done when:** afflicted enemies show purple bar, take +15%(+gear), can drop type-matched orbs.

## PHASE 8 — Elemental Skill Modifications I
**Goal:** Skills carry elements that create ailments.
**Dependencies:** P2, P4, P7.

**Pseudocode**
```
# data/ailments.json drives all numbers
on_hit(element):
  FIRE  → add Burn stack (DoT ticks through P2 pipeline each second)
  ICE   → add Slow; chill_buildup += k; if buildup>=freeze_threshold → Freeze(stun)
  SHOCK → add StaticCharge; if charged enemies nearby → chain bolt to them
ailment_tick(dt): for each ailment: apply per-tick dmg via damage_pipeline(...);
                  decay duration; expire at 0
```
Each ailment = data (duration, magnitude, stack rule). DoT routes through the pipeline so
resistances + Vulnerable apply.
**Integration:** extend existing `ElementalEffectManager`; skills tag their element (P13 later).
**Done when:** fire burns, ice slows/freezes, shock arcs between shocked enemies.

## PHASE 9 — Elemental Modifications II (Synergies)
**Goal:** Ailments interact and scale.
**Dependencies:** P8 (+4,6,7).

**Pseudocode**
```
tree nodes + affixes add: burn_damage%, freeze_threshold/duration, shock_chain_count/range
combos (data-tunable):
  frozen target → takes +shatter_bonus hit damage
  burning + vulnerable → DoT *= combo_mult
  shock chain → spreads/refreshes ailments across chained targets
optional keystone nodes: change element behavior (e.g. "Burn never expires")  # build-defining
```
**Integration:** combo checks live in `ailments.py`, read tuning data; tree/affixes feed
magnitudes via `Stats`.
**Done when:** ailments scale off tree/gear, combos fire, elemental builds feel distinct.

## PHASE 10 — Save/Load, Endless Loop & Balance
**Goal:** Persist everything; lock the loop; centralize tuning.
**Dependencies:** all.

**Pseudocode**
```
# core/save.py — JSON slot (justified: human-readable, schema-flexible, no native seam exists)
def save(player, world):
    write {version, level, xp, gold, stats_base, allocated_nodes:[ids],
           inventory:[item_dicts incl keystones], equipped:{slot:item},
           highest_gr, world_seed}
def load(path):
    rebuild player; re-allocate nodes by id; StatAggregator.recompute(); restore inventory/gear;
    reseed world  → loaded character identical to saved
# endless loop ties P5: normal→keystone→choose GR→clear→bigger rewards→repeat
```
**Balance:** all curves already in `data/tuning.json` (R5): XP, GR hp/dmg/density/reward,
drop rates, ailment numbers, Vulnerable %. Pacing levers: keystone drop rate, GR reward_k,
xp.exp, density ramp.
**Done when:** save/reload is identical; full rift→keystone→GR→reward→escalation runs endlessly.

---

# PHASES 11–15 (endless world + deep build systems)

> These supersede the fixed `MapManager` (R4) and the static skill/enemy systems with
> **one continuously generated endless rift world**. P5's rift *progress* logic is preserved;
> only the *playfield* changes from "a map" to "streamed chunks."

## PHASE 11 — Endless Rift World Generation
**Goal:** Replace isolated maps with an infinitely streaming procedural world — no loading screens.
**Dependencies:** P1–10.

**Pseudocode**
```
# systems/world/world_manager.py  (seeded — rng.py — so worlds are saveable/reproducible)
def update_world(player):
    cur = chunk_at(player.x, player.y)
    for n in neighbors(cur, radius=GEN_RADIUS):
        if not loaded(n): generate_chunk(n)          # deterministic from (seed, cx, cy)
    for c in loaded_chunks:
        if dist(c, cur) > UNLOAD_RADIUS: save_chunk_state(c); unload(c)
def generate_chunk(coord):
    biome = pick_biome(seed, coord)                  # data/biomes.json
    tiles = gen_tiles(biome); enemies = seed_packs(biome)  # P12 director fills live
    return Chunk(coord, biome, tiles, enemies, events, portals, structures)
# rift progress unchanged from P5 — boss spawns NEAR player, no map swap:
def on_enemy_killed(e): rift.progress += e.progress_value
                        if full: spawn_rift_boss_near_player()
```
**Data shapes:** `ChunkDefinition`, `BiomeDefinition` (§). Camera follows player across chunks.
**Integration:** `WorldManager` exposes the same "active entities / draw playfield" interface
`Game` used from `MapManager` (R4) — `Game.update/draw` change minimally. `chunk.discovered`
+ `world_seed` go in the save (P10).
**Done when:** world streams infinitely, multiple biomes appear, no load screens, rift
progression continues indefinitely.

## PHASE 12 — Enemy Ecosystem & Spawn Director
**Goal:** Diablo-style dynamic populations.
**Dependencies:** P11.

**Pseudocode**
```
# systems/spawn_director.py
config reads: difficulty, player_level, rift_level, chunk.biome, time_alive, kills_per_minute
def tick(dt):
    budget = pack_budget(player_level, rift_level, kills_per_minute)
    while budget>0: spawn pack(size, family from biome.enemy_pool, tier rolled)
    maybe roll elite (elite_frequency) → wrap with EliteEnemy(affixes[1..2])
    maybe trigger event (event_frequency): Demon Invasion|Treasure Goblin|Void Breach|
                                           Cursed Shrine|Ancient Guardian
tier ∈ {Normal,Magic,Rare,Champion,Elite,Boss,RiftBoss} → stat multipliers (data)
family ∈ {Undead,Demons,Constructs,Beasts,Cultists,Elementals,Voidborn,Angels,Mutants,Ancients}
elite affixes ∈ {Molten,Frozen,Arcane,Explosive,Regenerating,Vampiric,Stormcaller,
                 Juggernaut,Teleporting,Reflective}  # each = behavior + on-hit/on-death hook
```
**Data shapes:** `EnemyFamilyDefinition`, `EliteAffixDefinition`, `SpawnDirectorConfig` (§).
**Integration:** director fills `Chunk.enemies` (P11); all spawns are `Enemy`/`EliteEnemy`
data rows (R2); elite affixes hook the P2 pipeline + P7/P8 ailments.
**Done when:** packs vary naturally, elites appear, events spawn dynamically, difficulty feels alive.

## PHASE 13 — Spell System & Active Skill Framework
**Goal:** PoE-inspired active skills that level independently.
**Dependencies:** P2–12.

**Pseudocode**
```
# spells/active_skills.py, data/skills.json
class Skill: id,name,level,xp,mana_cost,cooldown,tags[],modifiers[]   # modifiers from P14
starter set: Fireball, Ice Shard, Chain Lightning, Arc Slash, Poison Nova, Meteor, Blink, Summon Skeleton
def on_skill_event(skill, kind): skill.xp += xp_for(kind)   # kind: killed|used|damage_dealt
                                 while skill.xp>=skill_to_next(): skill_level_up(skill)
def skill_level_up(s): s.level++; apply SkillLevelDefinition (damage,radius,duration,effect+)
each skill has its own mastery path (SkillMasteryNode graph) e.g. Fireball:
   Split Projectile→Explosion Radius→Burn Duration→Chain Explosion→Meteor Conversion
```
**Data shapes:** `SkillDefinition`, `SkillLevelDefinition`, `SkillMasteryNode` (§).
**Integration:** skills route damage through P2 pipeline + tag element for P8 ailments; XP
events subscribe to P1 `on_death` + hit callbacks. Skill state added to save (P10).
**Done when:** skills gain XP, level independently, and grow stronger over time.

## PHASE 14 — Skill Modification & Rune System
**Goal:** Runes evolve a skill into a different ability.
**Dependencies:** P13.

**Pseudocode**
```
# spells/runes.py, data/runes.json
modifier types:
  Projectile: +Projectiles,Pierce,Fork,Chain,Return,Boomerang
  Area: Larger Radius,Lingering Ground,Shockwave,Nova
  Element: Fire→Ice, Fire→Shock, Physical→Poison
  Behavior: Auto Target,Orbit Player,Triggered (Cast On Critical/Kill)
def apply_runes(skill):
    cast_plan = base_cast(skill)
    for rune in skill.modifiers: cast_plan = rune.transform(cast_plan)  # composable
    return cast_plan
# e.g. Fireball + Fork + Chain + Meteor Conversion ≈ Meteor Shower (no new skill needed)
```
**Data shapes:** `RuneDefinition` (§).
**Integration:** runes mutate the cast pipeline before P2 damage; element runes swap the P8
ailment applied. Equipped runes saved per-skill (P10).
**Done when:** skills transform, multiple rune combos work, build diversity explodes.

## PHASE 15 — Advanced Passive Atlas & Ascendancy
**Goal:** Permanent endgame build identity + world-shaping atlas.
**Dependencies:** P14.

**Pseudocode**
```
# progression/ascendancy.py — unlock specialization at levels 20/40/60/80
ascendancies: Elementalist(Burn/Shock/Freeze mastery), Berserker(Atk speed/Life leech/Rage),
              Necromancer(Minions/Corpses/Summons), Riftwalker(Teleport/Void dmg/Chunk manip)
# progression/atlas.py — separate endgame tree (atlas.json)
atlas nodes modify: biome_frequency, boss_frequency, elite_density, loot_quality, event_rates
keystones: Glass Cannon(+100% dmg,-50% maxHP), Eternal Flame(burn never expires, cannot freeze),
           Overcharged(shock stacks infinitely)
# atlas effects feed P11 generation + P12 director as global modifiers
def apply_atlas(world_gen_params, director_config): scale by allocated atlas nodes
```
**Data shapes:** `AscendancyDefinition`, `AtlasNodeDefinition` (§).
**Integration:** ascendancy = extra `Stats` layer + behavior flags; atlas modifies P11/P12
parameters → "atlas influences the generated world." Both saved (P10).
**Done when:** character identity is permanent, endgame progression exists, atlas shapes the world.

---

# Data Shapes

```jsonc
// skill-tree node (data/skill_tree.json)
{ "id":"speed_2","type":"notable","pos":[460,520],"cost":1,
  "edges":["speed_1","speed_3"], "bonuses":{"attack_speed":0.20} }

// armor affix roll (on an Item)
{ "slot":"chest","rarity":"rare","ilvl":42,
  "affixes":[{"stat":"increased_health","value":85},
             {"stat":"fire_resistance","value":31},
             {"stat":"cooldown_reduction","value":0.08}] }

// jewelry affix roll
{ "slot":"ring_1","rarity":"unique","ilvl":60,
  "affixes":[{"stat":"crit_chance","value":0.06},
             {"stat":"crit_damage","value":0.45},
             {"stat":"increased_vulnerable_damage","value":0.20}] }

// boss (1 of pool of 10) — data/enemies.json
{ "id":"ashbringer","theme":"fire","is_boss":true,"hp":4000,"damage":120,
  "abilities":["flame_nova","meteor_call","burning_ground"],
  "xp_reward":5000,"gold_reward":1200,"progress_value":0 }

// rift keystone (inventory consumable)
{ "item_id":"rift_keystone","name":"Rift Keystone","type":"keystone","stack":3 }

// GR config (level 1..100) — derived from tuning.json
{ "gr_level":47,"hp_mult":1.08**47,"dmg_mult":1.06**47,
  "density_mult":1.0+0.02*47,"reward_mult":1+0.15*47,"loot_quality":47 }

// ailment definition — data/ailments.json
{ "id":"burn","element":"fire","duration":3.0,"tick":1.0,"magnitude":0.25,
  "stack_rule":"stack","max_stacks":5 }
{ "id":"vulnerable","duration":6.0,"bonus_damage":0.15,"orb_drop_chance":0.20 }

// ChunkDefinition (P11)
{ "chunk_id":"7_-3","world_x":7,"world_y":-3,"biome_id":"frozen_tundra",
  "tiles":[],"enemies":[],"events":[],"portals":[],"structures":[],"discovered":false }

// BiomeDefinition (P11)
{ "id":"burning_hellscape","enemy_pool":["demons","elementals"],"spawn_density":1.3,
  "hazards":["lava_pool"],"loot_bonus":0.1,"boss_pool":["ashbringer"],"music":"hell" }

// EnemyFamilyDefinition (P12)
{ "id":"undead","members":["skeleton","lich"],"resistances":{"cold":0.2,"chaos":-0.2} }

// EliteAffixDefinition (P12)
{ "id":"molten","on_death":"explode_fire","aura":"burning_ground","stat_mult":{"hp":1.5} }

// SpawnDirectorConfig (P12)
{ "base_pack_size":5,"elite_frequency":0.08,"event_frequency":0.03,
  "density_per_grlevel":0.02,"tier_weights":{"normal":70,"magic":20,"rare":8,"champion":2} }

// SkillDefinition (P13)
{ "id":"fireball","name":"Fireball","mana_cost":15,"cooldown":0.6,"tags":["fire","projectile"],
  "base":{"damage":40,"radius":24},"max_level":20,"mastery_tree":"fireball_mastery" }

// SkillLevelDefinition (P13)
{ "level":7,"damage":92,"radius":30,"duration":3.2,"effect_strength":1.6 }

// SkillMasteryNode (P13)
{ "id":"fb_explosion","skill":"fireball","cost":1,"edges":["fb_split"],
  "effect":{"explosion_radius":0.25} }

// RuneDefinition (P14)
{ "id":"fork","modifier_type":"projectile","rarity":"rare",
  "effects":{"fork_count":2},"transform":"split_on_hit" }

// AscendancyDefinition (P15)
{ "id":"elementalist","unlock_level":20,
  "nodes":["em_burn_mastery","em_shock_mastery","em_freeze_mastery"] }

// AtlasNodeDefinition (P15)
{ "id":"atlas_elite_density","cost":1,"edges":["atlas_start"],
  "effect":{"elite_density":0.15} }

// save file (data/save_slot_0.json) — P10
{ "version":1,"level":34,"xp":1820,"gold":{"copper":3,"silver":2,"gold":5,"diamond":1},
  "stats_base":{...},"allocated_nodes":["root","speed_1","speed_2","fire_1"],
  "skills":[{"id":"fireball","level":7,"xp":340,"runes":["fork","chain"]}],
  "ascendancy":"elementalist","atlas_nodes":["atlas_start","atlas_elite_density"],
  "inventory":[{...},{"item_id":"rift_keystone","stack":2}],
  "equipped":{"chest":{...},"ring_1":{...}},
  "highest_gr":47,"world_seed":884412 }
```

---

# Balance Levers (Phase 10 — all tuning is data)

Every curve lives in `data/` so a balance pass touches no code:

| File | Levers | Pacing effect |
|------|--------|---------------|
| `tuning.json` `xp` | `base`, `exponent`, `max_level` | level cadence |
| `tuning.json` `per_level` | hp/mana/damage growth | power curve |
| `tuning.json` `rift` | `normal_threshold`, `max_alive`, `spawn_interval`, `keystone_reward`, `boss_loot_drops`, `trash_drop_chance` | rift length, density, loot flow |
| `tuning.json` `gr` | `hp_base`, `dmg_base`, `density_per_level`, `reward_k`, `threshold_per_level`, `max_level` | GR difficulty vs reward slope |
| `affixes.json` | per-affix `min`/`max`/`per_ilvl`/`weight`/`slots` | gear power & rarity feel |
| `ailments.json` | burn/freeze/shock numbers, `vulnerable` %/orb-chance, `combos` | ailment build strength |
| `enemies.json`, `bosses.json` | hp/damage/rewards/`progress_value` | encounter pacing |
| `skill_tree.json` | node bonuses/edges/cost | build identity |

**Key fun-not-grind levers:** `gr.reward_k` (reward per GR level), `rift.keystone_reward`
(GR access rate), `xp.exponent` (level wall), `gr.density_per_level` (screen pressure),
`vulnerable.orb_drop_chance` (rift-speed payoff for setup).

---

# Build Checklist (strict order)

- [x] **Step 0** analysis read; R1–R6 refactors acknowledged.
- [x] **P1** Entity base + `on_death` + scaling/HUD health bars; enemies data-driven.
- [x] **P2** `Stats` aggregator + single damage pipeline + dt-based regen/attack-speed/gold.
- [x] **P3** XP curve + level-up (points, stats, restore, cue) on `on_death`.
- [x] **P4** Passive graph from data; neighbor-rule allocation → `StatAggregator`.
- [x] **P5** Normal rift (yellow)→10-boss pool→keystone; GR picker 1–100 (purple)→scaled rewards.
- [x] **P6** Affix roller; base+tree+gear aggregation; crit/CDR/regen/resist/vuln-dmg.
- [x] **P7** Vulnerable: +15%(+gear), purple bar, type-matched progress orbs.
- [x] **P8** Elements → Burn / Slow+Freeze / Shock-chain through pipeline.
- [x] **P9** Tree+gear ailment scaling + combos + element keystones.
- [x] **P10** JSON save/load identical rebuild; centralized tuning; endless loop verified.
- [x] **P11** Seeded streaming chunk world; biomes; no load screens; rift progress preserved.
- [x] **P12** Spawn director: families, tiers, elite affixes, dynamic events.
- [x] **P13** Active skills with independent XP/levels + per-skill mastery.
- [x] **P14** Runes transform skills (composable cast pipeline).
- [x] **P15** Ascendancies (20/40/60/80) + atlas tree shaping P11/P12.

**Save location:** `saves/save_slot_{n}.json` (F5 save / F9 load). Per-skill `skills`/`runes`
and `ascendancy`/`atlas`/`world_seed` fields in the data shape above are reserved for
Phases 11–15; the Phase 10 writer emits the implemented subset and the loader ignores unknown keys.

**Assumptions:** no audio/asset pipeline yet (placeholder cues); save = JSON slot (no prior
format); `0.016` dt replaced with measured `dt` early (R3); existing 8 fixed maps are retired
by P5/P11 but their enemy/reward data is migrated into `data/enemies.json`.
