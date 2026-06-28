"""Elemental damage system and damage type mechanics."""


class ElementType:
    """Enum-like class for elemental damage types."""
    PHYSICAL = "physical"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    CHAOS = "chaos"


class ElementalDamage:
    """Represents elemental damage with modifiers and effects."""
    
    def __init__(self, element_type, base_damage, modifier=1.0):
        """
        Initialize elemental damage.
        
        Args:
            element_type: Type of element (physical, fire, cold, lightning, chaos)
            base_damage: Base damage amount
            modifier: Multiplicative modifier (1.0 = 100%, 1.5 = 150%)
        """
        self.element_type = element_type
        self.base_damage = base_damage
        self.modifier = modifier
        self.effects = {}  # Special effects (e.g., burn, freeze, shock)
    
    def get_total_damage(self):
        """Get final damage after modifiers."""
        return self.base_damage * self.modifier
    
    def add_effect(self, effect_name, duration=1.0, intensity=1.0):
        """
        Add an elemental effect.
        
        Args:
            effect_name: Name of effect (burn, freeze, shock, etc.)
            duration: How long effect lasts
            intensity: Strength of effect (1.0 = normal)
        """
        self.effects[effect_name] = {
            'duration': duration,
            'intensity': intensity,
            'remaining': duration
        }
    
    def update_effects(self, delta_time):
        """Update effect timers."""
        for effect in list(self.effects.keys()):
            self.effects[effect]['remaining'] -= delta_time
            if self.effects[effect]['remaining'] <= 0:
                del self.effects[effect]


class ElementalResistance:
    """Tracks elemental resistances for an entity."""
    
    def __init__(self, default_resistance=0):
        """
        Initialize resistances.
        
        Args:
            default_resistance: Default resistance for all elements (%)
        """
        self.resistances = {
            ElementType.PHYSICAL: 0,
            ElementType.FIRE: default_resistance,
            ElementType.COLD: default_resistance,
            ElementType.LIGHTNING: default_resistance,
            ElementType.CHAOS: 0,  # Chaos always 0
        }
    
    def set_resistance(self, element_type, amount):
        """Set resistance for an element (0-100%)."""
        if element_type in self.resistances:
            self.resistances[element_type] = max(0, min(100, amount))
    
    def add_resistance(self, element_type, amount):
        """Add to an element's resistance (0-100%)."""
        if element_type in self.resistances:
            self.resistances[element_type] = max(0, min(100, 
                                                   self.resistances[element_type] + amount))
    
    def get_resistance(self, element_type):
        """Get resistance value for an element."""
        return self.resistances.get(element_type, 0)
    
    def calculate_damage_after_resistance(self, element_type, damage):
        """
        Calculate damage after applying resistance.
        
        Args:
            element_type: Type of elemental damage
            damage: Base damage amount
            
        Returns:
            Damage after resistance reduction
        """
        resistance = self.get_resistance(element_type)
        # Each % of resistance reduces damage by 1%
        # So 50% resistance = 50% damage reduction
        damage_multiplier = 1.0 - (resistance / 100.0)
        return damage * max(0.1, damage_multiplier)  # Minimum 10% damage


class ElementalEffectManager:
    """Manages active elemental effects on an entity."""
    
    def __init__(self):
        """Initialize effect manager."""
        self.active_effects = {}
        self.damage_over_time = 0
    
    def apply_effect(self, effect_name, element_type, duration, intensity):
        """
        Apply an elemental effect.
        
        Args:
            effect_name: "burn", "freeze", "shock", etc.
            element_type: The element causing the effect
            duration: How long the effect lasts
            intensity: Strength of effect
        """
        key = f"{element_type}_{effect_name}"
        self.active_effects[key] = {
            'name': effect_name,
            'element': element_type,
            'duration': duration,
            'remaining': duration,
            'intensity': intensity,
        }
    
    def update(self, delta_time):
        """Update all active effects."""
        self.damage_over_time = 0
        
        for key in list(self.active_effects.keys()):
            effect = self.active_effects[key]
            effect['remaining'] -= delta_time
            
            if effect['remaining'] <= 0:
                del self.active_effects[key]
                continue
            
            # Calculate damage over time
            if effect['name'] == 'burn':
                # Burn deals 10% of base damage per second per intensity
                self.damage_over_time += 10 * effect['intensity'] * delta_time
            elif effect['name'] == 'shock':
                # Shock increases damage taken by 10% per intensity (not DPS)
                pass  # Handled elsewhere
            elif effect['name'] == 'poison':
                # Poison deals chaos damage over time
                self.damage_over_time += 15 * effect['intensity'] * delta_time
    
    def get_active_effects(self):
        """Get list of active effects."""
        return list(self.active_effects.values())
    
    def get_shock_amplification(self):
        """
        Get damage amplification from shock stacks.
        
        Returns:
            Multiplier for damage (1.0 + 0.1 * shock_intensity)
        """
        shock_intensity = 0
        for key, effect in self.active_effects.items():
            if effect['name'] == 'shock':
                shock_intensity += effect['intensity']
        return 1.0 + (0.1 * shock_intensity)
    
    def is_frozen(self):
        """Check if entity is frozen (cannot act)."""
        for key, effect in self.active_effects.items():
            if effect['name'] == 'freeze' and effect['remaining'] > 0:
                return True
        return False
    
    def clear_effects(self):
        """Clear all active effects."""
        self.active_effects.clear()
        self.damage_over_time = 0


class ElementalScaling:
    """Handles how spells scale with elemental modifiers."""
    
    def __init__(self, base_damage=10):
        """Initialize scaling."""
        self.base_damage = base_damage
        self.element_scalings = {}
    
    def set_scaling(self, element_type, multiplier):
        """
        Set how much a spell scales with an element.
        
        Args:
            element_type: The element type
            multiplier: Scaling multiplier (e.g., 1.5 = 150% of base)
        """
        self.element_scalings[element_type] = multiplier
    
    def calculate_damage(self, element_type, modifiers_dict=None):
        """
        Calculate final damage for an element.
        
        Args:
            element_type: The element to use
            modifiers_dict: Dictionary of skill tree bonuses
            
        Returns:
            Final damage amount
        """
        if modifiers_dict is None:
            modifiers_dict = {}
        
        # Base damage with scaling
        scaling = self.element_scalings.get(element_type, 1.0)
        damage = self.base_damage * scaling
        
        # Apply element-specific bonuses
        element_bonus = modifiers_dict.get(f'{element_type}_damage', 0)
        damage += element_bonus
        
        # Apply global spell damage bonus
        global_bonus = modifiers_dict.get('spell_damage', 0)
        damage = damage * (1.0 + global_bonus / 100.0)
        
        return max(1, damage)  # Minimum 1 damage


# Elemental effect definitions
ELEMENTAL_EFFECTS = {
    'burn': {
        'element': ElementType.FIRE,
        'description': 'Deals fire damage over time',
        'can_stack': True,
        'max_stacks': 20,
    },
    'freeze': {
        'element': ElementType.COLD,
        'description': 'Slows and immobilizes enemy',
        'can_stack': False,
        'effect_on_apply': 'stun',
    },
    'shock': {
        'element': ElementType.LIGHTNING,
        'description': 'Increases damage taken by 10% per stack',
        'can_stack': True,
        'max_stacks': 20,
    },
    'poison': {
        'element': ElementType.CHAOS,
        'description': 'Deals chaos damage over time',
        'can_stack': True,
        'max_stacks': 20,
    },
}
