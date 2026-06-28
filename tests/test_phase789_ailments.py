"""Phases 7-9 tests: Vulnerable, elemental ailments, scaling & combos.

ASCII-only output. Run: python test_phase789_ailments.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.entities.enemy import Enemy, EnemyType
from src.entities.player import Player
from src.systems.combat import CombatSystem
from src.spells.elements import ElementType
from src.core.damage import roll_damage, apply_ailment_damage


def check(label, cond):
    assert cond, label


def test_phase789_ailments():
    class FakeMap:
        width = 1200
        height = 800


    # Deterministic source (no random crits) for clean multiplier checks.
    class Caster:
        x = 5000  # far away so enemies wander rather than chase during the test
        y = 5000
        crit_chance = 0.0
        crit_damage = 1.5
        increased_vulnerable_damage = 0.0
        burn_damage_increase = 0.0
        freeze_threshold_reduction = 0.0
        freeze_duration_bonus = 0.0
        shock_chain_bonus = 0
        shock_range_bonus = 0.0


    print("PHASE 7 -- Vulnerable")
    src = Caster()
    e = Enemy(0, 0, EnemyType.LICH)
    e.resistances = {}   # isolate the Vulnerable multiplier from family resistances
    n, _ = roll_damage(src, e, 100, "physical")
    e.elemental_effects.apply_vulnerable()
    check("not vulnerable -> base damage", abs(n - 100) < 1e-6)
    check("is_vulnerable after apply", e.elemental_effects.is_vulnerable())
    v, _ = roll_damage(src, e, 100, "physical")
    check("vulnerable adds +15%", abs(v - 115) < 1e-6)
    src.increased_vulnerable_damage = 0.25
    v2, _ = roll_damage(src, e, 100, "physical")
    check("gear increased-vuln stacks (+40%)", abs(v2 - 140) < 1e-6)
    src.increased_vulnerable_damage = 0.0

    print("PHASE 8 -- Burn / Freeze / Shock")
    # Burn DoT ticks through the pipeline and reduces HP over time
    eb = Enemy(0, 0, EnemyType.LICH)
    hp0 = eb.health
    eb.elemental_effects.apply_burn(src)
    for _ in range(190):  # > 3s of ticks
        eb.update(src, FakeMap(), 1 / 60)
    check("burn damage-over-time reduced HP", eb.health < hp0)
    check("burn expired after duration", "burn" not in eb.elemental_effects.active)

    # Freeze: buildup -> stun (can't move/attack)
    ef = Enemy(0, 0, EnemyType.LICH)
    ef.elemental_effects.apply_chill(src)
    check("single chill slows but not frozen",
          ef.elemental_effects.move_multiplier() < 1.0 and not ef.elemental_effects.is_frozen())
    ef.elemental_effects.apply_chill(src)
    ef.elemental_effects.apply_chill(src)
    check("freeze buildup triggers freeze", ef.elemental_effects.is_frozen())
    check("frozen enemy cannot move", ef.elemental_effects.move_multiplier() == 0.0)
    check("frozen enemy cannot attack", not ef.can_attack(src))

    # Shock: stacks amplify damage taken
    es = Enemy(0, 0, EnemyType.LICH)
    es.elemental_effects.apply_shock(src)
    es.elemental_effects.apply_shock(src)
    check("shock is tracked", es.elemental_effects.is_shocked())
    check("shock amplifies damage taken (2 stacks = 1.16x)",
          abs(es.elemental_effects.get_shock_amplification() - 1.16) < 1e-6)

    print("PHASE 9 -- Scaling & Combos")
    # Shatter: frozen targets take bonus hit damage
    esh = Enemy(0, 0, EnemyType.LICH)
    esh.resistances = {}   # isolate shatter from family resistances
    base, _ = roll_damage(src, esh, 100, "physical")
    for _ in range(3):
        esh.elemental_effects.apply_chill(src)
    shat, _ = roll_damage(src, esh, 100, "physical")
    check("shatter: frozen takes +50% hit damage", abs(shat - 150) < 1e-6)

    # Burn damage scales with source burn_damage_increase (tree/gear)
    e_a = Enemy(0, 0, EnemyType.LICH)
    e_a.elemental_effects.apply_burn(src)
    base_dps = e_a.elemental_effects.active["burn"]["dps"]
    src.burn_damage_increase = 0.5
    e_b = Enemy(0, 0, EnemyType.LICH)
    e_b.elemental_effects.apply_burn(src)
    check("burn dps scales with burn_damage_increase",
          e_b.elemental_effects.active["burn"]["dps"] > base_dps)
    src.burn_damage_increase = 0.0

    # Burning + Vulnerable multiplies DoT (combo)
    ev = Enemy(0, 0, EnemyType.LICH)
    hp_no = ev.health
    apply_ailment_damage(ev, 20, "fire")   # sub-lethal so clamping doesn't hide it
    dealt_plain = hp_no - ev.health
    ev2 = Enemy(0, 0, EnemyType.LICH)
    ev2.elemental_effects.apply_vulnerable()
    hp_yes = ev2.health
    apply_ailment_damage(ev2, 20, "fire")
    dealt_vuln = hp_yes - ev2.health
    check("burning + vulnerable multiplies DoT", dealt_vuln > dealt_plain)

    # Freeze threshold reduction makes freezing faster (Phase 9 scaling)
    src.freeze_threshold_reduction = 2  # threshold 3 -> 1
    ez = Enemy(0, 0, EnemyType.LICH)
    ez.elemental_effects.apply_chill(src)
    check("freeze threshold reduction speeds freezing", ez.elemental_effects.is_frozen())
