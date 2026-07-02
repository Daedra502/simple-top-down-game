# Top-Down ARPG Game Framework

A simple but extensible top-down action RPG game framework built with Python and Pygame, inspired by games like Path of Exile and Diablo.

## Features

- **Player Character**: Controllable protagonist with health, mana, and skill system
- **Leveling System**: Max level 100 with skill points (1 per level)
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
- **Chests**: Treasure chests spawn periodically as you explore, rewarding money, XP and equipment loot
- **Map Obstacles**: Solid cover (rocks, pillars, crystals) to path around and bramble hazards to avoid
- **Bounty Board**: Accept rotating contracts (cull enemy families, hunt elites, crack chests, slay bosses) at the town board for gold, loot and rift keystones
- **Ritual Circles**: Field channel events -- hold your ground inside the circle while waves press in to claim the hoard
- **Rustic Town + Atmosphere**: Embervale village hub (plaza, well, blacksmith, market, portal) and a moody per-layout ambient/vignette pass over the rift
- **Procedural Audio**: A music engine with choir, strings, FM bells, sub-drones and war-drums that swaps between field / dungeon / town / boss themes (inspired by Diablo III/IV and Path of Exile 1/2), plus eerie per-monster creature voices and distinct player-minion cues
- **Combat System**: Projectile-based spell casting with collision detection
- **Passive Skill Tree**: A ~260-node PoE2-style radial web with six themed regions (Fire, Lightning, Sorcery, Alacrity, Summoning, Blood & Iron, Winter), wheels of minors around notables, ring roads between regions, and keystones at the rim
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

### Leveling System (Max Level 100)
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

### Passive Skill Tree
- **~260 nodes** arranged as a PoE2-style radial web: root at the center, six
  themed regions, wheels of minors around notables, and keystones at the rim
- **Regions**: Fire (burn), Winter (freeze), Lightning (shock/crit), Sorcery
  (mana/spell power/projectiles), Alacrity (attack & move speed), Summoning
  (minions), Blood & Iron (life/armor/resistances)
- **Allocation rule**: a node can be taken only if connected to an allocated
  node; refunds keep the tree connected to the root
- Press **P** to open the tree; right-drag to pan, mouse wheel to zoom

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
├── pytest.ini              # Test suite configuration
├── README.md              # This file
├── src/
│   ├── __init__.py
│   ├── entities/          # Game entities (player, enemy, boss, minion, chest)
│   ├── core/              # Stats, damage, save/load, data loading
│   ├── systems/           # Combat, rifts, world streaming, spawn director, quests
│   ├── spells/            # Skills, skill tree, gems, runes, keystones, elements
│   ├── items/             # Items, affixes, inventory, set bonuses
│   ├── progression/       # Ascendancy and atlas
│   ├── maps/              # Map/layout management
│   ├── ui/                # HUD, character sheet, tooltips, health bars
│   └── audio/             # Synthesized sound effects
└── tests/                 # pytest suite (see "Running Tests" below)
    ├── conftest.py        # Shared setup: sys.path + headless SDL
    └── test_phase*.py     # One module per development phase
```

## Running Tests

The test suite lives in `tests/` and runs under [pytest](https://docs.pytest.org/):

```bash
pip install pytest          # if not already installed
pytest                      # run the whole suite
pytest tests/test_phase10_save.py   # run a single module
pytest -k save              # run tests matching a keyword
```

`tests/conftest.py` puts the project root on `sys.path` and forces headless
SDL drivers, so tests run without opening a window or audio device and can be
invoked from any directory. Add new tests as `tests/test_*.py` with
`def test_*()` functions using plain `assert`.

## Extending the Game

### Adding New Spells
Edit `src/spells/spells.py` to create new spell classes inheriting from `Spell` base class.

### Adding New Enemy Types
Edit `src/entities/enemy.py` to add new enemy types and behaviors.

### Adding New Skill Tree Nodes
Edit the region/wheel/cluster definitions in `tools/build_skill_tree.py`, then
run `python tools/build_skill_tree.py` to regenerate `data/skill_tree.json`
(the script validates connectivity, spacing, and the legacy node contract).

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
