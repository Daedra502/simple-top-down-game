"""Shared pytest setup for the test suite.

Runs before any test module is imported, so it:
  * puts the project root on sys.path (lets tests do `from main import Game`
    and `from src...` no matter where pytest is invoked from), and
  * forces headless SDL drivers so pygame never opens a window or audio device.

This replaces the per-file `sys.path.insert(...)` hacks and `os.environ`
boilerplate the individual tests used to carry.
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture
def test_slot():
    """A hidden, disposable save slot seeded from the most recent real save.

    Any test that exercises save/load should take this fixture and use the
    yielded slot id instead of a hardcoded numeric slot. This guarantees the
    suite operates on a *copy* of the player's most recent save and never
    reads, overwrites, or deletes a real slot (0..4). The slot file is removed
    after the test.
    """
    from src.core import save as save_system

    save_system.clear_test_slot()      # start clean in case a prior run crashed
    slot = save_system.seed_test_slot()
    try:
        yield slot
    finally:
        save_system.clear_test_slot()
