# Top-Down ARPG Game Framework - Project Instructions

## Project Overview
An extensible top-down action RPG game framework built with Python and Pygame. Features player character with leveling system (max level 50), 8 enemy types with varied rewards, 4-tier currency system, wand upgrades, skill tree with 11+ nodes and 4 keystones, 8 maps with treasure chests, 5 item sets with bonuses, and dynamic combat mechanics.

## Current Version (Phase 4 Tasks 1-2 Complete)

### NEW in Phase 4: Keystone Mechanics ✅
- 4 keystones at end of skill tree branches
- **Elemental Focus** (Fire): +30% spell damage, +20 mana, cleanse status
- **Spell Echo** (Mana): Cast twice, -0.2 cooldown, +0.15 attack speed, +50 mana
- **Omnivamp** (Damage): 20% lifesteal, 1.25x multiplier, +100 health, +15 damage
- **Projectile Mastery** (Hybrid): +2 chain, +2 pierce, +25 damage, +0.1 attack speed
- Each keystones tracked and applied per frame
- Virtual `apply_to_player()` pattern for extensibility

### NEW in Phase 4: Set Bonus System ✅
- 5 synergistic item sets with 2pc/3pc/4pc bonuses
- **Inferno's Blessing** (Fire): Fire damage focus
- **Frozen Heart** (Cold): Cold damage focus
- **Storm's Fury** (Lightning): Lightning damage focus
- **Void Walker** (Chaos): Chaos damage focus
- **Wanderer's Blessing** (Balanced): Mixed bonuses
- SetBonusCalculator tracks equipped items and applies bonuses
- Bonuses displayed in character sheet UI (C key)
- Applied every frame in game loop

### Leveling & Progression
- Player level system (max level 50)
- 1 skill point awarded per level
- XP gained from enemies and treasure chests
- Stats increase on level up (health +10, mana +5)
- Skill tree now 28+ nodes with 5 branches + 4 keystones

### Currency System
- 4-tier: Copper → Silver (10:1) → Gold (10:1) → Diamond (10:1)
- No wallet limit, auto-normalizes to larger denominations
- Each enemy type rewards different money amounts
- Money displayed in UI with symbols

### Enemy Types (8 Total)
1. **Goblin** - 20 HP, 3 DMG, 25 XP, 5 Copper
2. **Orc** - 50 HP, 8 DMG, 50 XP, 1 Silver
3. **Necromancer** - 40 HP, 6 DMG, 60 XP, 5 Copper + 1 Silver
4. **Skeleton** - 30 HP, 5 DMG, 35 XP, 8 Copper
5. **Demon** - 80 HP, 12 DMG, 100 XP, 2 Silver + 1 Gold
6. **Dragon** - 150 HP, 20 DMG, 200 XP, 3 Gold + 1 Diamond
7. **Vampire** - 60 HP, 10 DMG, 90 XP, 3 Silver
8. **Lich** - 100 HP, 15 DMG, 150 XP, 1 Silver + 2 Gold

### Skill Tree System
- 28+ skill nodes with prerequisites organized in 5 branches
- **Branches**: Fire, Cold, Lightning, Speed, Mana/Support
- **Damage Nodes**: Increase spell damage (5-10 per node)
- **Speed Nodes**: Increase attack speed (0.1-0.25 multiplier)
- **Effect Nodes**: Add special effects to spells
- **Stat Nodes**: Increase max health (25) or max mana (30)
- **Keystone Nodes** (4): Major game-changing abilities at branch ends
- Keystones tracked via `skill_tree.get_active_keystones()` and `has_keystone()`
- Open with **T** key

### Wand Upgrade System
- Upgrade wand with copper currency
- Each level increases spell damage
- Damage bonus is multiplicative or additive (whichever is larger)
- Cost increases per level (starting at ~100 copper)

### Item Set Bonuses (NEW Phase 4)
- Each item has a `set_name` attribute
- ItemManager tracks equipped items via `SetBonusCalculator`
- Bonuses applied when 2+ pieces of same set equipped
- 2pc/3pc/4pc tiers provide increasing bonuses
- Display in character sheet (C key) shows:
  - Set progress (X/4 pieces)
  - Active bonus values
- Bonuses applied every frame to player stats

### Treasure Chests
- Each map has 2-3 treasure chests
- Auto-open when player approaches (within 40 units)
- Contain mix of copper, silver, gold, diamond, and XP
- Darker color when opened

