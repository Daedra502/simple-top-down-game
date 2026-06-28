"""PoE2-style passive skill tree (DESIGN.md Phase 4).

The graph is data-driven (data/skill_tree.json, R5). Allocation follows the
PoE2 rule: a node can be allocated only if it is connected by an edge to an
already-allocated node. Deallocation is connectivity-preserving so the allocated
subgraph always stays reachable from the (free, always-allocated) root.

Allocated node bonuses are summed by ``get_active_effects()`` and funnel into the
player's central Stats 'tree' layer (the StatAggregator -- see Player /
Game.recompute_player_stats).
"""
from enum import Enum

from src.core.data_loader import load_json


class NodeType(Enum):
    """Kept for backward compatibility; tree classification now uses ``tier``."""
    PASSIVE = 0
    SPELL = 1
    DAMAGE = 2
    SPEED = 3
    DEFENSE = 4
    SUPPORT = 5


# Visual radius per tier.
_TIER_RADIUS = {"minor": 14, "notable": 19, "keystone": 23}


class SkillNode:
    """A single node in the skill tree, built from a data row."""

    def __init__(self, node_id, name, pos, tier, cost, bonuses, color):
        self.node_id = node_id
        self.name = name
        self.x, self.y = pos
        self.tier = tier
        self.cost = cost
        self.effects = dict(bonuses)
        self.allocated = False

        # Backward-compat: some older code/tests read node.node_type.
        self.node_type = NodeType.SUPPORT if tier == "keystone" else NodeType.PASSIVE

        # Undirected adjacency (PoE2 rule) + directed-out list for drawing
        # each connection exactly once.
        self.neighbors = []
        self.children = []

        self.color = tuple(color)
        self.radius = _TIER_RADIUS.get(tier, 14)
        self.allocated_color = self.color
        self.unallocated_color = tuple(c // 2 for c in self.color)

    def can_allocate(self, allocations):
        """PoE2 rule: allocatable if any neighbor is already allocated."""
        if self.allocated:
            return False
        return any(allocations.get(n, False) for n in self.neighbors)

    def get_description(self):
        desc = f"{self.name} ({self.tier})\n"
        if self.effects:
            desc += "Effects:\n"
            for effect, value in self.effects.items():
                if isinstance(value, float):
                    desc += f"  {effect}: +{value:.1%}\n"
                else:
                    desc += f"  {effect}: +{value}\n"
        return desc


class SkillTree:
    """Graph of passive nodes with path-based allocation."""

    ROOT_ID = "root"

    def __init__(self):
        self.nodes = {}
        self.allocations = {}
        self.root_node = None
        self._load_from_data()

    # --- construction -----------------------------------------------------
    def _load_from_data(self):
        data = load_json("skill_tree.json")

        for node_id, row in data.items():
            node = SkillNode(
                node_id,
                row["name"],
                row["pos"],
                row.get("tier", "minor"),
                row.get("cost", 1),
                row.get("bonuses", {}),
                row.get("color", [150, 150, 150]),
            )
            self.nodes[node_id] = node
            self.allocations[node_id] = False

        # Link edges undirected; keep one directed-out entry for rendering.
        for node_id, row in data.items():
            for other in row.get("edges", []):
                self._link(node_id, other)

        # Root is free and starts allocated.
        self.root_node = self.nodes[self.ROOT_ID]
        self.root_node.allocated = True
        self.allocations[self.ROOT_ID] = True

    def _link(self, a, b):
        if b not in self.nodes or a not in self.nodes:
            return
        na, nb = self.nodes[a], self.nodes[b]
        if b not in na.neighbors:
            na.neighbors.append(b)
        if a not in nb.neighbors:
            nb.neighbors.append(a)
        if b not in na.children:
            na.children.append(b)  # render this edge once, from a

    # --- allocation -------------------------------------------------------
    def allocate_node(self, node_id):
        """Allocate a node if it connects to the allocated subgraph."""
        node = self.nodes.get(node_id)
        if node is None or not node.can_allocate(self.allocations):
            return False
        node.allocated = True
        self.allocations[node_id] = True
        return True

    def deallocate_node(self, node_id):
        """Deallocate a node if doing so keeps the rest connected to root."""
        if node_id == self.ROOT_ID or node_id not in self.nodes:
            return False
        node = self.nodes[node_id]
        if not node.allocated:
            return False

        # Tentatively remove and verify all remaining allocated nodes still
        # reach root through allocated nodes.
        node.allocated = False
        self.allocations[node_id] = False
        if self._all_allocated_connected():
            return True

        # Revert -- removal would orphan part of the tree.
        node.allocated = True
        self.allocations[node_id] = True
        return False

    def _all_allocated_connected(self):
        """True if every allocated node is reachable from root via allocated nodes."""
        allocated = {nid for nid, on in self.allocations.items() if on}
        if not allocated:
            return True
        seen = {self.ROOT_ID}
        stack = [self.ROOT_ID]
        while stack:
            cur = stack.pop()
            for nb in self.nodes[cur].neighbors:
                if nb in allocated and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        return seen == allocated

    def reset_tree(self):
        """Reset every node except the (free) root."""
        for node_id, node in self.nodes.items():
            if node_id != self.ROOT_ID:
                node.allocated = False
                self.allocations[node_id] = False

    # --- aggregation / queries -------------------------------------------
    def get_active_effects(self):
        """Sum the bonuses of all allocated nodes (the StatAggregator input)."""
        effects = {}
        for node_id, on in self.allocations.items():
            if on:
                for effect, value in self.nodes[node_id].effects.items():
                    effects[effect] = effects.get(effect, 0) + value
        return effects

    def get_allocated_count(self):
        """Count allocated nodes, excluding the free root."""
        return sum(1 for nid, on in self.allocations.items() if on and nid != self.ROOT_ID)

    def get_tree_info(self):
        return {
            "nodes": self.nodes,
            "allocations": self.allocations,
            "allocated_count": self.get_allocated_count(),
        }

    def get_active_keystones(self):
        """IDs of allocated keystone nodes."""
        from src.spells.keystones import NODE_TO_KEYSTONE
        return [nid for nid, on in self.allocations.items()
                if on and nid in NODE_TO_KEYSTONE]

    def has_keystone(self, node_id):
        from src.spells.keystones import NODE_TO_KEYSTONE
        if node_id not in NODE_TO_KEYSTONE:
            return False
        return self.allocations.get(node_id, False)
