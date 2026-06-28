"""Rift & Greater Rift system (DESIGN.md Phase 5) -- the endless engine.

A normal rift is modeled as Greater-Rift level 0, so a single set of scaling
formulas covers both: ``mult = base ** gr_level`` is 1.0 when gr_level == 0. The
rift *type* still distinguishes the progress-bar color and the boss reward
(normal rifts drop a Rift Keystone; greater rifts pay scaled XP/money/loot).

All tunable numbers live in data/tuning.json (R5).
"""
from src.core.data_loader import load_json

NORMAL = "normal"
GREATER = "greater"

YELLOW = (235, 215, 40)   # normal rift bar
PURPLE = (170, 70, 220)   # greater rift bar


class RiftManager:
    """Owns rift progression state and the GR scaling formulas."""

    def __init__(self):
        cfg = load_json("tuning.json")
        self.rift_cfg = cfg["rift"]
        self.gr_cfg = cfg["gr"]
        self.start_normal()

    # --- lifecycle --------------------------------------------------------
    def start_normal(self):
        """Begin (or restart into) a normal rift."""
        self.type = NORMAL
        self.gr_level = 0
        self.progress = 0
        self.threshold = self.rift_cfg["normal_threshold"]
        self.boss_active = False
        self.spawning_enabled = True
        self.spawn_timer = 0.0
        self.chunks_traveled = 0

    def open_greater(self, level):
        """Open a Greater Rift at the chosen level (1..max)."""
        level = max(1, min(self.gr_cfg["max_level"], int(level)))
        self.type = GREATER
        self.gr_level = level
        self.progress = 0
        self.threshold = (self.rift_cfg["normal_threshold"]
                          + self.gr_cfg["threshold_per_level"] * level)
        self.boss_active = False
        self.spawning_enabled = True
        self.spawn_timer = 0.0
        self.chunks_traveled = 0

    def notify_chunk_travel(self):
        """Advance the rift as the player explores a new chunk (linear journey).

        Travel is the primary driver toward the boss; kills/orbs still add a bit
        on top via add_progress. Returns the new chunks_traveled total.
        """
        self.chunks_traveled += 1
        self.add_progress(self.rift_cfg.get("chunk_progress", 2.0))
        return self.chunks_traveled

    # --- progression ------------------------------------------------------
    def update(self, dt):
        if self.spawn_timer > 0:
            self.spawn_timer -= dt

    def add_progress(self, value):
        """Add rift progress from a kill (ignored once the boss is out)."""
        if not self.boss_active:
            self.progress = min(self.threshold, self.progress + value)

    def ready_for_boss(self):
        return (not self.boss_active) and self.progress >= self.threshold

    def begin_boss(self):
        """Lock progress and stop trash spawns; the boss is now active."""
        self.boss_active = True
        self.spawning_enabled = False

    # --- scaling (functions of gr_level; 1.0 / base at level 0) -----------
    def hp_mult(self):
        return self.gr_cfg["hp_base"] ** self.gr_level

    def dmg_mult(self):
        return self.gr_cfg["dmg_base"] ** self.gr_level

    def reward_mult(self):
        return 1.0 + self.gr_cfg["reward_k"] * self.gr_level

    def density(self):
        base = self.rift_cfg["max_alive"]
        return int(base * (1.0 + self.gr_cfg["density_per_level"] * self.gr_level))

    # --- presentation -----------------------------------------------------
    @property
    def bar_color(self):
        return YELLOW if self.type == NORMAL else PURPLE

    @property
    def label(self):
        if self.type == NORMAL:
            return "Rift"
        return f"Greater Rift  Lv {self.gr_level}"

    @property
    def progress_fraction(self):
        return self.progress / self.threshold if self.threshold else 0.0