### Map System (8 Maps Total)
1. **Whispering Forest** - 8 enemies (Goblins, Orcs), 2 chests
2. **Dark Caverns** - 10 enemies (Orcs, Necromancers), 2 chests
3. **Ancient Necropolis** - 12 enemies (Necromancers), 2 chests
4. **Skeleton Pit** - 14 enemies (Skeletons), 3 chests
5. **Demon Realm** - 12 enemies (Demons, Vampires), 2 chests
6. **Dragon Lair** - 8 enemies (Dragons, Demons), 2 chests
7. **Lich Tomb** - 10 enemies (Liches, Dragons, Vampires), 3 chests
8. **Shadow Abyss** - 15 enemies (All types), 3 chests

### Attack Speed System
- `player.attack_speed` - multiplier for cooldown reduction
- Increases from skill tree nodes
- Applied formula: `int(cooldown / attack_speed)`
- Faster casting with higher attack speed

## Game Controls

- **WASD**: Move character
- **Mouse Click**: Cast spell at cursor
- **1-3**: Switch between skills
- **T**: Open skill tree overlay
- **Space**: Pause/Resume
- **ESC**: Quit game

## Core Game Systems

### Player Stats & Resources
- Health (scales with level)
- Mana (scales with level)
- Experience (XP to next level)
- Skill Points (1 per level up)
- Wallet (Copper, Silver, Gold, Diamond)
- Wand Level (damage multiplier)

### Combat Mechanics
- Projectile-based spell system
- 3 spell types: Fireball, Frost Bolt, Lightning Strike
- Mana consumption per spell
- Cooldown system with attack speed modifier
- Collision detection with circle-circle algorithm

### Progression Path
- Level up → Gain skill points
- Allocate skill points to skill tree nodes
- Unlock damage bonuses and attack speed
- Collect money from enemies and chests
- Upgrade wand with money for more damage
- Progress through 8 maps to win

## Customization Guide

### Adjust Enemy Stats
Edit `src/entities/enemy.py` in the `__init__` method:
```python
self.max_health = 50      # Change HP
self.damage = 8           # Change damage
self.speed = 1.5          # Change movement speed
self.experience_reward = 50
self.money_reward = {'copper': 0, 'silver': 1, 'gold': 0, 'diamond': 0}
```

### Modify Skill Tree Nodes
Edit `src/spells/skill_tree.py` in `_initialize_tree()`:
```python
self.add_node(
    "node_id", "Name", "Description",
    {"damage_modifier": 10},  # Effects dictionary
    x, y                      # Position for visual layout
)
```

### Change Chest Rewards
Edit `src/maps/map_manager.py` when creating Map:
```python
Chest(x, y, copper=50, silver=1, gold=0, diamond=0, xp=100)
```

### Adjust Wand Upgrade Cost
In `src/entities/player.py` `upgrade_wand()` method:
```python
def upgrade_wand(self, cost_copper=100):  # Change default cost
```

### Modify Attack Speed Calculation
In `src/entities/player.py` `cast_skill()` method:
```python
cooldowns = {0: 30, 1: 25, 2: 35}
self.skill_cooldowns[skill_id] = max(5, int(cooldowns[skill_id] / self.attack_speed))
```

## File Locations

### Key Files
- `main.py` - Game loop and rendering
- `src/entities/player.py` - Player with leveling & wallet
- `src/entities/enemy.py` - 8 enemy types
- `src/entities/chest.py` - Treasure chest system
- `src/spells/spells.py` - Spell definitions
- `src/spells/skill_tree.py` - 11 skill tree nodes
- `src/maps/map_manager.py` - 8 maps with chests
- `src/systems/combat.py` - Damage and collision
- `src/systems/collision.py` - Distance calculations

### Config Files
- `requirements.txt` - Dependencies (pygame, numpy)
- `README.md` - Full documentation
- `.github/copilot-instructions.md` - This file

## Performance Notes

- Game runs at 60 FPS by default
- Map size: 1200x800 pixels
- Max 15 enemies per map
- Collision detection: O(n*m) where n=enemies, m=projectiles

## Troubleshooting

### Dependencies Error
```bash
pip install -r requirements.txt
```

### Slow Performance
Lower FPS in `main.py`: `self.fps = 30`

### Import Errors
Ensure `src/` folder contains `__init__.py` files

## Future Development Ideas

- [ ] Procedural map generation
- [ ] Boss encounters with unique mechanics
- [ ] Sound effects and music system
- [ ] Particle effects for spells
- [ ] Item drops and rarity system
- [ ] Character stat allocation screen
- [ ] Difficulty levels
- [ ] Multiplayer networking
- [ ] Additional skill tree branches
- [ ] Quest system

## Questions or Issues?

Refer to `README.md` for detailed documentation and game mechanics explanations.
