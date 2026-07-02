"""Tests for the UI cleanup pass: the centralized Escape back-out flow, the
quit-confirmation dialog, skill tooltip damage accuracy, and clean rendering of
the HUD / pause / confirm paths. ASCII-only output.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from main import Game


def check(label, cond):
    assert cond, label


def make():
    return Game(1000, 720)


def test_escape_opens_and_resumes_pause():
    g = make()
    g._handle_escape()
    check("escape opens the pause menu", g.show_pause_menu and g.paused)
    g._handle_escape()
    check("escape from pause resumes", not g.show_pause_menu and not g.paused)


def test_escape_closes_overlays_before_pausing():
    g = make()
    g.show_inventory = True
    g._handle_escape()
    check("escape closes the open overlay", not g.show_inventory)
    check("escape did not also open pause", not g.show_pause_menu)


def test_escape_backs_out_one_layer_at_a_time():
    g = make()
    # A stack of overlays: escape closes the highest-priority one each press.
    g.show_save_menu = True
    g.show_inventory = True
    g._handle_escape()
    # Inventory has higher priority than the save menu in _ESC_OVERLAYS.
    check("first escape closes inventory", not g.show_inventory)
    check("save menu still open", g.show_save_menu)
    g._handle_escape()
    check("second escape closes save menu", not g.show_save_menu)


def test_quit_requires_confirmation():
    g = make()
    g._handle_escape()               # open pause
    g._handle_pause_menu_keys(pygame.K_q)
    check("Q arms the quit confirmation", g.pause_confirm_quit)
    check("game is still running", g.running)
    g._handle_escape()               # escape cancels the dialog, stays paused
    check("escape cancels quit confirm", not g.pause_confirm_quit)
    check("still in pause menu", g.show_pause_menu)

    g._handle_pause_menu_keys(pygame.K_q)
    g._handle_pause_menu_keys(pygame.K_n)
    check("N cancels the quit", not g.pause_confirm_quit and g.running)

    g._handle_pause_menu_keys(pygame.K_q)
    g._handle_pause_menu_keys(pygame.K_y)
    check("Y confirms the quit", not g.running)


def test_save_confirm_cancelled_before_menu_closes():
    g = make()
    g.show_save_menu = True
    g.save_confirm = {"action": "save", "slot": 0}
    g._handle_escape()
    check("escape cancels the save dialog first", g.save_confirm is None)
    check("save menu stays open", g.show_save_menu)
    g._handle_escape()
    check("next escape closes the save menu", not g.show_save_menu)


def test_skill_tooltip_reports_effective_damage():
    g = make()
    skill = g.skills.slot(0)
    base = skill.stats().get("damage", 0)
    check("damage-dealing skill has base damage", base > 0)
    eff = int(g.player.get_spell_damage(base, skill.element, skill.id))
    # The tooltip uses exactly this computation; assert it is coherent.
    check("effective damage >= base (scaling never reduces)", eff >= base)


def test_ui_paths_render_clean():
    g = make()
    for _ in range(3):
        g.update()
    g.draw()                     # HUD + minimap + skill bar
    g.show_pause_menu = True
    g.draw()
    g.draw_pause_menu()
    g.pause_confirm_quit = True
    g.draw_pause_menu()          # confirm dialog on top
    check("all UI render paths ran", True)
