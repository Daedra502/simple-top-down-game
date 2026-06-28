"""Synergistic item sets and specialized item creation."""
import random
from src.items.item import Item, ItemRarity, ItemSlot


class ItemSet:
    """A set of related items that synergize together."""
    
    def __init__(self, set_name, theme_description, set_bonus_effects):
        """
        Initialize an item set.
        
        Args:
            set_name: Name of the set
            theme_description: What this set is about
            set_bonus_effects: Dict of effects when wearing 2, 3, 4+ pieces
        """
        self.set_name = set_name
        self.theme_description = theme_description
        self.set_bonus_effects = set_bonus_effects
        self.items = []
    
    def add_item(self, item):
        """Add an item to this set."""
        item.set_name = self.set_name
        self.items.append(item)
    
    def get_set_bonus(self, pieces_equipped):
        """
        Get the bonus for equipping N pieces of this set.
        
        Args:
            pieces_equipped: Number of pieces equipped
            
        Returns:
            Dictionary of bonuses
        """
        if pieces_equipped >= 4:
            return self.set_bonus_effects.get(4, {})
        elif pieces_equipped == 3:
            return self.set_bonus_effects.get(3, {})
        elif pieces_equipped == 2:
            return self.set_bonus_effects.get(2, {})
        return {}


class SynergisticItemFactory:
    """Factory for creating thematic, synergistic item sets."""
    
    item_sets = {}
    
    @classmethod
    def create_all_sets(cls):
        """Create all item sets."""
        cls._create_fire_set()
        cls._create_cold_set()
        cls._create_lightning_set()
        cls._create_chaos_set()
        cls._create_balanced_set()
    
    @classmethod
    def _create_fire_set(cls):
        """Create Fire Mage set - focus on fire damage and casting speed."""
        
        fire_set = ItemSet(
            "Inferno's Blessing",
            "Fire-themed items focused on spell damage and casting speed",
            {
                2: {'fire_damage': 15, 'cast_speed': 0.1},
                3: {'fire_damage': 30, 'cast_speed': 0.2, 'elemental_damage': 10},
                4: {'fire_damage': 50, 'cast_speed': 0.35, 'mana': 50},
            }
        )
        
        # Inferno Staff (Weapon)
        staff = Item("inferno_staff", "Inferno Staff", "weapon", 
                    ItemRarity.RARE, ItemSlot.WEAPON_2H, level_requirement=5)
        staff.set_stat('damage', 30)
        staff.set_stat('elemental_damage', 15)
        staff.add_stat('attack_speed', 0.1)
        staff.add_stat('mana', 25)
        fire_set.add_item(staff)
        
        # Ember Crown (Head)
        crown = Item("ember_crown", "Ember Crown", "armor",
                    ItemRarity.RARE, ItemSlot.HEAD, level_requirement=5)
        crown.set_stat('health', 30)
        crown.set_stat('mana', 30)
        crown.add_stat('fire_damage', 10)
        fire_set.add_item(crown)
        
        # Flame Robes (Chest)
        robes = Item("flame_robes", "Flame Robes", "armor",
                    ItemRarity.RARE, ItemSlot.CHEST, level_requirement=5)
        robes.set_stat('health', 50)
        robes.set_stat('armor', 15)
        robes.add_stat('fire_damage', 15)
        robes.add_stat('mana', 20)
        fire_set.add_item(robes)
        
        # Heatwave Ring (Accessory)
        ring = Item("heatwave_ring", "Heatwave Ring", "accessory",
                   ItemRarity.RARE, ItemSlot.RING_1, level_requirement=5)
        ring.set_stat('damage', 10)
        ring.set_stat('mana', 20)
        ring.add_stat('fire_damage', 8)
        ring.add_stat('attack_speed', 0.05)
        fire_set.add_item(ring)
        
        cls.item_sets["Inferno's Blessing"] = fire_set
    
    @classmethod
    def _create_cold_set(cls):
        """Create Frost Mage set - focus on defense and crowd control."""
        
        cold_set = ItemSet(
            "Frozen Heart",
            "Cold-themed items focused on defense and crowd control",
            {
                2: {'armor': 20, 'health': 30},
                3: {'armor': 40, 'health': 60, 'cold_resistance': 20},
                4: {'armor': 60, 'health': 100, 'mana': 40},
            }
        )
        
        # Frostbrand Staff (Weapon)
        staff = Item("frostbrand_staff", "Frostbrand Staff", "weapon",
                    ItemRarity.RARE, ItemSlot.WEAPON_2H, level_requirement=5)
        staff.set_stat('damage', 25)
        staff.set_stat('armor', 10)
        staff.add_stat('mana', 30)
        cold_set.add_item(staff)
        
        # Glacial Crown (Head)
        crown = Item("glacial_crown", "Glacial Crown", "armor",
                    ItemRarity.RARE, ItemSlot.HEAD, level_requirement=5)
        crown.set_stat('health', 35)
        crown.set_stat('armor', 15)
        cold_set.add_item(crown)
        
        # Permafrost Coat (Chest)
        coat = Item("permafrost_coat", "Permafrost Coat", "armor",
                   ItemRarity.RARE, ItemSlot.CHEST, level_requirement=5)
        coat.set_stat('health', 60)
        coat.set_stat('armor', 25)
        coat.add_stat('mana', 15)
        cold_set.add_item(coat)
        
        # Winter's Embrace (Accessory)
        amulet = Item("winters_embrace", "Winter's Embrace", "accessory",
                     ItemRarity.RARE, ItemSlot.AMULET, level_requirement=5)
        amulet.set_stat('health', 25)
        amulet.set_stat('armor', 10)
        cold_set.add_item(amulet)
        
        cls.item_sets["Frozen Heart"] = cold_set
    
    @classmethod
    def _create_lightning_set(cls):
        """Create Storm Mage set - focus on attack speed and critical strikes."""
        
        lightning_set = ItemSet(
            "Storm's Fury",
            "Lightning-themed items focused on attack speed and critical strikes",
            {
                2: {'attack_speed': 0.15, 'damage': 15},
                3: {'attack_speed': 0.3, 'damage': 30, 'mana': 30},
                4: {'attack_speed': 0.5, 'damage': 50, 'health': 40},
            }
        )
        
        # Voltaic Wand (Weapon)
        wand = Item("voltaic_wand", "Voltaic Wand", "weapon",
                   ItemRarity.RARE, ItemSlot.WEAPON_1H, level_requirement=5)
        wand.set_stat('damage', 20)
        wand.add_stat('attack_speed', 0.15)
        wand.add_stat('mana', 25)
        lightning_set.add_item(wand)
        
        # Static Crown (Head)
        crown = Item("static_crown", "Static Crown", "armor",
                    ItemRarity.RARE, ItemSlot.HEAD, level_requirement=5)
        crown.set_stat('health', 25)
        crown.set_stat('mana', 25)
        crown.add_stat('attack_speed', 0.1)
        lightning_set.add_item(crown)
        
        # Shock Robes (Chest)
        robes = Item("shock_robes", "Shock Robes", "armor",
                    ItemRarity.RARE, ItemSlot.CHEST, level_requirement=5)
        robes.set_stat('health', 45)
        robes.set_stat('mana', 20)
        robes.add_stat('attack_speed', 0.15)
        lightning_set.add_item(robes)
        
        # Voltage Loop (Accessory)
        ring = Item("voltage_loop", "Voltage Loop", "accessory",
                   ItemRarity.RARE, ItemSlot.RING_2, level_requirement=5)
        ring.set_stat('damage', 12)
        ring.set_stat('mana', 15)
        ring.add_stat('attack_speed', 0.1)
        lightning_set.add_item(ring)
        
        cls.item_sets["Storm's Fury"] = lightning_set
    
    @classmethod
    def _create_chaos_set(cls):
        """Create Chaos set - focus on damage and unique effects."""
        
        chaos_set = ItemSet(
            "Void Walker",
            "Chaotic items focused on high damage and unique effects",
            {
                2: {'damage': 25, 'health': 25},
                3: {'damage': 50, 'health': 50, 'armor': 15},
                4: {'damage': 80, 'health': 80, 'mana': 50},
            }
        )
        
        # Void Staff (Weapon)
        staff = Item("void_staff", "Void Staff", "weapon",
                    ItemRarity.UNIQUE, ItemSlot.WEAPON_2H, level_requirement=7)
        staff.set_stat('damage', 35)
        staff.add_stat('health', 20)
        staff.add_stat('mana', 25)
        chaos_set.add_item(staff)
        
        # Nightmare Crown (Head)
        crown = Item("nightmare_crown", "Nightmare Crown", "armor",
                    ItemRarity.UNIQUE, ItemSlot.HEAD, level_requirement=7)
        crown.set_stat('health', 30)
        crown.set_stat('damage', 15)
        chaos_set.add_item(crown)
        
        # Abyss Cloak (Chest)
        cloak = Item("abyss_cloak", "Abyss Cloak", "armor",
                    ItemRarity.UNIQUE, ItemSlot.CHEST, level_requirement=7)
        cloak.set_stat('health', 55)
        cloak.set_stat('armor', 20)
        cloak.add_stat('damage', 20)
        chaos_set.add_item(cloak)
        
        # Chaos Signet (Accessory)
        ring = Item("chaos_signet", "Chaos Signet", "accessory",
                   ItemRarity.UNIQUE, ItemSlot.RING_1, level_requirement=7)
        ring.set_stat('damage', 15)
        ring.set_stat('health', 15)
        chaos_set.add_item(ring)
        
        cls.item_sets["Void Walker"] = chaos_set
    
    @classmethod
    def _create_balanced_set(cls):
        """Create Balanced set - good all-around stats."""
        
        balanced_set = ItemSet(
            "Wanderer's Blessing",
            "Balanced items with good stats for all situations",
            {
                2: {'health': 20, 'damage': 10},
                3: {'health': 40, 'damage': 20, 'armor': 10},
                4: {'health': 60, 'damage': 30, 'armor': 20, 'mana': 30},
            }
        )
        
        # Traveler's Staff (Weapon)
        staff = Item("travelers_staff", "Traveler's Staff", "weapon",
                    ItemRarity.RARE, ItemSlot.WEAPON_2H, level_requirement=3)
        staff.set_stat('damage', 22)
        staff.add_stat('health', 10)
        balanced_set.add_item(staff)
        
        # Scout's Hat (Head)
        hat = Item("scouts_hat", "Scout's Hat", "armor",
                  ItemRarity.RARE, ItemSlot.HEAD, level_requirement=3)
        hat.set_stat('health', 20)
        hat.add_stat('armor', 5)
        balanced_set.add_item(hat)
        
        # Wanderer's Tunic (Chest)
        tunic = Item("wanderers_tunic", "Wanderer's Tunic", "armor",
                    ItemRarity.RARE, ItemSlot.CHEST, level_requirement=3)
        tunic.set_stat('health', 40)
        tunic.set_stat('armor', 10)
        tunic.add_stat('damage', 8)
        balanced_set.add_item(tunic)
        
        # Adventurer's Ring (Accessory)
        ring = Item("adventurers_ring", "Adventurer's Ring", "accessory",
                   ItemRarity.RARE, ItemSlot.RING_1, level_requirement=3)
        ring.set_stat('health', 15)
        ring.set_stat('damage', 8)
        balanced_set.add_item(ring)
        
        cls.item_sets["Wanderer's Blessing"] = balanced_set
    
    @classmethod
    def get_set(cls, set_name):
        """Get an item set by name."""
        return cls.item_sets.get(set_name)
    
    @classmethod
    def get_all_sets(cls):
        """Get all item sets."""
        return list(cls.item_sets.values())
    
    @classmethod
    def get_set_items_for_slot(cls, set_name, equipment_slot):
        """Get items from a set for a specific equipment slot."""
        item_set = cls.get_set(set_name)
        if not item_set:
            return None
        
        for item in item_set.items:
            if item.slot == equipment_slot:
                return item
        return None
    
    @classmethod
    def create_random_from_set(cls, set_name, rarity=None):
        """
        Create a random item from a set.
        
        Args:
            set_name: Name of the set
            rarity: Optional specific rarity to use
            
        Returns:
            Random item from the set, or None if set not found
        """
        item_set = cls.get_set(set_name)
        if not item_set:
            return None
        
        item = random.choice(item_set.items)
        return item
    
    @classmethod
    def get_synergistic_item(cls, player_level, preferred_element=None):
        """
        Get a synergistic item appropriate for player level.
        
        Args:
            player_level: Current player level
            preferred_element: Optional preferred element (fire, cold, lightning, chaos)
            
        Returns:
            Random synergistic item
        """
        # Select set based on level and preference
        if player_level >= 7 and random.random() < 0.3:
            set_name = "Void Walker"
        elif player_level >= 5:
            sets = ["Inferno's Blessing", "Frozen Heart", "Storm's Fury"]
            if preferred_element == "fire":
                set_name = "Inferno's Blessing"
            elif preferred_element == "cold":
                set_name = "Frozen Heart"
            elif preferred_element == "lightning":
                set_name = "Storm's Fury"
            else:
                set_name = random.choice(sets)
        else:
            set_name = "Wanderer's Blessing"
        
        return cls.create_random_from_set(set_name)


# Initialize synergistic items on import
SynergisticItemFactory.create_all_sets()
