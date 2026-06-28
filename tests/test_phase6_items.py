"""Phase 6 tests: affix rolling, gear aggregation, resistances, drop scaling.

ASCII-only output. Run: python test_phase6_items.py
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.items.item import ItemFactory, ItemRarity, ItemSlot
from src.items import affixes as AF
from main import Game


def check(label, cond):
    assert cond, label


def test_phase6_items():
    print("PHASE 6 -- Itemization: Armor & Jewelry")

    # Affix pool coverage (all required stats present)
    pool = AF._pool()
    required = {
        "crit_chance", "crit_damage", "status_radius", "cooldown_reduction",
        "attack_speed", "damage", "mana_regen", "health_regen",
        "max_health", "max_mana", "increased_vulnerable_damage",
        "fire_resistance", "cold_resistance", "lightning_resistance",
        "chaos_resistance", "physical_resistance",
    }
    stats_in_pool = {a["stat"] for a in pool.values()}
    check("affix pool covers all required stats", required <= stats_in_pool)

    # Rarity controls affix count
    check("common rolls 1 affix", AF.affix_count(0) == 1)
    check("unique rolls 4 affixes", AF.affix_count(3) == 4)
    ring = ItemFactory.roll_item(ItemSlot.RING_1, 50, ItemRarity.UNIQUE)
    check("unique item has 4 affixes", len(ring.affixes) == 4)
    check("jewelry only rolls jewelry-legal affixes",
          all("jewelry" in pool[a["id"]]["slots"] for a in ring.affixes))

    # Higher ilvl rolls bigger values (statistical: average over many rolls)
    def avg_health(ilvl):
        vals = []
        for _ in range(200):
            a = AF.roll_affixes("armor", ilvl, 3)
            vals += [x["value"] for x in a if x["stat"] == "max_health"]
        return sum(vals) / max(1, len(vals))
    check("ilvl scales affix magnitude", avg_health(80) > avg_health(5))

    # Gear aggregation into the player's Stats layer
    g = Game()
    p = g.player
    g.recompute_player_stats()
    base_cd, base_hpr, base_hp = p.crit_damage, p.health_regen, p.max_health

    def make_item(slot, affs):
        it = ItemFactory.roll_item(slot, 1, ItemRarity.COMMON)
        it.affixes = affs
        return it

    g.item_manager.equipment.equip_item(make_item(ItemSlot.RING_1, [
        {"id": "crit_damage", "stat": "crit_damage", "value": 0.5, "label": "Crit Dmg", "is_percent": True},
        {"id": "increased_vulnerable_damage", "stat": "increased_vulnerable_damage", "value": 0.2, "label": "Vuln", "is_percent": True},
    ]))
    g.item_manager.equipment.equip_item(make_item(ItemSlot.CHEST, [
        {"id": "increased_health", "stat": "max_health", "value": 100, "label": "Health", "is_percent": False},
        {"id": "health_regen", "stat": "health_regen", "value": 5, "label": "HP Regen", "is_percent": False},
        {"id": "fire_resistance", "stat": "fire_resistance", "value": 40, "label": "Fire Res", "is_percent": False},
    ]))
    g.recompute_player_stats()

    check("crit damage reads from gear", abs(p.crit_damage - (base_cd + 0.5)) < 1e-6)
    check("increased vulnerable damage reads from gear", abs(p.increased_vulnerable_damage - 0.2) < 1e-6)
    check("max health reads from gear", p.max_health == base_hp + 100)
    check("health regen reads from gear", abs(p.health_regen - (base_hpr + 5)) < 1e-6)
    check("fire resistance reads from gear", p.get_resistance("fire") == 40)

    # Resistance cap at 75
    g.item_manager.equipment.equip_item(make_item(ItemSlot.LEGS, [
        {"id": "fire_resistance", "stat": "fire_resistance", "value": 90, "label": "Fire Res", "is_percent": False},
    ]))
    g.recompute_player_stats()
    check("resistance caps at 75", p.get_resistance("fire") == 75)

    # Physical resistance reduces incoming damage path
    g.item_manager.equipment.equip_item(make_item(ItemSlot.HEAD, [
        {"id": "physical_resistance", "stat": "physical_resistance", "value": 50, "label": "Phys Res", "is_percent": False},
    ]))
    g.recompute_player_stats()
    check("physical resistance is read", p.get_resistance("physical") == 50)

    # Drop scaling: higher GR shifts rarity upward (statistical)
    def unique_rate(gr):
        n = sum(1 for _ in range(2000)
                if ItemFactory.generate_drop(50, gr).rarity == ItemRarity.UNIQUE)
        return n / 2000.0
    check("higher GR drops more uniques", unique_rate(80) >= unique_rate(0))
