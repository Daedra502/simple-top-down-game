"""Item system for inventory and equipment."""
import random
from enum import Enum


class ItemRarity(Enum):
    """Item rarity levels."""
    COMMON = 0
    UNCOMMON = 1
    RARE = 2
    UNIQUE = 3


class ItemSlot(Enum):
    """Equipment slot types."""
    WEAPON_2H = "2h_weapon"
    WEAPON_1H = "1h_weapon"
    WEAPON_1H_OFF = "1h_weapon_off"   # optional secondary (off-hand) weapon
    OFF_HAND = "off_hand"
    HEAD = "head"
    CHEST = "chest"
    LEGS = "legs"
    FEET = "feet"
    HANDS = "hands"
    BELT = "belt"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    AMULET = "amulet"
    
    # Non-equipment slots
    CONSUMABLE = "consumable"
    MATERIAL = "material"


# Human-friendly equipment slot labels for UI panels/tooltips.
SLOT_DISPLAY_NAMES = {
    ItemSlot.WEAPON_1H: "Main Weapon",
    ItemSlot.WEAPON_1H_OFF: "Secondary Weapon",
    ItemSlot.WEAPON_2H: "Two-Handed Weapon",
    ItemSlot.OFF_HAND: "Off-Hand",
    ItemSlot.HEAD: "Head",
    ItemSlot.CHEST: "Chest",
    ItemSlot.LEGS: "Legs",
    ItemSlot.FEET: "Feet",
    ItemSlot.HANDS: "Hands",
    ItemSlot.BELT: "Belt",
    ItemSlot.RING_1: "Ring I",
    ItemSlot.RING_2: "Ring II",
    ItemSlot.AMULET: "Amulet",
}


def slot_display_name(slot):
    """Friendly label for an equipment slot (falls back to a title-cased value)."""
    return SLOT_DISPLAY_NAMES.get(slot, slot.value.replace("_", " ").title())


class Item:
    """Represents an item in the game."""
    
    def __init__(self, item_id, name, item_type, rarity=ItemRarity.COMMON, 
                 slot=ItemSlot.CONSUMABLE, level_requirement=1):
        """
        Initialize an item.
        
        Args:
            item_id: Unique identifier for the item type
            name: Display name
            item_type: Type of item (weapon, armor, accessory)
            rarity: Rarity level
            slot: Equipment slot this item can occupy
            level_requirement: Minimum level to equip
        """
        self.item_id = item_id
        self.name = name
        self.item_type = item_type
        self.rarity = rarity
        self.slot = slot
        self.level_requirement = level_requirement

        # Rolled affixes (Phase 6): list of {id, stat, value, label, is_percent}
        self.affixes = []
        self.ilvl = level_requirement

        # Upgrade level (Phase 17): money-bought levels that scale this item's
        # stats. 0..MAX_UPGRADE; each level adds UPGRADE_PER_LEVEL to the mult.
        self.upgrade_level = 0

        # Legacy flat stats dictionary
        self.stats = {
            'health': 0,
            'mana': 0,
            'damage': 0,
            'attack_speed': 0.0,
            'armor': 0,
            'elemental_damage': 0,
            'resistances': {}
        }
        
        # Color based on rarity
        self.rarity_colors = {
            ItemRarity.COMMON: (200, 200, 200),
            ItemRarity.UNCOMMON: (100, 255, 100),
            ItemRarity.RARE: (50, 150, 255),
            ItemRarity.UNIQUE: (255, 150, 0),
        }
    
    def set_stat(self, stat_name, value):
        """Set a stat on the item."""
        if stat_name in self.stats:
            self.stats[stat_name] = value
    
    def add_stat(self, stat_name, value):
        """Add to a stat on the item (merges dict stats like resistances)."""
        if stat_name in self.stats:
            current = self.stats[stat_name]
            if isinstance(current, dict) and isinstance(value, dict):
                for key, amount in value.items():
                    current[key] = current.get(key, 0) + amount
            else:
                self.stats[stat_name] += value
    
    def get_color(self):
        """Get the color for this item's rarity."""
        return self.rarity_colors.get(self.rarity, (200, 200, 200))

    def get_sell_value(self):
        """Copper value when sold from the inventory.

        Scales with rarity, item level, and any upgrade investment.
        """
        base = {
            ItemRarity.COMMON: 5,
            ItemRarity.UNCOMMON: 15,
            ItemRarity.RARE: 40,
            ItemRarity.UNIQUE: 120,
        }.get(self.rarity, 5)
        value = int(base * (1 + max(self.ilvl, self.level_requirement) * 0.1))
        value = int(value * self.upgrade_multiplier())
        return value * max(1, getattr(self, 'stack', 1))

    # --- upgrades (Phase 17) ---------------------------------------------
    MAX_UPGRADE = 20
    UPGRADE_PER_LEVEL = 0.05   # +5% to all of this item's stats per level

    def upgrade_multiplier(self):
        """Stat multiplier from purchased upgrade levels (1.0 at level 0)."""
        return 1.0 + self.UPGRADE_PER_LEVEL * getattr(self, 'upgrade_level', 0)

    def upgrade_cost(self):
        """Copper cost of the NEXT upgrade level (rises with rarity/ilvl/level)."""
        base = 40 + max(self.ilvl, self.level_requirement) * 4
        base *= (self.rarity.value + 1)
        return int(base * (getattr(self, 'upgrade_level', 0) + 1))

    def can_upgrade(self):
        return getattr(self, 'upgrade_level', 0) < self.MAX_UPGRADE
    
    def get_description(self):
        """Get formatted item description."""
        desc = f"{self.name}\n"
        desc += f"Rarity: {self.rarity.name}\n"
        desc += f"Type: {self.item_type}\n"
        desc += f"Slot: {self.slot.value}\n"
        desc += f"Level Requirement: {self.level_requirement}\n\n"
        
        # Add legacy flat stats
        for stat, value in self.stats.items():
            if stat == 'resistances':
                continue
            if value != 0:
                if isinstance(value, float):
                    desc += f"{stat}: +{value:.2f}\n"
                else:
                    desc += f"{stat}: +{value}\n"

        # Add rolled affixes
        for af in self.affixes:
            if af.get('is_percent'):
                desc += f"{af['label']}: +{af['value'] * 100:.1f}%\n"
            else:
                desc += f"{af['label']}: +{af['value']}\n"

        return desc


