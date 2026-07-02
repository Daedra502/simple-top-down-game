"""Tests for the new player activities: town bounty board contracts and field
ritual circles (stand-and-channel events). ASCII-only output.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from main import Game
from src.systems.bounties import BountyManager


def check(label, cond):
    assert cond, label


# --- BountyManager unit behavior ---------------------------------------------
def test_bounty_offers_and_accept():
    bm = BountyManager()
    check("board offers three contracts", len(bm.offers) == 3)
    check("no active contract at start", bm.active is None)

    picked = bm.accept(0)
    check("accepting activates the contract", bm.active is picked and picked)
    check("offers rerolled after accepting", len(bm.offers) == 3)
    check("bad index is rejected", bm.accept(99) is None)


def test_bounty_progress_and_completion():
    bm = BountyManager()
    bm.active = {"id": "purge_undead", "desc": "Purge the undead",
                 "type": "kill_family", "family": "undead", "target": 3,
                 "gold": 2, "loot": 1, "keystones": 0}
    bm.progress = 0

    check("wrong family does not advance",
          bm.notify("kill_family", family="demons") is None and bm.progress == 0)
    check("wrong event does not advance",
          bm.notify("open_chest") is None and bm.progress == 0)
    bm.notify("kill_family", family="undead")
    bm.notify("kill_family", family="undead")
    check("progress counts matching kills", bm.progress == 2)
    reward = bm.notify("kill_family", family="undead")
    check("completion returns the reward bundle",
          reward is not None and reward["gold"] == 2)
    check("contract cleared after completion", bm.active is None)
    check("completion counted", bm.completed_count == 1)


def test_bounty_save_round_trip():
    bm = BountyManager()
    bm.accept(1)
    bm.progress = 2
    data = bm.to_dict()

    bm2 = BountyManager()
    bm2.from_dict(data)
    check("active contract restored", bm2.active == bm.active)
    check("progress restored", bm2.progress == 2)
    check("offers restored", bm2.offers == bm.offers)


# --- Game integration ---------------------------------------------------------
def test_bounty_payout_through_game():
    g = Game(900, 650)
    g.bounties.active = {"id": "elite_hunt", "desc": "Slay empowered foes",
                         "type": "kill_elite", "family": None, "target": 1,
                         "gold": 4, "loot": 1, "keystones": 1}
    g.bounties.progress = 0
    gold_before = g.player.gold
    ks_before = g.item_manager.keystone_count()

    g._notify_bounty("kill_elite")
    check("gold paid out", g.player.gold == gold_before + 4)
    check("keystone paid out", g.item_manager.keystone_count() == ks_before + 1)
    check("loot dropped at the player", len(g.dropped_items) >= 1)
    check("contract cleared", g.bounties.active is None)


def test_bounty_board_is_a_town_station():
    g = Game(900, 650)
    g._enter_town()
    board = next(s for s in g.town_stations if s['key'] == 'board')
    g.player.x, g.player.y = board['x'], board['y']
    g._update_town()
    check("board station detected", g._near_station is board)
    g._interact_station()
    check("board overlay opened", g.show_bounty_board)
    g.draw()   # overlay renders clean
    g.show_bounty_board = False


# --- Ritual circles -----------------------------------------------------------
def test_ritual_spawns_channels_and_pays_out():
    g = Game(900, 650)
    g.update()

    # Force a circle to appear.
    g.ritual_spawn_timer = g.RITUAL_INTERVAL
    g._update_rituals()
    check("ritual circle spawned", len(g.rituals) == 1)
    r = g.rituals[0]

    # Stand inside and channel to completion.
    g.player.x, g.player.y = r['x'], r['y']
    xp_before = g.player.experience + g.player.level * 100000
    enemies_before = len(g.world.enemies)
    for _ in range(int(g.RITUAL_TIME / g.dt) + 30):
        g._update_rituals()
        if r['done']:
            break
    check("channel completes while standing inside", r['done'])
    check("pressure waves spawned enemies", len(g.world.enemies) > enemies_before)
    check("loot dropped at the circle", len(g.dropped_items) >= 2)
    xp_after = g.player.experience + g.player.level * 100000
    check("xp granted", xp_after > xp_before)

    # A finished circle spawns no further waves.
    n = len(g.world.enemies)
    for _ in range(60):
        g._update_rituals()
    check("done circle stays quiet", len(g.world.enemies) == n)


def test_ritual_progress_decays_outside():
    g = Game(900, 650)
    g.rituals.append({'x': 0.0, 'y': 0.0, 'progress': 0.0,
                      'done': False, 'wave_timer': 999.0})
    r = g.rituals[0]
    g.player.x, g.player.y = r['x'], r['y']
    for _ in range(60):
        g._update_rituals()
    check("progress builds inside", r['progress'] > 0.5)

    p = r['progress']
    g.player.x, g.player.y = r['x'] + 500, r['y']
    for _ in range(30):
        g._update_rituals()
    check("progress decays outside", r['progress'] < p)
    check("progress never goes negative", r['progress'] >= 0)


def test_rituals_clear_in_town():
    g = Game(900, 650)
    g.rituals.append({'x': 10.0, 'y': 10.0, 'progress': 1.0,
                      'done': False, 'wave_timer': 0.0})
    g._enter_town()
    check("rituals cleared on entering town", len(g.rituals) == 0)
