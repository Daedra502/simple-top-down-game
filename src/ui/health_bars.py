"""Health and mana bar UI components for players and enemies."""
import pygame
import math


def _lerp_color(a, b, t):
    """Linear interpolation between two RGB colors (t in 0..1)."""
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def health_fraction_color(frac):
    """Green (full) -> yellow (half) -> red (empty)."""
    green, yellow, red = (50, 220, 50), (230, 200, 40), (220, 50, 50)
    if frac > 0.5:
        return _lerp_color(green, yellow, (1.0 - frac) * 2.0)
    return _lerp_color(yellow, red, (0.5 - frac) * 2.0)


class HealthBar:
    """Represents a health/resource bar with smooth animation."""
    
    def __init__(self, x, y, width, height, max_value, color=(255, 0, 0)):
        """
        Initialize a health bar.
        
        Args:
            x, y: Position of the bar
            width, height: Dimensions of the bar
            max_value: Maximum health value
            color: RGB color tuple for the bar
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.max_value = max_value
        self.current_value = max_value
        self.display_value = max_value  # For smooth animation
        self.color = color
        self.background_color = (50, 50, 50)
        self.border_color = (255, 255, 255)
        self.damaged_color = (255, 100, 0)  # Flash color when damaged
        self.damage_flash_time = 0
        self.font = pygame.font.Font(None, 14)
        # Color behavior
        self.use_health_gradient = False  # green->yellow->red by fill fraction
        self.color_override = None        # e.g. purple while Vulnerable (Phase 7)
    
    def set_value(self, value):
        """Update the current health value."""
        self.current_value = max(0, min(value, self.max_value))
        
        # Flash on damage
        if self.current_value < self.display_value:
            self.damage_flash_time = 0.3
    
    def update(self, delta_time=0.016):
        """Update animation state."""
        # Smooth animation toward current value
        diff = self.current_value - self.display_value
        if abs(diff) > 0.1:
            self.display_value += diff * 0.1  # Smooth transition
        else:
            self.display_value = self.current_value
        
        # Damage flash timer
        if self.damage_flash_time > 0:
            self.damage_flash_time -= delta_time
    
    def draw(self, surface, show_text=True):
        """Draw the health bar."""
        # Background bar
        bg_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, self.background_color, bg_rect)
        pygame.draw.rect(surface, self.border_color, bg_rect, 1)
        
        # Health bar (with smooth animation)
        if self.max_value > 0:
            bar_width = (self.display_value / self.max_value) * self.width
        else:
            bar_width = 0
        
        # Base color: explicit override > health gradient > fixed color
        frac = (self.display_value / self.max_value) if self.max_value > 0 else 0
        if self.color_override is not None:
            base_color = self.color_override
        elif self.use_health_gradient:
            base_color = health_fraction_color(frac)
        else:
            base_color = self.color

        # Choose color based on damage flash
        if self.damage_flash_time > 0:
            # Interpolate between base and damaged color
            t = self.damage_flash_time / 0.3  # 0 to 1 (1 = just damaged, 0 = done)
            color = tuple(
                int(base_color[i] * (1 - t) + self.damaged_color[i] * t)
                for i in range(3)
            )
        else:
            color = base_color
        
        if bar_width > 0:
            bar_rect = pygame.Rect(self.x, self.y, bar_width, self.height)
            pygame.draw.rect(surface, color, bar_rect)
        
        # Text overlay (if enabled)
        if show_text:
            text = self.font.render(
                f"{int(self.current_value)}/{int(self.max_value)}",
                True,
                (255, 255, 255)
            )
            text_rect = text.get_rect(center=(
                self.x + self.width // 2,
                self.y + self.height // 2
            ))
            surface.blit(text, text_rect)


class PlayerResourcesUI:
    """UI panel showing player health, mana, and level."""
    
    def __init__(self, x, y, width=300):
        """
        Initialize player resources UI.
        
        Args:
            x, y: Position of the panel
            width: Width of the panel
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = 120
        
        self.health_bar = HealthBar(x + 10, y + 20, width - 20, 20, 100, (220, 30, 30))
        self.mana_bar = HealthBar(x + 10, y + 50, width - 20, 20, 100, (30, 100, 200))
        
        self.font = pygame.font.Font(None, 18)
        self.small_font = pygame.font.Font(None, 14)
        self.bg_color = (10, 10, 20)
        self.border_color = (100, 150, 200)
    
    def update(self, player, delta_time=0.016):
        """Update from player state."""
        self.health_bar.max_value = player.max_health
        self.health_bar.set_value(player.health)
        self.health_bar.update(delta_time)
        
        self.mana_bar.max_value = player.max_mana
        self.mana_bar.set_value(player.mana)
        self.mana_bar.update(delta_time)
    
    def draw(self, surface, player):
        """Draw the resources panel."""
        # Background panel
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, self.bg_color, panel_rect)
        pygame.draw.rect(surface, self.border_color, panel_rect, 2)
        
        # Title
        title = self.font.render("Character", True, (255, 200, 0))
        surface.blit(title, (self.x + 10, self.y + 3))
        
        # Bars
        self.health_bar.draw(surface, show_text=True)
        self.mana_bar.draw(surface, show_text=True)
        
        # Level and skill points
        info_text = self.small_font.render(
            f"Level: {player.level}  |  Skill Pts: {player.skill_points}",
            True,
            (200, 200, 200)
        )
        surface.blit(info_text, (self.x + 10, self.y + 80))


