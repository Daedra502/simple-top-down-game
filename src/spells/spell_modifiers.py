"""Spell modifier and scaling system."""


class SpellModifiers:
    """Calculates final spell properties based on all modifiers."""
    
    def __init__(self, base_spell_id):
        """
        Initialize spell modifiers.
        
        Args:
            base_spell_id: ID of the base spell
        """
        self.base_spell_id = base_spell_id
        self.modifiers = {}
        self.tags = []  # Tags like "projectile", "spell", "fire", etc.
    
    def add_tag(self, tag):
        """Add a tag to this spell."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def set_modifier(self, modifier_name, value):
        """Set a modifier value."""
        self.modifiers[modifier_name] = value
    
    def add_modifier(self, modifier_name, value):
        """Add to an existing modifier."""
        if modifier_name in self.modifiers:
            self.modifiers[modifier_name] += value
        else:
            self.modifiers[modifier_name] = value
    
    def multiply_modifier(self, modifier_name, multiplier):
        """Multiply an existing modifier."""
        if modifier_name in self.modifiers:
            self.modifiers[modifier_name] *= multiplier
    
    def get_modifier(self, modifier_name, default=0):
        """Get a modifier value."""
        return self.modifiers.get(modifier_name, default)
    
    def apply_skill_tree_bonuses(self, skill_tree_bonuses):
        """
        Apply bonuses from skill tree allocations.
        
        Args:
            skill_tree_bonuses: Dict of bonuses from allocated skill nodes
        """
        for bonus_name, bonus_value in skill_tree_bonuses.items():
            self.add_modifier(bonus_name, bonus_value)
    
    def apply_support_gem_modifiers(self, support_gems):
        """
        Apply modifiers from linked support gems.
        
        Args:
            support_gems: List of SupportGem objects
        """
        for gem in support_gems:
            # Check if gem supports this spell
            if gem.supports_spell(self.tags):
                gem.apply_modifiers(self.modifiers)
    
    def get_final_damage(self, base_damage):
        """
        Calculate final damage with all modifiers.
        
        Args:
            base_damage: Base spell damage
            
        Returns:
            Final damage value
        """
        damage = base_damage
        
        # Apply base damage increases
        damage += self.get_modifier('spell_damage', 0)
        
        # Apply element-specific damage
        for element in ['fire', 'cold', 'lightning', 'chaos']:
            element_key = f'{element}_damage'
            damage += self.get_modifier(element_key, 0)
        
        # Apply global multipliers
        multiplier = 1.0
        multiplier *= (1.0 + self.get_modifier('global_damage_multiplier', 0))
        multiplier *= (1.0 + self.get_modifier('spell_damage_multiplier', 0))
        
        damage = damage * multiplier
        return max(1, int(damage))
    
    def get_area_radius(self, base_radius):
        """Get area of effect radius with modifiers."""
        radius = base_radius
        radius *= (1.0 + self.get_modifier('area_radius', 0))
        return max(1, int(radius))
    
    def get_cast_speed(self, base_cooldown):
        """
        Get adjusted cooldown with cast speed modifiers.
        
        Args:
            base_cooldown: Base cooldown in frames
            
        Returns:
            Adjusted cooldown
        """
        speed_bonus = 1.0 + self.get_modifier('cast_speed', 0)
        cooldown = base_cooldown / speed_bonus
        return max(1, int(cooldown))
    
    def get_projectile_speed(self, base_speed):
        """Get projectile speed with modifiers."""
        speed = base_speed
        speed *= (1.0 + self.get_modifier('projectile_speed', 0))
        return max(0.5, speed)
    
    def get_chain_count(self, base_chain=0):
        """Get number of chains from projectile chain modifiers."""
        chain = base_chain
        chain += self.get_modifier('chain_count', 0)
        return max(0, int(chain))
    
    def get_pierce_count(self, base_pierce=0):
        """Get number of pierces from projectile pierce modifiers."""
        pierce = base_pierce
        pierce += self.get_modifier('pierces', 0)
        return max(0, int(pierce))
    
    def get_critical_chance(self, base_crit=0):
        """Get critical strike chance (0.0 to 1.0)."""
        crit = base_crit
        crit += self.get_modifier('crit_chance', 0)
        return max(0, min(1.0, crit))
    
    def get_critical_multiplier(self, base_mult=1.5):
        """Get critical damage multiplier."""
        mult = base_mult
        mult += self.get_modifier('crit_multiplier', 0)
        return max(1.0, mult)
    
    def get_all_modifiers(self):
        """Get all current modifiers as a dictionary."""
        return self.modifiers.copy()
    
    def get_description(self):
        """Get formatted description of all active modifiers."""
        desc = "Spell Modifiers:\n"
        for mod, value in sorted(self.modifiers.items()):
            if isinstance(value, float) and value < 10:
                desc += f"  {mod}: +{value:.1%}\n"
            else:
                desc += f"  {mod}: +{value}\n"
        return desc


class SpellScalingProfile:
    """Defines how a spell scales with different stats."""
    
    def __init__(self, spell_id):
        """
        Initialize scaling profile.
        
        Args:
            spell_id: ID of the spell
        """
        self.spell_id = spell_id
        self.scalings = {}  # stat_name: scaling_amount
    
    def add_scaling(self, stat_name, scaling_amount):
        """
        Add scaling for a stat.
        
        Args:
            stat_name: Name of stat to scale with (e.g., "intelligence")
            scaling_amount: How much this stat contributes (e.g., 0.5 = 50% of stat value)
        """
        self.scalings[stat_name] = scaling_amount
    
    def calculate_scaling_damage(self, stats_dict):
        """
        Calculate damage from stat scaling.
        
        Args:
            stats_dict: Dictionary of player stats
            
        Returns:
            Damage added from scaling
        """
        scaling_damage = 0
        for stat_name, scaling_amount in self.scalings.items():
            if stat_name in stats_dict:
                scaling_damage += stats_dict[stat_name] * scaling_amount
        return scaling_damage
    
    def get_scalings(self):
        """Get all scalings."""
        return self.scalings.copy()


class SpellConfiguration:
    """Combines all spell configuration together."""
    
    def __init__(self, spell_id, base_damage, base_cooldown):
        """
        Initialize spell configuration.
        
        Args:
            spell_id: ID of the spell
            base_damage: Base damage
            base_cooldown: Base cooldown in frames
        """
        self.spell_id = spell_id
        self.base_damage = base_damage
        self.base_cooldown = base_cooldown
        
        self.modifiers = SpellModifiers(spell_id)
        self.scaling = SpellScalingProfile(spell_id)
        self.support_gems = []
    
    def add_support_gem(self, support_gem):
        """Add a support gem to this spell."""
        if support_gem not in self.support_gems:
            self.support_gems.append(support_gem)
    
    def remove_support_gem(self, support_gem):
        """Remove a support gem from this spell."""
        if support_gem in self.support_gems:
            self.support_gems.remove(support_gem)
    
    def get_final_damage(self, player_stats=None):
        """
        Calculate final spell damage.
        
        Args:
            player_stats: Dictionary of player stats
            
        Returns:
            Final damage value
        """
        # Start with base damage
        damage = self.base_damage
        
        # Add scaling damage
        if player_stats:
            damage += self.scaling.calculate_scaling_damage(player_stats)
        
        # Apply modifiers
        damage = self.modifiers.get_final_damage(damage)
        
        return max(1, damage)
    
    def get_final_cooldown(self):
        """Get final cooldown with modifiers."""
        return self.modifiers.get_cast_speed(self.base_cooldown)
    
    def get_full_description(self):
        """Get full spell description."""
        desc = f"Spell: {self.spell_id}\n"
        desc += f"Base Damage: {self.base_damage}\n"
        desc += f"Base Cooldown: {self.base_cooldown}\n"
        desc += f"Support Gems: {len(self.support_gems)}\n\n"
        desc += self.modifiers.get_description()
        return desc


# Pre-configured spell profiles

def create_fireball_config():
    """Create Fireball spell configuration."""
    config = SpellConfiguration("fireball", 25, 30)
    config.modifiers.add_tag("projectile")
    config.modifiers.add_tag("spell")
    config.modifiers.add_tag("fire")
    config.scaling.add_scaling("intelligence", 0.5)
    return config


def create_frostbolt_config():
    """Create Frost Bolt spell configuration."""
    config = SpellConfiguration("frostbolt", 20, 25)
    config.modifiers.add_tag("projectile")
    config.modifiers.add_tag("spell")
    config.modifiers.add_tag("cold")
    config.scaling.add_scaling("intelligence", 0.4)
    return config


def create_lightning_config():
    """Create Lightning Strike spell configuration."""
    config = SpellConfiguration("lightning", 30, 35)
    config.modifiers.add_tag("spell")
    config.modifiers.add_tag("lightning")
    config.scaling.add_scaling("intelligence", 0.6)
    return config
