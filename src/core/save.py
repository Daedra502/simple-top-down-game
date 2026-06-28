"""Save / Load system (DESIGN.md Phase 10).

A character is persisted to a human-readable JSON slot (chosen over a binary
format because the project had no prior save seam, the schema keeps evolving, and
JSON is trivial to inspect/debug and forward-migrate via ``version``).

Serialized state: level / XP / skill points, the Stats *base* (which carries all
per-level growth), wallet, highest GR, selected active skill, wand level,
allocated skill-tree nodes (by id), active-skill levels/mastery/runes, full
inventory (incl. keystones), equipped gear (restored into the exact slot it was
saved in, so dual weapons and dual rings survive), the stash, quest progress, and
ascendancy/atlas. Loading rebuilds the tree's allocated set, re-equips gear, then
recomputes aggregated stats so a loaded character is identical to the saved one.

Schema growth is backward-compatible: every new field is read with ``.get`` and a
default, so a v1 save still loads in a v2 build.
"""
import json
import os

from src.items.item import Item, ItemRarity, ItemSlot

SAVE_VERSION = 2
_SAVE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "saves")


def slot_path(slot=0):
    return os.path.normpath(os.path.join(_SAVE_DIR, f"save_slot_{slot}.json"))


# --- item (de)serialization --------------------------------------------------
def item_to_dict(item):
    return {
        "item_id": item.item_id,
        "name": item.name,
        "item_type": item.item_type,
        "rarity": item.rarity.value,
        "slot": item.slot.value,
        "level_requirement": item.level_requirement,
        "ilvl": getattr(item, "ilvl", item.level_requirement),
        "affixes": list(getattr(item, "affixes", [])),
        "stats": item.stats,
        "stack": getattr(item, "stack", None),
        "upgrade_level": getattr(item, "upgrade_level", 0),
    }


def item_from_dict(d):
    item = Item(
        d["item_id"], d["name"], d["item_type"],
        rarity=ItemRarity(d["rarity"]),
        slot=ItemSlot(d["slot"]),
        level_requirement=d["level_requirement"],
    )
    item.ilvl = d.get("ilvl", item.level_requirement)
    item.affixes = list(d.get("affixes", []))
    item.stats = d.get("stats", item.stats)
    item.upgrade_level = d.get("upgrade_level", 0)
    if d.get("stack") is not None:
        item.stack = d["stack"]
    return item


# --- whole-game state --------------------------------------------------------
def build_save(game):
    """Capture the full character state as a JSON-serializable dict."""
    p = game.player
    equipped = {slot.value: item_to_dict(it)
                for slot, it in game.item_manager.equipment.equipment.items()
                if it is not None}

    return {
        "version": SAVE_VERSION,
        "level": p.level,
        "experience": p.experience,
        "skill_points": p.skill_points,
        "xp_to_level": p.xp_to_level,
        "stats_base": dict(p.stats.base),
        "health": p.health,
        "mana": p.mana,
        "wallet": {"copper": p.copper, "silver": p.silver,
                   "gold": p.gold, "diamond": p.diamond},
        "highest_gr": p.highest_gr,
        "active_skill": getattr(p, "active_skill", 0),
        "wand_level": getattr(p, "wand_level", 0),
        "wand_damage_bonus": getattr(p, "wand_damage_bonus", 0),
        "allocated_nodes": [nid for nid, on in game.skill_tree.allocations.items()
                            if on and nid != game.skill_tree.ROOT_ID],
        "inventory": [item_to_dict(it) for it in game.item_manager.inventory.items],
        "equipped": equipped,
        "stash": [item_to_dict(it) for it in getattr(game, "stash", [])],
        "quests": game.quests.to_dict() if hasattr(game, "quests") else {},
        "world_seed": getattr(game.world, "seed", None),
        "skills": game.skills.to_dict() if hasattr(game, "skills") else [],
        "ascendancy": game.ascendancy.to_dict() if hasattr(game, "ascendancy") else {},
        "atlas": game.atlas.to_dict() if hasattr(game, "atlas") else {},
    }


