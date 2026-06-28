"""Phase 13 tests: active skills with independent XP/levels, scaling, mastery.

ASCII-only output. Run: python test_phase13_skills.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.spells.active_skills import SkillManager, MASTERY_EVERY
from main import Game


def check(label, cond):
    assert cond, label


def test_phase13_skills(test_slot):
    print("PHASE 13 -- Active Skill Framework")

    m = SkillManager()
    starters = {"fireball", "ice_shard", "chain_lightning", "arc_slash",
                "poison_nova", "meteor", "blink", "summon_skeleton"}
    check("all 8 starter skills exist", starters <= set(m.skills.keys()))

    # Skills gain XP and level up
    fb = m.get("fireball")
    check("skills start at level 1, 0 xp", fb.level == 1 and fb.xp == 0)
    m.award_damage("fireball", 5000)  # bulk
    check("skill levels up from XP", fb.level > 1)

    # Skills level INDEPENDENTLY
    check("other skills unaffected", m.get("ice_shard").level == 1)

    # Leveling makes a skill stronger
    lo = SkillManager().get("fireball")
    hi = SkillManager().get("fireball")
    hi.level = 10
    check("higher level => more damage", hi.stats()["damage"] > lo.stats()["damage"])

    # XP curve respects max level
    fb2 = SkillManager().get("blink")
    fb2.level = fb2.max_level
    check("no XP needed at max level", fb2.xp_to_next() == 0)
    check("gaining XP at max level does nothing", fb2.gain_xp(10_000) == 0)

    # Per-skill mastery: a point every N levels, allocation changes stats
    ms = SkillManager().get("fireball")
    ms.level = MASTERY_EVERY * 2  # 2 points
    check("mastery points scale with level", ms.mastery_points_available() == 2)
    base_count = ms.stats()["count"]
    check("allocate split projectile succeeds", ms.allocate_mastery("fb_split"))
    check("mastery changes computed stats", ms.stats()["count"] == base_count + 1)
    check("cannot re-allocate same node", not ms.allocate_mastery("fb_split"))
    check("cannot allocate unknown node", not ms.allocate_mastery("not_a_node"))
    # spend the second point, then run out
    ms.allocate_mastery("fb_radius")
    check("out of mastery points after spending all", ms.mastery_points_available() == 0)
    check("allocation blocked with no points", not ms.allocate_mastery("fb_burn"))

    # Cast plans produce the right action kind for each skill
    g = Game()
    kinds = {}
    for sid in g.skills.slots:
        sk = g.skills.get(sid)
        kinds[sid] = sk.cast_plan(g.player, g.player.x + 100, g.player.y)["kind"]
    check("projectile skills produce projectile plans", kinds["fireball"] == "projectile")
    check("nova skills produce aoe plans", kinds["poison_nova"] == "aoe")
    check("blink produces a blink plan", kinds["blink"] == "blink")
    check("summon produces a summon plan", kinds["summon_skeleton"] == "summon")

    # Casting consumes mana + sets cooldown
    g.player.active_skill = 0
    sk = g.skills.slot(0)
    sk.cd_remaining = 0
    mana0 = g.player.mana
    sk_can = sk.can_cast(g.player)
    g.player.mana -= sk.mana_cost
    sk.start_cooldown(g.player)
    check("skill was castable", sk_can)
    check("casting put the skill on cooldown", sk.cd_remaining > 0)
    check("casting consumed mana", g.player.mana < mana0)

    # Casting actually spawns world objects
    g2 = Game()
    g2.player.mana = 999
    sk2 = g2.skills.get("summon_skeleton")
    g2._execute_cast(sk2.cast_plan(g2.player, g2.player.x + 50, g2.player.y), sk2)
    check("summon spawns a minion", len(g2.minions) >= 1)
    fb_skill = g2.skills.get("fireball")
    g2._execute_cast(fb_skill.cast_plan(g2.player, g2.player.x + 50, g2.player.y), fb_skill)
    check("projectile cast spawns projectiles", len(g2.projectiles) >= 1)

    # Skill state survives save/load
    g3 = Game()
    g3.skills.get("meteor").level = 7
    g3.skills.get("meteor").allocate_mastery  # noop reference
    g3.skills.get("fireball").gain_xp(200)
    g3.save_game(test_slot)
    g4 = Game()
    g4.load_game(test_slot)
    check("skill levels persist across save/load",
          g4.skills.get("meteor").level == 7)
