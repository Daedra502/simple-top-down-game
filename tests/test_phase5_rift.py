"""Phase 5 tests: rift/GR state machine, scaling, keystones, boss pool, full loop.

ASCII-only output. Run: python test_phase5_rift.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.systems.rift import RiftManager, NORMAL, GREATER, YELLOW, PURPLE
from src.entities.boss import Boss, boss_keys
from main import Game


def check(label, cond):
    assert cond, label


def test_phase5_rift():
    print("PHASE 5 -- Rift & Greater Rift")

    # Boss pool of 10
    keys = boss_keys()
    check("boss pool has 10 bosses", len(keys) == 10)
    b = Boss(0, 0, keys[0])
    check("boss is flagged is_boss", b.is_boss is True)
    check("boss has abilities + theme", len(b.abilities) > 0 and b.theme)

    # Rift state machine: normal is GR level 0 (scaling unifies)
    r = RiftManager()
    check("starts as normal rift", r.type == NORMAL and r.gr_level == 0)
    check("normal bar is yellow", r.bar_color == YELLOW)
    check("normal scaling is identity", r.hp_mult() == 1.0 and r.reward_mult() == 1.0)

    # Progress + boss gating
    r.add_progress(r.threshold - 1)
    check("not ready before threshold", not r.ready_for_boss())
    r.add_progress(5)
    check("ready at/after threshold", r.ready_for_boss())
    check("progress clamps to threshold", r.progress == r.threshold)
    r.begin_boss()
    check("boss active stops more progress", (r.add_progress(10) or r.progress == r.threshold))

    # Greater rift scaling grows with level
    r.open_greater(50)
    check("greater rift type + level", r.type == GREATER and r.gr_level == 50)
    check("greater bar is purple", r.bar_color == PURPLE)
    check("hp scales up at GR50", r.hp_mult() > 10)
    check("reward scales up at GR50", r.reward_mult() > 1.0)
    check("GR level clamps to 1..100", RiftManager().__class__ and r.gr_cfg["max_level"] == 100)
    r.open_greater(99999)
    check("over-cap clamps to max", r.gr_level == 100)
    r.open_greater(-5)
    check("under-min clamps to 1", r.gr_level == 1)

    # Boss reward scaling
    b50 = Boss(0, 0, keys[0], hp_mult=29.0, dmg_mult=10.0, reward_mult=13.5)
    b1 = Boss(0, 0, keys[0])
    check("scaled boss has more hp", b50.max_health > b1.max_health * 10)
    check("scaled boss gives more xp", b50.experience_reward > b1.experience_reward * 10)

    # Keystone inventory
    g = Game()
    check("starts with 0 keystones", g.item_manager.keystone_count() == 0)
    g.item_manager.add_keystone(2)
    check("add keystones stacks", g.item_manager.keystone_count() == 2)
    check("consume returns True with stock", g.item_manager.consume_keystone() is True)
    check("count decremented", g.item_manager.keystone_count() == 1)
    g.item_manager.consume_keystone()
    check("consume on empty returns False", g.item_manager.consume_keystone() is False)

    # Full loop: normal boss -> keystone; GR boss -> highest_gr
    g2 = Game(); g2.dt = 1 / 60
    cm = g2.world   # the streaming world is now the playfield (Phase 11)


    g2.director.cfg["event_frequency"] = 0.0   # only packs, no events, for determinism


    def fill_and_kill_boss(target_gr):
        guard = 0
        while not g2.rift.boss_active and guard < 6000:
            g2.director.update(g2, 1 / 60)
            g2.director.spawn_timer = 0
            for e in list(cm.enemies):
                if not getattr(e, "is_boss", False):
                    if e not in g2.enemy_health_bars:
                        from src.ui.health_bars import EnemyHealthBar
                        g2.enemy_health_bars[e] = EnemyHealthBar(e)
                        e.on_death.subscribe(g2._on_enemy_death)
                    e.take_damage(10 ** 9)
            cm.enemies = [e for e in cm.enemies if e.health > 0]
            guard += 1
        boss = [e for e in cm.enemies if getattr(e, "is_boss", False)][0]
        from src.ui.health_bars import EnemyHealthBar
        g2.enemy_health_bars[boss] = EnemyHealthBar(boss)
        boss.on_death.subscribe(g2._on_enemy_death)
        boss.take_damage(10 ** 9)


    fill_and_kill_boss(0)
    check("normal rift boss grants a keystone", g2.item_manager.keystone_count() == 1)
    check("rift resets to normal after boss", g2.rift.type == NORMAL)

    g2.gr_selected_level = 10
    g2._try_open_greater_rift()
    check("GR opened by consuming keystone", g2.rift.type == GREATER and g2.item_manager.keystone_count() == 0)
    fill_and_kill_boss(10)
    check("clearing GR records highest_gr", g2.player.highest_gr == 10)