def apply_save(game, data):
    """Rebuild game state from a save dict and recompute aggregated stats."""
    p = game.player

    # Scalars
    p.level = data["level"]
    p.experience = data["experience"]
    p.skill_points = data["skill_points"]
    p.xp_to_level = data["xp_to_level"]
    p.highest_gr = data.get("highest_gr", 0)
    p.active_skill = data.get("active_skill", getattr(p, "active_skill", 0))
    p.wand_level = data.get("wand_level", 0)
    p.wand_damage_bonus = data.get("wand_damage_bonus", 0)

    w = data["wallet"]
    p.copper, p.silver = w["copper"], w["silver"]
    p.gold, p.diamond = w["gold"], w["diamond"]

    # Base stats carry per-level growth and any tuning; restore them wholesale.
    p.stats.base = dict(data["stats_base"])

    # Skill tree: reset then allocate saved nodes in a connectivity-safe order.
    game.skill_tree.reset_tree()
    pending = set(data.get("allocated_nodes", []))
    progressed = True
    while pending and progressed:
        progressed = False
        for nid in list(pending):
            if game.skill_tree.allocate_node(nid):
                pending.discard(nid)
                progressed = True
    # (any still-pending nodes were unreachable -> silently dropped)

    # Inventory
    inv = game.item_manager.inventory
    inv.items = [item_from_dict(d) for d in data.get("inventory", [])]
    inv._update_slot_positions()

    # Stash (Phase 18): persistent stored items.
    game.stash = [item_from_dict(d) for d in data.get("stash", [])]

    # Quests (Phase 18): restore the active objective + progress.
    if hasattr(game, "quests"):
        game.quests.load_dict(data.get("quests"))

    # Equipment. Restore each item into the *exact* slot it was saved in (keyed
    # by slot value), not by item.slot -- otherwise a secondary weapon or second
    # ring (whose item.slot is the primary) would collide with the primary and
    # be lost. Falls back to item.slot for unknown keys / legacy saves.
    equipment = game.item_manager.equipment
    for slot in equipment.equipment:
        equipment.equipment[slot] = None
    for slot_value, item_dict in data.get("equipped", {}).items():
        item = item_from_dict(item_dict)
        try:
            slot = ItemSlot(slot_value)
        except ValueError:
            slot = item.slot
        equipment.equip_item_to_slot(item, slot)

    # Active skills (Phase 13): restore levels / xp / mastery.
    if hasattr(game, "skills"):
        game.skills.load_list(data.get("skills"))

    # Endgame progression (Phase 15).
    if hasattr(game, "ascendancy") and data.get("ascendancy"):
        game.ascendancy.load_dict(data["ascendancy"])
    if hasattr(game, "atlas") and data.get("atlas"):
        game.atlas.load_dict(data["atlas"])

    # Rebuild the streaming world from the saved seed so it is reproducible.
    if data.get("world_seed") is not None:
        from src.systems.world import WorldManager
        game.world = WorldManager(seed=data["world_seed"])

    # Recompute effective stats (tree + gear + set + resistances), then restore
    # the saved current pools.
    game.recompute_player_stats()
    p.health = min(data["health"], p.max_health)
    p.mana = min(data["mana"], p.max_mana)


def save_to_slot(game, slot=0):
    os.makedirs(_SAVE_DIR, exist_ok=True)
    with open(slot_path(slot), "w", encoding="utf-8") as f:
        json.dump(build_save(game), f, indent=2)
    return slot_path(slot)


def has_save(slot=0):
    return os.path.exists(slot_path(slot))


def load_from_slot(game, slot=0):
    if not has_save(slot):
        return False
    with open(slot_path(slot), "r", encoding="utf-8") as f:
        apply_save(game, json.load(f))
    return True


# --- slot browsing (Phase 17 save UI) ---------------------------------------
def _class_name(chosen):
    """Display name for an ascendancy class id (or 'No Class')."""
    if not chosen:
        return "No Class"
    try:
        from src.core.data_loader import load_json
        return load_json("ascendancy.json").get(chosen, {}).get("name", chosen.title())
    except Exception:
        return str(chosen).title()


def peek_slot(slot=0):
    """Lightweight metadata for a save slot (no game mutation).

    Returns a dict the save UI uses to let the player tell slots apart, a special
    ``{"corrupt": True}`` marker if the file exists but can't be read, or None if
    the slot is empty.
    """
    path = slot_path(slot)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        w = d.get("wallet", {})
        wealth = (w.get("copper", 0) + w.get("silver", 0) * 10
                  + w.get("gold", 0) * 100 + w.get("diamond", 0) * 1000)
        return {
            "slot": slot,
            "level": d.get("level", 1),
            "highest_gr": d.get("highest_gr", 0),
            "class_name": _class_name(d.get("ascendancy", {}).get("chosen")),
            "wealth": wealth,
            "quests_done": d.get("quests", {}).get("completed_count", 0),
            "mtime": os.path.getmtime(path),
        }
    except Exception:
        # File exists but is unreadable/corrupt -- surface that, don't hide it.
        return {"slot": slot, "corrupt": True, "mtime": os.path.getmtime(path)}


def list_slots(count=5):
    """Metadata (or None) for slots 0..count-1."""
    return [peek_slot(i) for i in range(count)]


def latest_slot(count=5):
    """Index of the most-recently-modified existing save, or None."""
    best, best_t = None, -1.0
    for i in range(count):
        path = slot_path(i)
        if os.path.exists(path):
            t = os.path.getmtime(path)
            if t > best_t:
                best, best_t = i, t
    return best
