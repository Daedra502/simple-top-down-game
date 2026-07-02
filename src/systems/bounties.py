"""Bounty board (town activity).

The Embervale bounty board offers three contracts rolled from
data/bounties.json; the player accepts one at a time and completes it out in
the rift ("cull 18 beasts", "slay 4 empowered foes", "crack open 3 chests").
Progress is event-driven like quests: gameplay hooks call ``notify(...)`` and
completion returns the reward bundle for the Game to pay out (gold, loot
drops, rift keystones). Completing or abandoning a contract re-rolls the
offers, giving the board a fresh set each visit.

Kept UI-free and Game-free so it is unit-testable and easy to persist
(``to_dict``/``from_dict`` round-trip through the save file).
"""
import random

from src.core.data_loader import load_json


class BountyManager:
    OFFER_COUNT = 3

    def __init__(self):
        self.pool = load_json("bounties.json")
        self.offers = []          # rolled contract dicts shown at the board
        self.active = None        # accepted contract dict (or None)
        self.progress = 0
        self.completed_count = 0
        self.roll_offers()

    # --- rolling / accepting ------------------------------------------------
    def _roll_one(self, bounty_id, gr_level=0):
        row = self.pool[bounty_id]
        lo, hi = row["target"]
        # Deeper GR pushes targets (and gold) toward the high end and beyond.
        depth = 1.0 + min(1.0, gr_level / 50.0)
        target = int(round(random.randint(lo, hi) * depth))
        return {
            "id": bounty_id,
            "desc": row["desc"],
            "type": row["type"],
            "family": row.get("family"),
            "target": max(1, target),
            "gold": int(round(row["gold"] * depth)),
            "loot": row.get("loot", 1),
            "keystones": row.get("keystones", 0),
        }

    def roll_offers(self, gr_level=0):
        ids = random.sample(list(self.pool.keys()),
                            min(self.OFFER_COUNT, len(self.pool)))
        self.offers = [self._roll_one(bid, gr_level) for bid in ids]

    def accept(self, index, gr_level=0):
        """Accept an offered contract by index; replaces any active one."""
        if not (0 <= index < len(self.offers)):
            return None
        self.active = self.offers[index]
        self.progress = 0
        self.roll_offers(gr_level)
        return self.active

    def abandon(self, gr_level=0):
        self.active = None
        self.progress = 0
        self.roll_offers(gr_level)

    # --- progress -------------------------------------------------------------
    def notify(self, event_type, family=None, amount=1):
        """Advance the active contract; returns the reward dict on completion.

        ``kill_family`` contracts additionally require the killed enemy's
        family to match; other types match on event alone.
        """
        b = self.active
        if not b or amount <= 0 or b["type"] != event_type:
            return None
        if b["type"] == "kill_family" and b.get("family") != family:
            return None
        self.progress += amount
        if self.progress < b["target"]:
            return None
        self.active = None
        self.progress = 0
        self.completed_count += 1
        return b

    def describe_active(self):
        """One-line HUD text for the active contract, or None."""
        b = self.active
        if not b:
            return None
        return f"Bounty: {b['desc']}  ({self.progress}/{b['target']})"

    # --- persistence ------------------------------------------------------------
    def to_dict(self):
        return {
            "active": self.active,
            "progress": self.progress,
            "completed_count": self.completed_count,
            "offers": self.offers,
        }

    def from_dict(self, data):
        if not data:
            return
        self.active = data.get("active")
        self.progress = data.get("progress", 0)
        self.completed_count = data.get("completed_count", 0)
        offers = data.get("offers")
        if offers:
            self.offers = offers
