import math

class CollisionSystem:
    """Handles collision detection between entities."""
    
    @staticmethod
    def check_rect_collision(rect1, rect2):
        """Check if two rectangles collide."""
        return rect1.colliderect(rect2)
    
    @staticmethod
    def check_circle_collision(x1, y1, r1, x2, y2, r2):
        """Check if two circles collide."""
        dx = x2 - x1
        dy = y2 - y1
        distance = math.sqrt(dx**2 + dy**2)
        return distance < (r1 + r2)
    
    @staticmethod
    def get_distance(x1, y1, x2, y2):
        """Calculate distance between two points."""
        dx = x2 - x1
        dy = y2 - y1
        return math.sqrt(dx**2 + dy**2)
