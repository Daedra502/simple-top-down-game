"""Phase 10 tests: save/load round-trips a character identically.

ASCII-only output. Run: python test_phase10_save.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from main import Game
from src.items.item import ItemFactory, ItemRarity, ItemSlot
from src.core import save as save_system


def check(label, cond):
    assert cond, label


def test_phase10_save(test_slot):
    def snapshot_state(g):
        p = g.player
        return dict(
            level=p.level, sp=p.skill_points, xp=round(p.experience, 3),
            xp_to_level=p.xp_to_level,
            wallet=(p.copper, p.silver, p.gold, p.diamond),
            highest_gr=p.highest_gr,
            keystones=g.item_manager.keystone_count(),
            inv=len(g.item_manager.inventory.items),
            equipped=len(g.item_manager.equipment.get_all_equipped_items()),
            nodes=sorted(n for n, on in g.skill_tree.allocations.items() if on),
            resistances=dict(p.resistances),
            stats=p.stats.snapshot(),
        )


    print("PHASE 10 -- Save / Load")

    # Build a non-trivial character
    g = Game()
    p = g.player
    p.add_experience(50000)
    for nid in ["speed_1", "atk_1", "atk_2", "atk_notable", "move_1", "fire_1"]:
        g.skill_tree.allocate_node(nid)
    p.add_money(copper=7, silver=3, gold=4, diamond=2)
    g.item_manager.add_keystone(3)
    for slot in (ItemSlot.CHEST, ItemSlot.RING_1, ItemSlot.HEAD):
        g.item_manager.equipment.equip_item(ItemFactory.roll_item(slot, 60, ItemRarity.UNIQUE))
    g.player.highest_gr = 37
    g.recompute_player_stats()

    before = snapshot_state(g)
    saved_path = save_system.save_to_slot(g, test_slot)
    check("save file created", save_system.has_save(test_slot))

    # Load into a brand-new game
    g2 = Game()
    loaded = g2.load_game(test_slot)
    check("load returns success", loaded)
    after = snapshot_state(g2)

    check("level / xp / skill points identical",
          (before["level"], before["xp"], before["sp"], before["xp_to_level"]) ==
          (after["level"], after["xp"], after["sp"], after["xp_to_level"]))
    check("wallet identical", before["wallet"] == after["wallet"])
    check("highest GR identical", before["highest_gr"] == after["highest_gr"])
    check("keystone count identical", before["keystones"] == after["keystones"])
    check("inventory size identical", before["inv"] == after["inv"])
    check("equipped count identical", before["equipped"] == after["equipped"])
    check("allocated nodes identical", before["nodes"] == after["nodes"])
    check("resistances identical", before["resistances"] == after["resistances"])
    check("EFFECTIVE STATS identical (aggregation rebuilt)", before["stats"] == after["stats"])

    # Affix data survives the round-trip
    ring_before = next(it for it in g.item_manager.equipment.get_all_equipped_items()
                       if it.slot in (ItemSlot.RING_1, ItemSlot.RING_2))
    ring_after = next(it for it in g2.item_manager.equipment.get_all_equipped_items()
                      if it.slot in (ItemSlot.RING_1, ItemSlot.RING_2))
    check("affixes survive round-trip",
          [(a["stat"], a["value"]) for a in ring_before.affixes] ==
          [(a["stat"], a["value"]) for a in ring_after.affixes])

    # Dual-wield weapons + dual rings + active skill restore into the EXACT slots
    gd = Game()
    weps = [ItemFactory.create_weapon(n, ItemRarity.RARE, 1) for n in ("Sword", "Axe")]
    rings = [ItemFactory.create_accessory("ring", ItemRarity.RARE, 1) for _ in range(2)]
    for it in weps + rings:
        gd.item_manager.inventory.add_item(it)
        gd._equip_from_inventory(it)
    gd.player.active_skill = 6
    gd.save_game(test_slot)
    gl = Game()
    gl.load_game(test_slot)
    eql = gl.item_manager.equipment.equipment
    check("off-hand weapon survives save/load",
          eql[ItemSlot.WEAPON_1H] is not None and eql[ItemSlot.WEAPON_1H_OFF] is not None)
    check("both ring slots survive save/load",
          eql[ItemSlot.RING_1] is not None and eql[ItemSlot.RING_2] is not None)
    check("selected active skill restored", gl.player.active_skill == 6)

    # Slot metadata exposes fields the UI needs to distinguish saves
    meta = save_system.peek_slot(test_slot)
    check("peek_slot exposes class/wealth/quests",
          meta is not None and {"class_name", "wealth", "quests_done"} <= set(meta))

    # Corrupt save files are reported, not silently treated as empty
    with open(save_system.slot_path(test_slot), "w", encoding="utf-8") as f:
        f.write("{ broken json")
    corrupt = save_system.peek_slot(test_slot)
    check("corrupt save reported as corrupt", corrupt is not None and corrupt.get("corrupt"))

    # Missing slot loads gracefully
    g3 = Game()
    check("loading an empty slot returns False", g3.load_game(31337) is False)
    # (the test_slot fixture removes the slot file afterward)
