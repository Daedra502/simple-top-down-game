"""Quest system (Phase 18).

A single active quest at a time, drawn at random from a pool of 50 objectives in
data/quests.json. Objectives are simple, event-driven counters ("slay 10
monsters", "open 3 chests", "earn 200 copper"): gameplay hooks call
``notify(event_type, amount)`` and, when the counter reaches the target, the
quest pays out XP and copper and a fresh random quest is rolled. Early quests are
small so a new character makes immediate, visible progress.

Event types (must match the quests' ``type`` field):
    kill, kill_elite, kill_boss, earn_gold, open_chest, level_up, travel,
    collect_loot
"""
import random

from src.core.data_loader import load_json


class QuestManager:
    def __init__(self, reward_cb=None):
        # reward_cb(xp, copper) is called when a quest completes (wired to the
        # player by the Game). Kept optional so the manager is unit-testable.
        self.pool = load_json("quests.json")
        self.reward_cb = reward_cb
        self.current_id = None
        self.progress = 0
        self.completed_count = 0
        self.last_completed_desc = None
        self._pick_new()

    # --- selection --------------------------------------------------------
    def _pick_new(self):
        """Choose a random quest (avoiding an immediate repeat when possible)."""
        ids = list(self.pool.keys())
        if not ids:
            self.current_id = None
            return
        if len(ids) > 1 and self.current_id in ids:
            ids.remove(self.current_id)
        self.current_id = random.choice(ids)
        self.progress = 0

    @property
    def current(self):
        return self.pool.get(self.current_id) if self.current_id else None

    def target(self):
        q = self.current
        return q["target"] if q else 0

    # --- progress ---------------------------------------------------------
    def notify(self, event_type, amount=1):
        """Advance the active quest if its objective matches; complete + reroll
        when the target is reached. Returns True on completion."""
        q = self.current
        if not q or amount <= 0 or q["type"] != event_type:
            return False
        self.progress += amount
        if self.progress >= q["target"]:
            return self._complete()
        return False

    def _complete(self):
        q = self.current
        if self.reward_cb and q:
            self.reward_cb(q.get("reward_xp", 0), q.get("reward_copper", 0))
        self.completed_count += 1
        self.last_completed_desc = q["desc"] if q else None
        self._pick_new()
        return True

    # --- presentation -----------------------------------------------------
    def status_line(self):
        q = self.current
        if not q:
            return "No active quest"
        return f"{q['desc']}  ({min(self.progress, q['target'])}/{q['target']})"

    def reward_line(self):
        q = self.current
        if not q:
            return ""
        return f"Reward: {q.get('reward_xp', 0)} XP, {q.get('reward_copper', 0)}c"

    # --- save -------------------------------------------------------------
    def to_dict(self):
        return {
            "current_id": self.current_id,
            "progress": self.progress,
            "completed_count": self.completed_count,
        }

    def load_dict(self, d):
        if not d:
            return
        cid = d.get("current_id")
        if cid in self.pool:
            self.current_id = cid
            self.progress = d.get("progress", 0)
        self.completed_count = d.get("completed_count", 0)
