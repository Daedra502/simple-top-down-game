"""Atlas system (DESIGN.md Phase 15).

A separate endgame passive tree, allocated with atlas points earned by clearing
Greater Rifts. Atlas nodes don't buff the character -- they reshape the generated
world: elite density, loot quality, event rate, boss frequency, and biome weights
(read by the SpawnDirector, the loot roller, and the WorldManager).
"""
from src.core.data_loader import load_json

ROOT_ID = "atlas_start"


class AtlasManager:
    def __init__(self):
        self.nodes = load_json("atlas.json")
        self.allocated = {ROOT_ID}    # root is free + always allocated
        self.points = 0

    def add_points(self, n=1):
        self.points += n

    def _node(self, node_id):
        return self.nodes.get(node_id)

    def can_allocate(self, node_id):
        node = self._node(node_id)
        if node is None or node_id in self.allocated or self.points <= 0:
            return False
        edges = node.get("edges", [])
        return (not edges) or any(e in self.allocated for e in edges)

    def allocate(self, node_id):
        if not self.can_allocate(node_id):
            return False
        self.allocated.add(node_id)
        self.points -= self._node(node_id).get("cost", 1)
        return True

    def get_effects(self):
        """Aggregate world-shaping effects from all allocated atlas nodes."""
        eff = {"elite_density": 0.0, "loot_quality": 0.0, "event_rate": 0.0,
               "boss_frequency": 0.0, "biome_weight": {}}
        for node_id in self.allocated:
            node = self._node(node_id)
            if not node:
                continue
            for k, v in node.get("effect", {}).items():
                if k == "biome_weight":
                    for biome, w in v.items():
                        eff["biome_weight"][biome] = eff["biome_weight"].get(biome, 1.0) * w
                else:
                    eff[k] = eff.get(k, 0.0) + v
        return eff

    def to_dict(self):
        return {"allocated": sorted(self.allocated), "points": self.points}

    def load_dict(self, d):
        self.allocated = set(d.get("allocated", [ROOT_ID])) | {ROOT_ID}
        self.points = d.get("points", 0)
