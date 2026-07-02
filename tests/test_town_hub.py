"""Behavioral tests for the town hub + teleport (T) and the atmosphere pass:
entering/leaving town round-trips the player, town is a true safe zone (no
spawns), stations interact, and the town/field rendering paths run clean.
ASCII-only output.
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from main import Game


def check(label, cond):
    assert cond, label


def make_game():
    return Game(900, 650)


def test_town_teleport_round_trip():
    g = make_game()
    g.player.x, g.player.y = 1234.0, -777.0
    g.player.rect.center = (1234, -777)

    g._toggle_town()
    check("entered town", g.in_town)
    import math
    dist = math.hypot(g.player.x - g.town_center[0], g.player.y - g.town_center[1])
    check("player warped into the plaza (near the well)", dist <= 120)
    check("field position remembered", g.town_return == (1234.0, -777.0))

    g._toggle_town()
    check("left town", not g.in_town)
    check("player restored to field position",
          (g.player.x, g.player.y) == (1234.0, -777.0))


def test_town_is_a_safe_zone():
    g = make_game()
    # Seed a fight + world features, then portal to town.
    g.update()
    g.chest_spawn_interval = 0.01
    for _ in range(30):
        g.update()
    g._enter_town()
    check("enemies cleared on entering town", len(g.world.enemies) == 0)
    check("chests cleared on entering town", len(g.world.chests) == 0)
    check("obstacles cleared on entering town", len(g.world.obstacles) == 0)

    # Nothing may spawn while in town, even with a hot chest timer.
    for _ in range(60):
        g.update()
    check("no enemies spawn in town", len(g.world.enemies) == 0)
    check("no chests spawn in town", len(g.world.chests) == 0)
    check("no obstacles spawn in town", len(g.world.obstacles) == 0)


def test_town_ends_boss_lockdown():
    g = make_game()
    g.rift.boss_active = True
    g.rift.spawning_enabled = False
    g._enter_town()
    check("boss lockdown lifted", not g.rift.boss_active)
    check("spawning re-enabled for the return", g.rift.spawning_enabled)


def test_station_proximity_and_interaction():
    g = make_game()
    g._enter_town()

    stash = next(s for s in g.town_stations if s['key'] == 'stash')
    g.player.x, g.player.y = stash['x'], stash['y']
    g._update_town()
    check("stash station detected", g._near_station is stash)
    g._interact_station()
    check("stash overlay opened", g.show_stash)
    g.show_stash = False

    portal = next(s for s in g.town_stations if s['key'] == 'portal')
    g.player.x, g.player.y = portal['x'], portal['y']
    g._update_town()
    check("portal station detected", g._near_station is portal)
    g._interact_station()
    check("portal returns to the field", not g.in_town)

    # Standing in the middle of nowhere: no station.
    g._enter_town()
    g.player.x, g.player.y = g.town_center[0] + 500, g.town_center[1]
    g._update_town()
    check("no station detected far away", g._near_station is None)


def test_town_and_field_rendering_paths():
    g = make_game()
    # Field: layout ambient + vignette.
    g.update()
    g.draw()
    check("field layout has an ambient tint", 'ambient' in g.map_layout)

    # Town: village ground, buildings, warm atmosphere.
    g._enter_town()
    g.update()
    g.draw()
    check("town rendering ran", g.in_town)
