"""Gem and modifier system for spell customization."""
from enum import Enum


class GemType(Enum):
    """Types of gems that modify spells."""
    ACTIVE = 0          # Base spells (Fireball, Frost Bolt, Lightning)
    SUPPORT = 1         # Modifies active spells
    KEYSTONE = 2        # Unlocks unique mechanics


class Gem:
    """Represents a spell gem with modifiers."""
    
    def __init__(self, gem_id, name, gem_type, description=""):
        """
        Initialize a gem.
        
        Args:
            gem_id: Unique identifier
            name: Display name
            gem_type: GemType enum value
            description: What this gem does
        """
        self.gem_id = gem_id
        self.name = name
        self.gem_type = gem_type
        self.description = description
        self.modifiers = {}  # Dict of modifier_name: value
        self.level = 1
        self.quality = 0  # Quality percentage (0-20%)
    
    def add_modifier(self, modifier_name, value):
        """Add a modifier to this gem."""
        self.modifiers[modifier_name] = value
    
    def get_modifier(self, modifier_name, default=0):
        """Get a modifier value with quality scaling."""
        if modifier_name not in self.modifiers:
            return default
        
        value = self.modifiers[modifier_name]
        # Quality increases modifier values by 1% per quality
        quality_multiplier = 1.0 + (self.quality * 0.01)
        
        if isinstance(value, float):
            return value * quality_multiplier
        else:
            return value
    
    def get_description(self):
        """Get formatted gem description."""
        desc = f"{self.name}\n"
        desc += f"Type: {self.gem_type.name}\n"
        desc += f"Level: {self.level}\n"
        if self.quality > 0:
            desc += f"Quality: +{self.quality}%\n"
        desc += f"\n{self.description}\n\n"
        
        desc += "Modifiers:\n"
        for mod, value in self.modifiers.items():
            if isinstance(value, float):
                desc += f"  {mod}: +{value:.1%}\n"
            else:
                desc += f"  {mod}: +{value}\n"
        
        return desc


class GemSocket:
    """A socket that can hold a gem."""
    
    def __init__(self, socket_id, socket_color="white", max_level=10):
        """
        Initialize a gem socket.
        
        Args:
            socket_id: Unique identifier
            socket_color: Color for visual identification
            max_level: Maximum gem level that fits
        """
        self.socket_id = socket_id
        self.socket_color = socket_color
        self.max_level = max_level
        self.gem = None
    
    def can_fit_gem(self, gem):
        """Check if a gem can fit in this socket."""
        return gem.level <= self.max_level
    
    def insert_gem(self, gem):
        """Insert a gem into this socket."""
        if not self.can_fit_gem(gem):
            return False
        
        self.gem = gem
        return True
    
    def remove_gem(self):
        """Remove the gem from this socket."""
        gem = self.gem
        self.gem = None
        return gem
    
    def has_gem(self):
        """Check if socket has a gem."""
        return self.gem is not None


class SupportGem:
    """A support gem that modifies active spells."""
    
    def __init__(self, gem_id, name, description=""):
        """
        Initialize a support gem.
        
        Args:
            gem_id: Unique identifier
            name: Display name
            description: What this gem does
        """
        self.gem_id = gem_id
        self.name = name
        self.description = description
        self.modifiers = {}
        self.requirements = []  # Spells this supports (empty = supports all)
        self.tags = []  # Tags like "projectile", "area", "spell"
    
    def add_modifier(self, modifier_name, value):
        """Add a modifier provided by this support gem."""
        self.modifiers[modifier_name] = value
    
    def add_requirement(self, spell_name):
        """Add a required spell tag."""
        self.requirements.append(spell_name)
    
    def add_tag(self, tag):
        """Add a tag to this support gem."""
        self.tags.append(tag)
    
    def supports_spell(self, spell_tags):
        """Check if this gem can support a spell."""
        if not self.requirements:
            return True  # Supports everything
        
        # Check if spell has any required tags
        return any(tag in spell_tags for tag in self.requirements)
    
    def apply_modifiers(self, modifiers_dict):
        """Apply this gem's modifiers to a modifiers dictionary."""
        for mod, value in self.modifiers.items():
            if mod in modifiers_dict:
                # Additive for most, multiplicative for multipliers
                if isinstance(value, float) and value < 2.0:
                    modifiers_dict[mod] = modifiers_dict[mod] * (1.0 + value)
                else:
                    modifiers_dict[mod] += value
            else:
                modifiers_dict[mod] = value


