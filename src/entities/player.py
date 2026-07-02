import pygame
import math
from src.entities.entity import Entity, Event
from src.core.stats import Stats, effects_to_stats
from src.systems import leveling
from src.entities.player_sprite import PlayerSprite


class Player(Entity):
    """Player character with abilities and skills."""

    def __init__(self, x, y):
        # Central Stats object: the single source of truth (DESIGN.md R1/Phase 2).
        # Skill tree, gear, set bonuses and ailments all write layers; effective
        # values are written through to the attributes below by recompute().
        self.stats = Stats()

        super().__init__(x, y, int(self.stats.get('max_health')))

        # Size
        self.width = 20
        self.height = 20

        # Collision surface/rect (kept for physics; visuals use the sprite).
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill((0, 200, 255))
        self.rect = self.image.get_rect()
        self.rect.center = (self.x, self.y)

        # Animated hooded battle-mage sprite (procedural; no external assets).
        self.sprite = PlayerSprite(target_size=self.height)
        self.facing = "down"
        self._cast_pose = 0.0     # seconds of cast pose remaining
        self._moving = False
        self._last_dt = 1.0 / 60.0

        # Movement
        self.velocity_x = 0
        self.velocity_y = 0

        # Combat stats (write-through cache of self.stats; see recompute()).
        self.mana = self.max_mana = int(self.stats.get('max_mana'))
        self.speed = self.stats.get('move_speed')
        self.mana_regen = self.stats.get('mana_regen')
        self.health_regen = self.stats.get('health_regen')
        self.damage = int(self.stats.get('damage'))
        self.attack_speed = self.stats.get('attack_speed')  # Multiplier for cooldowns
        self.crit_chance = self.stats.get('crit_chance')
        self.crit_damage = self.stats.get('crit_damage')
        self.cooldown_reduction = self.stats.get('cooldown_reduction')
        self.armor = int(self.stats.get('armor'))
        self.status_radius = self.stats.get('status_radius')
        self.increased_vulnerable_damage = self.stats.get('increased_vulnerable_damage')
        self.burn_damage_increase = self.stats.get('burn_damage_increase')
        self.freeze_duration_bonus = self.stats.get('freeze_duration_bonus')
        self.freeze_threshold_reduction = self.stats.get('freeze_threshold_reduction')
        self.shock_chain_bonus = self.stats.get('shock_chain_bonus')
        self.shock_range_bonus = self.stats.get('shock_range_bonus')
        self.extra_projectiles = int(self.stats.get('projectile_count'))
        self.projectile_speed_increase = self.stats.get('projectile_speed')
        self.attack_radius_increase = self.stats.get('attack_radius')

        # Resistances from gear (percent per element), set by recompute pipeline.
        self.resistances = {}

        # Leveling system (curve + caps come from data/tuning.json)
        self.level = 1
        self.max_level = leveling.max_level()
        self.experience = 0
        self.skill_points = 0
        self.xp_to_level = leveling.xp_to_next(1)
        self.on_level_up = Event()  # fires (new_level); HUD shows the cue
        
        # Wallet system: copper, silver (10 copper), gold (10 silver), diamond (10 gold)
        self.copper = 0
        self.silver = 0
        self.gold = 0
        self.diamond = 0

        # Endgame progression (Phase 5): highest Greater Rift cleared
        self.highest_gr = 0
        
        # Equipment: wand damage multiplier
        self.wand_level = 0
        self.wand_damage_bonus = 0  # Will be additive or multiplicative
        
        # Skill tree allocations
        self.skill_allocations = {}
        self.skill_tree_bonuses = {
            'fireball_damage': 0,
            'frostbolt_damage': 0,
            'lightning_damage': 0,
            'spell_damage': 0,
        }
        
        # Skills and cooldowns
        self.active_skill = 0  # 0: Fireball, 1: Frost Bolt, 2: Lightning Strike
        self.skill_cooldowns = {0: 0, 1: 0, 2: 0}
        self.skill_costs = {0: 20, 1: 15, 2: 25}  # Mana costs
        
        # Keystone effects (set by keystones)
        self.elemental_focus_active = False
        self.spell_echo_active = False
        self.spell_echo_count = 1
        self.spell_echo_cooldown_reduction = 0.0
        self.omnivamp_active = False
        self.life_steal_percent = 0.0
        self.life_steal_multiplier = 1.0
        self.projectile_mastery_active = False
        self.projectile_chain_bonus = 0
        self.projectile_pierce_bonus = 0
        
    def handle_input(self, keys):
        """Handle player input for movement and attacks."""
        self.velocity_x = 0
        self.velocity_y = 0
        
        # Movement
        if keys[pygame.K_w]:
            self.velocity_y = -self.speed
        if keys[pygame.K_s]:
            self.velocity_y = self.speed
        if keys[pygame.K_a]:
            self.velocity_x = -self.speed
        if keys[pygame.K_d]:
            self.velocity_x = self.speed
        # Active-skill selection (keys 1-8) is handled by the Game (Phase 13).
    
    def update(self, game_map=None, dt=1.0 / 60.0):
        """Update player position and regenerate resources (dt in seconds)."""
        # Update position
        self.x += self.velocity_x
        self.y += self.velocity_y

        # Map boundaries (only in bounded maps; the streaming world is infinite)
        if game_map and getattr(game_map, "bounded", True):
            self.x = max(self.width // 2, min(self.x, game_map.width - self.width // 2))
            self.y = max(self.height // 2, min(self.y, game_map.height - self.height // 2))

        # Update rect position
        self.rect.center = (self.x, self.y)

        # Animation state: facing follows the dominant movement axis; the cast
        # pose lingers briefly after a spell (set via notify_cast()).
        if self.velocity_x or self.velocity_y:
            if abs(self.velocity_x) > abs(self.velocity_y):
                self.facing = "right" if self.velocity_x > 0 else "left"
            else:
                self.facing = "down" if self.velocity_y > 0 else "up"
        self._moving = bool(self.velocity_x or self.velocity_y)
        if self._cast_pose > 0:
            self._cast_pose = max(0.0, self._cast_pose - dt)
        self._last_dt = dt

        # Resource regeneration (per second, dt-based -- DESIGN.md R3/Phase 2)
        if self.mana < self.max_mana:
            self.mana = min(self.max_mana, self.mana + self.mana_regen * dt)
        if self.health < self.max_health:
            self.health = min(self.max_health, self.health + self.health_regen * dt)

        # Update skill cooldowns (frame-based countdown)
        for skill_id in self.skill_cooldowns:
            if self.skill_cooldowns[skill_id] > 0:
                self.skill_cooldowns[skill_id] -= 1

    def recompute(self):
        """Write effective stat values from self.stats into the cached attributes."""
        self.max_health = int(self.stats.get('max_health'))
        self.max_mana = int(self.stats.get('max_mana'))
        self.move_speed = self.stats.get('move_speed')
        self.speed = self.move_speed
        self.mana_regen = self.stats.get('mana_regen')
        self.health_regen = self.stats.get('health_regen')
        self.damage = int(self.stats.get('damage'))
        self.attack_speed = self.stats.get('attack_speed')
        self.crit_chance = self.stats.get('crit_chance')
        self.crit_damage = self.stats.get('crit_damage')
        self.cooldown_reduction = self.stats.get('cooldown_reduction')
        self.armor = int(self.stats.get('armor'))
        self.status_radius = self.stats.get('status_radius')
        self.increased_vulnerable_damage = self.stats.get('increased_vulnerable_damage')
        # Ailment scaling (Phase 9)
        self.burn_damage_increase = self.stats.get('burn_damage_increase')
        self.freeze_duration_bonus = self.stats.get('freeze_duration_bonus')
        self.freeze_threshold_reduction = self.stats.get('freeze_threshold_reduction')
        self.shock_chain_bonus = self.stats.get('shock_chain_bonus')
        self.shock_range_bonus = self.stats.get('shock_range_bonus')
        # Ascendancy-driven stats (Phase 15)
        self.life_leech = self.stats.get('life_leech')
        self.minion_damage_increase = self.stats.get('minion_damage_increase')
        # Projectile scaling from the passive tree (read by Skill.cast_plan).
        self.extra_projectiles = int(self.stats.get('projectile_count'))
        self.projectile_speed_increase = self.stats.get('projectile_speed')
        self.attack_radius_increase = self.stats.get('attack_radius')
        self.clamp_pools()

    def get_resistance(self, element):
        """Return resistance percent (0-75) for an element; used by combat."""
        return self.resistances.get(element, 0)

    def armor_damage_reduction(self):
        """Fraction of incoming physical damage mitigated by Armor.

        Diminishing-returns curve (Diablo/PoE style): armor is weighed against a
        level-scaled constant so early armor matters but stacking it has falloff.
        Capped at 75% so armor alone can never trivialize damage.
        """
        armor = max(0, getattr(self, 'armor', 0))
        denom = armor + 100 + 10 * self.level
        return min(0.75, armor / denom) if denom > 0 else 0.0

    def clamp_pools(self):
        """Keep current health/mana within the (possibly changed) maximums."""
        self.health = min(self.health, self.max_health)
        self.mana = min(self.mana, self.max_mana)

    def heal(self, amount):
        """Heal the player."""
        self.health = min(self.health + amount, self.max_health)
    
    def restore_mana(self, amount):
        """Restore mana to the player."""
        self.mana = min(self.mana + amount, self.max_mana)
    
    def can_cast_skill(self, skill_id):
        """Check if player can cast the specified skill."""
        if skill_id not in self.skill_cooldowns:
            return False
        if self.skill_cooldowns[skill_id] > 0:
            return False
        if self.mana < self.skill_costs[skill_id]:
            return False
        return True
    
    def cast_skill(self, skill_id):
        """Cast a skill if available."""
        if not self.can_cast_skill(skill_id):
            return None
        
        self.mana -= self.skill_costs[skill_id]
        # Apply attack speed multiplier to cooldowns
        cooldowns = {0: 30, 1: 25, 2: 35}
        self.skill_cooldowns[skill_id] = max(5, int(cooldowns[skill_id] / self.attack_speed))
        return skill_id
    
    def get_xp_requirement(self, level):
        """XP required to advance from the given level (data-driven curve)."""
        return leveling.xp_to_next(level)

    def add_experience(self, amount):
        """Add experience and handle leveling. Returns levels gained."""
        return leveling.gain_xp(self, amount)
    
    def add_money(self, copper=0, silver=0, gold=0, diamond=0):
        """Add money to wallet."""
        self.copper += copper
        self.silver += silver
        self.gold += gold
        self.diamond += diamond
        self.normalize_wallet()
    
    def normalize_wallet(self):
        """Convert excess smaller coins to larger denominations."""
        if self.copper >= 10:
            self.silver += self.copper // 10
            self.copper %= 10
        if self.silver >= 10:
            self.gold += self.silver // 10
            self.silver %= 10
        if self.gold >= 10:
            self.diamond += self.gold // 10
            self.gold %= 10
    
    def get_total_money_value(self):
        """Get total wallet value in copper."""
        return (self.diamond * 1000 + self.gold * 100 + 
                self.silver * 10 + self.copper)
    
    def spend_money(self, copper_amount):
        """Spend money. Returns True if successful."""
        total = self.get_total_money_value()
        if total < copper_amount:
            return False
        
        # Spend from largest to smallest
        remaining = copper_amount
        
        if self.diamond > 0:
            diamonds_spent = min(self.diamond, remaining // 1000)
            self.diamond -= diamonds_spent
            remaining -= diamonds_spent * 1000
        
        if self.gold > 0:
            gold_spent = min(self.gold, remaining // 100)
            self.gold -= gold_spent
            remaining -= gold_spent * 100
        
        if self.silver > 0:
            silver_spent = min(self.silver, remaining // 10)
            self.silver -= silver_spent
            remaining -= silver_spent * 10
        
        self.copper -= remaining
        return True
    
    def upgrade_wand(self, cost_copper=100):
        """Upgrade wand. Returns True if successful."""
        if not self.spend_money(cost_copper):
            return False
        
        self.wand_level += 1
        # Wand provides additive damage bonus per level
        old_bonus = self.wand_damage_bonus
        self.wand_damage_bonus = self.wand_level * 2  # 2 damage per level
        
        # Check if multiplicative would be better
        multiplicative_bonus = 1.0 + (self.wand_level * 0.05)  # 5% per level
        additive_bonus = self.wand_damage_bonus
        
        # If multiplicative is better, use that instead
        if self.damage * multiplicative_bonus > self.damage + additive_bonus:
            self.wand_damage_bonus = multiplicative_bonus
        
        return True
    
    def set_skill_tree_layer(self, skill_tree):
        """Populate the 'tree' stats layer + spell bonuses from allocated nodes."""
        effects = skill_tree.get_active_effects()
        self.stats.set_layer('tree', effects_to_stats(effects))

        # Spell-damage bonuses (% increases) are not core Stats; keep them in
        # their own dict. Collect every "*_damage" key generically so spell,
        # element, and per-skill damage nodes all apply via get_spell_damage.
        self.skill_tree_bonuses = {k: v for k, v in effects.items()
                                   if k.endswith('_damage')}
        # Canonical keys always present (older code/tests read them with .get).
        for key in ('spell_damage', 'fireball_damage', 'frostbolt_damage',
                    'lightning_damage', 'fire_damage'):
            self.skill_tree_bonuses.setdefault(key, 0)

    def reset_keystone_flags(self):
        """Reset all keystone-driven behavior flags to defaults."""
        self.elemental_focus_active = False
        self.spell_echo_active = False
        self.spell_echo_count = 1
        self.spell_echo_cooldown_reduction = 0.0
        self.omnivamp_active = False
        self.life_steal_percent = 0.0
        self.life_steal_multiplier = 1.0
        self.projectile_mastery_active = False
        self.projectile_chain_bonus = 0
        self.projectile_pierce_bonus = 0
        # Ascendancy keystone flags (Phase 15)
        self.eternal_flame = False
        self.overcharged = False

    def apply_skill_tree_bonuses(self, skill_tree):
        """Apply all bonuses from the skill tree, including keystones.

        Routes node bonuses through the Stats layer (single source of truth) and
        then applies keystone flags/effects on top.
        """
        from src.spells.keystones import get_keystone_for_node

        self.reset_keystone_flags()
        self.set_skill_tree_layer(skill_tree)
        self.recompute()

        # Apply active keystones (flags + small write-through stat bumps).
        for node_id in skill_tree.get_active_keystones():
            keystone = get_keystone_for_node(node_id)
            if keystone:
                keystone.apply_to_player(self)

        self.clamp_pools()
    
    def notify_cast(self, duration=0.25):
        """Trigger the cast pose for a short time (called when a spell fires)."""
        self._cast_pose = duration
        # Face the way we're moving stays; casting doesn't override facing here.

    def draw(self, surface, cam=(0, 0)):
        """Draw the animated battle-mage sprite, camera-offset and foot-anchored."""
        frame, bob = self.sprite.frame(self.facing, self._moving,
                                       self._cast_pose, self._last_dt)
        fw, fh = frame.get_size()
        # Anchor the sprite's feet near the collision center so it lines up with
        # shadows/other actors; center horizontally, bias downward slightly.
        sx = self.x - cam[0] - fw // 2
        sy = self.y - cam[1] - fh + self.height // 2 + 4 + bob
        surface.blit(frame, (int(sx), int(sy)))
    
    def get_status(self):
        """Return player status as string."""
        return f"Lvl: {self.level}/{self.max_level} | HP: {self.health:.0f}/{self.max_health} | Mana: {self.mana:.0f}/{self.max_mana}"
    
    # Maps an active-skill id to its tree "increased damage" bonus key.
    _SKILL_DAMAGE_KEY = {
        'fireball': 'fireball_damage',
        'ice_shard': 'frostbolt_damage',
        # chain_lightning is covered by the 'lightning' element bonus below.
    }

    def get_spell_damage(self, base_damage, element=None, skill_id=None):
        """Total spell damage: flat assembly then % increases from the tree/gear.

        Flat = base + generic damage (tree+gear `damage`) + wand. The percentage
        layer sums Increased Spell Damage, the matching element's Increased
        Damage, and the skill's own Increased Damage -- so allocating tree nodes
        (and equipping gear) actually scales each skill (DESIGN.md R1).
        """
        damage = base_damage + self.damage

        # Apply wand bonus (flat or multiplicative, whichever the wand chose).
        if isinstance(self.wand_damage_bonus, float):
            damage = damage * self.wand_damage_bonus
        else:
            damage += self.wand_damage_bonus

        # Percentage increases (values are stored as percent points, e.g. 18 = 18%).
        b = self.skill_tree_bonuses
        pct = b.get('spell_damage', 0)
        if element is not None:
            pct += b.get(f"{element}_damage", 0)
        if skill_id:
            key = self._SKILL_DAMAGE_KEY.get(skill_id)
            if key:
                pct += b.get(key, 0)

        return damage * (1.0 + pct / 100.0)
