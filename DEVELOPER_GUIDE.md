# Developer Quick Reference: New Systems

## Using the Health Bar System

### Display Player Health & Mana
```python
# Already integrated in main.py:
self.player_ui = PlayerResourcesUI(10, 10, 300)  # (x, y, width)

# In update loop:
self.player_ui.update(self.player, 0.016)

# In draw loop:
self.player_ui.draw(screen, self.player)
```

### Display Enemy Health Bars
```python
# Create for each enemy:
enemy_health_bar = EnemyHealthBar(enemy, offset_y=-40)

# Update each frame:
enemy_health_bar.update(0.016)

# Draw:
enemy_health_bar.draw(screen)
```

### Create Floating Damage Numbers
```python
# Initialize manager:
self.damage_numbers = DamageNumberManager()

# Add on hit:
self.damage_numbers.add_damage(x, y, damage_amount, damage_type)
# damage_type options: "normal", "crit", "heal", "fire", "cold", "lightning"

# Update each frame:
self.damage_numbers.update(0.016)

# Draw:
self.damage_numbers.draw(screen)
```

---

## Using the Inventory System

### Initialize ItemManager
```python
from src.items.inventory import ItemManager

# In Game.__init__:
self.item_manager = ItemManager(self.player, capacity=20)
```

### Add Items to Inventory
```python
from src.items.item import ItemFactory

# Create random item:
item = ItemFactory.create_random_item(level=5)

# Add to inventory:
if self.item_manager.inventory.add_item(item):
    print("Item added successfully")
else:
    print("Inventory full!")
```

### Equip Items
```python
# Equip an item from inventory:
unequipped = self.item_manager.try_equip_item(item)
if unequipped:
    print(f"Unequipped: {unequipped.name}")

# Unequip an item:
from src.items.item import ItemSlot
if self.item_manager.try_unequip_item(ItemSlot.CHEST):
    print("Item unequipped")
```

### Get Total Player Stats
```python
# Get stats including equipment bonuses:
total_stats = self.item_manager.get_total_stats()
print(f"Total Damage: {total_stats['total_damage']}")
print(f"Total Attack Speed: {total_stats['total_attack_speed']}")
```

### Inventory UI
```python
# Toggle inventory display:
if event.key == pygame.K_i:
    self.show_inventory = not self.show_inventory

# Draw in main.py:
if self.show_inventory:
    self.draw_inventory_overlay()
```

---

## Creating Custom Items

### Create a Specific Weapon
```python
from src.items.item import ItemFactory, ItemRarity

sword = ItemFactory.create_weapon("Legendary Sword", ItemRarity.UNIQUE, level=10)
self.item_manager.inventory.add_item(sword)
```

### Create Custom Item from Scratch
```python
from src.items.item import Item, ItemRarity, ItemSlot

# Create item:
custom_item = Item(
    item_id="my_custom_item",
    name="Custom Armor",
    item_type="armor",
    rarity=ItemRarity.RARE,
    slot=ItemSlot.CHEST,
    level_requirement=5
)

# Add stats:
custom_item.set_stat('health', 50)
custom_item.set_stat('armor', 20)
custom_item.add_stat('health', 10)  # Add to existing value

# Add to inventory:
self.item_manager.inventory.add_item(custom_item)
```

### Create Item Factory for Specific Items
```python
class CustomItemFactory:
    @staticmethod
    def create_fire_staff():
        item = Item(
            "fire_staff",
            "Fire Staff",
            "weapon",
            ItemRarity.RARE,
            ItemSlot.WEAPON_2H,
            level_requirement=10
        )
        item.set_stat('damage', 25)
        item.set_stat('elemental_damage', 15)
        item.add_stat('attack_speed', 0.1)
        return item
```

---

## Item Rarity & Colors

```python
from src.items.item import ItemRarity

# Rarity levels:
ItemRarity.COMMON        # Gray
ItemRarity.UNCOMMON      # Green
ItemRarity.RARE          # Blue
ItemRarity.UNIQUE        # Orange

# Get item color:
color = item.get_color()  # Returns (R, G, B) tuple

# Display with rarity color:
text = font.render(item.name, True, item.get_color())
screen.blit(text, (x, y))
```

---

## Equipment Slots Reference

