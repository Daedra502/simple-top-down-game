"""Confirms the Vulnerable status system (Phase 7) and the loot system (Phase 6)
are properly separated: loot -> inventory, orbs -> rift bar, and they never cross.

ASCII-only output. Run: python test_phase7_separation.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from main import Game
from src.entities.enemy import Enemy, EnemyType
from src.core import data_loader
from src.core.damage import roll_damage

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


def spawn_subscribed(g, vulnerable):
    """Add an enemy to the arena, subscribe the death hook, optional Vulnerable."""
    e = Enemy(g.player.x + 300, g.player.y, EnemyType.GOBLIN)
    g.world.enemies.append(e)
    e.on_death.subscribe(g._on_enemy_death)
    if vulnerable:
        e.elemental_effects.apply_vulnerable()
    return e


print("PHASE 7/6 SEPARATION -- Vulnerable status vs loot")

# Force both drop chances to 100% so the test is deterministic.
g = Game()
g.rift.rift_cfg["trash_drop_chance"] = 1.0
data_loader.load_json("ailments.json")["vulnerable"]["orb_drop_chance"] = 1.0

# 1) A NON-vulnerable kill: loot drops, NO orb.
orbs0, loot0 = len(g.progress_orbs), len(g.dropped_items)
e1 = spawn_subscribed(g, vulnerable=False)
e1.take_damage(10 ** 9)
check("non-vulnerable kill drops loot", len(g.dropped_items) == loot0 + 1)
check("non-vulnerable kill drops NO orb", len(g.progress_orbs) == orbs0)

# 2) A VULNERABLE kill: orb drops into the orb list (not the loot list).
orbs1, loot1 = len(g.progress_orbs), len(g.dropped_items)
e2 = spawn_subscribed(g, vulnerable=True)
e2.take_damage(10 ** 9)
check("vulnerable kill drops a progress orb", len(g.progress_orbs) == orbs1 + 1)
check("orb is a rift-progress object, not an Item",
      "value" in g.progress_orbs[-1] and "item" not in g.progress_orbs[-1])
check("orb is type-matched to current rift", g.progress_orbs[-1]["type"] == g.rift.type)

# 3) Loot is collected into the INVENTORY and never touches the rift bar.
g2 = Game()
inv0 = len(g2.item_manager.inventory.items)
prog0 = g2.rift.progress
g2.dropped_items.append({
    "item": __import__("src.items.item", fromlist=["ItemFactory"]).ItemFactory.generate_drop(10, 0),
    "x": g2.player.x, "y": g2.player.y, "time_to_live": 5.0,
})
g2.dt = 1 / 60
g2.update()
check("loot pickup goes to inventory", len(g2.item_manager.inventory.items) == inv0 + 1)
check("loot pickup does NOT push the rift bar", g2.rift.progress == prog0)

# 4) Orb is collected into the RIFT BAR and never enters the inventory.
g3 = Game()
inv_before = len(g3.item_manager.inventory.items)
g3.progress_orbs.append({
    "x": g3.player.x, "y": g3.player.y, "type": g3.rift.type,
    "color": g3.rift.bar_color, "value": 5, "ttl": 5.0,
})
prog_before = g3.rift.progress
g3.dt = 1 / 60
g3._update_progress_orbs()
check("orb pickup pushes the rift bar", g3.rift.progress == prog_before + 5)
check("orb pickup does NOT add to inventory",
      len(g3.item_manager.inventory.items) == inv_before)

# 5) The Vulnerable DEBUFF works with zero gear (pure status system).
g4 = Game()
p = g4.player                       # no equipment at all
target = Enemy(0, 0, EnemyType.LICH)
target.resistances = {}             # isolate Vulnerable from family resistances
p.crit_chance = 0.0                 # isolate the Vulnerable multiplier
base, _ = roll_damage(p, target, 100, "physical")
target.elemental_effects.apply_vulnerable()
vuln, _ = roll_damage(p, target, 100, "physical")
check("Vulnerable adds damage with no loot equipped", abs(vuln - 115) < 1e-6 and base == 100)

# 6) Mismatched orb type is ignored (yellow orb in a greater rift, etc.).
g5 = Game()
g5.progress_orbs.append({
    "x": g5.player.x, "y": g5.player.y, "type": "greater",   # wrong type
    "color": (0, 0, 0), "value": 9, "ttl": 5.0,
})
g5.dt = 1 / 60
pb = g5.rift.progress
g5._update_progress_orbs()
check("type-mismatched orb does not push the bar", g5.rift.progress == pb)

print("\n%d passed, %d failed" % (passed, failed))
raise SystemExit(1 if failed else 0)
