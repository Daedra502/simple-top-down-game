import random
from src.entities.enemy import Enemy, EnemyType
from src.entities.chest import Chest

class Map:
    """Represents a single game map/level."""
    
    def __init__(self, name, width, height, enemy_types, num_enemies, exit_pos, chests=None):
        self.name = name
        self.width = width
        self.height = height
        self.enemy_types = enemy_types
        self.num_enemies = num_enemies
        self.exit_pos = exit_pos  # Position of map exit
        self.player_spawn = (width // 2, height - 50)
        self.enemies = []
        self.chests = chests if chests else []
        self.generate_enemies()
    
    def generate_enemies(self):
        """Generate enemies for the map."""
        self.enemies = []
        for _ in range(self.num_enemies):
            enemy_type = random.choice(self.enemy_types)
            x = random.randint(50, self.width - 50)
            y = random.randint(50, self.height // 2)
            self.enemies.append(Enemy(x, y, enemy_type))
    
    def update(self, player, dt=1.0 / 60.0):
        """Update all enemies on the map (dt drives ailment ticks)."""
        alive_enemies = []
        for enemy in self.enemies:
            if enemy.health > 0:
                enemy.update(player, self, dt)
            if enemy.health > 0:
                alive_enemies.append(enemy)
        self.enemies = alive_enemies
    
    def draw(self, surface):
        """Draw the map background."""
        surface.fill((40, 40, 40))  # Dark gray background
        
        # Draw exit zone
        exit_x, exit_y = self.exit_pos
        import pygame
        pygame.draw.rect(surface, (100, 100, 255), (exit_x - 30, exit_y - 30, 60, 60))
        
        # Draw chests
        for chest in self.chests:
            chest.draw(surface)
        
        # Draw enemies
        for enemy in self.enemies:
            enemy.draw(surface)

class MapManager:
    """Manages different maps and level progression."""
    
    def __init__(self):
        self.maps = {
            'forest': Map(
                'Whispering Forest',
                1200,
                800,
                [EnemyType.GOBLIN, EnemyType.ORC],
                8,
                (1200 - 50, 400),
                [Chest(300, 200, copper=20, xp=30),
                 Chest(900, 150, silver=1, xp=20)]
            ),
            'caves': Map(
                'Dark Caverns',
                1200,
                800,
                [EnemyType.ORC, EnemyType.NECROMANCER],
                10,
                (1200 - 50, 400),
                [Chest(250, 300, copper=50, silver=1, xp=50),
                 Chest(950, 250, gold=1, xp=40)]
            ),
            'necropolis': Map(
                'Ancient Necropolis',
                1200,
                800,
                [EnemyType.NECROMANCER],
                12,
                (1200 - 50, 400),
                [Chest(300, 350, silver=2, gold=1, xp=80),
                 Chest(900, 300, copper=50, gold=1, xp=60)]
            ),
            'skeleton_pit': Map(
                'Skeleton Pit',
                1200,
                800,
                [EnemyType.SKELETON, EnemyType.SKELETON, EnemyType.NECROMANCER],
                14,
                (1200 - 50, 400),
                [Chest(300, 250, copper=100, xp=100),
                 Chest(600, 150, silver=3, xp=80),
                 Chest(900, 300, gold=1, silver=1, xp=90)]
            ),
            'demon_realm': Map(
                'Demon Realm',
                1200,
                800,
                [EnemyType.DEMON, EnemyType.VAMPIRE],
                12,
                (1200 - 50, 400),
                [Chest(250, 200, silver=1, gold=2, xp=150),
                 Chest(950, 350, gold=2, diamond=1, xp=120)]
            ),
            'dragon_lair': Map(
                'Dragon Lair',
                1200,
                800,
                [EnemyType.DRAGON, EnemyType.DEMON],
                8,
                (1200 - 50, 400),
                [Chest(300, 300, gold=3, diamond=1, xp=200),
                 Chest(900, 200, gold=5, diamond=2, xp=180)]
            ),
            'lich_tomb': Map(
                'Lich Tomb',
                1200,
                800,
                [EnemyType.LICH, EnemyType.DRAGON, EnemyType.VAMPIRE],
                10,
                (1200 - 50, 400),
                [Chest(250, 150, gold=4, diamond=2, xp=250),
                 Chest(600, 350, gold=3, diamond=1, xp=200),
                 Chest(950, 250, diamond=3, xp=300)]
            ),
            'shadow_abyss': Map(
                'Shadow Abyss',
                1200,
                800,
                [EnemyType.LICH, EnemyType.DEMON, EnemyType.DRAGON],
                15,
                (1200 - 50, 400),
                [Chest(300, 200, gold=5, diamond=2, xp=350),
                 Chest(600, 400, gold=4, diamond=3, xp=300),
                 Chest(900, 150, diamond=5, xp=400)]
            ),
        }
        
        self.map_progression = ['forest', 'caves', 'necropolis', 'skeleton_pit', 
                               'demon_realm', 'dragon_lair', 'lich_tomb', 'shadow_abyss']
        self.current_map_index = 0
        self.current_map = self.maps[self.map_progression[self.current_map_index]]
    
    def get_current_map(self):
        """Get the currently active map."""
        return self.current_map
    
    def next_map(self):
        """Progress to the next map."""
        if self.current_map_index < len(self.map_progression) - 1:
            self.current_map_index += 1
            map_key = self.map_progression[self.current_map_index]
            self.current_map = self.maps[map_key]
            return True
        return False
    
    def reset_current_map(self):
        """Reset the current map with new enemy positions."""
        map_key = self.map_progression[self.current_map_index]
        self.current_map = self.maps[map_key]
    
    def get_map_info(self):
        """Get information about the current map."""
        return {
            'name': self.current_map.name,
            'enemies_remaining': len(self.current_map.enemies),
            'total_enemies': self.current_map.num_enemies,
        }