```python
from src.items.item import ItemSlot

# Available slots:
ItemSlot.WEAPON_2H      # Two-handed weapon
ItemSlot.WEAPON_1H      # One-handed weapon
ItemSlot.OFF_HAND       # Off-hand item
ItemSlot.HEAD           # Helmet
ItemSlot.CHEST          # Chest armor
ItemSlot.LEGS           # Leg armor
ItemSlot.FEET           # Boots
ItemSlot.HANDS          # Gloves
ItemSlot.BELT           # Belt
ItemSlot.RING_1         # First ring
ItemSlot.RING_2         # Second ring
ItemSlot.AMULET         # Amulet/necklace
```

---

## Event Integration Pattern

### Typical Damage Event
```python
# When enemy is hit:
damage = 25
enemy.take_damage(damage)

# Show damage:
self.damage_numbers.add_damage(enemy.x, enemy.y - 20, damage, 'normal')

# Crit hit:
if is_crit:
    self.damage_numbers.add_damage(enemy.x, enemy.y - 20, damage * 1.5, 'crit')
```

### Typical Item Drop Event
```python
# When enemy dies:
def on_enemy_death(enemy):
    # Generate loot:
    item = ItemFactory.create_random_item(level=self.player.level)
    
    # Add to inventory:
    self.item_manager.inventory.add_item(item)
    
    # Show notification:
    print(f"Dropped: {item.name} ({item.rarity.name})")
```

---

## Performance Tips

### Health Bars
- Create once and reuse
- Only update if entity health changed
- Store display_value for smooth animation

### Damage Numbers
- Use object pooling for frequently created objects
- Store in array and update all at once
- Remove from array when done

### Inventory
- Sort only when needed
- Cache equipped stat bonuses
- Update character stats only when equipment changes

---

## Debugging

### Check if Inventory is Working
```python
# Print inventory contents:
for item in self.item_manager.inventory.items:
    print(f"- {item.name} ({item.rarity.name})")

# Print equipped items:
for slot, item in self.item_manager.equipment.equipment.items():
    if item:
        print(f"{slot}: {item.name}")

# Print total stats:
stats = self.item_manager.get_total_stats()
print(f"Total stats: {stats}")
```

### Check Health Bars
```python
# Verify health bar values:
bar = self.player_ui.health_bar
print(f"Health: {bar.current_value}/{bar.max_value}")

# Check enemy bar:
enemy_bar = self.enemy_health_bars[enemy]
print(f"Enemy health: {enemy_bar.bar.current_value}")
```

### Check Damage Numbers
```python
# Count active damage numbers:
print(f"Active damage numbers: {len(self.damage_numbers.numbers)}")

# Check oldest number:
if self.damage_numbers.numbers:
    print(f"Oldest number age: {self.damage_numbers.numbers[0].age}")
```

---

## Common Issues & Solutions

### Issue: Health bars not showing
**Solution**: Ensure update() is called before draw()
```python
# In update():
self.player_ui.update(self.player, 0.016)

# In draw():
self.player_ui.draw(screen, self.player)
```

### Issue: Inventory full error
**Solution**: Increase capacity or check before adding
```python
# Increase capacity:
self.item_manager = ItemManager(self.player, capacity=30)

# Or check:
if not self.item_manager.inventory.is_full():
    self.item_manager.inventory.add_item(item)
```

### Issue: Equipment bonuses not applying
**Solution**: Apply equipment bonuses after equipping
```python
# After equipping item:
self.item_manager.try_equip_item(item)
self.item_manager.apply_equipment_bonuses()  # Apply stats
```

### Issue: Damage numbers disappearing too fast
**Solution**: Adjust lifetime in DamageNumber class
```python
# In src/ui/health_bars.py DamageNumber.__init__:
self.lifetime = 1.5  # Increase from 1.0
```

---

## Extending the Systems

### Custom Health Bar Color
```python
# Create colored bars for different entity types:
player_bar = HealthBar(x, y, 100, 20, max_health, (50, 200, 50))  # Green
boss_bar = HealthBar(x, y, 100, 20, max_health, (255, 0, 0))  # Red
elite_bar = HealthBar(x, y, 100, 20, max_health, (255, 150, 0))  # Orange
```

### Custom Item Type
```python
# Add new item type to ItemSlot enum:
class ItemSlot(Enum):
    WEAPON_2H = "2h_weapon"
    CONSUMABLE = "consumable"
    QUEST_ITEM = "quest_item"  # NEW
```

### Custom Rarity
```python
# Add new rarity tier:
class ItemRarity(Enum):
    COMMON = 0
    UNIQUE = 3
    LEGENDARY = 4  # NEW
```

---

**Last Updated**: Session 1
**Version**: 1.0
