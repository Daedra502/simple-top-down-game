"""Inventory system for managing player items."""
from src.items.item import ItemSlot


class InventorySlot:
    """A single slot in the inventory."""
    
    def __init__(self, x, y, width=50, height=50):
        """
        Initialize an inventory slot.
        
        Args:
            x, y: Visual position
            width, height: Dimensions of the slot
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.item = None
    
    def set_item(self, item):
        """Place an item in this slot."""
        self.item = item
    
    def get_item(self):
        """Get the item in this slot."""
        return self.item
    
    def clear(self):
        """Remove the item from this slot."""
        self.item = None
    
    def contains_point(self, x, y):
        """Check if a point is inside this slot."""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)


class Inventory:
    """Player inventory system."""
    
    def __init__(self, capacity=20, grid_cols=5):
        """
        Initialize inventory.
        
        Args:
            capacity: Maximum number of items
            grid_cols: Number of columns in grid layout
        """
        self.capacity = capacity
        self.grid_cols = grid_cols
        self.grid_rows = (capacity + grid_cols - 1) // grid_cols
        self.slots = []
        self.items = []
        
        # Create grid of slots (visual layout)
        self._create_grid()
    
    def _create_grid(self):
        """Create the inventory grid layout."""
        slot_width = 50
        slot_height = 50
        padding = 5
        
        for i in range(self.capacity):
            row = i // self.grid_cols
            col = i % self.grid_cols
            x = col * (slot_width + padding) + padding
            y = row * (slot_height + padding) + padding
            self.slots.append(InventorySlot(x, y, slot_width, slot_height))
    
    def add_item(self, item):
        """
        Add an item to the inventory.
        
        Returns:
            True if successful, False if inventory is full
        """
        if len(self.items) >= self.capacity:
            return False
        
        self.items.append(item)
        self._update_slot_positions()
        return True
    
    def remove_item(self, item):
        """
        Remove an item from the inventory.
        
        Returns:
            True if successful, False if item not found
        """
        if item in self.items:
            self.items.remove(item)
            self._update_slot_positions()
            return True
        return False
    
    def _update_slot_positions(self):
        """Update which items are in which slots based on item list."""
        for i, item in enumerate(self.items):
            if i < len(self.slots):
                self.slots[i].set_item(item)
        
        # Clear remaining slots
        for i in range(len(self.items), len(self.slots)):
            self.slots[i].clear()
    
    def get_item_at_position(self, x, y):
        """Find item at a given position (returns None if not found)."""
        for slot in self.slots:
            if slot.contains_point(x, y) and slot.item:
                return slot.item
        return None
    
    def get_empty_slot(self):
        """Get the first empty inventory slot."""
        for slot in self.slots:
            if slot.item is None:
                return slot
        return None
    
    def is_full(self):
        """Check if inventory is full."""
        return len(self.items) >= self.capacity
    
    def get_items_of_type(self, item_type):
        """Get all items of a specific type."""
        return [item for item in self.items if item.item_type == item_type]
    
    def get_items_for_slot(self, equipment_slot):
        """Get all items that can equip in a specific equipment slot."""
        return [item for item in self.items if item.slot == equipment_slot]
    
    def sort_by_rarity(self):
        """Sort inventory by item rarity (highest first)."""
        self.items.sort(key=lambda x: x.rarity.value, reverse=True)
        self._update_slot_positions()
    
    def sort_by_type(self):
        """Sort inventory by item type."""
        self.items.sort(key=lambda x: x.item_type)
        self._update_slot_positions()


class EquipmentSlots:
    """Manages equipped items."""
    
    def __init__(self):
        """Initialize equipment slots."""
        self.equipment = {
            ItemSlot.WEAPON_1H: None,
            ItemSlot.WEAPON_1H_OFF: None,   # optional secondary weapon (dual wield)
            ItemSlot.WEAPON_2H: None,
            ItemSlot.OFF_HAND: None,
            ItemSlot.HEAD: None,
            ItemSlot.CHEST: None,
            ItemSlot.LEGS: None,
            ItemSlot.FEET: None,
            ItemSlot.HANDS: None,
            ItemSlot.BELT: None,
            ItemSlot.RING_1: None,
            ItemSlot.RING_2: None,
            ItemSlot.AMULET: None,
        }
    
    def equip_item(self, item):
        """
        Equip an item.
        
        Returns:
            Unequipped item if something was replaced, None otherwise
        """
        if item.slot not in self.equipment:
            return None
        
        unequipped = self.equipment[item.slot]
        self.equipment[item.slot] = item
        return unequipped
    
    def equip_item_to_slot(self, item, slot):
        """Equip an item into an explicit slot (e.g. routing a second 1H weapon
        into the off-hand weapon slot). Returns whatever was displaced, if any."""
        if slot not in self.equipment:
            return None
        unequipped = self.equipment[slot]
        self.equipment[slot] = item
        return unequipped

    def unequip_item(self, slot):
        """
        Unequip an item from a slot.

        Returns:
            The unequipped item, or None if slot was empty
        """
        if slot not in self.equipment:
            return None
        
        item = self.equipment[slot]
        self.equipment[slot] = None
        return item
    
    def get_equipped_item(self, slot):
        """Get the item equipped in a slot."""
        return self.equipment.get(slot)
    
    def get_all_equipped_items(self):
        """Get all equipped items."""
        return [item for item in self.equipment.values() if item is not None]
    
    def get_stat_bonuses(self):
        """Calculate total stat bonuses from equipped items."""
        bonuses = {
            'health': 0,
            'mana': 0,
            'damage': 0,
            'attack_speed': 0.0,
            'armor': 0,
            'elemental_damage': 0,
        }
        
        for item in self.get_all_equipped_items():
            for stat, value in item.stats.items():
                if stat != 'resistances' and stat in bonuses:
                    bonuses[stat] += value
        
        return bonuses
    
    def get_resistances(self):
        """Get total resistances from equipped items."""
        resistances = {}
        
        for item in self.get_all_equipped_items():
            for resistance, value in item.stats.get('resistances', {}).items():
                if resistance not in resistances:
                    resistances[resistance] = 0
                resistances[resistance] += value
        
        return resistances


class ItemManager:
    """Manages inventory and equipment for the player."""
    
    def __init__(self, player, capacity=20):
        """
        Initialize item manager.
        
        Args:
            player: The player entity
            capacity: Inventory capacity
        """
        from src.items.set_bonuses import SetBonusTracker
        
        self.player = player
        self.inventory = Inventory(capacity=capacity)
        self.equipment = EquipmentSlots()
        self.set_bonus_tracker = SetBonusTracker()
        self.active_set_bonuses = {}  # Current set bonuses applied
    
    def try_equip_item(self, item):
        """
        Try to equip an item.
        
        Returns:
            Item that was unequipped (if any), or None
        """
        if self.inventory.remove_item(item):
            unequipped = self.equipment.equip_item(item)
            if unequipped:
                self.inventory.add_item(unequipped)
            return unequipped
        return None
    
    def try_equip_item_to_slot(self, item, slot):
        """Equip ``item`` into a specific equipment ``slot`` (used for the
        optional secondary weapon). Any displaced item returns to the backpack.
        """
        if self.inventory.remove_item(item):
            unequipped = self.equipment.equip_item_to_slot(item, slot)
            if unequipped:
                self.inventory.add_item(unequipped)
            return unequipped
        return None

    def try_unequip_item(self, slot):
        """
        Try to unequip an item.
        
        Returns:
            True if successful
        """
        item = self.equipment.unequip_item(slot)
        if item:
            return self.inventory.add_item(item)
        return False
    
    def apply_equipment_bonuses(self):
        """Apply equipment bonuses to the player."""
        bonuses = self.equipment.get_stat_bonuses()

        # Apply stat bonuses
        self.player.health += bonuses['health']
        self.player.max_health += bonuses['health']
        self.player.mana += bonuses['mana']
        self.player.max_mana += bonuses['mana']
        self.player.damage += bonuses['damage']
        self.player.attack_speed += bonuses['attack_speed']

    # --- Stats-layer adapters (DESIGN.md Phase 2/6): map item stat shape onto
    # the player's central Stats keys so gear funnels through one source of truth.
    # Spell-damage % stats are summed separately (see get_spell_damage_bonuses)
    # and fed into the player's spell-damage pipeline, not the core Stats layer.
    SPELL_DAMAGE_STATS = {
        'spell_damage', 'fire_damage', 'cold_damage', 'lightning_damage',
        'physical_damage', 'chaos_damage', 'fireball_damage', 'frostbolt_damage',
    }

    def get_gear_stats(self):
        """Core Stats contribution from equipped items (legacy stats + affixes),
        each scaled by the item's upgrade multiplier."""
        from src.items.affixes import is_resistance_stat
        key_map = {'health': 'max_health', 'mana': 'max_mana', 'damage': 'damage',
                   'attack_speed': 'attack_speed', 'armor': 'armor'}
        gear = {}
        for item in self.equipment.get_all_equipped_items():
            mult = item.upgrade_multiplier() if hasattr(item, 'upgrade_multiplier') else 1.0
            for stat, value in item.stats.items():
                mapped = key_map.get(stat)
                if mapped and value:
                    gear[mapped] = gear.get(mapped, 0) + value * mult
            for af in getattr(item, 'affixes', []):
                stat = af['stat']
                if is_resistance_stat(stat) or stat in self.SPELL_DAMAGE_STATS:
                    continue
                gear[stat] = gear.get(stat, 0) + af['value'] * mult
        return gear

    def get_spell_damage_bonuses(self):
        """Sum gear "increased damage" % affixes (spell/element/skill), scaled by
        each item's upgrade level. Returned as percent points to match the tree."""
        out = {}
        for item in self.equipment.get_all_equipped_items():
            mult = item.upgrade_multiplier() if hasattr(item, 'upgrade_multiplier') else 1.0
            for af in getattr(item, 'affixes', []):
                if af['stat'] in self.SPELL_DAMAGE_STATS:
                    out[af['stat']] = out.get(af['stat'], 0) + af['value'] * mult
            # Legacy "elemental damage" on crafted weapons counts as % spell damage.
            elem = item.stats.get('elemental_damage', 0)
            if elem:
                out['spell_damage'] = out.get('spell_damage', 0) + elem * mult
        return out

    def get_resistances(self, cap=75):
        """Total elemental + physical resistances from gear, capped (Phase 6)."""
        from src.items.affixes import is_resistance_stat, resistance_element
        res = dict(self.equipment.get_resistances())  # legacy item.stats resists
        for item in self.equipment.get_all_equipped_items():
            mult = item.upgrade_multiplier() if hasattr(item, 'upgrade_multiplier') else 1.0
            for af in getattr(item, 'affixes', []):
                if is_resistance_stat(af['stat']):
                    elem = resistance_element(af['stat'])
                    res[elem] = res.get(elem, 0) + af['value'] * mult
        return {k: min(cap, v) for k, v in res.items()}

    def upgrade_item(self, item):
        """Spend wallet money to add one upgrade level (max 20). Returns True if
        the upgrade was purchased."""
        if not item.can_upgrade():
            return False
        if not self.player.spend_money(item.upgrade_cost()):
            return False
        item.upgrade_level += 1
        return True

    # --- Rift keystones (DESIGN.md Phase 5): stackable consumables in inventory.
    def _find_keystone(self):
        for item in self.inventory.items:
            if getattr(item, "item_id", None) == "rift_keystone":
                return item
        return None

    def keystone_count(self):
        ks = self._find_keystone()
        return getattr(ks, "stack", 0) if ks else 0

    def add_keystone(self, amount=1):
        ks = self._find_keystone()
        if ks is not None:
            ks.stack = getattr(ks, "stack", 1) + amount
        else:
            from src.items.item import ItemFactory
            self.inventory.add_item(ItemFactory.create_keystone(amount))

    def consume_keystone(self):
        """Spend one keystone. Returns True if one was available."""
        ks = self._find_keystone()
        if ks is None or getattr(ks, "stack", 0) <= 0:
            return False
        ks.stack -= 1
        if ks.stack <= 0:
            self.inventory.remove_item(ks)
        return True

    def get_set_stats(self):
        """Active set-bonus contribution, as a Stats layer dict."""
        set_bonuses = self.update_set_bonuses()
        totals = self.set_bonus_tracker.calculator.get_total_bonuses(set_bonuses)
        out = {}
        key_map = {
            'health': 'max_health', 'max_health': 'max_health',
            'mana': 'max_mana', 'max_mana': 'max_mana',
            'damage': 'damage', 'attack_speed': 'attack_speed', 'armor': 'armor',
        }
        for key, value in totals.items():
            mapped = key_map.get(key)
            if mapped and not isinstance(value, dict):
                out[mapped] = out.get(mapped, 0) + value
        return out
    
    def get_total_stats(self):
        """Get player's total stats including equipment."""
        stats = {
            'health': self.player.health,
            'max_health': self.player.max_health,
            'mana': self.player.mana,
            'max_mana': self.player.max_mana,
            'damage': self.player.damage,
            'attack_speed': self.player.attack_speed,
        }
        
        bonuses = self.equipment.get_stat_bonuses()
        stats['total_damage'] = stats['damage'] + bonuses['damage']
        stats['total_attack_speed'] = stats['attack_speed'] + bonuses['attack_speed']
        
        return stats
    
    def update_set_bonuses(self):
        """Recalculate and update set bonuses from current equipment."""
        equipped_items = self.equipment.get_all_equipped_items()
        self.active_set_bonuses = self.set_bonus_tracker.update(equipped_items)
        return self.active_set_bonuses
    
    def get_active_set_bonuses(self):
        """Get current active set bonuses."""
        return self.active_set_bonuses.copy()
    
    def get_set_bonus_summary(self):
        """Get a summary of active sets for display."""
        self.update_set_bonuses()
        return self.set_bonus_tracker.get_summary()
    
    def apply_set_bonuses_to_player(self):
        """Apply calculated set bonuses to player stats."""
        # Calculate set bonuses first
        set_bonuses = self.update_set_bonuses()
        
        # Apply bonuses to player
        self.set_bonus_tracker.calculator.apply_set_bonuses_to_player(self.player, set_bonuses)
