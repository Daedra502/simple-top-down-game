import pygame
import math

class Projectile(pygame.sprite.Sprite):
    """Base projectile class for spells."""
    
    def __init__(self, x, y, target_x, target_y, speed, damage, color, radius=5, lifetime=300):
        super().__init__()
        
        self.x = x
        self.y = y
        self.damage = damage
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        
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
    
    def update(self):
        """Update projectile position and lifetime."""
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.lifetime -= 1
        self.rect.center = (self.x, self.y)
    
    def is_alive(self):
        """Check if projectile is still alive."""
        return self.lifetime > 0
    
    def draw(self, surface, cam=(0, 0)):
        """Draw the projectile at its world position offset by the camera."""
        surface.blit(self.image, (self.x - cam[0] - self.radius,
                                  self.y - cam[1] - self.radius))

class Spell:
    """Base spell class."""
    
    def __init__(self, name, damage, projectile_color):
        self.name = name
        self.damage = damage
        self.projectile_color = projectile_color
    
    def cast(self, x, y, target_x, target_y):
        """Cast the spell and return a projectile."""
        raise NotImplementedError

class Fireball(Spell):
    """Fireball spell - high damage, medium speed."""
    
    def __init__(self):
        super().__init__("Fireball", 25, (255, 100, 0))
        self.speed = 6
        self.radius = 8
    
    def cast(self, x, y, target_x, target_y):
        """Create a fireball projectile."""
        return Projectile(x, y, target_x, target_y, self.speed, self.damage, 
                         self.projectile_color, self.radius, 400)

class FrostBolt(Spell):
    """Frost Bolt spell - medium damage, fast speed, slows enemies."""
    
    def __init__(self):
        super().__init__("Frost Bolt", 18, (100, 200, 255))
        self.speed = 8
        self.radius = 6
        self.slow_duration = 60
    
    def cast(self, x, y, target_x, target_y):
        """Create a frost bolt projectile."""
        return Projectile(x, y, target_x, target_y, self.speed, self.damage,
                         self.projectile_color, self.radius, 350)

class LightningStrike(Spell):
    """Lightning Strike spell - high damage, very fast, hits multiple targets."""
    
    def __init__(self):
        super().__init__("Lightning Strike", 30, (255, 255, 100))
        self.speed = 12
        self.radius = 5
    
    def cast(self, x, y, target_x, target_y):
        """Create a lightning projectile."""
        return Projectile(x, y, target_x, target_y, self.speed, self.damage,
                         self.projectile_color, self.radius, 300)

# Create instances of each spell
SPELLS = {
    0: Fireball(),
    1: FrostBolt(),
    2: LightningStrike()
}