class ItemFactory:
    """Factory for creating items."""
    
    @staticmethod
    def create_weapon(name, rarity=ItemRarity.COMMON, level=1):
        """Create a weapon item."""
        item = Item(
            f"weapon_{name.lower()}",
            name,
            "weapon",
            rarity=rarity,
            slot=ItemSlot.WEAPON_1H,
            level_requirement=level
        )
        
        # Base damage scaling with rarity
        damage_multiplier = 1.0 + (rarity.value * 0.5)
        item.set_stat('damage', int(10 * damage_multiplier))
        
        # Rarity-specific bonuses
        if rarity == ItemRarity.UNCOMMON:
            item.add_stat('attack_speed', 0.05)
        elif rarity == ItemRarity.RARE:
            item.add_stat('attack_speed', 0.1)
            item.add_stat('damage', 5)
        elif rarity == ItemRarity.UNIQUE:
            item.add_stat('attack_speed', 0.15)
            item.add_stat('elemental_damage', 10)
        
        return item
    
    @staticmethod
    def create_armor(armor_type, rarity=ItemRarity.COMMON, level=1):
        """Create an armor item."""
        slot_map = {
            'helmet': ItemSlot.HEAD,
            'chest': ItemSlot.CHEST,
            'legs': ItemSlot.LEGS,
            'boots': ItemSlot.FEET,
            'gloves': ItemSlot.HANDS,
            'belt': ItemSlot.BELT,
        }
        
        slot = slot_map.get(armor_type, ItemSlot.CHEST)
        name = f"{armor_type.capitalize()}"
        
        item = Item(
            f"armor_{armor_type.lower()}",
            name,
            "armor",
            rarity=rarity,
            slot=slot,
            level_requirement=level
        )
        
        # Base stats
        health_multiplier = 1.0 + (rarity.value * 0.3)
        item.set_stat('health', int(20 * health_multiplier))
        item.set_stat('armor', int(10 * health_multiplier))
        
        # Rarity bonuses
        if rarity == ItemRarity.UNCOMMON:
            item.add_stat('health', 10)
        elif rarity == ItemRarity.RARE:
            item.add_stat('health', 25)
            item.add_stat('armor', 5)
        elif rarity == ItemRarity.UNIQUE:
            item.add_stat('health', 40)
            item.add_stat('resistances', {'fire': 10, 'cold': 10})
        
        return item
    
    @staticmethod
    def create_accessory(accessory_type, rarity=ItemRarity.COMMON, level=1):
        """Create an accessory item."""
        slot_map = {
            'ring': ItemSlot.RING_1,
            'amulet': ItemSlot.AMULET,
        }
        
        slot = slot_map.get(accessory_type, ItemSlot.RING_1)
        name = f"{accessory_type.capitalize()}"
        
        item = Item(
            f"accessory_{accessory_type.lower()}_{random.randint(1, 1000)}",
            name,
            "accessory",
            rarity=rarity,
            slot=slot,
            level_requirement=level
        )
        
        # Base stats
        item.set_stat('mana', int(15 * (1 + rarity.value * 0.2)))
        
        # Rarity bonuses
        if rarity == ItemRarity.UNCOMMON:
            item.add_stat('mana', 10)
        elif rarity == ItemRarity.RARE:
            item.add_stat('damage', 5)
            item.add_stat('mana', 20)
        elif rarity == ItemRarity.UNIQUE:
            item.add_stat('damage', 10)
            item.add_stat('health', 30)
            item.add_stat('mana', 30)
        
        return item
    
    # --- Affix-based generation (Phase 6) --------------------------------
    ARMOR_SLOTS = {
        "head": ItemSlot.HEAD, "chest": ItemSlot.CHEST, "legs": ItemSlot.LEGS,
        "feet": ItemSlot.FEET, "hands": ItemSlot.HANDS, "belt": ItemSlot.BELT,
    }
    JEWELRY_SLOTS = {"ring": ItemSlot.RING_1, "amulet": ItemSlot.AMULET}

    @staticmethod
    def slot_category(slot):
        """Map an equipment slot to an affix slot category."""
        if slot in (ItemSlot.RING_1, ItemSlot.RING_2, ItemSlot.AMULET):
            return "jewelry"
        if slot in (ItemSlot.WEAPON_1H, ItemSlot.WEAPON_1H_OFF,
                    ItemSlot.WEAPON_2H, ItemSlot.OFF_HAND):
            return "weapon"
        return "armor"

    @staticmethod
    def roll_item(slot, ilvl, rarity, name=None):
        """Create an armor/jewelry/weapon item with rolled affixes."""
        from src.items.affixes import roll_affixes

        category = ItemFactory.slot_category(slot)
        if name is None:
            quality = {ItemRarity.COMMON: "Worn", ItemRarity.UNCOMMON: "Fine",
                       ItemRarity.RARE: "Exquisite", ItemRarity.UNIQUE: "Mythic"}[rarity]
            name = f"{quality} {slot.value.replace('_', ' ').title()}"

        item = Item(
            f"{category}_{slot.value}_{random.randint(1, 1_000_000)}",
            name,
            category,
            rarity=rarity,
            slot=slot,
            level_requirement=max(1, ilvl // 2),
        )
        item.ilvl = ilvl
        item.affixes = roll_affixes(category, ilvl, rarity.value)
        return item

    @staticmethod
    def generate_drop(ilvl, gr_level=0, quality=0.0):
        """Roll a dropped item; rarity improves with GR level + atlas quality."""
        # Shift the distribution toward higher rarities at higher GR levels.
        # Every boundary (including the unique floor) moves, so deeper rifts
        # reliably drop more rares and uniques. Atlas loot quality adds more.
        shift = min(0.45, gr_level * 0.004 + quality)
        common_cut = 0.55 - shift
        uncommon_cut = 0.83 - shift * 0.5
        unique_floor = 0.97 - shift * 0.3
        roll = random.random()
        if roll < common_cut:
            rarity = ItemRarity.COMMON
        elif roll < uncommon_cut:
            rarity = ItemRarity.UNCOMMON
        elif roll < unique_floor:
            rarity = ItemRarity.RARE
        else:
            rarity = ItemRarity.UNIQUE

        # Bias toward armor, then jewelry/weapon.
        category = random.choice(["armor", "armor", "jewelry", "weapon"])
        if category == "armor":
            slot = random.choice(list(ItemFactory.ARMOR_SLOTS.values()))
        elif category == "jewelry":
            slot = random.choice(list(ItemFactory.JEWELRY_SLOTS.values()))
        else:
            slot = ItemSlot.WEAPON_1H
        return ItemFactory.roll_item(slot, ilvl, rarity)

    @staticmethod
    def create_keystone(stack=1):
        """Create a Rift Keystone -- a stackable consumable (DESIGN.md Phase 5)."""
        item = Item(
            "rift_keystone",
            "Rift Keystone",
            "keystone",
            rarity=ItemRarity.RARE,
            slot=ItemSlot.CONSUMABLE,
            level_requirement=1,
        )
        item.stack = stack
        return item

    @staticmethod
    def create_random_item(level=1):
        """Create a random item appropriate for the player's level."""
        # Try synergistic items first (30% chance if level appropriate)
        if level >= 3 and random.random() < 0.3:
            try:
                from src.items.synergistic_items import SynergisticItemFactory
                item = SynergisticItemFactory.get_synergistic_item(level)
                if item:
                    return item
            except ImportError:
                pass  # Fall back to regular items
        
        # Rarity weighting
        rarity_roll = random.random()
        if rarity_roll < 0.60:
            rarity = ItemRarity.COMMON
        elif rarity_roll < 0.85:
            rarity = ItemRarity.UNCOMMON
        elif rarity_roll < 0.95:
            rarity = ItemRarity.RARE
        else:
            rarity = ItemRarity.UNIQUE
        
        # Item type
        item_type = random.choice(['weapon', 'armor', 'accessory'])
        
        if item_type == 'weapon':
            return ItemFactory.create_weapon(
                random.choice(['Sword', 'Staff', 'Wand', 'Dagger']),
                rarity, level
            )
        elif item_type == 'armor':
            return ItemFactory.create_armor(
                random.choice(['helmet', 'chest', 'legs', 'boots', 'gloves', 'belt']),
                rarity, level
            )
        else:
            return ItemFactory.create_accessory(
                random.choice(['ring', 'amulet']),
                rarity, level
            )
