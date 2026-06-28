"""Shared entity base: position, health, and damage/death event hooks.

The ``on_death`` hook (DESIGN.md Phase 1) lets later phases attach XP (Phase 3),
loot and rift progress (Phase 5/7) without the entity knowing about them.
"""
import pygame


class Event:
    """A tiny observer/event: subscribe callables, fire them with args."""

    def __init__(self):
        self._listeners = []

    def subscribe(self, fn):
        if fn not in self._listeners:
            self._listeners.append(fn)
        return fn

    def unsubscribe(self, fn):
        if fn in self._listeners:
            self._listeners.remove(fn)

    def fire(self, *args, **kwargs):
        # Iterate a copy so a listener may unsubscribe during dispatch.
        for fn in list(self._listeners):
            fn(*args, **kwargs)


class Entity(pygame.sprite.Sprite):
    """Base for anything with position, health, and a life cycle."""

    def __init__(self, x, y, max_health):
        super().__init__()
        self.x = x
        self.y = y
        self.max_health = max_health
        self.health = max_health

        self.on_damaged = Event()   # fires (entity, amount)
        self.on_death = Event()     # fires (entity) exactly once
        self._dead = False

    @property
    def is_alive(self):
        return not self._dead

    def take_damage(self, amount):
        """Apply damage, fire hooks, return True if this killed the entity."""
        amount = max(0, amount)
        self.health -= amount
        self.on_damaged.fire(self, amount)

        if self.health <= 0:
            self.health = 0
            if not self._dead:
                self._dead = True
                self.die()
        return self._dead

    def die(self):
        """Fire the death hook. Override to add entity-specific behavior."""
        self.on_death.fire(self)
