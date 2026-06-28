# Top-Down ARPG Game Framework

A simple but extensible top-down action RPG game framework built with Python and Pygame, inspired by games like Path of Exile and Diablo.

## Features

- **Player Character**: Controllable protagonist with health, mana, and skill system
- **Leveling System**: Max level 50 with skill points (1 per level)
- **Currency System**: 4-tier currency (Copper, Silver, Gold, Diamond)
- **Wand Upgrades**: Increase spell damage with money
- **Multiple Skills**: 
  - **Fireball** (Q1): High damage, medium cooldown
  - **Frost Bolt** (Q2): Medium damage, fast casting
  - **Lightning Strike** (Q3): High damage, high cooldown
- **Enemy AI**: 8 enemy types with intelligent behavior and unique rewards
  - Original: Goblins, Orcs, Necromancers
  - New: Skeletons, Demons, Dragons, Vampires, Liches
- **Multiple Maps**: Progress through 8 unique maps with increasing difficulty
- **Chests**: Treasure chests with money and XP rewards on each map
- **Combat System**: Projectile-based spell casting with collision detection
- **Skill Tree**: 11 skill nodes for damage, attack speed, and special effects
- **Attack Speed**: Increase spell casting speed from skill tree
- **Map Progression**: Defeat all enemies and reach the exit to progress to the next map
- **Experience System**: Gain experience from defeating enemies and opening chests

## Installation

1. **Install Python 3.8+** from [python.org](https://www.python.org/)

2. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

## How to Play

1. **Run the Game**:
```bash
python main.py
```

2. **Controls**:
   - **WASD**: Move your character
   - **Mouse Click**: Cast your current spell at the cursor location
   - **1-3**: Switch between skills
   - **T**: Open skill tree
   - **Space**: Pause/Resume
   - **ESC**: Quit game

3. **Objective**:
   - Defeat all enemies on the map
   - Open chests to collect money and XP
   - Reach the blue exit zone (bottom-right corner)
   - Progress through all 8 maps to win the game

## Game Features in Detail

### Leveling System (Max Level 50)
- Gain XP from defeating enemies and opening chests
- Receive 1 skill point per level
- Stats increase on level up (+10 health, +5 mana per level)
- XP requirement scales with level

### Currency & Wallet
- **Copper**: Base currency
- **Silver**: 10 Copper = 1 Silver
- **Gold**: 10 Silver = 1 Gold
- **Diamond**: 10 Gold = 1 Diamond
- No wallet limit, auto-normalizes larger denominations
- Earn money from enemy kills and chests

### Wand System
- Upgrade your wand with money to increase spell damage
- Wand level increases by 1 per upgrade
- Damage bonus is applied multiplicatively or additively (whichever is larger)

### Skill Tree
- **11 unique skill nodes** with prerequisites
- **Damage Nodes**: Increase Fireball, Frost Bolt, or Lightning damage
- **Speed Nodes**: Increase attack speed (faster spell cooldowns)
- **Effect Nodes**: Add special effects to spells (burn, freeze, chain)
- **Stat Nodes**: Increase max health or max mana
- Press **T** to view the skill tree

### Enemy Types & Rewards
| Enemy | Level Range | XP | Money |
|-------|------------|-----|-------|
| Goblin | 1+ | 25 XP | 5 Copper |
| Orc | 1+ | 50 XP | 1 Silver |
| Necromancer | 1+ | 60 XP | 5 Copper + 1 Silver |
| Skeleton | 4+ | 35 XP | 8 Copper |
| Demon | 5+ | 100 XP | 2 Silver + 1 Gold |
| Dragon | 6+ | 200 XP | 3 Gold + 1 Diamond |
| Vampire | 5+ | 90 XP | 3 Silver |
| Lich | 6+ | 150 XP | 1 Silver + 2 Gold |

### Maps & Progression
1. **Whispering Forest** - 8 Goblins/Orcs
2. **Dark Caverns** - 10 Orcs/Necromancers
3. **Ancient Necropolis** - 12 Necromancers
4. **Skeleton Pit** - 14 Skeletons/Necromancers
5. **Demon Realm** - 12 Demons/Vampires
6. **Dragon Lair** - 8 Dragons/Demons
7. **Lich Tomb** - 10 Liches/Dragons/Vampires
8. **Shadow Abyss** - 15 Liches/Demons/Dragons

Each map contains 2-3 treasure chests with rewards.

## Project Structure

```
simple top down game/
├── main.py                 # Main game loop and entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .github/
│   └── copilot-instructions.md
└── src/
    ├── __init__.py
    ├── entities/          # Game entities
    │   ├── player.py      # Player with leveling and wallet
    │   ├── enemy.py       # 8 enemy types with AI
    │   └── chest.py       # Chest/treasure system
    ├── systems/           # Core game systems
    │   ├── combat.py      # Combat mechanics
    │   └── collision.py   # Collision detection
    ├── spells/            # Spell system
    │   ├── spells.py      # Spell definitions
    │   └── skill_tree.py  # Skill tree with 11 nodes
    └── maps/              # Level management
        └── map_manager.py # 8 maps with chests
```

## Extending the Game

### Adding New Spells
Edit `src/spells/spells.py` to create new spell classes inheriting from `Spell` base class.

### Adding New Enemy Types
Edit `src/entities/enemy.py` to add new enemy types and behaviors.

### Adding New Skill Tree Nodes
Edit `src/spells/skill_tree.py` to add new nodes in `_initialize_tree()`.

### Customizing Player Stats
Modify values in `Player.__init__()` in `src/entities/player.py`:
- `max_health`: Player health points
- `max_mana`: Mana for spells
- `damage`: Base damage output
- `speed`: Movement speed
- `attack_speed`: Multiplier for cooldown reduction

## Tips & Tricks

- **Money Management**: Save money for wand upgrades to boost damage
- **Skill Tree Strategy**: Prioritize damage nodes early, then attack speed
- **Enemy Strategy**: Focus on weaker enemies first, save strong ones for later
- **Chest Hunting**: Explore all areas to find treasure chests
- **Level Grinding**: Kill enemies on earlier maps for safe XP gains

## Troubleshooting

### "Module not found" errors
Run: `pip install -r requirements.txt`

### Game runs slowly
Lower FPS value in `main.py`: change `self.fps = 60` to a lower value (e.g., 30)

### Pygame not installing
Try: `pip install --upgrade pygame`

## Performance Notes

- The game runs at 60 FPS by default
- Map size is 1200x800 pixels
- Maximum 15 enemies per map
- Collision detection is O(n*m) where n=enemies, m=projectiles

## Future Enhancement Ideas

- [ ] Sound effects and background music
- [ ] Character leveling and stat allocation
- [ ] Boss encounters with unique mechanics
- [ ] Procedural map generation
- [ ] Item drops and equipment rarity
- [ ] Multiplayer networking
- [ ] Particle effects for spells
- [ ] Difficulty levels
- [ ] New skill tree branches

## License

This project is open-source and free to use for educational purposes.
