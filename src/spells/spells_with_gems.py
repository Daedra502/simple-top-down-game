"""Spell system with gem socket integration."""

import pygame
import math
from src.spells.gems import GemLibrary, GemType, SupportGem
from src.spells.spell_modifiers import (
    SpellConfiguration, 
    create_fireball_config,
    create_frostbolt_config,
    create_lightning_config
)


class ProjectileWithGems(pygame.sprite.Sprite):
    """Projectile that carries spell configuration with gem modifiers."""
    
    def __init__(self, x, y, target_x, target_y, speed, damage, color, 
                 radius=5, lifetime=300, spell_config=None, element_type=None):
        super().__init__()
        
        self.x = x
        self.y = y
        self.base_damage = damage
        self.spell_config = spell_config
        self.element_type = element_type
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        
        # Apply spell configuration modifiers to damage
        if spell_config:
            self.damage = spell_config.get_final_damage(player_stats={})
        else:
            self.damage = damage
        
        # Calculate direction
        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > 0:
            self.velocity_x = (dx / distance) * speed
            self.velocity_y = (dy / distance) * speed
        else:
            self.velocity_x = 0
            self.velocity_y = 0
        
        # Graphics
        self.radius = radius
        self.color = color
        self.image = pygame.Surface((radius * 2, radius * 2))
        self.image.fill((0, 0, 0))
        self.image.set_colorkey((0, 0, 0))
        pygame.draw.circle(self.image, color, (radius, radius), radius)
        
        self.rect = self.image.get_rect()
        self.rect.center = (self.x, self.y)
        
        # Gem properties - default values, can be modified by support gems
        self.chain_count = 0
        self.max_chain = getattr(spell_config, 'max_chain', 0) if spell_config else 0
        self.pierce_count = 0
        self.max_pierce = getattr(spell_config, 'max_pierce', 0) if spell_config else 0
        self.chained_targets = set()  # Prevent same enemy chain
    
    def update(self):
        """Update projectile position and lifetime."""
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.lifetime -= 1
        self.rect.center = (self.x, self.y)
    
    def is_alive(self):
        """Check if projectile is still alive."""
        return self.lifetime > 0
    
    def can_chain(self):
        """Check if projectile can chain to another target."""
        return self.chain_count < self.max_chain
    
    def can_pierce(self):
        """Check if projectile can pierce through enemies."""
        return self.pierce_count < self.max_pierce
    
    def apply_chain(self, target_id):
        """Mark target as chained to."""
        if self.can_chain():
            self.chain_count += 1
            self.chained_targets.add(target_id)
            return True
        return False
    
    def apply_pierce(self):
        """Use one pierce charge."""
        if self.can_pierce():
            self.pierce_count += 1
            return True
        return False
    
    def draw(self, surface):
        """Draw the projectile."""
        surface.blit(self.image, self.rect)


class SpellWithGems:
    """Spell that supports gem sockets and modifiers."""
    
    def __init__(self, name, base_damage, projectile_color, element_type=None):
        self.name = name
        self.base_damage = base_damage
        self.projectile_color = projectile_color
        self.element_type = element_type
        self.speed = 6
        self.radius = 8
        self.lifetime = 300
        
        # Gem socket support
        self.sockets = []  # List of gems inserted in this spell
        self.config = None  # Spell configuration with applied modifiers
        self.tags = []  # Spell tags for gem matching (e.g., ["projectile", "area"])
    
    def add_socket_gem(self, gem):
        """Add a gem to this spell's socket."""
        if gem.gem_type == GemType.SUPPORT:
            self.sockets.append(gem)
            self._rebuild_configuration()
            return True
        return False
    
    def remove_socket_gem(self, gem):
        """Remove a gem from this spell's socket."""
        if gem in self.sockets:
            self.sockets.remove(gem)
            self._rebuild_configuration()
            return True
        return False
    
    def get_socket_gems(self):
        """Get all gems in this spell's sockets."""
        return list(self.sockets)
    
    def _rebuild_configuration(self):
        """Rebuild spell configuration with current gems."""
        # Create base configuration
        if self.name == "Fireball":
            self.config = create_fireball_config()
        elif self.name == "Frostbolt":
            self.config = create_frostbolt_config()
        elif self.name == "Lightning Strike":
            self.config = create_lightning_config()
        else:
            # Generic spell config
            self.config = SpellConfiguration(
                base_damage=self.base_damage,
                modifiers={},
                tags=self.tags
            )
        
        # Apply all support gem modifiers
        for gem in self.sockets:
            if isinstance(gem, SupportGem):
                self.config.apply_support_gem_modifiers(gem)
    
    def cast(self, x, y, target_x, target_y):
        """Cast the spell and return a projectile with gem modifiers."""
        if not self.config:
            self._rebuild_configuration()
        
        # Build configuration from gems
        final_speed = self.speed
        if self.config and hasattr(self.config, 'modifiers'):
            final_speed = self.config.modifiers.get_projectile_speed(self.speed)
        
        return ProjectileWithGems(
            x, y, target_x, target_y,
            speed=final_speed,
            damage=self.base_damage,
            color=self.projectile_color,
            radius=self.radius,
            lifetime=self.lifetime,
            spell_config=self.config,
            element_type=self.element_type
        )
    
    def get_description(self):
        """Get spell description with socket information."""
        desc = f"{self.name}\n"
        desc += f"Base Damage: {self.base_damage}\n"
        
        if self.sockets:
            desc += f"Sockets: {len(self.sockets)} gems\n"
            for gem in self.sockets:
                desc += f"  - {gem.name}\n"
        else:
            desc += "Sockets: Empty\n"
        
        if self.config:
            final_dmg = self.config.get_final_damage(self.base_damage)
            desc += f"Final Damage: {final_dmg:.1f}\n"
        
        return desc


class FireballWithGems(SpellWithGems):
    """Fireball spell with gem socket support."""
    
    def __init__(self):
        super().__init__("Fireball", 25, (255, 100, 0), element_type="fire")
        self.speed = 6
        self.radius = 8
        self.tags = ["projectile", "area", "fire"]
        self._rebuild_configuration()


class FrostBoltWithGems(SpellWithGems):
    """Frost Bolt spell with gem socket support."""
    
    def __init__(self):
        super().__init__("Frostbolt", 18, (100, 200, 255), element_type="cold")
        self.speed = 8
        self.radius = 6
        self.tags = ["projectile", "cold"]
        self._rebuild_configuration()


class LightningStrikeWithGems(SpellWithGems):
    """Lightning Strike spell with gem socket support."""
    
    def __init__(self):
        super().__init__("Lightning Strike", 30, (255, 255, 100), element_type="lightning")
        self.speed = 12
        self.radius = 5
        self.tags = ["projectile", "lightning"]
        self._rebuild_configuration()


# Spell library with gem support
SPELLS_WITH_GEMS = {
    0: FireballWithGems(),
    1: FrostBoltWithGems(),
    2: LightningStrikeWithGems(),
}


def get_spell_with_gems(spell_id):
    """Get a spell with gem socket support."""
    return SPELLS_WITH_GEMS.get(spell_id)


def cast_spell_with_gems(spell_id, x, y, target_x, target_y):
    """Cast a spell using gem-integrated system."""
    spell = get_spell_with_gems(spell_id)
    if spell:
        return spell.cast(x, y, target_x, target_y)
    return None
