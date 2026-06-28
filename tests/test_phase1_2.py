"""Phase 1 + 2 tests: Entity/on_death, data-driven enemies, Stats, damage pipeline.

ASCII-only output so it runs on a default Windows (cp1252) console.
Run: python test_phase1_2.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.core.stats import Stats
from src.core.damage import roll_damage
from src.entities.entity import Entity, Event
from src.entities.enemy import Enemy, EnemyType
from src.entities.player import Player


def check(label, cond):
    assert cond, label


def test_phase1_2():
    print("PHASE 1 -- Entity, on_death hook, data-driven enemies")

    # Event/Entity death hook fires exactly once
    fired = []
    e = Entity(0, 0, 30)
    e.on_death.subscribe(lambda ent: fired.append(1))
    check("take_damage returns not-dead above 0 hp", e.take_damage(10) is False)
    check("survivor health reduced", e.health == 20)
    check("lethal hit returns dead", e.take_damage(999) is True)
    check("on_death fired once", fired == [1])
    e.take_damage(5)  # already dead
    check("on_death does not refire after death", fired == [1])

    # Data-driven enemy stats come from data/enemies.json
    g = Enemy(0, 0, EnemyType.GOBLIN)
    d = Enemy(0, 0, EnemyType.DRAGON)
    check("goblin loaded from data (hp 20)", g.max_health == 20 and g.name == "Goblin")
    check("dragon loaded from data (hp 150)", d.max_health == 150 and d.progress_value == 5)
    check("enemy inherits Entity death hook", hasattr(g, "on_death") and isinstance(g.on_death, Event))


    print("PHASE 2 -- Stats aggregator, regen, attack speed, damage pipeline")

    # Stats layering: base + flat layer, and *_increase multiplier
    s = Stats()
    check("base max_health is 100", s.get("max_health") == 100)
    s.set_layer("gear", {"max_health": 50})
    check("flat gear layer adds (150)", s.get("max_health") == 150)
    s.set_layer("tree", {"max_health_increase": 0.10})
    check("increase layer multiplies (165)", abs(s.get("max_health") - 165) < 1e-6)
    s.set_layer("gear", {})
    check("clearing a layer reverts (110)", abs(s.get("max_health") - 110) < 1e-6)

    # Player writes stats through to cached attributes
    p = Player(100, 100)
    check("player max_health from stats (100)", p.max_health == 100)
    p.stats.set_layer("gear", {"attack_speed": 0.25, "max_mana": 40})
    p.recompute()
    check("attack speed funnels through stats (1.25)", abs(p.attack_speed - 1.25) < 1e-6)
    check("max_mana funnels through stats (140)", p.max_mana == 140)

    # dt-based regen (per second)
    p.mana = 0.0
    for _ in range(60):
        p.update(None, 1.0 / 60.0)  # one simulated second
    check("mana regenerates ~regen/sec", abs(p.mana - p.mana_regen) < 0.5)

    # Damage pipeline: crit multiplies, min damage floor holds
    class Dummy:
        crit_chance = 1.0   # always crit
        crit_damage = 2.0
    dmg, is_crit = roll_damage(Dummy(), object(), 50, "physical")
    check("guaranteed crit doubles damage (100)", is_crit and abs(dmg - 100) < 1e-6)
    Dummy.crit_chance = 0.0
    dmg, is_crit = roll_damage(Dummy(), object(), 7, "physical")
    check("no-crit passes base through (7)", (not is_crit) and abs(dmg - 7) < 1e-6)