class KeystoneNode:
    """A keystone passive that unlocks unique mechanics."""
    
    def __init__(self, node_id, name, description=""):
        """
        Initialize a keystone node.
        
        Args:
            node_id: Unique identifier
            name: Display name
            description: What makes this powerful
        """
        self.node_id = node_id
        self.name = name
        self.description = description
        self.effects = {}  # Special game-changing effects
        self.requirements = []
    
    def add_effect(self, effect_name, effect_value):
        """Add a keystone effect."""
        self.effects[effect_name] = effect_value
    
    def add_requirement(self, required_node_id):
        """Add a prerequisite node."""
        self.requirements.append(required_node_id)


# Pre-defined gem library

class GemLibrary:
    """Factory and registry for all gems in the game."""
    
    gems = {}
    support_gems = {}
    keystone_nodes = {}
    
    @classmethod
    def create_all_gems(cls):
        """Initialize all gems in the game."""
        
        # ACTIVE SPELL GEMS
        cls._create_spell_gems()
        
        # SUPPORT GEMS
        cls._create_support_gems()
        
        # KEYSTONE NODES
        cls._create_keystone_nodes()
    
    @classmethod
    def _create_spell_gems(cls):
        """Create base spell gems."""
        
        # Fireball
        fireball = Gem("spell_fireball", "Fireball", GemType.ACTIVE,
                      "Launches a burning projectile that explodes on impact")
        fireball.add_modifier('base_damage', 25)
        fireball.add_modifier('fire_damage', 0.5)
        fireball.add_modifier('area_radius', 30)
        cls.gems["spell_fireball"] = fireball
        
        # Frost Bolt
        frostbolt = Gem("spell_frostbolt", "Frost Bolt", GemType.ACTIVE,
                       "Launches a freezing projectile that slows enemies")
        frostbolt.add_modifier('base_damage', 20)
        frostbolt.add_modifier('cold_damage', 0.6)
        frostbolt.add_modifier('projectile_speed', 1.2)
        cls.gems["spell_frostbolt"] = frostbolt
        
        # Lightning Strike
        lightning = Gem("spell_lightning", "Lightning Strike", GemType.ACTIVE,
                       "Calls down lightning that shocks nearby enemies")
        lightning.add_modifier('base_damage', 30)
        lightning.add_modifier('lightning_damage', 0.4)
        lightning.add_modifier('chain_range', 50)
        cls.gems["spell_lightning"] = lightning
    
    @classmethod
    def _create_support_gems(cls):
        """Create support gems."""
        
        # Faster Casting
        faster_cast = SupportGem("support_faster_cast", "Faster Casting",
                                "Reduces spell cast time")
        faster_cast.add_modifier('cast_speed', 0.25)  # 25% faster
        faster_cast.add_tag("spell")
        cls.support_gems["support_faster_cast"] = faster_cast
        
        # Increased Area of Effect
        inc_area = SupportGem("support_inc_area", "Increased Area of Effect",
                             "Makes spells affect a larger area")
        inc_area.add_modifier('area_radius', 1.5)  # 50% larger
        inc_area.add_tag("area")
        cls.support_gems["support_inc_area"] = inc_area
        
        # Added Fire Damage
        add_fire = SupportGem("support_add_fire", "Added Fire Damage",
                             "Adds fire damage to spells")
        add_fire.add_modifier('fire_damage', 15)
        add_fire.add_tag("fire")
        cls.support_gems["support_add_fire"] = add_fire
        
        # Added Cold Damage
        add_cold = SupportGem("support_add_cold", "Added Cold Damage",
                             "Adds cold damage to spells")
        add_cold.add_modifier('cold_damage', 15)
        add_cold.add_tag("cold")
        cls.support_gems["support_add_cold"] = add_cold
        
        # Critical Strike Chance
        crit_chance = SupportGem("support_crit_chance", "Critical Strike Chance",
                                "Increases critical strike chance")
        crit_chance.add_modifier('crit_chance', 0.25)  # 25%
        cls.support_gems["support_crit_chance"] = crit_chance
        
        # Increased Damage
        inc_damage = SupportGem("support_inc_damage", "Increased Damage",
                               "Increases spell damage")
        inc_damage.add_modifier('spell_damage', 0.40)  # 40% more
        cls.support_gems["support_inc_damage"] = inc_damage
        
        # Projectile Piercing
        pierce = SupportGem("support_pierce", "Projectile Pierce",
                           "Projectiles pass through enemies")
        pierce.add_modifier('pierces', 10)
        pierce.add_tag("projectile")
        cls.support_gems["support_pierce"] = pierce
        
        # Chain Reaction
        chain = SupportGem("support_chain", "Chain",
                          "Projectiles chain between enemies")
        chain.add_modifier('chain_count', 3)
        chain.add_tag("projectile")
        cls.support_gems["support_chain"] = chain
    
    @classmethod
    def _create_keystone_nodes(cls):
        """Create keystone passive nodes."""
        
        # Elemental Focus
        elem_focus = KeystoneNode("keystone_elem_focus", "Elemental Focus",
                                 "Spells deal 50% more elemental damage but cannot inflict status effects")
        elem_focus.add_effect('elemental_damage_multiplier', 1.5)
        elem_focus.add_effect('no_status_effects', True)
        cls.keystone_nodes["keystone_elem_focus"] = elem_focus
        
        # Spell Echo
        spell_echo = KeystoneNode("keystone_spell_echo", "Spell Echo",
                                 "Spells fire twice but take 50% longer to cast")
        spell_echo.add_effect('spell_repeats', 1)  # Fires twice total
        spell_echo.add_effect('cast_speed_penalty', 0.5)
        cls.keystone_nodes["keystone_spell_echo"] = spell_echo
        
        # Omnivamp
        omnivamp = KeystoneNode("keystone_omnivamp", "Omnivamp",
                               "All spell damage grants 2% life leech")
        omnivamp.add_effect('life_leech_percent', 0.02)
        cls.keystone_nodes["keystone_omnivamp"] = omnivamp
        
        # Projectile Mastery
        proj_master = KeystoneNode("keystone_proj_master", "Projectile Mastery",
                                  "Projectiles move 25% faster and pierce more")
        proj_master.add_effect('projectile_speed', 1.25)
        proj_master.add_effect('pierce_bonus', 5)
        cls.keystone_nodes["keystone_proj_master"] = proj_master
    
    @classmethod
    def get_gem(cls, gem_id):
        """Get a gem by ID."""
        return cls.gems.get(gem_id)
    
    @classmethod
    def get_support_gem(cls, gem_id):
        """Get a support gem by ID."""
        return cls.support_gems.get(gem_id)
    
    @classmethod
    def get_keystone(cls, node_id):
        """Get a keystone node by ID."""
        return cls.keystone_nodes.get(node_id)
    
    @classmethod
    def get_all_gems(cls):
        """Get all gems."""
        return cls.gems.values()
    
    @classmethod
    def get_all_support_gems(cls):
        """Get all support gems."""
        return cls.support_gems.values()


# Initialize gem library on import
GemLibrary.create_all_gems()
