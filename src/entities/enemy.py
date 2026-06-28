import pygame
import random
import math
from src.systems.ailments import AilmentManager
from src.entities.entity import Entity
from src.core.data_loader import load_json


class EnemyType:
    """Stable type ids that map to keys in data/enemies.json."""
    GOBLIN = 0
    ORC = 1
    NECROMANCER = 2
    SKELETON = 3
    DEMON = 4
    DRAGON = 5
    VAMPIRE = 6
    LICH = 7


# type id -> data key
ENEMY_TYPE_KEYS = {
    EnemyType.GOBLIN: "goblin",
    EnemyType.ORC: "orc",
    EnemyType.NECROMANCER: "necromancer",
    EnemyType.SKELETON: "skeleton",
    EnemyType.DEMON: "demon",
    EnemyType.DRAGON: "dragon",
    EnemyType.VAMPIRE: "vampire",
    EnemyType.LICH: "lich",
}

# data key -> type id (used by biome enemy pools, Phase 11)
KEY_TO_ENEMY_TYPE = {v: k for k, v in ENEMY_TYPE_KEYS.items()}

# enemy data key -> family (for resistances, Phase 12)
FAMILY_OF = {
    "goblin": "beasts", "orc": "mutants", "skeleton": "undead",
    "necromancer": "cultists", "demon": "demons", "dragon": "ancients",
    "vampire": "undead", "lich": "voidborn",
}


class Enemy(Entity):
    """Enemy character with AI and combat, defined by data (DESIGN.md R2)."""

    def __init__(self, x, y, enemy_type=EnemyType.GOBLIN):
        self.enemy_type = enemy_type

        # Load stats from data instead of a hardcoded if/elif ladder.
        key = ENEMY_TYPE_KEYS.get(enemy_type, "goblin")
        data = load_json("enemies.json")[key]

        super().__init__(x, y, data["max_health"])

        self.name = data["name"]
        self.width = data["width"]
        self.height = data["height"]
        self.color = tuple(data["color"])
        self.damage = data["damage"]
        self.speed = data["speed"]
        self.experience_reward = data["xp_reward"]
        self.money_reward = dict(data["money"])
        self.progress_value = data.get("progress_value", 1)  # rift fill (Phase 5)
        self.is_boss = data.get("is_boss", False)

        # Family resistances (Phase 12): elemental builds matter vs families.
        self.family = FAMILY_OF.get(key)
        self.resistances = {}
        if self.family:
            fam = load_json("enemy_families.json").get(self.family, {})
            self.resistances = dict(fam.get("resistances", {}))

        # Tier / elite affixes / behaviors (Phase 12); set by the spawn director.
        self.tier = "normal"
        self.is_elite = False
        self.elite_affixes = []      # list of affix ids
        self.behaviors = {}          # merged affix behavior data
        self.cc_immune = False
        self.is_treasure_goblin = False
        self.loot_drops = 1
        self._behavior_timer = 0.0

        # Ailment / elemental effects tracking (Phases 7-9)
        self.elemental_effects = AilmentManager(self)

        # Create surface
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.center = (self.x, self.y)

        # AI
        self.target = None
        self.ai_timer = 0
        self.attack_cooldown = 0
        self.wander_direction = random.uniform(0, 2 * math.pi)
    
    def update(self, player, game_map, dt=1.0 / 60.0):
        """Update enemy behavior and position (dt drives ailment ticks)."""
        self.target = player

        # Frozen enemies can't move; slow scales movement speed (Phase 8).
        # Juggernaut elites ignore crowd control (Phase 12).
        move_mult = 1.0 if self.cc_immune else self.elemental_effects.move_multiplier()
        speed = self.speed * move_mult

        if move_mult > 0:
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            distance = math.sqrt(dx**2 + dy**2)

            if distance < 300:
                # Chase the player
                if distance > 0:
                    self.x += (dx / distance) * speed
                    self.y += (dy / distance) * speed
            else:
                # Wander
                self.ai_timer -= 1
                if self.ai_timer <= 0:
                    self.wander_direction = random.uniform(0, 2 * math.pi)
                    self.ai_timer = random.randint(30, 90)

                self.x += math.cos(self.wander_direction) * speed * 0.5
                self.y += math.sin(self.wander_direction) * speed * 0.5

        # Map boundaries (only in bounded maps; the streaming world is infinite)
        if getattr(game_map, "bounded", True):
            self.x = max(self.width // 2, min(self.x, game_map.width - self.width // 2))
            self.y = max(self.height // 2, min(self.y, game_map.height - self.height // 2))

        self.rect.center = (self.x, self.y)

        # Attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        # Elite behaviors: regeneration + teleport (Phase 12).
        if self.behaviors:
            self._apply_behaviors(dt, player)

        # Tick ailments; burn damage-over-time routes through the pipeline.
        burn_damage = self.elemental_effects.update(dt)
        if burn_damage > 0:
            from src.core.damage import apply_ailment_damage
            apply_ailment_damage(self, burn_damage, "fire")

    def _apply_behaviors(self, dt, player):
        regen = self.behaviors.get("regen")
        if regen and self.health < self.max_health:
            self.health = min(self.max_health, self.health + self.max_health * regen * dt)

        tp = self.behaviors.get("teleport")
        if tp:
            self._behavior_timer += dt
            if self._behavior_timer >= tp["interval"]:
                self._behavior_timer = 0.0
                ang = random.uniform(0, 2 * math.pi)
                dist = random.uniform(tp["range"] * 0.4, tp["range"])
                self.x = player.x + math.cos(ang) * dist
                self.y = player.y + math.sin(ang) * dist
                self.rect.center = (self.x, self.y)

    def get_resistance(self, element):
        """Family resistance percent for an element (Phase 12)."""
        return self.resistances.get(element, 0)
    
    def can_attack(self, player):
        """Check if enemy can attack the player."""
        if not self.cc_immune and self.elemental_effects.is_frozen():
            return False
        if self.attack_cooldown > 0:
            return False
        
        dx = player.x - self.x
        dy = player.y - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        return distance < 50
    
    def attack(self):
        """Perform an attack."""
        self.attack_cooldown = 60
        return self.damage
    
    def draw(self, surface, cam=(0, 0)):
        """Draw the enemy at its world position offset by the camera."""
        surface.blit(self.image, (self.x - cam[0] - self.width // 2,
                                  self.y - cam[1] - self.height // 2))
