import math
from src.spells.elements import ElementType, ElementalDamage, ElementalEffectManager

class CombatSystem:
    """Handles combat interactions between entities."""
    
    def __init__(self):
        self.combat_log = []
    
    def check_hit(self, projectile, target):
        """Check if a projectile hits a target."""
        dx = target.x - projectile.x
        dy = target.y - projectile.y
        distance = math.sqrt(dx**2 + dy**2)
        
        return distance < (projectile.radius + max(target.width, target.height) / 2)
    
    def apply_damage(self, damage, target, damage_type="physical"):
        """Apply damage to a target."""
        final_damage = damage
        is_dead = target.take_damage(final_damage)
        
        self.combat_log.append(f"{damage_type}: {final_damage} damage dealt")
        return is_dead
    
    def deal_spell_damage(self, source, target, base_damage,
                          element_type=ElementType.PHYSICAL, apply_status=True):
        """Deal damage through the central pipeline (crit -> amps -> resist).

        Returns ``(final_damage, is_crit, is_dead)``.
        """
        from src.core.damage import roll_damage

        final_damage, is_crit = roll_damage(source, target, base_damage, element_type)
        is_dead = target.take_damage(final_damage)

        # Apply elemental ailments via the unified manager (Phase 8); source is
        # passed so tree/gear ailment scaling (Phase 9) applies.
        effects = getattr(target, 'elemental_effects', None)
        if apply_status and effects is not None:
            if element_type == ElementType.FIRE:
                effects.apply_burn(source)
            elif element_type == ElementType.COLD:
                effects.apply_chill(source)
            elif element_type == ElementType.LIGHTNING:
                effects.apply_shock(source)
            elif element_type == ElementType.CHAOS:
                effects.apply_burn(source)

            # Critical strikes set up Vulnerable (Phase 7) -- rewards crit builds.
            if is_crit and not is_dead:
                effects.apply_vulnerable(source)

        self.combat_log.append(f"{element_type}: {final_damage:.0f} damage (crit={is_crit})")
        return final_damage, is_crit, is_dead

    def apply_elemental_damage(self, damage, target, element_type=ElementType.PHYSICAL,
                               modifier=1.0, apply_status=True):
        """
        Apply elemental damage with status effects.
        
        Args:
            damage: Base damage amount
            target: Target entity (must have take_damage method)
            element_type: Type of element (fire, cold, lightning, chaos, physical)
            modifier: Elemental scaling modifier
            apply_status: Whether to apply status effects
            
        Returns:
            is_dead: Whether the target died
        """
        # Calculate final damage
        elemental_dmg = ElementalDamage(element_type, damage, modifier)
        final_damage = elemental_dmg.get_total_damage()
        
        # Apply damage
        is_dead = target.take_damage(final_damage)
        
        # Apply status effects if target supports it
        if apply_status and hasattr(target, 'elemental_effects'):
            if element_type == ElementType.FIRE:
                # Apply burn effect
                target.elemental_effects.apply_effect("burn", element_type, duration=3.0, intensity=1.0)
            elif element_type == ElementType.COLD:
                # Apply freeze effect
                target.elemental_effects.apply_effect("freeze", element_type, duration=2.0, intensity=1.0)
            elif element_type == ElementType.LIGHTNING:
                # Apply shock effect
                target.elemental_effects.apply_effect("shock", element_type, duration=4.0, intensity=1.0)
            elif element_type == ElementType.CHAOS:
                # Apply poison effect
                target.elemental_effects.apply_effect("poison", element_type, duration=5.0, intensity=1.0)
        
        self.combat_log.append(f"{element_type}: {final_damage} damage dealt (modifier: {modifier}x)")
        return is_dead
    
    def resolve_melee_combat(self, attacker, defender):
        """Resolve melee combat between two entities."""
        dx = defender.x - attacker.x
        dy = defender.y - attacker.y
        distance = math.sqrt(dx**2 + dy**2)
        
        attack_range = 50
        if distance < attack_range:
            damage = attacker.attack() if hasattr(attacker, 'attack') else attacker.damage
            is_dead = self.apply_damage(damage, defender, "melee")
            return is_dead
        
        return False

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
