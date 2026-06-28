"""
Keystone node system - special game-changing abilities for advanced builds.

Keystones are powerful nodes that provide unique mechanics and stat bonuses.
They represent the culmination of specific skill tree branches.
"""


class Keystone:
    """Base class for keystone abilities."""
    
    def __init__(self, keystone_id, name, element_type, base_effects, description):
        """
        Initialize a keystone.
        
        Args:
            keystone_id: Unique identifier
            name: Display name
            element_type: Associated element (fire, cold, lightning, chaos, hybrid)
            base_effects: Dict of stat modifiers
            description: Flavor text describing the effect
        """
        self.keystone_id = keystone_id
        self.name = name
        self.element_type = element_type
        self.base_effects = base_effects.copy()
        self.description = description
        self.active = False
    
    def get_effects(self):
        """Get all effects from this keystone."""
        return self.base_effects.copy()
    
    def apply_to_player(self, player):
        """Apply keystone-specific effects to player. Override in subclasses."""
        # Default: just apply base effects
        effects = self.get_effects()
        for effect, value in effects.items():
            if hasattr(player, effect):
                current = getattr(player, effect)
                if isinstance(current, (int, float)):
                    setattr(player, effect, current + value)


class ElementalFocusKeystone(Keystone):
    """
    Elemental Focus: Spells remove status effects from player.
    Bonus: +30% spell damage when clean (no status effects).
    """
    
    def __init__(self):
        super().__init__(
            "elemental_focus",
            "Elemental Focus",
            "fire",
            {"spell_damage": 30, "max_mana": 20},  # Base bonuses
            "Spells remove status effects. Gain 30% spell damage when clean."
        )
        self.cleanse_on_cast = True
        self.clean_damage_bonus = 0.30
    
    def apply_to_player(self, player):
        """Apply Elemental Focus effects."""
        super().apply_to_player(player)
        player.elemental_focus_active = True


class SpellEchoKeystone(Keystone):
    """
    Spell Echo: Spells cast twice per click.
    Bonus: +0.2 cooldown reduction on echoed spells.
    
    Doubles mana cost, halves effective cooldown.
    """
    
    def __init__(self):
        super().__init__(
            "spell_echo",
            "Spell Echo",
            "hybrid",
            {"attack_speed": 0.15, "max_mana": 50},  # Base bonuses
            "Spells cast twice. Echoed spells have reduced cooldown."
        )
        self.echo_count = 2
        self.echo_cooldown_reduction = 0.2
        self.mana_multiplier = 2.0  # Double mana cost
    
    def apply_to_player(self, player):
        """Apply Spell Echo effects."""
        super().apply_to_player(player)
        player.spell_echo_active = True
        player.spell_echo_count = self.echo_count
        player.spell_echo_cooldown_reduction = self.echo_cooldown_reduction


class OmnivampKeystone(Keystone):
    """
    Omnivamp: Heal for 20% of damage dealt.
    Bonus: +25% life steal effectiveness.
    
    Self-sustaining playstyle - trades offensive stats for survivability.
    """
    
    def __init__(self):
        super().__init__(
            "omnivamp",
            "Omnivamp",
            "chaos",
            {"max_health": 100, "spell_damage": 15},  # Base bonuses
            "Heal for 20% of damage dealt. Enhanced life steal."
        )
        self.life_steal_percent = 0.20
        self.life_steal_multiplier = 1.25
    
    def apply_to_player(self, player):
        """Apply Omnivamp effects."""
        super().apply_to_player(player)
        player.omnivamp_active = True
        player.life_steal_percent = self.life_steal_percent
        player.life_steal_multiplier = self.life_steal_multiplier


class ProjectileMasteryKeystone(Keystone):
    """
    Projectile Mastery: All projectiles gain +2 chain and +2 pierce.
    Bonus: Spell damage increased by 25%.
    
    Encourages multi-enemy engagement and complex projectile interactions.
    """
    
    def __init__(self):
        super().__init__(
            "projectile_mastery",
            "Projectile Mastery",
            "lightning",
            {"spell_damage": 25, "attack_speed": 0.1},  # Base bonuses
            "Projectiles gain chain and pierce. Multi-target specialist."
        )
        self.chain_bonus = 2
        self.pierce_bonus = 2
        self.chain_pierce_damage_penalty = 0.10  # 10% damage per chain/pierce
    
    def apply_to_player(self, player):
        """Apply Projectile Mastery effects."""
        super().apply_to_player(player)
        player.projectile_mastery_active = True
        player.projectile_chain_bonus = self.chain_bonus
        player.projectile_pierce_bonus = self.pierce_bonus


class KeystoneManager:
    """Manages keystones and their effects."""
    
    # Registry of all available keystones
    KEYSTONES = {
        'elemental_focus': ElementalFocusKeystone(),
        'spell_echo': SpellEchoKeystone(),
        'omnivamp': OmnivampKeystone(),
        'projectile_mastery': ProjectileMasteryKeystone(),
    }
    
    @staticmethod
    def get_keystone(keystone_id):
        """Get a keystone by ID."""
        return KeystoneManager.KEYSTONES.get(keystone_id)
    
    @staticmethod
    def get_all_keystones():
        """Get all keystones."""
        return list(KeystoneManager.KEYSTONES.values())
    
    @staticmethod
    def get_keystone_by_name(name):
        """Get a keystone by name."""
        for ks in KeystoneManager.KEYSTONES.values():
            if ks.name == name:
                return ks
        return None


# Mapping of keystone IDs to skill tree node IDs
KEYSTONE_NODES = {
    'elemental_focus': 'fire_key',      # Fire branch keystone
    'spell_echo': 'mana_3',              # Mana fountain (not primary keystone, using as echo)
    'omnivamp': 'dmg_3',                 # Arcane Mastery (chaos/hybrid path)
    'projectile_mastery': 'hybrid_ld',   # Voltage Surge (lightning/damage)
}

# Reverse mapping
NODE_TO_KEYSTONE = {v: k for k, v in KEYSTONE_NODES.items()}


def is_keystone_node(node_id):
    """Check if a node ID is a keystone."""
    return node_id in NODE_TO_KEYSTONE


def get_keystone_for_node(node_id):
    """Get the keystone for a given node ID."""
    keystone_id = NODE_TO_KEYSTONE.get(node_id)
    if keystone_id:
        return KeystoneManager.get_keystone(keystone_id)
    return None
