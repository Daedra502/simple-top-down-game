"""Dynamic spawn director (DESIGN.md Phase 12).

Replaces the simple one-at-a-time top-up with Diablo-style population control:
spawns vary by pack, tier (Normal/Magic/Rare/Champion/Elite), elite affixes, and
occasional dynamic events. Decisions are modulated by GR level, the current
biome, time alive and recent kill rate -- all tunable in data/spawn_director.json.
"""
import math
import random

from src.core.data_loader import load_json
from src.entities.enemy import Enemy, KEY_TO_ENEMY_TYPE, EnemyType
from src.entities.elite import build_enemy

_KILL_WINDOW = 60.0  # seconds for kills-per-minute


class SpawnDirector:
    def __init__(self):
        self.cfg = load_json("spawn_director.json")
        self.events = load_json("events.json")
        self.spawn_timer = 0.0
        self.time_alive = 0.0
        self._kill_times = []

    # --- kill tracking (difficulty "feel") --------------------------------
    def notify_kill(self):
        self._kill_times.append(self.time_alive)

    def kills_per_minute(self):
        cutoff = self.time_alive - _KILL_WINDOW
        self._kill_times = [t for t in self._kill_times if t >= cutoff]
        return len(self._kill_times)

    # --- tier / affix rolls ----------------------------------------------
    def roll_tier(self, gr_level, elite_bonus=0.0):
        weights = dict(self.cfg["tier_weights"])
        for tier, per in self.cfg.get("tier_weight_grlevel_shift", {}).items():
            weights[tier] = weights.get(tier, 0) + per * gr_level
        # Atlas "elite density" pushes the curve toward elites/champions (Phase 15).
        if elite_bonus:
            weights["elite"] = weights.get("elite", 0) + elite_bonus * 12
            weights["champion"] = weights.get("champion", 0) + elite_bonus * 10
        tiers = list(weights.keys())
        return random.choices(tiers, weights=[weights[t] for t in tiers])[0]

    def roll_affixes(self, tier):
        count = self.cfg.get("elite_affix_count", {}).get(tier, 0)
        if count <= 0:
            return []
        pool = list(load_json("elite_affixes.json").keys())
        return random.sample(pool, min(count, len(pool)))

    def _make(self, game, enemy_key, tier, affixes):
        etype = KEY_TO_ENEMY_TYPE.get(enemy_key, EnemyType.GOBLIN)
        enemy = build_enemy(etype, tier, affixes)
        game._scale_enemy(enemy)  # GR hp/damage scaling on top of tier
        return enemy

    # --- main tick --------------------------------------------------------
    def update(self, game, dt):
        self.time_alive += dt
        r = game.rift
        if not r.spawning_enabled or r.boss_active:
            self.spawn_timer = self.cfg["spawn_interval"]
            return

        self.spawn_timer -= dt
        if self.spawn_timer > 0:
            return
        self.spawn_timer = self.cfg["spawn_interval"]

        atlas = game.atlas.get_effects() if hasattr(game, "atlas") else {}

        # Occasionally fire a dynamic event (atlas raises the rate, Phase 15).
        event_freq = self.cfg["event_frequency"] * (1.0 + atlas.get("event_rate", 0.0))
        if random.random() < event_freq:
            self.trigger_event(game)
            return

        biome = game.world.current_biome(game.player)
        layout_mult = getattr(game, "map_layout", {}).get("density_mult", 1.0)
        density = int(r.density() * biome.get("spawn_density", 1.0) * layout_mult)
        # A lively fight: push density up a touch when the player is clearing fast.
        density += min(4, self.kills_per_minute() // 20)
        if len(game.world.enemies) >= density:
            return

        self.spawn_pack(game, biome, density)

    def spawn_pack(self, game, biome, density):
        headroom = max(1, density - len(game.world.enemies))
        size = int(round(self.cfg["base_pack_size"]
                         + self.cfg["pack_size_per_grlevel"] * game.rift.gr_level))
        size = max(1, min(headroom, size))

        cx, cy = game._ring_spawn_point()
        pool = biome.get("enemy_pool") or ["goblin"]
        scatter = self.cfg["pack_scatter"]
        atlas = game.atlas.get_effects() if hasattr(game, "atlas") else {}
        elite_bonus = atlas.get("elite_density", 0.0)

        for _ in range(size):
            enemy_key = random.choice(pool)
            tier = self.roll_tier(game.rift.gr_level, elite_bonus)
            affixes = self.roll_affixes(tier)
            enemy = self._make(game, enemy_key, tier, affixes)
            enemy.x = cx + random.uniform(-scatter, scatter)
            enemy.y = cy + random.uniform(-scatter, scatter)
            enemy.rect.center = (enemy.x, enemy.y)
            game.world.enemies.append(enemy)

    # --- dynamic events ---------------------------------------------------
    def trigger_event(self, game):
        event_id = random.choice(list(self.events.keys()))
        ev = self.events[event_id]
        game._set_rift_message(ev["label"])
        kind = ev["kind"]

        if kind in ("swarm", "miniboss"):
            count = ev.get("count", 1)
            cx, cy = game._ring_spawn_point()
            for _ in range(count):
                enemy = self._make(game, ev["enemy"], ev.get("tier", "normal"), [])
                enemy.x = cx + random.uniform(-90, 90)
                enemy.y = cy + random.uniform(-90, 90)
                enemy.rect.center = (enemy.x, enemy.y)
                game.world.enemies.append(enemy)

        elif kind == "goblin":
            enemy = self._make(game, ev["enemy"], ev.get("tier", "magic"), [])
            enemy.is_treasure_goblin = True
            enemy.loot_drops = ev.get("loot_drops", 6)
            cx, cy = game._ring_spawn_point()
            enemy.x, enemy.y = cx, cy
            enemy.rect.center = (cx, cy)
            game.world.enemies.append(enemy)

        elif kind == "curse":
            # Cursed Shrine: curse every nearby enemy with Vulnerable.
            for e in game.world.enemies:
                e.elemental_effects.apply_vulnerable(game.player)
