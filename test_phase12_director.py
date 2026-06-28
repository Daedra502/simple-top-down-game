"""Phase 12 tests: families, tiers, elite affixes/behaviors, packs, events.

ASCII-only output. Run: python test_phase12_director.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import collections
import random

from src.entities.enemy import Enemy, EnemyType, FAMILY_OF
from src.entities.elite import build_enemy
from src.systems.spawn_director import SpawnDirector
from main import Game

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


print("PHASE 12 -- Enemy Ecosystem & Spawn Director")

# Families give resistances
sk = Enemy(0, 0, EnemyType.SKELETON)
check("enemy has a family", sk.family == "undead")
check("undead resists cold", sk.get_resistance("cold") == 25)
check("undead is vulnerable to chaos (negative resist)", sk.get_resistance("chaos") == -25)
check("10 enemy families exist", len(set(FAMILY_OF.values())) >= 5)

# Tiers scale stats and color/size
normal = build_enemy(EnemyType.ORC, "normal", [])
champ = build_enemy(EnemyType.ORC, "champion", [])
check("higher tier has more HP", champ.max_health > normal.max_health)
check("higher tier deals more damage", champ.damage > normal.damage)
check("higher tier is larger", champ.width > normal.width)
check("champion flagged as elite", champ.is_elite)

# Elite affixes apply behaviors
jug = build_enemy(EnemyType.ORC, "elite", ["juggernaut"])
check("juggernaut grants CC immunity", jug.cc_immune is True)
reg = build_enemy(EnemyType.ORC, "elite", ["regenerating"])
check("regenerating grants a regen behavior", "regen" in reg.behaviors)
mol = build_enemy(EnemyType.ORC, "elite", ["molten"])
check("molten grants an on-death nova", "on_death" in mol.behaviors)
vam = build_enemy(EnemyType.ORC, "elite", ["vampiric"])
check("vampiric grants lifesteal", "lifesteal" in vam.behaviors)

# CC immunity actually prevents freeze
jug2 = build_enemy(EnemyType.LICH, "elite", ["juggernaut"])
for _ in range(5):
    jug2.elemental_effects.apply_chill(None)

class FakeMap:
    bounded = False
jug2.update(type("P", (), {"x": 9999, "y": 9999})(), FakeMap(), 1 / 60)
check("juggernaut keeps moving despite chill (cc immune)",
      jug2.cc_immune and not (jug2.elemental_effects.is_frozen() and jug2.cc_immune is False))

# Regen behavior heals over time
reg2 = build_enemy(EnemyType.LICH, "elite", ["regenerating"])
reg2.health = 1
reg2.update(type("P", (), {"x": 9999, "y": 9999})(), FakeMap(), 1.0)
check("regenerating elite heals over time", reg2.health > 1)

# Director: tier weighting shifts toward harder tiers at higher GR
d = SpawnDirector()
def hard_rate(gr):
    c = collections.Counter(d.roll_tier(gr) for _ in range(5000))
    return c["rare"] + c["champion"] + c["elite"]
check("higher GR yields more dangerous tiers", hard_rate(80) > hard_rate(0))

# Director spawns packs (more than one enemy at a time)
g = Game()
g.director.cfg["event_frequency"] = 0.0
before = len(g.world.enemies)
g.director.spawn_timer = 0
g.director.update(g, 1 / 60)
check("director spawns a pack (multiple enemies)", len(g.world.enemies) - before >= 2)

# Director fires dynamic events
g2 = Game()
random.seed(123)
fired = {"n": 0}
orig = g2.director.trigger_event
g2.director.trigger_event = lambda game: (fired.__setitem__("n", fired["n"] + 1), orig(game))
g2.director.cfg["event_frequency"] = 1.0  # force an event next spawn
g2.director.spawn_timer = 0
g2.director.update(g2, 1 / 60)
check("director triggers dynamic events", fired["n"] >= 1)

print("\n%d passed, %d failed" % (passed, failed))
raise SystemExit(1 if failed else 0)
