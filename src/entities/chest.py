import pygame

class Chest(pygame.sprite.Sprite):
    """Treasure chest that can be opened for rewards."""
    
    def __init__(self, x, y, copper=0, silver=0, gold=0, diamond=0, xp=0):
        super().__init__()
        
        self.x = x
        self.y = y
        self.width = 30
        self.height = 30
        
        # Rewards
        self.copper = copper
        self.silver = silver
        self.gold = gold
        self.diamond = diamond
        self.xp_reward = xp
        
        self.opened = False
        
        # Graphics
        self.image = pygame.Surface((self.width, self.height))
        self.color = (200, 150, 50)  # Gold color
        self.image.fill(self.color)
        self.rect = self.image.get_rect()
        self.rect.center = (self.x, self.y)
    
    def open(self):
        """Open the chest."""
        if not self.opened:
            self.opened = True
            self.color = (100, 75, 25)  # Darker color when opened
            self.image.fill(self.color)
            return {
                'copper': self.copper,
                'silver': self.silver,
                'gold': self.gold,
                'diamond': self.diamond,
                'xp': self.xp_reward
            }
        return None
    
    def draw(self, surface):
        """Draw the chest."""
        surface.blit(self.image, self.rect)
