"""Unified ailment system (DESIGN.md Phases 7-9).

One AilmentManager lives on each enemy (as ``enemy.elemental_effects``) and owns:
  - Vulnerable (Phase 7): +damage taken, purple bar, orb drops.
  - Burn (Phase 8): stacking damage-over-time that ticks through the pipeline.
  - Freeze/Slow (Phase 8): cold slows; enough buildup freezes (stuns).
  - Shock (Phase 8): amplifies damage taken; lightning chains between shocked.

All numbers come from data/ailments.json (R5). Phase-9 scaling reads optional
``*_increase`` / ``*_bonus`` attributes off the damage source (the player).
Backward-compat shims (``apply_effect``, ``get_shock_amplification``,
``is_frozen``) keep the older combat methods and tests working.
"""
from src.core.data_loader import load_json


def _src(source, attr, default=0):
    return getattr(source, attr, default) if source is not None else default


class AilmentManager:
    def __init__(self, owner=None):
        self.owner = owner
        self.cfg = load_json("ailments.json")
        self.active = {}          # id -> state dict with 'remaining'
        self._freeze_buildup = 0
        self._frozen_timer = 0.0

    # --- Vulnerable (Phase 7) --------------------------------------------
    def apply_vulnerable(self, source=None):
        self.active["vulnerable"] = {"remaining": self.cfg["vulnerable"]["duration"]}

    def is_vulnerable(self):
        return "vulnerable" in self.active

    # --- Burn (Phase 8) ---------------------------------------------------
    def apply_burn(self, source=None, bonus_increase=0.0):
        """Apply/refresh burn. ``bonus_increase`` is a per-cast ignite bonus
        (e.g. Fireball's ignite mastery) added on top of the source's global
        burn_damage_increase."""
        c = self.cfg["burn"]
        dps = c["dps"] * (1.0 + _src(source, "burn_damage_increase", 0.0) + bonus_increase)
        # Eternal Flame (ascendancy keystone, Phase 15): burns never expire.
        duration = 1e9 if getattr(source, "eternal_flame", False) else c["duration"]
        existing = self.active.get("burn")
        if existing and c.get("stackable"):
            existing["stacks"] = min(c["max_stacks"], existing["stacks"] + 1)
            existing["remaining"] = duration
            existing["dps"] = dps
        else:
            self.active["burn"] = {"remaining": duration, "stacks": 1,
                                   "dps": dps, "tick_timer": c["tick"]}

    # --- Freeze / Slow (Phase 8) -----------------------------------------
    def apply_chill(self, source=None):
        c = self.cfg["freeze"]
        self.active["slow"] = {"remaining": c["duration"], "slow": c["slow"]}
        self._freeze_buildup += 1
        threshold = max(1, c["freeze_threshold"] - int(_src(source, "freeze_threshold_reduction", 0)))
        if self._freeze_buildup >= threshold:
            self._freeze_buildup = 0
            self._frozen_timer = c["freeze_duration"] + _src(source, "freeze_duration_bonus", 0.0)

    def is_frozen(self):
        return self._frozen_timer > 0

    def move_multiplier(self):
        if self.is_frozen():
            return 0.0
        slow = self.active.get("slow")
        return (1.0 - slow["slow"]) if slow else 1.0

    # --- Shock (Phase 8) --------------------------------------------------
    def apply_shock(self, source=None):
        c = self.cfg["shock"]
        existing = self.active.get("shock")
        # Overcharged (ascendancy keystone, Phase 15): shock stacks uncapped.
        cap = 9999 if getattr(source, "overcharged", False) else c["max_stacks"]
        stacks = min(cap, (existing["stacks"] + 1) if existing else 1)
        self.active["shock"] = {"remaining": c["duration"], "stacks": stacks}

    def is_shocked(self):
        return "shock" in self.active

    def get_shock_amplification(self):
        s = self.active.get("shock")
        if not s:
            return 1.0
        return 1.0 + self.cfg["shock"]["amp_per_stack"] * s["stacks"]

    # --- per-frame update -------------------------------------------------
    def update(self, dt):
        """Advance timers; return burn damage to apply this frame (0 if none)."""
        if self._frozen_timer > 0:
            self._frozen_timer -= dt
            if self._frozen_timer <= 0:
                # Unfreeze: clear lingering slow and reset slow buildup to 0 so
                # the target must be chilled from scratch again (design intent).
                self.active.pop("slow", None)
                self._freeze_buildup = 0

        for key in list(self.active):
            self.active[key]["remaining"] -= dt
            if self.active[key]["remaining"] <= 0:
                del self.active[key]

        burn = self.active.get("burn")
        if burn:
            burn["tick_timer"] -= dt
            if burn["tick_timer"] <= 0:
                burn["tick_timer"] += self.cfg["burn"]["tick"]
                return burn["dps"] * self.cfg["burn"]["tick"] * burn["stacks"]
        return 0.0

    # --- backward-compat shims -------------------------------------------
    def apply_effect(self, name, element=None, duration=1.0, intensity=1.0):
        dispatch = {
            "burn": self.apply_burn, "poison": self.apply_burn,
            "freeze": self.apply_chill, "shock": self.apply_shock,
            "vulnerable": self.apply_vulnerable,
        }
        if name in dispatch:
            dispatch[name]()

    def clear_effects(self):
        self.active.clear()
        self._freeze_buildup = 0
        self._frozen_timer = 0.0

    def get_active_effects(self):
        """Compat: list of {name, intensity} dicts for older UI/tests."""
        return [{"name": key, "intensity": state.get("stacks", 1)}
                for key, state in self.active.items()]
