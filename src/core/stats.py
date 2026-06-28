"""Central Stats aggregator -- the single source of truth for player stats.

Resolves DESIGN.md R1: instead of many systems mutating ``player.max_health`` in
place (and clobbering each other), every system writes a *layer*, and the
effective value is computed from ``base`` + all layers.

Combine rule per stat key:
    effective = (base[key] + sum(layer[key])) * (1 + sum(layer[key + "_increase"]))

So a flat node bonus uses ``{"max_health": 50}`` while a percentage bonus uses
``{"max_health_increase": 0.10}``. Most existing skill-tree data is flat, and
fractional stats like ``attack_speed`` are stored as flat additions onto the
base of 1.0 -- both work unchanged.
"""

# Base stats for a fresh level-1 character. Per-level growth (Phase 3) and
# balance tuning (Phase 10) mutate ``base`` directly.
BASE_STATS = {
    "max_health": 100,
    "max_mana": 100,
    "health_regen": 2.0,      # per second
    "mana_regen": 10.0,       # per second
    "move_speed": 5.0,
    "attack_speed": 1.0,      # multiplier; higher = faster
    "damage": 10,
    "crit_chance": 0.05,      # 5%
    "crit_damage": 1.5,       # +50% on crit
    "cooldown_reduction": 0.0,
    "armor": 0,
    "status_radius": 1.0,                 # multiplier for status-effect radius
    "increased_vulnerable_damage": 0.0,   # bonus mult vs Vulnerable (Phase 7)
    "burn_damage_increase": 0.0,          # ailment scaling (Phase 9)
    "freeze_duration_bonus": 0.0,
    "freeze_threshold_reduction": 0.0,
    "shock_chain_bonus": 0,
    "shock_range_bonus": 0.0,
    "life_leech": 0.0,                    # heal % of damage dealt (Phase 15)
    "minion_damage_increase": 0.0,        # minion scaling (Phase 15)
    "projectile_count": 0,                # extra projectiles added to every cast
    "projectile_speed": 0.0,              # additive % increase to projectile speed
    "attack_radius": 0.0,                 # additive % increase to projectile/AoE size
}

# Effect keys (from skill tree / gear / set bonuses) that map onto Stats.
# Anything not in here (e.g. spell-specific *_damage) is handled separately.
STAT_EFFECT_KEYS = {
    "max_health", "max_mana", "health_regen", "mana_regen",
    "move_speed", "attack_speed", "damage", "armor",
    "crit_chance", "crit_damage", "cooldown_reduction",
    "status_radius", "increased_vulnerable_damage",
    "burn_damage_increase", "freeze_duration_bonus", "freeze_threshold_reduction",
    "shock_chain_bonus", "shock_range_bonus",
    "life_leech", "minion_damage_increase",
    "projectile_count", "projectile_speed", "attack_radius",
}


def effects_to_stats(effects):
    """Filter a raw effects dict down to the keys Stats understands."""
    out = {}
    for key, value in effects.items():
        if key in STAT_EFFECT_KEYS or key.endswith("_increase"):
            out[key] = out.get(key, 0) + value
    return out


class Stats:
    """Holds base stats plus named modifier layers and computes effective values."""

    LAYER_NAMES = ("tree", "gear", "set", "ailment")

    def __init__(self, base=None):
        self.base = dict(base) if base else dict(BASE_STATS)
        self.layers = {name: {} for name in self.LAYER_NAMES}

    def set_layer(self, name, modifiers):
        """Replace an entire layer (e.g. recompute the gear layer on equip)."""
        if name not in self.layers:
            self.layers[name] = {}
        self.layers[name] = dict(modifiers) if modifiers else {}

    def clear_layer(self, name):
        self.layers[name] = {}

    def get(self, key):
        """Return the effective value of a stat: (base + flats) * (1 + increases)."""
        flat = self.base.get(key, 0)
        increase = 0.0
        for layer in self.layers.values():
            flat += layer.get(key, 0)
            increase += layer.get(key + "_increase", 0)
        return flat * (1.0 + increase)

    def snapshot(self):
        """Effective values for every known stat -- handy for UI/debug/save."""
        keys = set(self.base) | STAT_EFFECT_KEYS
        return {k: self.get(k) for k in keys}
