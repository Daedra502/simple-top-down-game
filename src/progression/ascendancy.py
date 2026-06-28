"""Ascendancy system (DESIGN.md Phase 15).

At level 20 a character permanently chooses one of four specializations. Points
are earned at levels 20/40/60/80 and spent on a small per-class node tree whose
bonuses feed a dedicated Stats layer and whose keystones flip build-defining
flags (Glass Cannon, Eternal Flame, Overcharged).
"""
from src.core.data_loader import load_json
from src.core.stats import effects_to_stats

UNLOCK_LEVEL = 20
MILESTONES = (20, 40, 60, 80)
POINTS_PER_MILESTONE = 2   # so keystone paths are reachable within the level cap

# Build-defining keystone effects.
ASCENDANCY_KEYSTONES = {
    "glass_cannon":  {"stats": {"damage_increase": 1.0, "max_health_increase": -0.5},
                      "flags": []},
    "eternal_flame": {"stats": {}, "flags": ["eternal_flame"]},
    "overcharged":   {"stats": {}, "flags": ["overcharged"]},
}


class AscendancyManager:
    def __init__(self):
        self.classes = load_json("ascendancy.json")
        self.chosen = None        # class id, or None until level 20
        self.allocated = []       # node ids

    # --- selection / allocation ------------------------------------------
    def available_classes(self):
        return list(self.classes.keys())

    def choose(self, class_id, level):
        if self.chosen is not None or level < UNLOCK_LEVEL:
            return False
        if class_id not in self.classes:
            return False
        self.chosen = class_id
        return True

    def points_available(self, level):
        earned = POINTS_PER_MILESTONE * sum(1 for m in MILESTONES if level >= m)
        return earned - len(self.allocated)

    def _nodes(self):
        if self.chosen is None:
            return []
        return self.classes[self.chosen]["nodes"]

    def _node(self, node_id):
        for n in self._nodes():
            if n["id"] == node_id:
                return n
        return None

    def can_allocate(self, node_id, level):
        node = self._node(node_id)
        if node is None or node_id in self.allocated:
            return False
        if self.points_available(level) <= 0:
            return False
        edges = node.get("edges", [])
        return (not edges) or any(e in self.allocated for e in edges)

    def allocate(self, node_id, level):
        if not self.can_allocate(node_id, level):
            return False
        self.allocated.append(node_id)
        return True

    # --- effects ----------------------------------------------------------
    def get_stat_layer(self):
        """Aggregate node bonuses + keystone stats into a Stats-layer dict."""
        effects = {}
        for node_id in self.allocated:
            node = self._node(node_id)
            if not node:
                continue
            for k, v in node.get("bonuses", {}).items():
                effects[k] = effects.get(k, 0) + v
            ks = node.get("keystone")
            if ks and ks in ASCENDANCY_KEYSTONES:
                for k, v in ASCENDANCY_KEYSTONES[ks]["stats"].items():
                    effects[k] = effects.get(k, 0) + v
        return effects_to_stats(effects)

    def get_flags(self):
        flags = []
        for node_id in self.allocated:
            node = self._node(node_id)
            ks = node.get("keystone") if node else None
            if ks and ks in ASCENDANCY_KEYSTONES:
                flags.extend(ASCENDANCY_KEYSTONES[ks]["flags"])
        return flags

    # --- save -------------------------------------------------------------
    def to_dict(self):
        return {"chosen": self.chosen, "allocated": list(self.allocated)}

    def load_dict(self, d):
        self.chosen = d.get("chosen")
        self.allocated = list(d.get("allocated", []))
