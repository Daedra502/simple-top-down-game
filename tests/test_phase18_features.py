"""Phase 18 tests: quests, town hub + stash, map layouts, auto-fire, sounds.

ASCII-only output. Run: python test_phase18_features.py
"""
import math
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from main import Game
from src.systems.quests import QuestManager
from src.audio.sounds import SoundManager
from src.items.item import ItemFactory, ItemRarity, ItemSlot


def check(label, cond):
    assert cond, label


def test_phase18_features(test_slot):
    print("PHASE 18 -- Quests / Town / Stash / Layouts / Auto-fire / Sound")

    # --- Quests -----------------------------------------------------------------
    qm = QuestManager()
    check("quest pool has exactly 100 entries", len(qm.pool) == 100)
    check("a quest is active at start", qm.current is not None)

    got = []
    qm.reward_cb = lambda xp, c: got.append((xp, c))
    qm.pool["__k"] = {"type": "kill", "desc": "Slay 2", "target": 2,
                      "reward_xp": 10, "reward_copper": 7}
    qm.current_id, qm.progress = "__k", 0
    check("wrong event type ignored", not qm.notify("open_chest", 5))
    check("matching event advances", not qm.notify("kill", 1) and qm.progress == 1)
    done = qm.notify("kill", 1)
    check("quest completes at target", done and got == [(10, 7)])
    check("a new quest is rolled after completion", qm.current_id != "__k")

    # --- Sounds (synthesized, fail-safe) ---------------------------------------
    sm = SoundManager()
    check("sound manager builds element cues (or no-ops safely)",
          (not sm.enabled) or set(sm._sounds) >= {"fire", "cold", "lightning"})

    # --- Game-level integration -------------------------------------------------
    g = Game(900, 650)

    # Map layout chosen and applied to the world
    check("a map layout is selected", getattr(g, "map_layout", None) is not None)
    check("world received the layout", g.world.layout is g.map_layout)

    # Auto-fire toggle + behavior
    from src.entities.enemy import Enemy, EnemyType
    g.auto_aim = True
    g.world.enemies.append(Enemy(60, 0, EnemyType.GOBLIN))
    g.player.active_skill = 0  # fireball (projectile)
    g.player.mana = g.player.max_mana
    before = len(g.projectiles)
    g._auto_fire()
    check("auto-fire launches at nearest enemy", len(g.projectiles) > before)

    # Mouse-wheel cycling math
    n = len(g.skills.slots)
    g.player.active_skill = 0
    g.player.active_skill = (g.player.active_skill - 1) % n
    check("wheel-up wraps to last skill", g.player.active_skill == n - 1)

    # Town portal round-trip
    g.auto_aim = False
    g.player.x, g.player.y = 1234, -567
    g._toggle_town()
    check("town portal enters town + stores return", g.in_town and g.town_return == (1234, -567))
    check("player warped into the town plaza",
          math.hypot(g.player.x - g.town_center[0],
                     g.player.y - g.town_center[1]) <= 120)
    g._toggle_town()
    check("town portal returns to field position", (not g.in_town) and g.player.x == 1234)

    # Stash transfer
    item = ItemFactory.roll_item(ItemSlot.CHEST, 12, ItemRarity.RARE)
    g.item_manager.inventory.add_item(item)
    g.show_stash = True
    g.draw_stash_overlay()
    g._handle_stash_click(g._stash_left_rects[-1][0].center, 1)
    check("item moves backpack -> stash", item in g.stash and item not in g.item_manager.inventory.items)
    g.draw_stash_overlay()
    g._handle_stash_click(g._stash_right_rects[-1][0].center, 1)
    check("item moves stash -> backpack", item in g.item_manager.inventory.items)

    # Stash + quests persist across save/load
    g.stash = [ItemFactory.roll_item(ItemSlot.HEAD, 8, ItemRarity.UNCOMMON)]
    g.quests.completed_count = 4
    g.save_game(test_slot)
    g.stash = []
    g.quests.completed_count = 0
    g.load_game(test_slot)
    check("stash persists across save/load", len(g.stash) == 1)
    check("quest progress persists across save/load", g.quests.completed_count == 4)

    # --- Dual rings + tooltip comparison ----------------------------------------
    r1 = ItemFactory.create_accessory("ring", ItemRarity.RARE, 1)
    r2 = ItemFactory.create_accessory("ring", ItemRarity.UNIQUE, 1)
    g.item_manager.inventory.add_item(r1)
    g.item_manager.inventory.add_item(r2)
    g._equip_from_inventory(r1)
    g._equip_from_inventory(r2)
    eqp = g.item_manager.equipment.equipment
    check("second ring fills the empty ring slot (dual ring)",
          eqp[ItemSlot.RING_1] is r1 and eqp[ItemSlot.RING_2] is r2)

    r3 = ItemFactory.create_accessory("ring", ItemRarity.RARE, 1)
    check("a hovered ring compares against both equipped rings",
          len(g._equipped_compare_items(r3)) == 2)

    from src.ui.tooltip import compute_item_stats, build_comparison_lines
    helm = ItemFactory.create_armor("helmet", ItemRarity.RARE, 1)
    helm2 = ItemFactory.create_armor("helmet", ItemRarity.COMMON, 1)
    clines = build_comparison_lines(helm, helm2)
    check("comparison produces a delta header + lines", clines and "current" in clines[0][0])
    check("compute_item_stats reduces an item to canonical keys",
          isinstance(compute_item_stats(helm), dict) and compute_item_stats(helm))
    # Rendering the side-by-side comparison must not raise.
    g.item_tooltip.draw_with_comparison(g.screen, r3, g._equipped_compare_items(r3),
                                        (400, 300), g.width, g.height, g.player.level)
    check("comparison tooltip renders", True)

    # --- Pause menu + volume sliders --------------------------------------------
    check("sfx volume clamps to [0,1]",
          (g.sound.set_sfx_volume(2.0) or True) and g.sound.sfx_volume == 1.0)
    g.sound.set_sfx_volume(0.6)
    g.show_pause_menu = True
    g.paused = True
    g.draw()  # builds button + slider hit-rects
    check("pause menu exposes resume/saves/controls/quit",
          {a for _, a in g._pause_buttons} == {"resume", "saves", "controls", "quit"})
    check("pause menu has SFX + Music sliders",
          {k for _, _, k in g._volume_sliders} == {"sfx", "music"})
    # Drag the music slider to ~30%
    track = next(t for t, _, k in g._volume_sliders if k == "music")
    g._dragging_slider = "music"
    g._drag_volume((track.x + int(track.width * 0.3), track.y))
    check("dragging the music slider sets the volume", abs(g.sound.music_volume - 0.3) < 0.05)
    # Show Controls toggles the keybind list; Resume closes the menu
    for rect, act in g._pause_buttons:
        if act == "controls":
            g._handle_pause_menu_click(rect.center, 1)
    check("controls toggle expands keybinds", g.show_controls)
    g.draw()
    for rect, act in g._pause_buttons:
        if act == "resume":
            g._handle_pause_menu_click(rect.center, 1)
    check("resume button closes the pause menu", not g.show_pause_menu)

    # A full draw pass in town and in the field must not raise
    g._toggle_town(); g.draw()
    g._toggle_town(); g.draw()
    check("draw works in town and field", True)
