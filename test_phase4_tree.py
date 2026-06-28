"""Phase 4 tests: data-driven PoE2 passive tree, neighbor-rule allocation,
connectivity-preserving deallocation, and stat aggregation.

ASCII-only output. Run: python test_phase4_tree.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.spells.skill_tree import SkillTree
from src.entities.player import Player

passed = 0
failed = 0


def check(label, cond):
    global passed, failed
    if cond:
        passed += 1
        print("  [PASS] " + label)
    else:
        failed += 1
        print("  [FAIL] " + label)


print("PHASE 4 -- Passive Skill Tree")

t = SkillTree()

# Loaded from data, root pre-allocated and free
check("tree loads from data (>=36 nodes)", len(t.nodes) >= 36)
check("root is pre-allocated", t.allocations["root"] is True)
check("root excluded from allocated count", t.get_allocated_count() == 0)
check("required nodes exist (move/atk/regen)",
      all(n in t.nodes for n in ("move_notable", "atk_notable", "hpregen_notable")))

# PoE2 rule: cannot allocate a node not adjacent to the allocated set
check("non-adjacent node not allocatable", not t.nodes["move_2"].can_allocate(t.allocations))
check("allocate detached node fails", t.allocate_node("move_2") is False)

# Allocate along a connected path
check("allocate speed_1 (adjacent to root)", t.allocate_node("speed_1") is True)
check("allocate move_1 (adjacent to speed_1)", t.allocate_node("move_1") is True)
check("allocate move_2 now succeeds", t.allocate_node("move_2") is True)
check("count reflects 3 allocations", t.get_allocated_count() == 3)

# Connectivity-preserving deallocation
check("cannot deallocate a cut vertex (speed_1)", t.deallocate_node("speed_1") is False)
check("can deallocate a leaf (move_2)", t.deallocate_node("move_2") is True)
check("cannot deallocate root", t.deallocate_node("root") is False)

# Aggregation: allocated bonuses change the player's effective stats
p = Player(0, 0)
base_ms, base_dmg = p.stats.get("move_speed"), p.stats.get("damage")

tree = SkillTree()
for nid in ("speed_1", "atk_1", "atk_2", "atk_notable"):
    tree.allocate_node(nid)
p.apply_skill_tree_bonuses(tree)
check("attack damage increased via tree", p.damage > base_dmg)
check("attack speed increased via tree (speed_1 + atk_notable)", p.attack_speed > 1.0)

tree2 = SkillTree()
for nid in ("speed_1", "move_1", "move_2", "move_notable"):
    tree2.allocate_node(nid)
p2 = Player(0, 0)
p2.apply_skill_tree_bonuses(tree2)
check("move speed increased via tree", p2.move_speed > base_ms)

# get_active_effects sums allocated node bonuses (StatAggregator input)
eff = tree2.get_active_effects()
check("active effects aggregate move_speed_increase",
      eff.get("move_speed_increase", 0) > 0)

print("\n%d passed, %d failed" % (passed, failed))
raise SystemExit(1 if failed else 0)