class EnemyHealthBar:
    """Floating health bar that appears above enemies."""
    
    def __init__(self, enemy, offset_y=-40):
        """
        Initialize enemy health bar.
        
        Args:
            enemy: The enemy entity
            offset_y: Y offset from enemy position
        """
        self.enemy = enemy
        is_boss = getattr(enemy, "is_boss", False)
        # Bosses get a wider bar that sits higher above the larger sprite.
        bar_w = 90 if is_boss else 50
        self.offset_y = -(enemy.height // 2 + 14) if is_boss else offset_y
        self.bar = HealthBar(0, 0, bar_w, 8, enemy.max_health, (220, 50, 50))
        self.bar.use_health_gradient = True  # color feedback as HP drops
        self.show_time = 3.0  # Hide after 3 seconds of full health
        self.time_since_damage = 3.0
    
    def update(self, delta_time=0.016):
        """Update health bar state."""
        self.bar.max_value = self.enemy.max_health
        
        # Check if damage occurred
        if self.enemy.health < self.bar.current_value:
            self.show_time = 3.0
            self.time_since_damage = 0
        
        self.bar.set_value(self.enemy.health)

        # Vulnerable enemies show a purple bar (Phase 7).
        effects = getattr(self.enemy, "elemental_effects", None)
        if effects is not None and getattr(effects, "is_vulnerable", None) and effects.is_vulnerable():
            self.bar.color_override = (180, 70, 230)
        else:
            self.bar.color_override = None

        self.bar.update(delta_time)

        # Update position to follow enemy
        self.bar.x = self.enemy.x - self.bar.width // 2
        self.bar.y = self.enemy.y + self.offset_y
        
        # Timer for fading
        self.time_since_damage += delta_time
    
    def draw(self, surface, cam=(0, 0)):
        """Draw the health bar (camera-offset) if recently damaged."""
        if self.enemy.health < self.enemy.max_health or self.time_since_damage < self.show_time:
            ox, oy = self.bar.x, self.bar.y
            self.bar.x -= cam[0]
            self.bar.y -= cam[1]
            self.bar.draw(surface, show_text=False)
            self.bar.x, self.bar.y = ox, oy


class DamageNumber:
    """Floating damage number that appears above hits."""
    
    def __init__(self, x, y, damage, color=(255, 255, 255), damage_type="normal"):
        """
        Initialize damage number.
        
        Args:
            x, y: Position to spawn
            damage: Damage amount to display
            color: RGB color for text
            damage_type: "normal", "crit", "heal"
        """
        self.x = x
        self.y = y
        self.damage = damage
        self.color = color
        self.damage_type = damage_type
        self.lifetime = 1.0  # Seconds
        self.age = 0
        self.opacity = 1.0  # set each update(); init so a draw-before-update is safe
        self.velocity_y = -2  # Float upward
        self.font = pygame.font.Font(None, 24)
        
        # Format text
        if damage_type == "crit":
            self.text_str = f"{int(damage)}!"
            self.size = 28
            self.font = pygame.font.Font(None, self.size)
        elif damage_type == "heal":
            self.text_str = f"+{int(damage)}"
            self.color = (100, 255, 100)
        else:
            self.text_str = f"{int(damage)}"
    
    def update(self, delta_time=0.016):
        """Update damage number state."""
        self.age += delta_time
        self.y += self.velocity_y
        
        # Fade out
        self.opacity = max(0, 1.0 - (self.age / self.lifetime))
    
    def is_alive(self):
        """Check if damage number should still be displayed."""
        return self.age < self.lifetime
    
    def draw(self, surface, cam=(0, 0)):
        """Draw the damage number (camera-offset)."""
        if not self.is_alive():
            return

        text = self.font.render(self.text_str, True, self.color)
        text.set_alpha(int(self.opacity * 255))
        text_rect = text.get_rect(center=(self.x - cam[0], self.y - cam[1]))
        surface.blit(text, text_rect)


class DamageNumberManager:
    """Manages all floating damage numbers."""
    
    def __init__(self):
        """Initialize damage number manager."""
        self.numbers = []
    
    def add_damage(self, x, y, damage, damage_type="normal"):
        """Add a new damage number."""
        color_map = {
            "normal": (255, 255, 255),
            "crit": (255, 200, 0),
            "heal": (100, 255, 100),
            "fire": (255, 100, 0),
            "cold": (100, 150, 255),
            "lightning": (255, 255, 0),
        }
        color = color_map.get(damage_type, (255, 255, 255))
        self.numbers.append(DamageNumber(x, y, damage, color, damage_type))
    
    def update(self, delta_time=0.016):
        """Update all damage numbers."""
        for number in self.numbers[:]:
            number.update(delta_time)
            if not number.is_alive():
                self.numbers.remove(number)
    
    def draw(self, surface, cam=(0, 0)):
        """Draw all damage numbers (camera-offset)."""
        for number in self.numbers:
            number.draw(surface, cam)
