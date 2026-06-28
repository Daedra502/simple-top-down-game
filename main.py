import pygame
import sys
import math
import random
from src.entities.player import Player
from src.entities.boss import Boss, boss_keys
from src.entities.chest import Chest
from src.systems.world import WorldManager
from src.systems.rift import RiftManager, NORMAL, GREATER
from src.systems.spawn_director import SpawnDirector
from src.progression import AscendancyManager, AtlasManager
from src.core import save as save_system
from src.systems.combat import CombatSystem
from src.systems.collision import CollisionSystem
from src.spells.spells import SPELLS, Projectile
from src.spells.spells_with_gems import SPELLS_WITH_GEMS, cast_spell_with_gems
from src.spells.active_skills import SkillManager
from src.systems.quests import QuestManager
from src.entities.minion import Minion
from src.spells.skill_tree import SkillTree
from src.ui.ui_components import SkillBarUI, SkillTreeUI
from src.ui.health_bars import PlayerResourcesUI, EnemyHealthBar, DamageNumberManager
from src.ui.character_sheet import CharacterSheetUI
from src.ui.tooltip import ItemTooltip
from src.audio import get_sound_manager
from src.items.inventory import ItemManager, Inventory, EquipmentSlots
from src.items.item import ItemFactory
from src.spells.elements import ElementType, ElementalEffectManager
from src.spells.gems import GemLibrary

class Game:
    """Main game class handling the game loop and logic."""

    # Pylon shrines (Phase 16): spawn as the player travels a linear rift.
    PYLON_PICKUP_RADIUS = 45
    PYLON_BUFF_DURATION = 12.0
    CONDUIT_RADIUS = 260          # Conduit pylon electrocute radius
    CONDUIT_TICK = 0.4            # seconds between conduit zaps
    CONDUIT_BASE_DAMAGE = 30

    # Minimap (Phase 16): PoE2-style corner map.
    MINIMAP_SIZE = 200
    MINIMAP_VIEW = 1500          # world-px radius shown around the player

    # Forking projectiles (Lightning Spark): chain to nearby enemies on hit.
    FORK_RANGE = 360            # max distance a fork will reach for a new target
    FORK_DAMAGE_FALLOFF = 0.8   # each fork deals this fraction of the parent's damage

    # Homing projectiles: how sharply they bend toward a target per frame.
    HOMING_TURN = 0.22          # 0..1 lerp of velocity toward the target direction
    HOMING_RANGE = 600          # only seek enemies within this distance

    # Save/Load slot UI (Phase 17).
    NUM_SAVE_SLOTS = 5

    def __init__(self, width=1200, height=800):
        pygame.init()
        
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Top-Down ARPG")
        
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.dt = 1.0 / 60.0  # seconds; updated each frame in run()
        self.running = True
        self.paused = False
        self.show_pause_menu = False  # Esc opens this menu (options + keybinds + quit)
        self.show_controls = False    # keybind reference is collapsed by default
        self._pause_buttons = []      # [(rect, action)] rebuilt each draw
        self._volume_sliders = []     # [(track_rect, knob_rect, kind)]
        self._dragging_slider = None  # 'sfx' | 'music' while a knob is held

        # Clickable hit-rects rebuilt each frame while the inventory is open,
        # so handle_events() can map a click to an item action.
        self._inv_item_rects = []    # [(rect, item)]  -> left=equip, right=sell
        self._equip_item_rects = []  # [(rect, slot, item)] -> left=unequip
        self._dropped_item_rects = []  # [(rect, item)] -> ground-item hover tooltips
        self.item_tooltip = ItemTooltip()

        # Per-spell mastery ("Spell Trees") overlay state (Phase 16).
        self.show_spell_tree = False
        self.spell_tree_selected = 0
        self._spell_tab_rects = []   # [(rect, index)]
        self._spell_node_rects = []  # [(rect, skill_id, node_id)]
        
        # Game systems
        self.world = WorldManager()           # endless streaming world (Phase 11)
        self.combat_system = CombatSystem()
        self.collision_system = CollisionSystem()
        self.skill_tree = SkillTree()
        
        # UI components
        self.skill_bar_ui = SkillBarUI(0, height - 100, width, 100)
        self.skill_tree_ui = SkillTreeUI(self.skill_tree, width - 100, height - 100)
        self.player_ui = PlayerResourcesUI(10, 10, 300)
        self.damage_numbers = DamageNumberManager()
        self.enemy_health_bars = {}  # Map enemy to health bar
        
        # Create character sheet UI (initialized later when item_manager is ready)
        self.character_sheet_ui = None
        self.show_character_sheet = False
        
        # Game entities -- player starts at the world origin (Phase 11)
        self.player = Player(0, 0)

        # Level-up feedback cue (Phase 3)
        self.level_up_cue_time = 0.0
        self.level_up_level = 0
        self.player.on_level_up.subscribe(self._on_level_up)

        # Active skills (Phase 13) + rune effects (Phase 14)
        self.skills = SkillManager()
        self.sound = get_sound_manager()   # synthesized attack SFX + ambient music
        self.sound.start_music()
        self.auto_aim = False              # Vampire-Survivors-style auto-fire toggle
        # Quests (Phase 18): one active objective at a time from a 50-quest pool.
        self.quests = QuestManager(reward_cb=self._on_quest_reward)
        self.minions = []
        self.aoe_effects = []   # transient AoE visuals
        self.ground_zones = []  # lingering damage zones (Lingering Ground rune)

        # Rift / Greater Rift engine (Phase 5) + spawn director (Phase 12)
        self.rift = RiftManager()
        self.director = SpawnDirector()
        self.boss_key_pool = boss_keys()

        # Endgame progression (Phase 15)
        self.ascendancy = AscendancyManager()
        self.atlas = AtlasManager()
        self.show_progression = False
        self.rift_boss = None
        self.show_gr_picker = False
        self.gr_selected_level = 1
        self.rift_message = ""
        self.rift_message_time = 0.0
        self.progress_orbs = []  # rift progress orbs from Vulnerable enemies (Phase 7)

        # Pylon shrines + linear-rift travel tracking (Phase 16).
        self.pylons = []                 # [{x, y, type, taken}]
        self.pylon_speed_timer = 0.0     # Speed pylon buff remaining
        self.pylon_conduit_timer = 0.0   # Conduit pylon buff remaining
        self._conduit_tick = 0.0
        self.show_minimap = True
        self.minimap_visited = set()     # chunk coords for the minimap trail
        self._reset_rift_exploration()

        # Town hub (Phase 18): safe area with stash / merchant / smith stations.
        self.in_town = False
        self.town_return = None          # world pos to resume at when leaving town
        self.town_center = (0.0, 0.0)
        self.town_stations = []          # [{name, x, y, key, color}]
        self.stash = []                  # persistent stored items
        self.STASH_CAPACITY = 60
        self.show_stash = False
        self._stash_left_rects = []      # backpack rows in the stash overlay
        self._stash_right_rects = []     # stash rows in the stash overlay
        self._near_station = None        # station the player can interact with (E)

        # Save/Load slot menu (Phase 17).
        self.show_save_menu = False
        self.active_save_slot = 0
        self._save_slot_rects = []       # [(rect, slot_index)]
        # Pending Save/Load confirmation: {'action': 'load'|'save', 'slot': i} or None.
        self.save_confirm = None
        self._save_confirm_rects = []    # [(rect, 'yes'|'no')]

        # Projectiles in the air
        self.projectiles = []
        
        # UI
        self.font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 18)
        
        # Game state
        self.game_over = False
        self.won = False
        self.show_skill_tree = False
        self.show_inventory = False
        
        # Item system
        self.item_manager = ItemManager(self.player, capacity=20)
        self.dropped_items = []  # Items on the ground waiting to be picked up
        
        # Initialize character sheet UI now that we have item_manager
        self.character_sheet_ui = CharacterSheetUI(self.player, self.skill_tree,
                                                   self.item_manager, 100, 80, 700, 600)

        # Town hub stations (Phase 18) placed around the town center.
        self._init_town_stations()

        # Pick the first rift's map layout (Phase 18).
        self._apply_map_layout()

    # --- camera (Phase 11): the player is kept centered on screen -----------
    @property
    def cam(self):
        """Top-left world coordinate of the viewport."""
        return (self.player.x - self.width // 2, self.player.y - self.height // 2)

    def screen_to_world(self, sx, sy):
        cx, cy = self.cam
        return (sx + cx, sy + cy)

    def handle_events(self):
        """Handle user input and events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                # Pause menu captures input while open (resume / quit)
                if self.show_pause_menu:
                    self._handle_pause_menu_keys(event.key)
                    continue
                # Greater Rift picker captures input while open
                if self.show_gr_picker:
                    self._handle_gr_picker_keys(event.key)
                    continue
                # Ascendancy/Atlas overlay captures input while open (Phase 15)
                if self.show_progression:
                    self._handle_progression_keys(event.key)
                    continue
                # Save/Load confirmation dialog captures input while open
                if self.show_save_menu and self.save_confirm is not None:
                    self._handle_save_menu_keys(event.key)
                    continue
                # Stash overlay captures input while open (Esc/E closes it)
                if self.show_stash:
                    if event.key in (pygame.K_ESCAPE, pygame.K_e):
                        self.show_stash = False
                    continue
                if event.key == pygame.K_ESCAPE:
                    # On the end screens Esc still exits; otherwise it opens the
                    # pause menu instead of closing the game.
                    if self.game_over or self.won:
                        self.running = False
                    else:
                        self.show_pause_menu = True
                        self.paused = True
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_t:
                    self._toggle_town()              # Town portal (Phase 18)
                elif event.key == pygame.K_p:
                    self.show_skill_tree = not self.show_skill_tree   # passive tree
                elif event.key == pygame.K_e:
                    # Interact with a town station (or close the stash).
                    if self.in_town and self._near_station:
                        self._interact_station()
                elif event.key == pygame.K_i:
                    self.show_inventory = not self.show_inventory
                elif event.key == pygame.K_k:
                    self.show_spell_tree = not self.show_spell_tree
                elif event.key == pygame.K_m:
                    self.show_minimap = not self.show_minimap
                elif event.key == pygame.K_l:
                    self.show_save_menu = not self.show_save_menu
                    self.save_confirm = None  # never leave a stale dialog pending
                elif event.key == pygame.K_c:
                    self.show_character_sheet = not self.show_character_sheet
                elif event.key == pygame.K_v:
                    self.show_progression = not self.show_progression
                elif event.key == pygame.K_g:
                    # Open the GR picker (only meaningful with a keystone)
                    self.gr_selected_level = max(1, self.player.highest_gr + 1)
                    self.show_gr_picker = True
                elif event.key == pygame.K_F5:
                    self.save_game()
                elif event.key == pygame.K_F9:
                    self.load_game()
                elif self.show_spell_tree and pygame.K_1 <= event.key <= pygame.K_3:
                    # While the spell-tree menu is open, 1-3 pick the spell tab.
                    self.spell_tree_selected = event.key - pygame.K_1
                elif event.key == pygame.K_f:
                    # Toggle Vampire-Survivors-style auto-fire.
                    self.auto_aim = not self.auto_aim
                    self._set_rift_message(
                        "Auto-fire ON" if self.auto_aim else "Auto-fire OFF")
                elif pygame.K_1 <= event.key <= pygame.K_8:
                    # Select active skill 1-8 (Phase 13)
                    idx = event.key - pygame.K_1
                    if idx < len(self.skills.slots):
                        self.player.active_skill = idx
            elif event.type == pygame.MOUSEWHEEL and not self._modal_open():
                # Scroll wheel cycles the selected active skill.
                n = len(self.skills.slots)
                if n:
                    self.player.active_skill = (self.player.active_skill - event.y) % n
            elif event.type == pygame.MOUSEBUTTONDOWN and self.show_pause_menu:
                self._handle_pause_menu_click(event.pos, event.button)
            elif event.type == pygame.MOUSEMOTION and self.show_pause_menu:
                if self._dragging_slider and event.buttons[0]:
                    self._drag_volume(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and self.show_pause_menu:
                if self._dragging_slider:
                    self.sound.save_settings()   # persist once the drag finishes
                self._dragging_slider = None
            elif event.type == pygame.MOUSEBUTTONDOWN and self.show_inventory:
                # Left-click: equip backpack item / unequip gear.
                # Right-click: sell backpack item for copper.
                self._handle_inventory_click(event.pos, event.button)
            elif event.type == pygame.MOUSEBUTTONDOWN and self.show_spell_tree:
                self._handle_spell_tree_click(event.pos, event.button)
            elif event.type == pygame.MOUSEBUTTONDOWN and self.show_save_menu:
                self._handle_save_menu_click(event.pos, event.button)
            elif event.type == pygame.MOUSEBUTTONDOWN and self.show_stash:
                self._handle_stash_click(event.pos, event.button)
            elif event.type == pygame.MOUSEBUTTONDOWN and self.show_skill_tree:
                if event.button == 1:  # Left click
                    self.skill_tree_ui.handle_click(event.pos, self.player)
            elif event.type == pygame.MOUSEMOTION and self.show_skill_tree:
                buttons = pygame.mouse.get_pressed()
                self.skill_tree_ui.handle_mouse_motion(event.pos, buttons)
    
    def handle_input(self):
        """Handle continuous input (movement, casting)."""
        keys = pygame.key.get_pressed()
        
        # Movement input
        self.player.handle_input(keys)
        
        # Mouse input for casting the active skill (target in world space).
        # Suppressed while a modal overlay/menu owns the mouse, or while the town
        # hub is open (no combat in town), or while auto-fire is doing the aiming.
        if (pygame.mouse.get_pressed()[0] and not self._modal_open()
                and not self.in_town and not self.auto_aim):  # Left click
            mouse_x, mouse_y = pygame.mouse.get_pos()
            world_mx, world_my = self.screen_to_world(mouse_x, mouse_y)
            skill = self.skills.slot(self.player.active_skill)
            self._try_cast(skill, world_mx, world_my)

    def _try_cast(self, skill, tx, ty):
        """Spend mana, start the cooldown, award XP, play the SFX, and execute a
        cast at (tx, ty). Single funnel used by manual clicks and auto-fire so
        sound and bookkeeping are identical for both. Returns True if it fired.
        """
        if not skill or not skill.can_cast(self.player):
            return False
        self.player.mana -= skill.mana_cost
        skill.start_cooldown(self.player)
        self.skills.award_cast(skill.id)
        self.sound.play_skill(skill)
        self._execute_cast(skill.cast_plan(self.player, tx, ty), skill)
        return True

    def _auto_fire(self):
        """Auto-aim/auto-cast the active skill at the nearest enemy (toggle).

        Mirrors Vampire Survivors / Mega Bonk: with auto-fire on, the active
        skill is loosed automatically at the closest enemy whenever it is off
        cooldown and affordable -- no clicking or aiming required.
        """
        skill = self.skills.slot(self.player.active_skill)
        if not skill or not skill.can_cast(self.player):
            return
        target = self._nearest_enemy(self.player.x, self.player.y)
        if target is None:
            return
        self._try_cast(skill, target.x, target.y)
    
    def update(self):
        """Update game state."""
        # Opening any menu/overlay (inventory, passive tree, spell trees,
        # character sheet, GR picker, progression, pause menu) freezes the world.
        if self.paused or self.game_over or self.won or self._modal_open():
            return
        
        current_map = self.world

        # Stream chunks in/out as the player moves (Phase 11)
        self.world.update_world(self.player)

        # In the town hub, skip rift travel/spawning; just track station proximity.
        if self.in_town:
            self.player.update(current_map, self.dt)
            self.recompute_player_stats()
            self.player_ui.update(self.player, self.dt)
            self._update_town()
            if self.rift_message_time > 0:
                self.rift_message_time -= self.dt
            return

        # Linear rift progression: travel through chunks spawns pylons + boss.
        self._update_rift_exploration()

        # Update player
        self.player.update(current_map, self.dt)

        # Recompute effective stats from all sources (tree + gear + set bonuses)
        # through the single Stats source of truth.
        self.recompute_player_stats()

        # Rift boss blink: teleport near the player at random intervals.
        if self.rift_boss is not None and self.rift_boss.health > 0:
            self.rift_boss.maybe_teleport(self.player, self.dt)

        # Update enemies (dt drives ailment ticks: burn DoT, freeze/slow timers)
        current_map.update(self.player, self.dt)

        # Update projectiles and handle collisions
        self.update_projectiles(current_map)

        # Auto-fire (Vampire-Survivors style) loosens the active skill at the
        # nearest enemy when the toggle is on.
        if self.auto_aim and not self.in_town:
            self._auto_fire()

        # Check for chest openings
        for chest in current_map.chests:
            if not chest.opened:
                dx = self.player.x - chest.x
                dy = self.player.y - chest.y
                distance = math.sqrt(dx**2 + dy**2)
                
                if distance < 40:
                    rewards = chest.open()
                    if rewards:
                        self.player.add_money(
                            copper=rewards['copper'],
                            silver=rewards['silver'],
                            gold=rewards['gold'],
                            diamond=rewards['diamond']
                        )
                        self.player.add_experience(rewards['xp'])
                        self.quests.notify('open_chest', 1)

        # Enemy attacks
        self.handle_enemy_attacks()
        
        # Update player UI
        self.player_ui.update(self.player, self.dt)

        # Update enemy health bars; subscribe the death hook the first time we
        # see an enemy so XP/loot/money fire from one place (DESIGN.md Phase 1).
        for enemy in current_map.enemies:
            if enemy not in self.enemy_health_bars:
                self.enemy_health_bars[enemy] = EnemyHealthBar(enemy)
                enemy.on_death.subscribe(self._on_enemy_death)
            self.enemy_health_bars[enemy].update(self.dt)

        # Remove health bars for dead enemies
        dead_enemies = [e for e in self.enemy_health_bars if e not in current_map.enemies]
        for enemy in dead_enemies:
            del self.enemy_health_bars[enemy]

        # Update damage numbers
        self.damage_numbers.update(self.dt)

        # Active skills: tick cooldowns, minions, AoE visuals, ground zones
        self.skills.update(self.dt)
        self._update_minions()
        self._update_aoe_effects()
        self._update_ground_zones()

        # Tick down the level-up cue
        if self.level_up_cue_time > 0:
            self.level_up_cue_time -= self.dt

        # Update dropped items - check for pickup and expiration
        for dropped in self.dropped_items[:]:
            dropped['time_to_live'] -= self.dt
            
            # Check if player is close enough to pick up
            dx = self.player.x - dropped['x']
            dy = self.player.y - dropped['y']
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance < 40:  # Auto-pickup radius
                if self.item_manager.inventory.add_item(dropped['item']):
                    self.dropped_items.remove(dropped)
                    self.quests.notify('collect_loot', 1)
            elif dropped['time_to_live'] <= 0:
                # Remove expired item
                self.dropped_items.remove(dropped)
        
        # Rift engine: tick timers; spawn director populates the world (Phase 12)
        self.rift.update(self.dt)
        self.director.update(self, self.dt)
        self._update_progress_orbs()
        self._update_pylons()
        if self.rift_message_time > 0:
            self.rift_message_time -= self.dt

        # Check if player is dead
        if self.player.health <= 0:
            self.game_over = True
    
    def recompute_player_stats(self):
        """Rebuild the player's Stats layers from every source, then write through.

        Single source of truth (DESIGN.md R1): skill tree -> 'tree' layer,
        equipped gear -> 'gear' layer, set bonuses -> 'set' layer.
        """
        p = self.player
        p.reset_keystone_flags()
        p.set_skill_tree_layer(self.skill_tree)
        # Gear "increased damage" affixes add to the same spell-damage bonuses
        # the tree feeds, so items and passives stack on every skill.
        for stat, val in self.item_manager.get_spell_damage_bonuses().items():
            p.skill_tree_bonuses[stat] = p.skill_tree_bonuses.get(stat, 0) + val
        p.stats.set_layer('gear', self.item_manager.get_gear_stats())
        p.stats.set_layer('set', self.item_manager.get_set_stats())
        p.stats.set_layer('ascendancy', self.ascendancy.get_stat_layer())  # Phase 15
        # Speed pylon buff (Phase 16): temporary attack + move speed.
        if self.pylon_speed_timer > 0:
            p.stats.set_layer('pylon', {'attack_speed': 0.5, 'move_speed_increase': 0.4})
        else:
            p.stats.set_layer('pylon', {})
        p.resistances = self.item_manager.get_resistances()
        p.recompute()

        # Ascendancy keystone flags (Eternal Flame / Overcharged, Phase 15).
        for flag in self.ascendancy.get_flags():
            setattr(p, flag, True)

        # Atlas reshapes the world: push biome weights into the generator.
        self.world.biome_weights = self.atlas.get_effects()['biome_weight']

        # Keystones apply flags/effects on top of the recomputed stats.
        from src.spells.keystones import get_keystone_for_node
        for node_id in self.skill_tree.get_active_keystones():
            keystone = get_keystone_for_node(node_id)
            if keystone:
                keystone.apply_to_player(p)
        p.clamp_pools()
    
    def save_game(self, slot=0):
        """Persist the full character to a JSON slot (Phase 10)."""
        try:
            save_system.save_to_slot(self, slot)
            self._set_rift_message("Game saved")
        except Exception as exc:  # never let a save error crash the loop
            self._set_rift_message(f"Save failed: {exc}")

    def load_game(self, slot=0):
        """Reload the character from a JSON slot and recompute stats (Phase 10).

        Returns True on success, False if there was no save (errors are caught).
        """
        try:
            if save_system.load_from_slot(self, slot):
                self.rift.start_normal()       # resume in a fresh normal rift
                self._apply_map_layout()
                self._reset_rift_exploration()
                self.rift_boss = None
                self.progress_orbs.clear()
                self.enemy_health_bars.clear()
                self.minions.clear()
                self.aoe_effects.clear()
                self.ground_zones.clear()
                self._set_rift_message("Game loaded")
                return True
            self._set_rift_message("No save found")
            return False
        except Exception as exc:
            self._set_rift_message(f"Load failed: {exc}")
            return False

    def _on_level_up(self, new_level):
        """Level-up hook: trigger the on-screen feedback cue (Phase 3)."""
        self.level_up_cue_time = 2.5
        self.level_up_level = new_level
        self.quests.notify('level_up', 1)

    def _on_quest_reward(self, xp, copper):
        """Pay out a completed quest's XP + copper and announce the next one."""
        if xp:
            self.player.add_experience(xp)
        if copper:
            self.player.add_money(copper=copper)
        nxt = self.quests.current
        nxt_desc = f"  Next: {nxt['desc']}" if nxt else ""
        self._set_rift_message(f"Quest complete! +{xp} XP +{copper}c.{nxt_desc}")

    def _on_enemy_death(self, enemy):
        """Death hook (Phase 1). Routes to three *independent* concerns:
          - rewards (XP/gold),
          - the LOOT system (Phase 6: equipment drops -> inventory),
          - the VULNERABLE system (Phase 7: rift-progress orbs -> rift bar).
        These are deliberately separate -- loot never touches the rift bar and
        orbs never enter the inventory.
        """
        if getattr(enemy, 'is_boss', False):
            self._on_rift_boss_killed(enemy)
            return

        # Retro 8-bit death cue.
        self.sound.play_enemy_death()

        # Rewards
        self.player.add_experience(enemy.experience_reward)
        self._grant_money(enemy.money_reward)
        self.director.notify_kill()          # Phase 12: feeds difficulty pacing

        # Quest progress: every kill, plus a separate elite-kill objective.
        self.quests.notify('kill', 1)
        if getattr(enemy, 'is_elite', False):
            self.quests.notify('kill_elite', 1)

        # Award skill XP to whichever skill landed the kill (Phase 13).
        killer = getattr(enemy, '_last_skill_id', None)
        if killer:
            self.skills.award_kill(killer)
            # Cast On Kill rune: burst a nova where the enemy died (Phase 14).
            kskill = self.skills.get(killer)
            if kskill and 'cast_on_kill' in kskill.runes:
                self._spawn_nova(enemy.x, enemy.y, 90, kskill.stats()['damage'] * 0.5,
                                 kskill.element, kskill)

        # Elite on-death novas (molten/explosive/frozen/...) hit the player.
        if getattr(enemy, 'behaviors', None) and 'on_death' in enemy.behaviors:
            self._apply_elite_on_death(enemy)

        # Two separate drop systems, each owning its own world list + data.
        self._roll_combat_loot(enemy)        # Phase 6 -> self.dropped_items
        self._roll_vulnerable_orb(enemy)     # Phase 7 -> self.progress_orbs

        # Treasure goblins shower extra loot (Phase 12 event).
        if getattr(enemy, 'is_treasure_goblin', False):
            self._drop_loot(enemy.x, enemy.y, enemy.loot_drops)

        # Rift progression: each kill fills the bar; filling spawns the boss.
        self.rift.add_progress(getattr(enemy, 'progress_value', 1))
        if self.rift.ready_for_boss():
            self._spawn_rift_boss()

    def _apply_elite_on_death(self, enemy):
        """Elite on-death novas: damage the player if they're within radius."""
        for nova in enemy.behaviors.get('on_death', []):
            dist = math.hypot(self.player.x - enemy.x, self.player.y - enemy.y)
            if dist <= nova['radius']:
                element = nova.get('element', 'fire')
                dmg = enemy.damage * nova['damage_mult']
                dmg *= max(0.1, 1.0 - self.player.get_resistance(element) / 100.0)
                if self.player.take_damage(dmg):
                    self.game_over = True

    def _roll_combat_loot(self, enemy):
        """LOOT SYSTEM (Phase 6): chance to drop an affix item into the world.

        Equipment loot only; it is collected into the inventory and has nothing
        to do with the Vulnerable status or the rift progress bar.
        """
        if random.random() < self.rift.rift_cfg.get('trash_drop_chance', 0.4):
            self._drop_loot(enemy.x, enemy.y, 1)

    def _roll_vulnerable_orb(self, enemy):
        """VULNERABLE SYSTEM (Phase 7): a Vulnerable enemy may drop a rift orb.

        The orb feeds the rift *progress bar* (never the inventory) and is
        type-matched to the current rift. Entirely separate from combat loot.
        """
        effects = getattr(enemy, 'elemental_effects', None)
        if effects is not None and effects.is_vulnerable():
            self._maybe_drop_progress_orb(enemy.x, enemy.y)

    def _on_rift_boss_killed(self, boss):
        """Rift boss reward: big scaled XP/money/loot, then keystone or GR clear."""
        self.sound.play_enemy_death(boss=True)
        self.player.add_experience(boss.experience_reward)
        self._grant_money(boss.money_reward)
        self.quests.notify('kill_boss', 1)
        for _ in range(self.rift.rift_cfg['boss_loot_drops']):
            self._drop_loot(boss.x, boss.y, 1)

        if self.rift.type == NORMAL:
            n = self.rift.rift_cfg['keystone_reward']
            self.item_manager.add_keystone(n)
            self._set_rift_message(f"Rift cleared! +{n} Rift Keystone")
        else:
            self.player.highest_gr = max(self.player.highest_gr, self.rift.gr_level)
            self.atlas.add_points(1)   # Phase 15: GR clears fund the atlas
            self._set_rift_message(f"Greater Rift {self.rift.gr_level} cleared!  +1 Atlas Point")

        self.rift_boss = None
        self.rift.start_normal()
        self._apply_map_layout()          # fresh themed layout per rift
        self._reset_rift_exploration()
        self._apply_atlas_to_rift()

    def _drop_loot(self, x, y, count):
        # Item level scales with character level + GR level, so deeper rifts
        # roll higher affixes (Phase 6). Atlas loot quality adds rarity (Phase 15).
        ilvl = self.player.level + self.rift.gr_level
        quality = self.atlas.get_effects()['loot_quality']
        for _ in range(count):
            self.dropped_items.append({
                'item': ItemFactory.generate_drop(ilvl, self.rift.gr_level, quality),
                'x': x + random.randint(-20, 20),
                'y': y + random.randint(-20, 20),
                'time_to_live': 10.0,
            })

    def _grant_money(self, money):
        self.player.add_money(
            copper=money.get('copper', 0), silver=money.get('silver', 0),
            gold=money.get('gold', 0), diamond=money.get('diamond', 0),
        )
        # Quest progress measured in copper-equivalent of all coin earned.
        earned = (money.get('copper', 0) + money.get('silver', 0) * 10
                  + money.get('gold', 0) * 100 + money.get('diamond', 0) * 1000)
        if earned:
            self.quests.notify('earn_gold', earned)

    def _set_rift_message(self, text):
        self.rift_message = text
        self.rift_message_time = 3.0

    # --- rift progress orbs (Phase 7) ------------------------------------
    def _maybe_drop_progress_orb(self, x, y):
        """Vulnerable enemies have a chance to drop a type-matched progress orb."""
        vcfg = self._vulnerable_cfg()
        if random.random() >= vcfg['orb_drop_chance']:
            return
        self.progress_orbs.append({
            'x': x + random.randint(-12, 12),
            'y': y + random.randint(-12, 12),
            'type': self.rift.type,                 # yellow (normal) vs purple (GR)
            'color': self.rift.bar_color,
            'value': vcfg['orb_value'],
            'ttl': 12.0,
        })

    def _vulnerable_cfg(self):
        from src.core.data_loader import load_json
        return load_json('ailments.json')['vulnerable']

    def _update_progress_orbs(self):
        """Collect orbs the player walks over (type-matched) and expire old ones."""
        for orb in self.progress_orbs[:]:
            orb['ttl'] -= self.dt
            if math.hypot(self.player.x - orb['x'], self.player.y - orb['y']) < 40:
                if orb['type'] == self.rift.type:    # only matching orbs count
                    self.rift.add_progress(orb['value'])
                    if self.rift.ready_for_boss():
                        self._spawn_rift_boss()
                self.progress_orbs.remove(orb)
            elif orb['ttl'] <= 0:
                self.progress_orbs.remove(orb)

    def draw_progress_orbs(self, cam):
        for orb in self.progress_orbs:
            pos = (int(orb['x'] - cam[0]), int(orb['y'] - cam[1]))
            pygame.draw.circle(self.screen, orb['color'], pos, 7)
            pygame.draw.circle(self.screen, (255, 255, 255), pos, 7, 1)

    # --- spawning helpers (used by the SpawnDirector, Phase 12) -----------
    def _ring_spawn_point(self):
        """A point in a ring around the player -- just off-screen, in world space."""
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(self.width * 0.55, self.width * 0.7)
        return (self.player.x + math.cos(angle) * dist,
                self.player.y + math.sin(angle) * dist)

    def _scale_enemy(self, enemy):
        """Apply GR hp/damage scaling (no-op at GR level 0)."""
        if self.rift.gr_level <= 0:
            return
        enemy.max_health = int(enemy.max_health * self.rift.hp_mult())
        enemy.health = enemy.max_health
        enemy.damage = int(enemy.damage * self.rift.dmg_mult())

    def _spawn_rift_boss(self):
        """Spawn the rift boss near the player and lock trash spawns."""
        self.rift.begin_boss()
        # Prefer the current biome's themed boss pool (Phase 11).
        biome = self.world.current_biome(self.player)
        boss_key = random.choice(biome.get('boss_pool') or self.boss_key_pool)

        angle = random.uniform(0, 2 * math.pi)
        bx = self.player.x + math.cos(angle) * 220
        by = self.player.y + math.sin(angle) * 220

        boss = Boss(bx, by, boss_key,
                    hp_mult=self.rift.hp_mult(),
                    dmg_mult=self.rift.dmg_mult(),
                    reward_mult=self.rift.reward_mult())
        self.world.enemies.append(boss)
        self.rift_boss = boss
        self._set_rift_message(f"{boss.name} has appeared!")

    # --- linear rift travel + pylons (Phase 16) --------------------------
    def _reset_rift_exploration(self):
        """Reset per-rift travel tracking and pylons (on every rift (re)start)."""
        self.pylons = []
        self._rift_visited = set()
        self._rift_last_chunk = None
        layout = getattr(self, 'map_layout', None) or {}
        self._pylon_every = layout.get("pylon_every",
                                       self.rift.rift_cfg.get("pylon_every_chunks", 10))
        self._next_pylon_chunk = self._pylon_every
        self.minimap_visited = set()
        self.pylon_speed_timer = 0.0
        self.pylon_conduit_timer = 0.0

    def _update_rift_exploration(self):
        """Linear progression: count distinct chunks the player travels through,
        advancing the rift and spawning a pylon every N chunks."""
        cur = self.world.chunk_coord(self.player.x, self.player.y)
        if cur not in self._rift_visited:
            self._rift_visited.add(cur)
            self.minimap_visited.add(cur)
            # The spawn chunk doesn't count as travel.
            if self._rift_last_chunk is not None and not self.rift.boss_active:
                self.rift.notify_chunk_travel()
                self.quests.notify('travel', 1)
                if self.rift.chunks_traveled >= self._next_pylon_chunk:
                    self._spawn_pylon()
                    self._next_pylon_chunk += self._pylon_every
                if self.rift.ready_for_boss():
                    self._spawn_rift_boss()
        self._rift_last_chunk = cur

    def _spawn_pylon(self):
        """Drop a pylon shrine ahead of the player along their heading."""
        ptype = random.choice(["conduit", "speed"])
        hx, hy = self.player.velocity_x, self.player.velocity_y
        ang = math.atan2(hy, hx) if (hx or hy) else random.uniform(0, 2 * math.pi)
        dist = random.uniform(220, 320)
        self.pylons.append({
            "x": self.player.x + math.cos(ang) * dist,
            "y": self.player.y + math.sin(ang) * dist,
            "type": ptype, "taken": False,
        })
        self._set_rift_message(
            ("Conduit Pylon" if ptype == "conduit" else "Speed Pylon") + " appeared nearby!")

    def _update_pylons(self):
        """Activate pylons the player walks into; tick the active buffs."""
        for pylon in self.pylons:
            if not pylon["taken"] and math.hypot(
                    self.player.x - pylon["x"], self.player.y - pylon["y"]) < self.PYLON_PICKUP_RADIUS:
                self._activate_pylon(pylon)

        if self.pylon_speed_timer > 0:
            self.pylon_speed_timer -= self.dt
        if self.pylon_conduit_timer > 0:
            self.pylon_conduit_timer -= self.dt
            self._conduit_tick -= self.dt
            if self._conduit_tick <= 0:
                self._conduit_tick = self.CONDUIT_TICK
                self._conduit_zap()

    def _activate_pylon(self, pylon):
        pylon["taken"] = True
        if pylon["type"] == "speed":
            self.pylon_speed_timer = self.PYLON_BUFF_DURATION
            self._set_rift_message("Speed Pylon!  +Attack & Move Speed")
        else:
            self.pylon_conduit_timer = self.PYLON_BUFF_DURATION
            self._conduit_tick = 0.0
            self._set_rift_message("Conduit Pylon!  Electrocuting nearby foes")

    def _conduit_zap(self):
        """Conduit buff tick: electrocute every enemy within the radius."""
        dmg = self.player.get_spell_damage(self.CONDUIT_BASE_DAMAGE, ElementType.LIGHTNING)
        self.aoe_effects.append({"x": self.player.x, "y": self.player.y,
                                 "r": self.CONDUIT_RADIUS, "color": (120, 200, 255),
                                 "ttl": 0.2, "max_ttl": 0.2})
        for enemy in list(self.world.enemies):
            if math.hypot(enemy.x - self.player.x, enemy.y - self.player.y) <= self.CONDUIT_RADIUS:
                enemy._last_skill_id = None
                final, is_crit, _ = self.combat_system.deal_spell_damage(
                    self.player, enemy, dmg, element_type=ElementType.LIGHTNING)
                self.damage_numbers.add_damage(enemy.x, enemy.y - 20, final,
                                               "crit" if is_crit else "lightning")

    def draw_pylons(self, cam):
        """Draw pylon shrines in the world (pulsing while available)."""
        pulse = pygame.time.get_ticks() * 0.004
        for pylon in self.pylons:
            pos = (int(pylon["x"] - cam[0]), int(pylon["y"] - cam[1]))
            col = (120, 200, 255) if pylon["type"] == "conduit" else (120, 255, 160)
            if pylon["taken"]:
                col = tuple(c // 3 for c in col)
            pygame.draw.circle(self.screen, col, pos, 16)
            pygame.draw.circle(self.screen, (255, 255, 255), pos, 16, 2)
            if not pylon["taken"]:
                r = 22 + int(6 * (1 + math.sin(pulse)))
                pygame.draw.circle(self.screen, col, pos, r, 1)
                label = "Conduit" if pylon["type"] == "conduit" else "Speed"
                txt = self.small_font.render(label, True, col)
                self.screen.blit(txt, txt.get_rect(center=(pos[0], pos[1] - 28)))

    def draw_minimap(self):
        """PoE2-style corner minimap: explored trail, red enemy dots, pylons."""
        size = self.MINIMAP_SIZE
        mx = self.width - size - 12
        my = 12
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((10, 12, 20, 180))
        c = size // 2
        scale = (size / 2) / self.MINIMAP_VIEW
        cs = self.world.CHUNK_SIZE

        def to_map(wx, wy):
            return c + (wx - self.player.x) * scale, c + (wy - self.player.y) * scale

        # Explored chunks: a lighter region tracing where the player has been.
        half = (cs * scale) / 2
        for (ccx, ccy) in self.minimap_visited:
            sx, sy = to_map(ccx * cs + cs / 2, ccy * cs + cs / 2)
            rect = pygame.Rect(sx - half, sy - half, half * 2, half * 2)
            pygame.draw.rect(surf, (55, 65, 92, 160), rect)
            pygame.draw.rect(surf, (90, 110, 150, 200), rect, 1)

        # Pylons (small colored dots).
        for pylon in self.pylons:
            if pylon["taken"]:
                continue
            sx, sy = to_map(pylon["x"], pylon["y"])
            if 0 <= sx <= size and 0 <= sy <= size:
                col = (120, 200, 255) if pylon["type"] == "conduit" else (120, 255, 160)
                pygame.draw.circle(surf, col, (int(sx), int(sy)), 3)

        # Enemies (red dots); boss is an orange marker clamped to the edge.
        for enemy in self.world.enemies:
            sx, sy = to_map(enemy.x, enemy.y)
            if getattr(enemy, "is_boss", False):
                sx = max(5, min(size - 5, sx))
                sy = max(5, min(size - 5, sy))
                pygame.draw.circle(surf, (255, 120, 40), (int(sx), int(sy)), 4)
            elif 0 <= sx <= size and 0 <= sy <= size:
                pygame.draw.circle(surf, (235, 60, 60), (int(sx), int(sy)), 2)

        # Player (center) + frame.
        pygame.draw.circle(surf, (90, 220, 255), (c, c), 4)
        pygame.draw.circle(surf, (255, 255, 255), (c, c), 4, 1)
        pygame.draw.rect(surf, (160, 180, 220), surf.get_rect(), 2)
        self.screen.blit(surf, (mx, my))
        self.screen.blit(self.small_font.render("Map", True, (200, 210, 235)), (mx + 6, my + 4))

    # --- modal helpers / pause menu --------------------------------------
    def _modal_open(self):
        """True while any overlay/menu should capture the mouse (no casting)."""
        return (self.show_pause_menu or self.show_gr_picker or self.show_inventory
                or self.show_skill_tree or self.show_progression
                or self.show_character_sheet or self.show_spell_tree
                or self.show_save_menu or self.show_stash)

    def _handle_pause_menu_keys(self, key):
        """Pause menu input: Esc resumes, Q quits the game."""
        if key in (pygame.K_ESCAPE, pygame.K_p):
            self.show_pause_menu = False
            self.paused = False
        elif key == pygame.K_q:
            self.running = False

    def _resume_game(self):
        self.show_pause_menu = False
        self.paused = False

    def _handle_pause_menu_click(self, pos, button):
        """Route a click in the pause menu to a button or a volume slider."""
        if button != 1:
            return
        # Slider knobs/tracks first so a click on a track grabs the drag.
        for track, _knob, kind in self._volume_sliders:
            if track.inflate(0, 16).collidepoint(pos):
                self._dragging_slider = kind
                self._drag_volume(pos)
                return
        for rect, action in self._pause_buttons:
            if rect.collidepoint(pos):
                if action == 'resume':
                    self._resume_game()
                elif action == 'saves':
                    self.show_pause_menu = False
                    self.show_save_menu = True
                    self.save_confirm = None
                elif action == 'controls':
                    self.show_controls = not self.show_controls
                elif action == 'quit':
                    self.running = False
                return

    def _drag_volume(self, pos):
        """Set the SFX/Music volume from the cursor x within the slider track."""
        for track, _knob, kind in self._volume_sliders:
            if kind != self._dragging_slider:
                continue
            frac = (pos[0] - track.x) / max(1, track.width)
            frac = max(0.0, min(1.0, frac))
            if kind == 'sfx':
                self.sound.set_sfx_volume(frac)
            else:
                self.sound.set_music_volume(frac)
            return

    # --- inventory interaction (equip / unequip / sell) ------------------
    # --- map layouts (Phase 18) ------------------------------------------
    def _apply_map_layout(self):
        """Pick a random themed map layout for the current rift and apply it.

        The layout decorates chunks with distinctive props and tunes spawn
        density + pylon cadence, so each rift feels structurally different.
        """
        from src.core.data_loader import load_json
        layouts = load_json('map_layouts.json')
        self.map_layout_id = random.choice(list(layouts.keys()))
        self.map_layout = layouts[self.map_layout_id]
        self.world.layout = self.map_layout
        # Each fresh rift gets a newly generated music loop (modular variety).
        self.sound.regenerate_music()

    # --- town hub (Phase 18) ---------------------------------------------
    def _init_town_stations(self):
        """Place the town stations around the town center."""
        cx, cy = self.town_center
        self.town_stations = [
            {'name': 'Stash',         'x': cx - 170, 'y': cy - 30, 'key': 'stash',    'color': (120, 180, 255)},
            {'name': 'Merchant',      'x': cx + 170, 'y': cy - 30, 'key': 'merchant', 'color': (235, 200, 90)},
            {'name': 'Blacksmith',    'x': cx,       'y': cy + 170, 'key': 'smith',    'color': (220, 120, 90)},
            {'name': 'Return Portal', 'x': cx,       'y': cy - 180, 'key': 'portal',   'color': (180, 120, 255)},
        ]

    def _toggle_town(self):
        """Town portal: travel to town from the field, or back again (T)."""
        if self.in_town:
            self._leave_town()
        else:
            self._enter_town()

    def _enter_town(self):
        """Open a town portal: stash the field position and warp to the hub."""
        self.town_return = (self.player.x, self.player.y)
        self.in_town = True
        self.player.x, self.player.y = self.town_center
        self.player.rect.center = (int(self.town_center[0]), int(self.town_center[1]))
        # Town is a safe zone: clear the current fight and let spawns resume on return.
        self.world.enemies.clear()
        self.enemy_health_bars.clear()
        self.rift_boss = None
        self.progress_orbs.clear()
        if self.rift.boss_active:
            self.rift.boss_active = False
            self.rift.spawning_enabled = True
        self.sound.regenerate_music()   # calmer, distinct town theme
        self._set_rift_message("Town Portal: welcome to town. Press T to return.")

    def _leave_town(self):
        """Step back through the portal to where the player opened it."""
        self.in_town = False
        self.show_stash = False
        if self.town_return is not None:
            self.player.x, self.player.y = self.town_return
            self.player.rect.center = (int(self.town_return[0]), int(self.town_return[1]))
        self.sound.regenerate_music()   # fresh field track on return
        self._set_rift_message("Returned to the rift.")

    def _update_town(self):
        """Track which station (if any) the player is standing next to."""
        self._near_station = None
        for s in self.town_stations:
            if math.hypot(self.player.x - s['x'], self.player.y - s['y']) < 55:
                self._near_station = s
                return

    def _interact_station(self):
        """Activate the station the player is next to (E)."""
        s = self._near_station
        if not s:
            return
        if s['key'] == 'stash':
            self.show_stash = True
        elif s['key'] == 'merchant':
            self._sell_all_junk()
        elif s['key'] == 'smith':
            self.show_inventory = True   # upgrades happen in the inventory panel
        elif s['key'] == 'portal':
            self._leave_town()

    def _sell_all_junk(self):
        """Merchant convenience: sell every Common/Uncommon backpack item."""
        from src.items.item import ItemRarity
        junk = [it for it in list(self.item_manager.inventory.items)
                if getattr(it, 'item_type', None) != 'keystone'
                and it.rarity in (ItemRarity.COMMON, ItemRarity.UNCOMMON)]
        total = 0
        for it in junk:
            total += it.get_sell_value()
            self.item_manager.inventory.remove_item(it)
        if junk:
            self.player.add_money(copper=total)
            self._set_rift_message(f"Merchant bought {len(junk)} items for {total}c")
        else:
            self._set_rift_message("Nothing common to sell")

    # --- stash transfer ---------------------------------------------------
    def _handle_stash_click(self, pos, button):
        """Left-click moves an item between backpack and stash."""
        for rect, item in self._stash_left_rects:    # backpack -> stash
            if rect.collidepoint(pos):
                if len(self.stash) < self.STASH_CAPACITY and \
                        self.item_manager.inventory.remove_item(item):
                    self.stash.append(item)
                return
        for rect, item in self._stash_right_rects:    # stash -> backpack
            if rect.collidepoint(pos):
                if not self.item_manager.inventory.is_full():
                    self.stash.remove(item)
                    self.item_manager.inventory.add_item(item)
                return

    def _handle_inventory_click(self, pos, button):
        """Map a click in the inventory overlay to an item action.

        Backpack:  left-click -> equip,   right-click -> sell.
        Equipped:  left-click -> upgrade, right-click -> unequip.
        """
        for rect, item in self._inv_item_rects:
            if rect.collidepoint(pos):
                if button == 1:
                    self._equip_from_inventory(item)
                elif button == 3:
                    self._sell_item(item)
                return
        for rect, slot, item in self._equip_item_rects:
            if rect.collidepoint(pos):
                if button == 1:
                    self._upgrade_equipped(item)
                elif button == 3:
                    self._unequip_slot(slot)
                return

    def _upgrade_equipped(self, item):
        """Spend wallet money to add one upgrade level to an equipped item."""
        if not item.can_upgrade():
            self._set_rift_message(f"{item.name} is max upgrade (+{item.MAX_UPGRADE})")
            return
        cost = item.upgrade_cost()
        if self.item_manager.upgrade_item(item):
            self.recompute_player_stats()
            self._set_rift_message(f"Upgraded {item.name} to +{item.upgrade_level} ({cost}c)")
        else:
            self._set_rift_message(f"Need {cost}c to upgrade {item.name}")

    def _equip_from_inventory(self, item):
        """Equip a backpack item, swapping any item already in that slot.

        One-handed weapons dual-wield (main hand then off-hand), and rings use
        the same logic across the two ring slots: equipping a second ring fills
        the empty ring slot rather than replacing the first.
        """
        from src.items.item import ItemSlot
        if getattr(item, 'item_type', None) == 'keystone':
            return  # keystones are consumables, not gear
        if item.slot not in self.item_manager.equipment.equipment:
            self._set_rift_message(f"{item.name} can't be equipped")
            return
        if self.player.level < item.level_requirement:
            self._set_rift_message(f"Requires level {item.level_requirement}")
            return

        equip = self.item_manager.equipment.equipment
        # Pairs of slots that fill the empty one before replacing the first.
        paired = {
            ItemSlot.WEAPON_1H: (ItemSlot.WEAPON_1H, ItemSlot.WEAPON_1H_OFF, "secondary"),
            ItemSlot.RING_1: (ItemSlot.RING_1, ItemSlot.RING_2, "ring 2"),
            ItemSlot.RING_2: (ItemSlot.RING_1, ItemSlot.RING_2, "ring 2"),
        }
        pair = paired.get(item.slot)
        if pair and equip[pair[0]] is not None and equip[pair[1]] is None:
            # Primary slot is full -> fill the empty second slot.
            self.item_manager.try_equip_item_to_slot(item, pair[1])
            self._set_rift_message(f"Equipped {item.name} ({pair[2]})")
        else:
            # Default routes to the item's own slot (the primary of any pair).
            target = pair[0] if pair else item.slot
            self.item_manager.try_equip_item_to_slot(item, target)
            self._set_rift_message(f"Equipped {item.name}")
        self.recompute_player_stats()

    def _compare_slots_for(self, item):
        """Equipment slots a backpack item could occupy (dual-wield / dual-ring
        aware), used to pick the equipped item(s) to compare against."""
        from src.items.item import ItemSlot
        equip = self.item_manager.equipment.equipment
        s = getattr(item, 'slot', None)
        if s not in equip:
            return []
        if s == ItemSlot.WEAPON_1H:
            return [ItemSlot.WEAPON_1H, ItemSlot.WEAPON_1H_OFF]
        if s in (ItemSlot.RING_1, ItemSlot.RING_2):
            return [ItemSlot.RING_1, ItemSlot.RING_2]
        return [s]

    def _equipped_compare_items(self, item):
        """The currently-equipped item(s) in slots this backpack item fits."""
        equip = self.item_manager.equipment.equipment
        return [equip[sl] for sl in self._compare_slots_for(item)
                if equip.get(sl) is not None]

    def _unequip_slot(self, slot):
        """Move an equipped item back to the backpack (if there is room)."""
        item = self.item_manager.equipment.get_equipped_item(slot)
        if item is None:
            return
        if self.item_manager.inventory.is_full():
            self._set_rift_message("Inventory full -- can't unequip")
            return
        self.item_manager.try_unequip_item(slot)
        self.recompute_player_stats()
        self._set_rift_message(f"Unequipped {item.name}")

    def _sell_item(self, item):
        """Sell a backpack item for copper and remove it from the inventory."""
        if getattr(item, 'item_type', None) == 'keystone':
            self._set_rift_message("Rift Keystones can't be sold")
            return
        value = item.get_sell_value()
        if self.item_manager.inventory.remove_item(item):
            self.player.add_money(copper=value)
            self._set_rift_message(f"Sold {item.name} for {value}c")

    # --- per-spell mastery trees (Phase 16) ------------------------------
    # The three spells that have a dedicated mastery tree, in tab order.
    SPELL_TREE_SKILLS = [
        ("fireball", "Fireball"),
        ("ice_shard", "Frost Bolt"),
        ("chain_lightning", "Lightning Spark"),
    ]

    @staticmethod
    def _fmt_mastery_effect(key, val):
        """Human-readable label for a mastery node effect."""
        if key == "speed_mult":
            return f"+{int(val * 100)}% projectile speed"
        if key == "damage_mult":
            return f"+{int(val * 100)}% damage"
        if key == "burn_bonus":
            return f"+{int(val * 100)}% ignite (burn) damage"
        if key == "count":
            return f"+{int(val)} projectile"
        if key == "explosion":
            return f"explosion on hit (radius {int(val)})"
        if key == "explosion_radius":
            return f"+{int(val)} explosion radius"
        if key == "freeze_explosion":
            return f"freeze explosion (radius {int(val)})"
        if key == "extra_chill":
            return f"+{int(val)} chill buildup"
        if key == "pierce":
            return f"pierces {int(val)} enemies"
        if key == "fork":
            return f"forks {int(val)} times"
        if key == "homing":
            return "homing (seeks enemies)"
        if key in ("aoe_radius_add", "range_add", "radius_add"):
            return f"+{int(val)} {key.split('_')[0]}"
        if key == "convert":
            return f"convert to {val}"
        return f"{key}: {val}"

    def _handle_spell_tree_click(self, pos, button):
        """Click a tab to switch spell; click a node to (de)allocate mastery."""
        for rect, idx in self._spell_tab_rects:
            if rect.collidepoint(pos):
                self.spell_tree_selected = idx
                return
        for rect, sid, node_id in self._spell_node_rects:
            if rect.collidepoint(pos):
                skill = self.skills.get(sid)
                if skill is None:
                    return
                if button == 1:
                    if skill.allocate_mastery(node_id):
                        self._set_rift_message(f"Allocated {node_id}")
                    else:
                        self._set_rift_message("No mastery points available")
                elif button == 3:
                    if skill.deallocate_mastery(node_id):
                        self._set_rift_message(f"Refunded {node_id}")
                return

    # --- save / load slot menu (Phase 17) --------------------------------
    def _handle_save_menu_click(self, pos, button):
        """Left-click a slot to Load it; right-click to Save to it.

        Both destructive paths (loading over the live character, or overwriting
        an existing save) first raise a Yes/No confirmation so the player picks
        deliberately which file to read or write.
        """
        # A confirmation dialog, if open, captures clicks first.
        if self.save_confirm is not None:
            self._handle_save_confirm_click(pos, button)
            return

        for rect, slot in self._save_slot_rects:
            if rect.collidepoint(pos):
                if button == 1:
                    if save_system.has_save(slot):
                        # Confirm before discarding current progress.
                        self.save_confirm = {'action': 'load', 'slot': slot}
                    else:
                        self._set_rift_message("That slot is empty")
                elif button == 3:
                    if save_system.has_save(slot):
                        # Confirm before overwriting an existing save file.
                        self.save_confirm = {'action': 'save', 'slot': slot}
                    else:
                        # Empty slot: nothing to lose, save immediately.
                        self.save_game(slot)
                        self.active_save_slot = slot
                return

    def _handle_save_confirm_click(self, pos, button):
        """Resolve a click on the Save/Load confirmation dialog's Yes/No."""
        if button != 1:
            return
        for rect, choice in self._save_confirm_rects:
            if rect.collidepoint(pos):
                self._resolve_save_confirm(choice == 'yes')
                return

    def _resolve_save_confirm(self, yes):
        """Carry out (or cancel) the pending confirmed Save/Load action."""
        confirm, self.save_confirm = self.save_confirm, None
        if not yes or confirm is None:
            return
        slot = confirm['slot']
        if confirm['action'] == 'load':
            if self.load_game(slot):
                self.active_save_slot = slot
                self.show_save_menu = False
        else:  # 'save'
            self.save_game(slot)
            self.active_save_slot = slot

    def _handle_save_menu_keys(self, key):
        """Keyboard control for the confirmation dialog (Enter=yes, Esc/N=no)."""
        if key in (pygame.K_RETURN, pygame.K_y):
            self._resolve_save_confirm(True)
        elif key in (pygame.K_ESCAPE, pygame.K_n):
            self._resolve_save_confirm(False)

    def draw_save_menu(self):
        """Save/Load overlay: one row per slot with its character summary."""
        self._save_slot_rects = []
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 560, 460
        px = (self.width - pw) // 2
        py = (self.height - ph) // 2
        pygame.draw.rect(self.screen, (16, 20, 30), (px, py, pw, ph))
        pygame.draw.rect(self.screen, (120, 170, 220), (px, py, pw, ph), 3)

        title = self.large_font.render("Save / Load", True, (160, 210, 255))
        self.screen.blit(title, title.get_rect(center=(self.width // 2, py + 28)))

        slots = save_system.list_slots(self.NUM_SAVE_SLOTS)
        y = py + 64
        for i, meta in enumerate(slots):
            rect = pygame.Rect(px + 20, y, pw - 40, 56)
            hover = rect.collidepoint(*pygame.mouse.get_pos())
            active = (i == self.active_save_slot)
            pygame.draw.rect(self.screen, (45, 50, 70) if hover else (28, 32, 46), rect)
            pygame.draw.rect(self.screen, (255, 215, 120) if active else (90, 100, 130), rect, 2)

            head = f"Slot {i}" + ("   (current)" if active else "")
            self.screen.blit(self.font.render(head, True, (255, 255, 255)), (rect.x + 12, rect.y + 6))
            if meta:
                import time as _t
                when = _t.strftime("%Y-%m-%d %H:%M", _t.localtime(meta["mtime"]))
                sub = f"Level {meta['level']}   Best GR {meta['highest_gr']}   {when}"
                col = (200, 220, 200)
            else:
                sub = "<empty>"
                col = (150, 150, 150)
            self.screen.blit(self.small_font.render(sub, True, col), (rect.x + 12, rect.y + 32))
            self._save_slot_rects.append((rect, i))
            y += 64

        instr = self.small_font.render(
            "Left-click: Load slot   |   Right-click: Save to slot   |   "
            "F5/F9: quick save/load   |   L: Close",
            True, (200, 200, 200))
        self.screen.blit(instr, instr.get_rect(center=(self.width // 2, py + ph - 18)))

        # Confirmation dialog draws on top when a destructive action is pending.
        if self.save_confirm is not None:
            self.draw_save_confirm()

    def draw_save_confirm(self):
        """Yes/No dialog confirming a Load (discard progress) or Save (overwrite)."""
        self._save_confirm_rects = []
        c = self.save_confirm
        if c is None:
            return
        slot = c['slot']
        meta = save_system.peek_slot(slot)

        dw, dh = 460, 200
        dx = (self.width - dw) // 2
        dy = (self.height - dh) // 2
        # Dim the menu behind the dialog.
        shade = pygame.Surface((self.width, self.height))
        shade.set_alpha(120)
        shade.fill((0, 0, 0))
        self.screen.blit(shade, (0, 0))
        pygame.draw.rect(self.screen, (22, 26, 38), (dx, dy, dw, dh))
        accent = (255, 170, 90) if c['action'] == 'save' else (120, 200, 255)
        pygame.draw.rect(self.screen, accent, (dx, dy, dw, dh), 3)

        if c['action'] == 'load':
            head = "Load this save?"
            warn = "Unsaved progress on your current character will be lost."
        else:
            head = "Overwrite this save?"
            warn = "The existing save file in this slot will be replaced."

        title = self.font.render(head, True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(self.width // 2, dy + 30)))

        if meta:
            sub = f"Slot {slot}:  Level {meta['level']}   Best GR {meta['highest_gr']}"
        else:
            sub = f"Slot {slot}"
        sub_surf = self.small_font.render(sub, True, (200, 210, 230))
        self.screen.blit(sub_surf, sub_surf.get_rect(center=(self.width // 2, dy + 58)))
        warn_surf = self.small_font.render(warn, True, (255, 200, 130))
        self.screen.blit(warn_surf, warn_surf.get_rect(center=(self.width // 2, dy + 84)))

        # Yes / No buttons
        mouse = pygame.mouse.get_pos()
        for label, choice, bx, col in (
            ("Yes (Enter)", 'yes', dx + 50, (80, 160, 90)),
            ("No (Esc)", 'no', dx + dw - 50 - 160, (160, 80, 80)),
        ):
            rect = pygame.Rect(bx, dy + dh - 56, 160, 38)
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(self.screen, tuple(min(255, v + (40 if hover else 0)) for v in col), rect)
            pygame.draw.rect(self.screen, (230, 230, 230), rect, 2)
            txt = self.font.render(label, True, (255, 255, 255))
            self.screen.blit(txt, txt.get_rect(center=rect.center))
            self._save_confirm_rects.append((rect, choice))

    def draw_spell_tree_overlay(self):
        """Per-spell mastery overlay: tabs on the left, nodes on the right."""
        self._spell_tab_rects = []
        self._spell_node_rects = []

        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(175)
        overlay.fill((4, 4, 12))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 780, 560
        px = (self.width - pw) // 2
        py = (self.height - ph) // 2
        pygame.draw.rect(self.screen, (18, 18, 34), (px, py, pw, ph))
        pygame.draw.rect(self.screen, (150, 120, 220), (px, py, pw, ph), 3)

        title = self.large_font.render("Spell Trees", True, (210, 170, 255))
        self.screen.blit(title, title.get_rect(center=(self.width // 2, py + 26)))

        # Left column: one tab per spell, showing level + spare mastery points.
        tab_x = px + 20
        ty = py + 70
        for i, (sid, label) in enumerate(self.SPELL_TREE_SKILLS):
            rect = pygame.Rect(tab_x, ty, 200, 44)
            sel = (i == self.spell_tree_selected)
            pygame.draw.rect(self.screen, (60, 50, 90) if sel else (30, 30, 45), rect)
            pygame.draw.rect(self.screen, (200, 170, 255) if sel else (90, 90, 110), rect, 2)
            self.screen.blit(self.font.render(label, True, (255, 255, 255)), (tab_x + 10, ty + 5))
            sk = self.skills.get(sid)
            if sk:
                sub = self.small_font.render(
                    f"Lv {sk.level}   points: {sk.mastery_points_available()}",
                    True, (200, 200, 160))
                self.screen.blit(sub, (tab_x + 10, ty + 25))
            self._spell_tab_rects.append((rect, i))
            ty += 52

        # Right column: nodes for the selected spell.
        sid, label = self.SPELL_TREE_SKILLS[self.spell_tree_selected]
        sk = self.skills.get(sid)
        if sk is None:
            return
        nx = px + 250
        ny = py + 70
        head = self.font.render(
            f"{label}  --  Mastery Points: {sk.mastery_points_available()}",
            True, (255, 220, 120))
        self.screen.blit(head, (nx, ny))
        ny += 34

        for node in sk._mastery_nodes():
            rect = pygame.Rect(nx, ny, pw - 270, 32)
            allocated = node["id"] in sk.allocated_mastery
            if rect.collidepoint(*pygame.mouse.get_pos()):
                pygame.draw.rect(self.screen, (45, 45, 70), rect)
            mark = "[x]" if allocated else "[ ]"
            col = (140, 255, 140) if allocated else (215, 215, 215)
            self.screen.blit(self.font.render(f"{mark} {node['label']}", True, col),
                             (nx + 6, ny + 6))
            eff = ", ".join(self._fmt_mastery_effect(k, v) for k, v in node["effect"].items())
            self.screen.blit(self.small_font.render(eff, True, (170, 170, 215)),
                             (nx + 250, ny + 9))
            self._spell_node_rects.append((rect, sid, node["id"]))
            ny += 36

        instr = self.small_font.render(
            "Click tab or 1-3: select spell   |   Left-click node: allocate   |   "
            "Right-click: refund   |   K: Close",
            True, (200, 200, 200))
        self.screen.blit(instr, instr.get_rect(center=(self.width // 2, py + ph - 18)))

    # --- greater rift picker ---------------------------------------------
    def _handle_gr_picker_keys(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_g):
            self.show_gr_picker = False
        elif key in (pygame.K_UP, pygame.K_RIGHT, pygame.K_RIGHTBRACKET):
            self.gr_selected_level = min(self.rift.gr_cfg['max_level'], self.gr_selected_level + 1)
        elif key in (pygame.K_DOWN, pygame.K_LEFT, pygame.K_LEFTBRACKET):
            self.gr_selected_level = max(1, self.gr_selected_level - 1)
        elif key in (pygame.K_PAGEUP,):
            self.gr_selected_level = min(self.rift.gr_cfg['max_level'], self.gr_selected_level + 10)
        elif key in (pygame.K_PAGEDOWN,):
            self.gr_selected_level = max(1, self.gr_selected_level - 10)
        elif key == pygame.K_RETURN:
            self._try_open_greater_rift()

    def _try_open_greater_rift(self):
        """Consume a keystone and open the chosen Greater Rift level."""
        if self.item_manager.consume_keystone():
            self.rift.open_greater(self.gr_selected_level)
            self._reset_rift_exploration()
            self._apply_atlas_to_rift()
            self.rift_boss = None
            self.show_gr_picker = False
            self._set_rift_message(f"Opened Greater Rift {self.gr_selected_level}!")
        else:
            self._set_rift_message("No Rift Keystone! Clear a normal rift first.")

    def _apply_atlas_to_rift(self):
        """Atlas 'boss frequency' shortens the rift bar so bosses come sooner."""
        boss_freq = self.atlas.get_effects()['boss_frequency']
        if boss_freq:
            self.rift.threshold = max(5, int(self.rift.threshold * (1.0 - boss_freq)))

    # --- ascendancy / atlas input (Phase 15) ------------------------------
    def _handle_progression_keys(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_v):
            self.show_progression = False
            return
        classes = self.ascendancy.available_classes()
        if self.ascendancy.chosen is None:
            # Pick a class (requires level 20).
            if pygame.K_1 <= key <= pygame.K_4:
                idx = key - pygame.K_1
                if idx < len(classes):
                    if self.ascendancy.choose(classes[idx], self.player.level):
                        self._set_rift_message(f"Ascended: {classes[idx].title()}")
                    else:
                        self._set_rift_message("Reach level 20 to ascend.")
        else:
            # Allocate the Nth ascendancy node (1-4).
            if pygame.K_1 <= key <= pygame.K_4:
                nodes = self.ascendancy.classes[self.ascendancy.chosen]["nodes"]
                idx = key - pygame.K_1
                if idx < len(nodes) and self.ascendancy.allocate(nodes[idx]["id"], self.player.level):
                    self._set_rift_message(f"Allocated {nodes[idx]['label']}")
        # Atlas: 'A' allocates the next available atlas node.
        if key == pygame.K_a:
            for nid in self.atlas.nodes:
                if self.atlas.allocate(nid):
                    self._set_rift_message(f"Atlas: {self.atlas.nodes[nid]['label']}")
                    break

    # --- active-skill execution (Phase 13) + rune effects (Phase 14) ------
    def _execute_cast(self, plan, skill):
        # Auto Target rune: aim at the nearest enemy (Phase 14 behavior).
        if plan.get("auto_target"):
            nearest = self._nearest_enemy(self.player.x, self.player.y)
            if nearest is not None:
                plan["tx"], plan["ty"] = nearest.x, nearest.y

        kind = plan["kind"]
        if kind == "projectile":
            self._cast_projectiles(plan, skill)
        elif kind == "aoe":
            self._cast_aoe(plan, skill)
        elif kind == "blink":
            self._cast_blink(plan)
        elif kind == "summon":
            self._cast_summon(plan)

        # Area runes that layer on top of any cast (Phase 14).
        cx, cy = self._cast_center(plan)
        if plan.get("extra_nova"):
            self._spawn_nova(cx, cy, plan["extra_nova"], plan.get("damage", 0) * 0.6,
                             plan.get("element", "physical"), skill)
        if plan.get("lingering"):
            ling = plan["lingering"]
            self.ground_zones.append({
                "x": cx, "y": cy, "r": ling["radius"], "ttl": ling["duration"],
                "dps": max(1.0, plan.get("damage", 10) * ling["dps_mult"]),
                "element": plan.get("element", "physical"),
                "color": plan.get("color", (150, 150, 150)), "skill_id": skill.id,
            })

    def _cast_center(self, plan):
        if plan.get("at") == "target" or plan["kind"] in ("blink",):
            return plan.get("tx", self.player.x), plan.get("ty", self.player.y)
        return self.player.x, self.player.y

    def _nearest_enemy(self, x, y, exclude=None):
        best, best_d = None, 1e18
        for e in self.world.enemies:
            if e is exclude or e.health <= 0:
                continue
            d = math.hypot(e.x - x, e.y - y)
            if d < best_d:
                best, best_d = e, d
        return best

    def _spawn_nova(self, cx, cy, radius, damage, element, skill):
        self.aoe_effects.append({"x": cx, "y": cy, "r": radius, "color": skill.color,
                                 "ttl": 0.3, "max_ttl": 0.3})
        if damage <= 0:
            return
        for enemy in list(self.world.enemies):
            if math.hypot(enemy.x - cx, enemy.y - cy) <= radius:
                enemy._last_skill_id = skill.id
                final, is_crit, _ = self.combat_system.deal_spell_damage(
                    self.player, enemy, damage, element_type=element)
                self.skills.award_damage(skill.id, final)

    def _cast_projectiles(self, plan, skill):
        px, py = self.player.x, self.player.y
        aim = math.atan2(plan["ty"] - py, plan["tx"] - px)
        count = max(1, plan["count"])
        spread = 0.18
        for i in range(count):
            a = aim + (i - (count - 1) / 2.0) * spread
            tx, ty = px + math.cos(a) * 1000, py + math.sin(a) * 1000
            proj = Projectile(px, py, tx, ty, plan["speed"], plan["damage"],
                              plan["color"], plan["radius"], 300)
            proj.element_type = plan["element"]
            proj.skill_id = skill.id
            # Rune behaviors (Phase 14)
            proj.pierce = plan.get("pierce", 0)
            proj.chain = plan.get("chain", 0)
            proj.is_return = plan.get("return", False)
            proj.orbit = plan.get("orbit", False)
            proj._hit = set()
            proj._reversed = False
            proj._orbit_a = a
            # Per-spell mastery sub-mechanics (Fireball explosion/ignite,
            # Frost Bolt freeze explosion). 0 = inactive.
            f = plan.get("flags", {})
            proj.explosion_radius = f.get("explosion", 0) + f.get("explosion_radius", 0)
            proj.freeze_explosion_radius = f.get("freeze_explosion", 0)
            proj.burn_bonus = f.get("burn_bonus", 0.0)
            proj.extra_chill = int(f.get("extra_chill", 0))
            # Piercing (mastery flag + passive-tree bonus): pass through enemies.
            proj.pierce += int(f.get("pierce", 0)) + int(getattr(self.player, "projectile_pierce_bonus", 0))
            # Forking (Lightning Spark): branch toward new enemies on each hit.
            proj.fork = int(plan.get("fork", 0))
            # Homing: steer toward the nearest enemy like a heat-seeker.
            proj.homing = bool(plan.get("homing", False))
            self.projectiles.append(proj)

    def _cast_aoe(self, plan, skill):
        cx, cy = (self.player.x, self.player.y) if plan["at"] == "player" else (plan["tx"], plan["ty"])
        self.aoe_effects.append({"x": cx, "y": cy, "r": plan["aoe_radius"],
                                 "color": plan["color"], "ttl": 0.35, "max_ttl": 0.35})
        for enemy in list(self.world.enemies):
            if math.hypot(enemy.x - cx, enemy.y - cy) <= plan["aoe_radius"]:
                enemy._last_skill_id = skill.id   # set before damage (death fires hook)
                final, is_crit, _ = self.combat_system.deal_spell_damage(
                    self.player, enemy, plan["damage"], element_type=plan["element"])
                self.damage_numbers.add_damage(enemy.x, enemy.y - 20, final,
                                               "crit" if is_crit else "normal")
                self.skills.award_damage(skill.id, final)

    def _cast_blink(self, plan):
        px, py = self.player.x, self.player.y
        dx, dy = plan["tx"] - px, plan["ty"] - py
        dist = math.hypot(dx, dy)
        if dist > plan["range"] and dist > 0:
            dx, dy = dx / dist * plan["range"], dy / dist * plan["range"]
        self.player.x += dx
        self.player.y += dy
        self.player.rect.center = (self.player.x, self.player.y)

    def _cast_summon(self, plan):
        # Necromancer ascendancy scales minion damage (Phase 15).
        dmg = plan["damage"] * (1.0 + getattr(self.player, "minion_damage_increase", 0.0))
        for _ in range(plan["count"]):
            ang = random.uniform(0, 2 * math.pi)
            mx = self.player.x + math.cos(ang) * 40
            my = self.player.y + math.sin(ang) * 40
            self.minions.append(Minion(mx, my, dmg, plan["duration"],
                                       self.player, plan.get("color", (220, 220, 200))))

    def _update_minions(self):
        for m in self.minions[:]:
            result = m.update(self.world.enemies, self.dt)
            if result is not None:
                target, dmg = result
                target._last_skill_id = "summon_skeleton"
                if target.take_damage(dmg):
                    pass  # death hook handles rewards/XP
                self.skills.award_damage("summon_skeleton", dmg)
            if not m.alive:
                self.minions.remove(m)

    def _update_aoe_effects(self):
        for fx in self.aoe_effects[:]:
            fx["ttl"] -= self.dt
            if fx["ttl"] <= 0:
                self.aoe_effects.remove(fx)

    def update_projectiles(self, current_map):
        """Update projectiles + rune behaviors (pierce/chain/fork/return/orbit)."""
        alive_projectiles = []
        new_forks = []   # forked branches spawned this frame (processed next frame)

        for projectile in self.projectiles:
            projectile.update()

            # Returning rune: reverse course at the half-way point (Phase 14).
            if getattr(projectile, 'is_return', False) and not projectile._reversed \
                    and projectile.lifetime < projectile.max_lifetime / 2:
                projectile.velocity_x *= -1
                projectile.velocity_y *= -1
                projectile._reversed = True

            # Orbit rune: circle the player instead of flying straight.
            if getattr(projectile, 'orbit', False):
                projectile._orbit_a += 0.18
                radius = 90
                projectile.x = self.player.x + math.cos(projectile._orbit_a) * radius
                projectile.y = self.player.y + math.sin(projectile._orbit_a) * radius

            # Homing: bend the velocity toward the nearest enemy each frame.
            if getattr(projectile, 'homing', False):
                self._home_projectile(projectile)

            # Projectiles expire by lifetime (the world is infinite, Phase 11).
            if not projectile.is_alive():
                continue

            consumed = False
            for enemy in current_map.enemies:
                if enemy in getattr(projectile, '_hit', ()):
                    continue
                if self.collision_system.check_circle_collision(
                    projectile.x, projectile.y, projectile.radius,
                    enemy.x, enemy.y, max(enemy.width, enemy.height) / 2
                ):
                    self._hit_enemy_with_projectile(projectile, enemy, current_map)
                    if hasattr(projectile, '_hit'):
                        projectile._hit.add(enemy)

                    # Forking (Lightning Spark): branch toward another enemy.
                    if getattr(projectile, 'fork', 0) > 0:
                        branch = self._make_fork(projectile, enemy)
                        if branch is not None:
                            new_forks.append(branch)

                    # Pierce/chain keep the projectile alive; otherwise it dies.
                    if getattr(projectile, 'pierce', 0) > 0:
                        projectile.pierce -= 1
                    elif getattr(projectile, 'chain', 0) > 0:
                        projectile.chain -= 1
                        self._redirect_chain(projectile, enemy)
                    else:
                        consumed = True
                    break

            if not consumed:
                alive_projectiles.append(projectile)

        self.projectiles = alive_projectiles + new_forks

    def _make_fork(self, projectile, origin_enemy):
        """Spawn a forked branch from a hit enemy toward the nearest new enemy.

        Returns the new Projectile (or None if no valid target). Forks carry the
        parent's element/skill and a decremented fork count, never re-hitting an
        enemy the chain has already struck.
        """
        best, best_d = None, self.FORK_RANGE
        for e in self.world.enemies:
            if e is origin_enemy or e in projectile._hit or e.health <= 0:
                continue
            d = math.hypot(e.x - origin_enemy.x, e.y - origin_enemy.y)
            if d < best_d:
                best, best_d = e, d
        if best is None:
            return None

        speed = math.hypot(projectile.velocity_x, projectile.velocity_y) or 10
        fork = Projectile(origin_enemy.x, origin_enemy.y, best.x, best.y, speed,
                          projectile.damage * self.FORK_DAMAGE_FALLOFF,
                          projectile.color, projectile.radius, 200)
        fork.element_type = getattr(projectile, 'element_type', ElementType.LIGHTNING)
        fork.skill_id = getattr(projectile, 'skill_id', None)
        fork._hit = set(projectile._hit)        # don't bounce back to struck foes
        fork.fork = projectile.fork - 1
        fork.pierce = 0
        fork.chain = 0
        fork.is_return = False
        fork.orbit = False
        fork._reversed = False
        fork._orbit_a = 0
        fork.explosion_radius = 0
        fork.freeze_explosion_radius = 0
        fork.burn_bonus = 0.0
        fork.extra_chill = 0
        fork.homing = getattr(projectile, 'homing', False)
        return fork

    def _home_projectile(self, projectile):
        """Heat-seeker steering: rotate velocity toward the nearest enemy while
        preserving speed."""
        target = self._nearest_enemy(projectile.x, projectile.y)
        if target is None:
            return
        dx, dy = target.x - projectile.x, target.y - projectile.y
        dist = math.hypot(dx, dy)
        if dist > self.HOMING_RANGE or dist == 0:
            return
        speed = math.hypot(projectile.velocity_x, projectile.velocity_y) or 1.0
        # Lerp the heading toward the target, then renormalize to keep speed.
        nx = projectile.velocity_x + (dx / dist * speed - projectile.velocity_x) * self.HOMING_TURN
        ny = projectile.velocity_y + (dy / dist * speed - projectile.velocity_y) * self.HOMING_TURN
        n = math.hypot(nx, ny) or 1.0
        projectile.velocity_x = nx / n * speed
        projectile.velocity_y = ny / n * speed

    def _hit_enemy_with_projectile(self, projectile, enemy, current_map):
        """Apply one projectile hit (damage, XP, reflect, shock chain)."""
        element = getattr(projectile, 'element_type', None) or ElementType.PHYSICAL
        skill_id = getattr(projectile, 'skill_id', None)
        enemy._last_skill_id = skill_id   # set before damage (death fires hook)
        final_damage, is_crit, _ = self.combat_system.deal_spell_damage(
            self.player, enemy, projectile.damage, element_type=element)
        if skill_id:
            self.skills.award_damage(skill_id, final_damage)
        # Life Leech (Berserker ascendancy, Phase 15): heal a % of damage dealt.
        leech = getattr(self.player, 'life_leech', 0.0)
        if leech:
            self.player.health = min(self.player.max_health,
                                     self.player.health + final_damage * leech)
        self.damage_numbers.add_damage(enemy.x, enemy.y - 20, final_damage,
                                       'crit' if is_crit else 'normal')

        # Reflective elites bounce part of the damage back (Phase 12).
        reflect = getattr(enemy, 'behaviors', {}).get('reflect')
        if reflect and self.player.take_damage(final_damage * reflect):
            self.game_over = True

        # Per-spell mastery sub-mechanics (Phase 16).
        self._apply_projectile_mechanics(projectile, enemy, element, skill_id)

        # Static chain: lightning arcs between shocked enemies (Phase 8).
        if element == ElementType.LIGHTNING:
            self._apply_shock_chain(enemy, current_map, projectile.damage)

    def _apply_projectile_mechanics(self, projectile, enemy, element, skill_id):
        """Resolve spell-tree projectile add-ons on a hit: Fireball ignite +
        explosion, Frost Bolt freeze explosion."""
        effects = getattr(enemy, 'elemental_effects', None)
        skill = self.skills.get(skill_id) if skill_id else None

        # Fireball ignite: extra burn scaled by the skill's ignite nodes.
        burn_bonus = getattr(projectile, 'burn_bonus', 0.0)
        if burn_bonus and effects is not None:
            effects.apply_burn(self.player, bonus_increase=burn_bonus)

        # Frost Bolt Deep Chill: extra chill stacks build the freeze faster.
        extra_chill = getattr(projectile, 'extra_chill', 0)
        if extra_chill and effects is not None:
            for _ in range(int(extra_chill)):
                effects.apply_chill(self.player)

        # Fireball explosion: AoE fire burst on impact.
        exp_r = getattr(projectile, 'explosion_radius', 0)
        if exp_r > 0 and skill is not None:
            self._spawn_nova(enemy.x, enemy.y, exp_r, projectile.damage * 0.5,
                             element, skill)

        # Frost Bolt freeze explosion: cold burst when the target is frozen.
        fz_r = getattr(projectile, 'freeze_explosion_radius', 0)
        if fz_r > 0 and skill is not None and effects is not None and effects.is_frozen():
            self._spawn_nova(enemy.x, enemy.y, fz_r, projectile.damage * 0.6,
                             ElementType.COLD, skill)

    def _redirect_chain(self, projectile, origin):
        """Rune chain: steer the projectile toward the next unhit enemy."""
        nxt = None
        best = 1e18
        for e in self.world.enemies:
            if e in projectile._hit or e.health <= 0:
                continue
            d = math.hypot(e.x - origin.x, e.y - origin.y)
            if d < best:
                nxt, best = e, d
        if nxt is not None:
            speed = math.hypot(projectile.velocity_x, projectile.velocity_y) or 7
            dx, dy = nxt.x - projectile.x, nxt.y - projectile.y
            dist = math.hypot(dx, dy) or 1
            projectile.velocity_x = dx / dist * speed
            projectile.velocity_y = dy / dist * speed

    def _update_ground_zones(self):
        """Lingering Ground rune: damage enemies standing in the zone (Phase 14)."""
        for zone in self.ground_zones[:]:
            zone["ttl"] -= self.dt
            for enemy in list(self.world.enemies):
                if math.hypot(enemy.x - zone["x"], enemy.y - zone["y"]) <= zone["r"]:
                    enemy._last_skill_id = zone["skill_id"]
                    from src.core.damage import apply_ailment_damage
                    apply_ailment_damage(enemy, zone["dps"] * self.dt, zone["element"])
            if zone["ttl"] <= 0:
                self.ground_zones.remove(zone)
    
    def _apply_shock_chain(self, origin, current_map, base_damage):
        """Arc lightning from a hit enemy to nearby shocked enemies (Phase 8/9).

        Chain count/range scale with the player's shock stats (Phase 9). Chained
        targets also have Vulnerable spread to them if the data enables it.
        """
        from src.core.data_loader import load_json
        cfg = load_json('ailments.json')
        scfg = cfg['shock']
        combos = cfg.get('combos', {})

        rng = scfg['chain_range'] + getattr(self.player, 'shock_range_bonus', 0.0)
        max_links = scfg['chain_count'] + int(getattr(self.player, 'shock_chain_bonus', 0))
        chain_dmg = base_damage * scfg['chain_damage']

        # Only arc to *charged* (shocked) neighbours, nearest first.
        candidates = [e for e in current_map.enemies
                      if e is not origin and e.health > 0
                      and e.elemental_effects.is_shocked()
                      and math.hypot(e.x - origin.x, e.y - origin.y) <= rng]
        candidates.sort(key=lambda e: math.hypot(e.x - origin.x, e.y - origin.y))

        for target in candidates[:max_links]:
            _, is_crit, _ = self.combat_system.deal_spell_damage(
                self.player, target, chain_dmg,
                element_type=ElementType.LIGHTNING, apply_status=False)
            self.damage_numbers.add_damage(target.x, target.y - 20, chain_dmg, 'lightning')
            if combos.get('shock_spreads_vulnerable'):
                target.elemental_effects.apply_vulnerable(self.player)

    def handle_enemy_attacks(self):
        """Handle enemy attacks on the player."""
        for enemy in self.world.enemies:
            if enemy.can_attack(self.player):
                damage = enemy.attack()
                # Vampiric elites heal for a portion of the hit (Phase 12).
                lifesteal = getattr(enemy, 'behaviors', {}).get('lifesteal')
                if lifesteal:
                    enemy.health = min(enemy.max_health, enemy.health + damage * lifesteal)
                # Armor + physical resistance from gear reduce incoming melee hits.
                damage *= (1.0 - self.player.armor_damage_reduction())
                phys_res = self.player.get_resistance('physical')
                damage *= max(0.1, 1.0 - phys_res / 100.0)
                is_dead = self.player.take_damage(damage)
                if is_dead:
                    self.game_over = True
    
    def draw(self):
        """Draw the game state (camera-followed world, Phase 11)."""
        cam = self.cam

        # Draw streaming biome ground under the camera
        self.world.draw_ground(self.screen, cam, self.width, self.height)

        # Draw lingering ground zones (Phase 14)
        for zone in self.ground_zones:
            pos = (int(zone["x"] - cam[0]), int(zone["y"] - cam[1]))
            pygame.draw.circle(self.screen, zone["color"], pos, int(zone["r"]), 2)

        # Draw AoE effect rings (fading)
        for fx in self.aoe_effects:
            pos = (int(fx["x"] - cam[0]), int(fx["y"] - cam[1]))
            pygame.draw.circle(self.screen, fx["color"], pos, int(fx["r"]),
                               max(2, int(6 * fx["ttl"] / fx["max_ttl"])))

        # Draw enemies (world-space, camera-offset)
        for enemy in self.world.enemies:
            enemy.draw(self.screen, cam)

        # Rift-boss blink flash: a fading ring where the boss just teleported.
        if self.rift_boss is not None and getattr(self.rift_boss, 'teleport_flash', 0) > 0:
            b = self.rift_boss
            pos = (int(b.x - cam[0]), int(b.y - cam[1]))
            ring = int(40 + 120 * (1.0 - b.teleport_flash / 0.45))
            pygame.draw.circle(self.screen, (200, 120, 255), pos, ring, 3)

        # Draw minions
        for m in self.minions:
            m.draw(self.screen, cam)

        # Draw player
        self.player.draw(self.screen, cam)

        # Draw town stations when in the hub.
        if self.in_town:
            self.draw_town(cam)

        # Draw dropped items + rift progress orbs + pylon shrines
        self.draw_dropped_items(cam)
        self.draw_progress_orbs(cam)
        self.draw_pylons(cam)

        # Draw projectiles
        for projectile in self.projectiles:
            projectile.draw(self.screen, cam)

        # Draw enemy health bars
        for enemy_health_bar in self.enemy_health_bars.values():
            enemy_health_bar.draw(self.screen, cam)

        # Draw damage numbers
        self.damage_numbers.draw(self.screen, cam)

        # Draw UI
        self.draw_ui()
        
        # Draw player resources panel
        self.player_ui.draw(self.screen, self.player)
        
        # Update and draw skill bar (shows every usable active skill, 1-8)
        self.skill_bar_ui.draw(self.screen, self.skills, self.player)

        # Draw PoE2-style minimap (top-right)
        if self.show_minimap:
            self.draw_minimap()

        # Draw skill tree overlay
        if self.show_skill_tree:
            self.draw_skill_tree_overlay()
        
        # Draw inventory overlay
        if self.show_inventory:
            self.draw_inventory_overlay()

        # Draw per-spell mastery overlay
        if self.show_spell_tree:
            self.draw_spell_tree_overlay()
        
        # Draw character sheet overlay
        if self.show_character_sheet:
            self.draw_character_sheet_overlay()

        # Draw save/load slot menu
        if self.show_save_menu:
            self.draw_save_menu()

        # Draw stash transfer overlay
        if self.show_stash:
            self.draw_stash_overlay()
        
        # Draw rift progress bar + boss callouts (Phase 5)
        self.draw_rift_bar()

        # Draw transient rift message (keystone earned, GR opened, etc.)
        if self.rift_message_time > 0:
            self.draw_rift_message()

        # Draw level-up cue
        if self.level_up_cue_time > 0:
            self.draw_level_up_cue()

        # Draw Greater Rift picker overlay
        if self.show_gr_picker:
            self.draw_gr_picker()

        # Draw ascendancy / atlas overlay (Phase 15)
        if self.show_progression:
            self.draw_progression_overlay()

        # Draw pause overlay / pause menu (menu takes precedence)
        if self.show_pause_menu:
            self.draw_pause_menu()
        elif self.paused:
            self.draw_pause_overlay()
        
        # Draw game over overlay
        if self.game_over:
            self.draw_game_over_overlay()
        
        # Draw win overlay
        if self.won:
            self.draw_win_overlay()

        # Hover tooltips draw last so they sit on top of everything.
        self._draw_hover_tooltips()

        pygame.display.flip()

    def _draw_hover_tooltips(self):
        """Show an item tooltip for whatever the cursor is over.

        Priority: an open inventory's item rows, then a skill on the bar, then
        loose items lying on the ground. Only one tooltip shows at a time.
        """
        mouse = pygame.mouse.get_pos()

        # Inventory rows (backpack + equipped) when the inventory is open.
        if self.show_inventory:
            for rect, item in self._inv_item_rects:
                if rect.collidepoint(mouse):
                    # Backpack item: show it alongside the equipped item(s) it
                    # would compare against, with stat deltas.
                    self.item_tooltip.draw_with_comparison(
                        self.screen, item, self._equipped_compare_items(item),
                        mouse, self.width, self.height, self.player.level)
                    return
            for rect, _slot, item in self._equip_item_rects:
                if item is not None and rect.collidepoint(mouse):
                    self.item_tooltip.draw(self.screen, item, mouse,
                                           self.width, self.height, self.player.level)
                    return
            return  # inventory open but nothing hovered -> no other tooltips

        # No modal open: hover the skill bar or ground items.
        if not self._modal_open():
            skill = self.skill_bar_ui.skill_at(mouse)
            if skill is not None:
                self._draw_skill_tooltip(skill, mouse)
                return
            for rect, item in self._dropped_item_rects:
                if rect.collidepoint(mouse):
                    self.item_tooltip.draw(self.screen, item, mouse,
                                           self.width, self.height, self.player.level)
                    return

    def _draw_skill_tooltip(self, skill, pos):
        """Compact tooltip for a skill-bar slot: name, element, level, costs."""
        lines = [
            (skill.name, tuple(skill.color)),
            (f"{skill.element.title()} {skill.kind.title()}   Level {skill.level}/{skill.max_level}",
             (170, 175, 190)),
            (f"Mana Cost: {skill.mana_cost}", (110, 160, 255)),
            (f"Cooldown: {skill.cooldown:.2f}s", (200, 200, 120)),
        ]
        avail = skill.mastery_points_available()
        if avail > 0:
            lines.append((f"{avail} mastery point(s) to spend (K)", (140, 230, 165)))
        surfs = [self.small_font.render(t, True, c) for t, c in lines]
        w = max(s.get_width() for s in surfs) + 18
        h = sum(s.get_height() + 2 for s in surfs) + 14
        x, y = pos[0] + 16, pos[1] - h - 12
        if y < 4:
            y = pos[1] + 16
        if x + w > self.width:
            x = self.width - w - 4
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((12, 14, 22, 240))
        self.screen.blit(bg, (x, y))
        pygame.draw.rect(self.screen, tuple(skill.color), (x, y, w, h), 2, border_radius=4)
        cy = y + 7
        for s in surfs:
            self.screen.blit(s, (x + 9, cy))
            cy += s.get_height() + 2
    
    def draw_ui(self):
        """Draw the user interface."""
        # XP bar
        xp_text = f"XP: {int(self.player.experience)}/{int(self.player.xp_to_level)}"
        xp_surf = self.font.render(xp_text, True, (255, 200, 0))
        self.screen.blit(xp_surf, (320, 10))

        # Wallet
        wallet_text = f"Wallet: {self.player.diamond}D {self.player.gold}G {self.player.silver}S {self.player.copper}C"
        wallet_surf = self.font.render(wallet_text, True, (255, 215, 0))
        self.screen.blit(wallet_surf, (320, 35))

        # Biome / world info (Phase 11) + active map layout (Phase 18)
        info = self.world.get_info(self.player)
        layout_name = getattr(self, 'map_layout', {}).get('name', '-')
        map_text = (f"Biome: {info['name']} | Layout: {layout_name} | "
                    f"Enemies: {info['enemies_remaining']} | Chunks: {info['chunks_loaded']}")
        map_surf = self.font.render(map_text, True, (255, 255, 255))
        self.screen.blit(map_surf, (320, 60))
        
        # Active skill info (Phase 13)
        skill = self.skills.slot(self.player.active_skill)
        if skill:
            ready = "READY" if skill.cd_remaining <= 0 else f"{skill.cd_remaining:.1f}s"
            skills_text = (f"[{self.player.active_skill + 1}] {skill.name}  "
                           f"Lv{skill.level}  ({ready})  |  1-8 switch")
            skills_surf = self.font.render(skills_text, True, (255, 255, 255))
            self.screen.blit(skills_surf, (320, 85))
        
        # Inventory info
        inv_items = len(self.item_manager.inventory.items)
        inv_text = f"Inventory: {inv_items}/20 | Dropped Items: {len(self.dropped_items)} | Press I: Inventory"
        inv_surf = self.font.render(inv_text, True, (200, 200, 255))
        self.screen.blit(inv_surf, (320, 110))

        # Quest tracker (Phase 18)
        q_surf = self.font.render("Quest: " + self.quests.status_line(), True, (255, 225, 150))
        self.screen.blit(q_surf, (320, 135))
        qr_surf = self.small_font.render(self.quests.reward_line(), True, (180, 180, 140))
        self.screen.blit(qr_surf, (320, 158))
        
        # Instructions
        instr_text = ("WASD Move | Click/F Auto Cast | 1-8/Wheel Skill | T Town | P Tree | "
                      "K Spell Trees | I Inv | C Stats | M Map | V Ascend | G Rift | L Saves | ESC Menu")
        instr_surf = self.small_font.render(instr_text, True, (200, 200, 200))
        self.screen.blit(instr_surf, (10, self.height - 25))
    
    def draw_rift_bar(self):
        """Draw the rift progress bar (yellow normal / purple greater) up top."""
        r = self.rift
        bar_w, bar_h = 500, 22
        x = (self.width - bar_w) // 2
        y = 8

        # Frame + fill
        pygame.draw.rect(self.screen, (25, 25, 35), (x, y, bar_w, bar_h))
        fill_w = int(bar_w * r.progress_fraction)
        if fill_w > 0:
            pygame.draw.rect(self.screen, r.bar_color, (x, y, fill_w, bar_h))
        pygame.draw.rect(self.screen, (200, 200, 210), (x, y, bar_w, bar_h), 2)

        # Label + progress text
        if r.boss_active:
            label = f"{r.label}  -  BOSS"
        else:
            label = f"{r.label}   {int(r.progress)}/{int(r.threshold)}"
        text = self.small_font.render(label, True, (255, 255, 255))
        self.screen.blit(text, text.get_rect(center=(self.width // 2, y + bar_h // 2)))

        # Keystone count + chunks traveled + hint
        ks = self.item_manager.keystone_count()
        info = self.small_font.render(
            f"Keystones: {ks}   Best GR: {self.player.highest_gr}   "
            f"Chunks: {self.rift.chunks_traveled}   [G] Greater Rift",
            True, (220, 220, 160))
        self.screen.blit(info, (x, y + bar_h + 3))

        # Active pylon buffs.
        buffs = []
        if self.pylon_speed_timer > 0:
            buffs.append(("SPEED", f"{self.pylon_speed_timer:.0f}s", (120, 255, 160)))
        if self.pylon_conduit_timer > 0:
            buffs.append(("CONDUIT", f"{self.pylon_conduit_timer:.0f}s", (120, 200, 255)))
        bx = x
        for name, time_left, col in buffs:
            surf = self.small_font.render(f"{name} {time_left}", True, col)
            self.screen.blit(surf, (bx, y + bar_h + 20))
            bx += surf.get_width() + 16

    def draw_rift_message(self):
        """Draw the transient rift event message."""
        alpha = int(255 * min(1.0, self.rift_message_time))
        surf = self.font.render(self.rift_message, True, (255, 230, 120))
        surf.set_alpha(alpha)
        self.screen.blit(surf, surf.get_rect(center=(self.width // 2, 70)))

    def draw_progression_overlay(self):
        """Ascendancy + Atlas overlay (Phase 15)."""
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        x = 120
        y = 80
        title = self.large_font.render("Endgame Progression", True, (200, 160, 255))
        self.screen.blit(title, (x, y))
        y += 50

        # Ascendancy
        asc = self.ascendancy
        head = self.font.render(
            f"ASCENDANCY  (points: {asc.points_available(self.player.level)})",
            True, (255, 220, 120))
        self.screen.blit(head, (x, y)); y += 28
        if asc.chosen is None:
            sub = "Reach level 20, then press 1-4 to choose:" if self.player.level >= 20 \
                else f"Unlocks at level 20 (you are level {self.player.level})"
            self.screen.blit(self.small_font.render(sub, True, (200, 200, 200)), (x, y)); y += 22
            for i, cid in enumerate(asc.available_classes()):
                self.screen.blit(self.small_font.render(
                    f"  {i + 1}. {asc.classes[cid]['name']}", True, (220, 220, 220)), (x, y))
                y += 20
        else:
            self.screen.blit(self.small_font.render(
                f"Class: {asc.classes[asc.chosen]['name']}   (1-4 allocate nodes)",
                True, (180, 255, 180)), (x, y)); y += 22
            for i, node in enumerate(asc.classes[asc.chosen]["nodes"]):
                mark = "[x]" if node["id"] in asc.allocated else "[ ]"
                ks = "  * KEYSTONE" if node.get("keystone") else ""
                self.screen.blit(self.small_font.render(
                    f"  {i + 1}. {mark} {node['label']}{ks}", True, (220, 220, 220)), (x, y))
                y += 20

        y += 24
        head2 = self.font.render(f"ATLAS  (points: {self.atlas.points})  -  press A to allocate",
                                 True, (120, 220, 255))
        self.screen.blit(head2, (x, y)); y += 28
        for nid, node in self.atlas.nodes.items():
            mark = "[x]" if nid in self.atlas.allocated else "[ ]"
            self.screen.blit(self.small_font.render(
                f"  {mark} {node['label']}", True, (210, 210, 210)), (x, y))
            y += 20

        self.screen.blit(self.small_font.render("Press V or Esc to close", True, (200, 200, 200)),
                         (x, self.height - 40))

    def draw_gr_picker(self):
        """Draw the Greater Rift level picker overlay (Phase 5)."""
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(160)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 460, 240
        px = (self.width - pw) // 2
        py = (self.height - ph) // 2
        pygame.draw.rect(self.screen, (20, 16, 30), (px, py, pw, ph))
        pygame.draw.rect(self.screen, (170, 70, 220), (px, py, pw, ph), 3)

        title = self.large_font.render("Greater Rift", True, (200, 130, 255))
        self.screen.blit(title, title.get_rect(center=(self.width // 2, py + 32)))

        ks = self.item_manager.keystone_count()
        lines = [
            f"Selected Level:  {self.gr_selected_level}",
            f"Rift Keystones:  {ks}",
            "",
            "Left/Right: +/-1    PgUp/PgDn: +/-10",
            "Enter: Open (consumes 1 keystone)",
            "Esc / G: Cancel",
        ]
        big = self.large_font.render(f"Lv {self.gr_selected_level}", True, (255, 235, 120))
        self.screen.blit(big, big.get_rect(center=(self.width // 2, py + 78)))

        y = py + 108
        for i, line in enumerate(lines[1:]):
            color = (255, 255, 255) if i == 0 else (190, 190, 200)
            surf = self.small_font.render(line, True, color)
            self.screen.blit(surf, surf.get_rect(center=(self.width // 2, y)))
            y += 22

    def draw_level_up_cue(self):
        """Draw the fading 'LEVEL UP!' banner after a level-up (Phase 3)."""
        # Fade out over the last second of the cue.
        alpha = int(255 * min(1.0, self.level_up_cue_time))
        cx = self.width // 2
        cy = int(self.height * 0.28)

        title = self.large_font.render("LEVEL UP!", True, (255, 215, 0))
        subtitle = self.font.render(
            f"Level {self.level_up_level}   +1 Skill Point", True, (255, 255, 255)
        )
        title.set_alpha(alpha)
        subtitle.set_alpha(alpha)

        self.screen.blit(title, title.get_rect(center=(cx, cy)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(cx, cy + 32)))

    def draw_pause_overlay(self):
        """Draw pause overlay."""
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(128)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        pause_text = self.large_font.render("PAUSED", True, (255, 255, 255))
        text_rect = pause_text.get_rect(center=(self.width // 2, self.height // 2))
        self.screen.blit(pause_text, text_rect)

    # Keybinds shown in the pause menu (label, description).
    KEYBINDS = [
        ("WASD", "Move"),
        ("Left Click", "Cast active skill"),
        ("1 - 8 / Wheel", "Switch active skill"),
        ("F", "Toggle auto-fire (auto-aim)"),
        ("T", "Town portal (to/from town)"),
        ("E", "Interact with town station"),
        ("P", "Passive skill tree"),
        ("K", "Spell trees (per-spell mastery)"),
        ("I", "Inventory (equip / sell / upgrade)"),
        ("C", "Character sheet"),
        ("M", "Toggle minimap"),
        ("V", "Ascendancy / Atlas"),
        ("G", "Greater Rift"),
        ("L", "Save / Load slots"),
        ("Space", "Quick pause / resume"),
        ("F5 / F9", "Quick save / load"),
        ("Esc", "Pause menu (this)"),
        ("Q", "Quit game"),
    ]

    def _draw_button(self, rect, label, base, hover):
        """Draw a labeled menu button; returns the rect for hit-testing."""
        mouse = pygame.mouse.get_pos()
        col = hover if rect.collidepoint(mouse) else base
        pygame.draw.rect(self.screen, col, rect, border_radius=6)
        pygame.draw.rect(self.screen, (220, 225, 240), rect, 2, border_radius=6)
        txt = self.font.render(label, True, (255, 255, 255))
        self.screen.blit(txt, txt.get_rect(center=rect.center))
        return rect

    def _draw_volume_slider(self, x, y, w, label, value, kind):
        """Draw a labeled horizontal volume slider and register its hit-rects."""
        lab = self.font.render(label, True, (210, 220, 240))
        self.screen.blit(lab, (x, y - 24))
        pct = self.small_font.render(f"{int(round(value * 100))}%", True, (200, 210, 160))
        self.screen.blit(pct, pct.get_rect(midright=(x + w, y - 22)))

        track = pygame.Rect(x, y, w, 6)
        pygame.draw.rect(self.screen, (60, 64, 84), track, border_radius=3)
        fill = pygame.Rect(x, y, int(w * value), 6)
        pygame.draw.rect(self.screen, (120, 190, 255), fill, border_radius=3)
        knob = pygame.Rect(0, 0, 16, 20)
        knob.center = (x + int(w * value), y + 3)
        pygame.draw.rect(self.screen, (235, 240, 255), knob, border_radius=4)
        self._volume_sliders.append((track, knob, kind))

    def draw_pause_menu(self):
        """Streamlined pause menu: Resume / Save / Controls / Quit buttons, plus
        live SFX and Music volume sliders. Controls list is collapsed by default."""
        self._pause_buttons = []
        self._volume_sliders = []

        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(190)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))

        pw = 440
        ph = 600 if self.show_controls else 410
        px = (self.width - pw) // 2
        py = (self.height - ph) // 2
        pygame.draw.rect(self.screen, (18, 20, 34), (px, py, pw, ph), border_radius=10)
        pygame.draw.rect(self.screen, (120, 150, 220), (px, py, pw, ph), 3, border_radius=10)

        title = self.large_font.render("PAUSED", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(self.width // 2, py + 34)))

        cx = self.width // 2
        bw, bh, gap = 280, 44, 12
        bx = cx - bw // 2

        # --- Audio section ---------------------------------------------------
        sec = self.font.render("Audio", True, (255, 220, 120))
        self.screen.blit(sec, (px + 30, py + 66))
        sx, sw = px + 40, pw - 80
        self._draw_volume_slider(sx, py + 110, sw, "Sound Effects",
                                 self.sound.sfx_volume, 'sfx')
        self._draw_volume_slider(sx, py + 158, sw, "Music",
                                 self.sound.music_volume, 'music')

        # --- Buttons ---------------------------------------------------------
        y = py + 196
        self._pause_buttons.append(
            (self._draw_button(pygame.Rect(bx, y, bw, bh), "Resume",
                               (45, 90, 60), (60, 130, 85)), 'resume'))
        y += bh + gap
        self._pause_buttons.append(
            (self._draw_button(pygame.Rect(bx, y, bw, bh), "Save / Load",
                               (40, 60, 95), (60, 90, 140)), 'saves'))
        y += bh + gap
        ctl_label = "Hide Controls" if self.show_controls else "Show Controls"
        self._pause_buttons.append(
            (self._draw_button(pygame.Rect(bx, y, bw, bh), ctl_label,
                               (60, 60, 80), (90, 90, 120)), 'controls'))
        y += bh + gap

        # --- Collapsible keybind reference (two compact columns) ------------
        if self.show_controls:
            rows = (len(self.KEYBINDS) + 1) // 2
            row_h = 16
            col_x = (px + 24, px + pw // 2 + 6)
            for i, (keys, desc) in enumerate(self.KEYBINDS):
                cxk = col_x[i // rows]
                ky = y + (i % rows) * row_h
                self.screen.blit(self.small_font.render(keys, True, (150, 220, 255)), (cxk, ky))
                self.screen.blit(self.small_font.render(desc, True, (205, 205, 215)),
                                 (cxk + 92, ky))
            y += rows * row_h + 8

        self._pause_buttons.append(
            (self._draw_button(pygame.Rect(bx, y, bw, bh), "Quit Game",
                               (95, 45, 45), (135, 60, 60)), 'quit'))

        hint = self.small_font.render("Esc: Resume    Q: Quit    (drag sliders to set volume)",
                                      True, (190, 190, 200))
        self.screen.blit(hint, hint.get_rect(center=(cx, py + ph - 20)))


    def draw_skill_tree_overlay(self):
        """Draw skill tree overlay."""
        # Create temporary surface for skill tree
        tree_surface = pygame.Surface((self.width - 100, self.height - 100))
        self.skill_tree_ui.draw(tree_surface, self.player)
        
        # Draw on main screen
        self.screen.blit(tree_surface, (0, 0))
        
        # Draw close instructions
        close_text = self.font.render("Press P to close skill tree | WASD: Pan | Right drag: Pan", True, (255, 255, 255))
        self.screen.blit(close_text, (10, self.height - 30))
    
    def draw_town(self, cam):
        """Draw the town hub: station markers, labels and the interaction prompt."""
        for s in self.town_stations:
            sx = int(s['x'] - cam[0])
            sy = int(s['y'] - cam[1])
            near = (s is self._near_station)
            # Building marker
            pygame.draw.circle(self.screen, s['color'], (sx, sy), 26)
            pygame.draw.circle(self.screen, (255, 255, 255) if near else (30, 30, 40),
                               (sx, sy), 26, 3)
            label = self.small_font.render(s['name'], True, (235, 235, 245))
            self.screen.blit(label, label.get_rect(center=(sx, sy - 38)))

        # Town banner
        banner = self.font.render("TOWN  -  safe haven", True, (220, 230, 255))
        self.screen.blit(banner, banner.get_rect(center=(self.width // 2, 90)))

        # Interaction prompt for the station the player is standing on.
        if self._near_station:
            prompts = {
                'stash': "Press E: Open Stash",
                'merchant': "Press E: Sell all common/uncommon loot",
                'smith': "Press E: Open inventory to upgrade gear",
                'portal': "Press E: Return to the rift",
            }
            txt = prompts.get(self._near_station['key'], "Press E")
            ps = self.font.render(txt, True, (255, 235, 150))
            self.screen.blit(ps, ps.get_rect(center=(self.width // 2, self.height - 90)))

    def draw_stash_overlay(self):
        """Stash transfer panel: backpack (left) <-> stash (right), click to move."""
        self._stash_left_rects = []
        self._stash_right_rects = []

        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(160)
        overlay.fill((5, 8, 14))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 780, 540
        px = (self.width - pw) // 2
        py = (self.height - ph) // 2
        pygame.draw.rect(self.screen, (20, 24, 38), (px, py, pw, ph))
        pygame.draw.rect(self.screen, (120, 170, 220), (px, py, pw, ph), 3)
        title = self.large_font.render("Stash", True, (160, 210, 255))
        self.screen.blit(title, title.get_rect(center=(self.width // 2, py + 22)))

        row_h, col_w = 26, 350
        list_top = py + 64
        max_rows = (ph - 130) // row_h
        mouse = pygame.mouse.get_pos()

        def draw_col(items, x, header, rects):
            head = self.font.render(header, True, (180, 200, 255))
            self.screen.blit(head, (x, list_top - 28))
            for i, item in enumerate(items[:max_rows]):
                ry = list_top + i * row_h
                rect = pygame.Rect(x, ry, col_w, row_h - 2)
                if rect.collidepoint(mouse):
                    pygame.draw.rect(self.screen, (45, 50, 72), rect)
                label = item.name + (f" x{item.stack}" if getattr(item, 'stack', 1) > 1 else "")
                self.screen.blit(self.small_font.render(label, True, item.get_color()),
                                 (x + 6, ry + 5))
                rects.append((rect, item))

        inv = self.item_manager.inventory
        draw_col(inv.items, px + 20, f"Backpack ({len(inv.items)}/{inv.capacity})",
                 self._stash_left_rects)
        draw_col(self.stash, px + pw - col_w - 20,
                 f"Stash ({len(self.stash)}/{self.STASH_CAPACITY})", self._stash_right_rects)

        instr = self.small_font.render(
            "Left-click an item to move it between Backpack and Stash    |    E / Esc: Close",
            True, (200, 200, 200))
        self.screen.blit(instr, instr.get_rect(center=(self.width // 2, py + ph - 18)))

    def draw_inventory_overlay(self):
        """Interactive inventory: left column = backpack, right = equipped gear.

        Rebuilds the clickable hit-rects (_inv_item_rects / _equip_item_rects)
        each frame so handle_events() can resolve a click to an item action.
        """
        self._inv_item_rects = []
        self._equip_item_rects = []

        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(150)
        overlay.fill((5, 5, 12))
        self.screen.blit(overlay, (0, 0))

        panel_width = 760
        panel_height = 540
        panel_x = (self.width - panel_width) // 2
        panel_y = (self.height - panel_height) // 2

        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(self.screen, (20, 20, 40), panel_rect)
        pygame.draw.rect(self.screen, (100, 150, 200), panel_rect, 3)

        title_text = self.large_font.render("Inventory", True, (255, 200, 0))
        self.screen.blit(title_text, title_text.get_rect(center=(self.width // 2, panel_y + 22)))

        row_h = 26
        col_w = 350
        list_top = panel_y + 58
        max_rows = (panel_height - 120) // row_h

        # --- Backpack column (left): left-click equip, right-click sell -----
        inv = self.item_manager.inventory
        left_x = panel_x + 20
        head = self.font.render(f"Backpack  ({len(inv.items)}/{inv.capacity})",
                                True, (180, 200, 255))
        self.screen.blit(head, (left_x, list_top - 28))

        items = inv.items
        for i, item in enumerate(items[:max_rows]):
            ry = list_top + i * row_h
            rect = pygame.Rect(left_x, ry, col_w, row_h - 2)
            mx, my = pygame.mouse.get_pos()
            if rect.collidepoint(mx, my):
                pygame.draw.rect(self.screen, (45, 45, 70), rect)
            label = item.name
            if getattr(item, 'stack', 1) > 1:
                label += f" x{item.stack}"
            name_surf = self.small_font.render(label, True, item.get_color())
            self.screen.blit(name_surf, (left_x + 6, ry + 5))
            if getattr(item, 'item_type', None) != 'keystone':
                val_surf = self.small_font.render(f"{item.get_sell_value()}c",
                                                  True, (210, 190, 110))
                self.screen.blit(val_surf, (left_x + col_w - 60, ry + 5))
            self._inv_item_rects.append((rect, item))
        if len(items) > max_rows:
            more = self.small_font.render(f"... +{len(items) - max_rows} more",
                                          True, (160, 160, 160))
            self.screen.blit(more, (left_x + 6, list_top + max_rows * row_h + 2))

        # --- Equipped column (right): left-click upgrade / right-click unequip
        right_x = panel_x + panel_width - col_w - 20
        head2 = self.font.render("Equipped", True, (140, 255, 140))
        self.screen.blit(head2, (right_x, list_top - 28))

        from src.items.item import slot_display_name
        for i, (slot, item) in enumerate(self.item_manager.equipment.equipment.items()):
            ry = list_top + i * row_h
            rect = pygame.Rect(right_x, ry, col_w, row_h - 2)
            slot_name = slot_display_name(slot)
            slot_surf = self.small_font.render(slot_name, True, (150, 150, 170))
            self.screen.blit(slot_surf, (right_x + 6, ry + 5))
            if item is not None:
                mx, my = pygame.mouse.get_pos()
                if rect.collidepoint(mx, my):
                    pygame.draw.rect(self.screen, (45, 60, 45), rect)
                lvl = f" +{item.upgrade_level}" if item.upgrade_level else ""
                name_surf = self.small_font.render(item.name + lvl, True, item.get_color())
                self.screen.blit(name_surf, (right_x + 110, ry + 5))
                # Upgrade cost (or MAX) on the right edge.
                if item.can_upgrade():
                    up = self.small_font.render(f"{item.upgrade_cost()}c", True, (210, 190, 110))
                else:
                    up = self.small_font.render("MAX", True, (150, 200, 150))
                self.screen.blit(up, (right_x + col_w - 56, ry + 5))
                self._equip_item_rects.append((rect, slot, item))
            else:
                empty_surf = self.small_font.render("(empty)", True, (90, 90, 100))
                self.screen.blit(empty_surf, (right_x + 110, ry + 5))

        # Instructions
        instr = self.small_font.render(
            "Backpack: L-click Equip / R-click Sell    |    "
            "Equipped: L-click Upgrade / R-click Unequip    |    I: Close",
            True, (200, 200, 200))
        self.screen.blit(instr, instr.get_rect(center=(self.width // 2, panel_y + panel_height - 18)))

    def draw_character_sheet_overlay(self):
        """Draw character sheet overlay."""
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(100)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        # Draw character sheet
        if self.character_sheet_ui:
            self.character_sheet_ui.draw(self.screen)
        
        # Instructions
        instr = self.font.render("Press C to close character sheet", True, (200, 200, 200))
        instr_rect = instr.get_rect(center=(self.width // 2, self.height - 20))
        self.screen.blit(instr, instr_rect)
    
    def draw_dropped_items(self, cam):
        """Draw items dropped on the ground (camera-offset)."""
        self._dropped_item_rects = []
        for dropped in self.dropped_items:
            item = dropped['item']
            x = dropped['x'] - cam[0]
            y = dropped['y'] - cam[1]
            # Hover region (name label + marker) for ground tooltips.
            self._dropped_item_rects.append(
                (pygame.Rect(int(x) - 50, int(y) - 24, 100, 44), item))

            # Draw item name with rarity color
            item_color = item.get_color()
            item_text = self.small_font.render(item.name, True, item_color)

            # Flash if about to disappear
            if dropped['time_to_live'] < 2.0:
                alpha = int(100 + 150 * (dropped['time_to_live'] / 2.0))
                item_text.set_alpha(alpha)

            text_rect = item_text.get_rect(center=(x, y - 10))
            self.screen.blit(item_text, text_rect)
            pygame.draw.circle(self.screen, item_color, (int(x), int(y)), 15, 1)

    
    def draw_game_over_overlay(self):
        """Draw game over overlay."""
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        game_over_text = self.large_font.render("GAME OVER", True, (255, 0, 0))
        restart_text = self.font.render("Press ESC to exit", True, (255, 255, 255))
        
        text_rect1 = game_over_text.get_rect(center=(self.width // 2, self.height // 2 - 40))
        text_rect2 = restart_text.get_rect(center=(self.width // 2, self.height // 2 + 20))
        
        self.screen.blit(game_over_text, text_rect1)
        self.screen.blit(restart_text, text_rect2)
    
    def draw_win_overlay(self):
        """Draw win overlay."""
        overlay = pygame.Surface((self.width, self.height))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.screen.blit(overlay, (0, 0))
        
        win_text = self.large_font.render("YOU WIN!", True, (0, 255, 0))
        text_rect1 = win_text.get_rect(center=(self.width // 2, self.height // 2 - 120))
        self.screen.blit(win_text, text_rect1)
        
        # Final stats
        stats = [
            f"Final Level: {self.player.level}",
            f"Experience: {int(self.player.experience)}",
            f"Wallet: {self.player.diamond}💎 {self.player.gold}🟡 {self.player.silver}⚪ {self.player.copper}🟤",
            f"Skill Points: {self.player.skill_points}",
            f"Wand Level: {self.player.wand_level}",
        ]
        
        y_offset = -60
        for stat in stats:
            stat_text = self.font.render(stat, True, (255, 255, 255))
            text_rect = stat_text.get_rect(center=(self.width // 2, self.height // 2 + y_offset))
            self.screen.blit(stat_text, text_rect)
            y_offset += 30
        
        exit_text = self.font.render("Press ESC to exit", True, (255, 255, 255))
        text_rect3 = exit_text.get_rect(center=(self.width // 2, self.height // 2 + 150))
        self.screen.blit(exit_text, text_rect3)
    
    def run(self):
        """Main game loop."""
        while self.running:
            # Real frame delta in seconds (DESIGN.md R3). Clamp to avoid huge
            # steps after a stall (e.g. window drag).
            self.dt = min(self.clock.tick(self.fps) / 1000.0, 0.05)

            self.handle_events()
            self.handle_input()
            self.update()
            self.draw()
        
        pygame.quit()
        sys.exit()

def main():
    """Entry point: resume the most recent save, or create one for a new game."""
    game = Game()
    slot = save_system.latest_slot(Game.NUM_SAVE_SLOTS)
    if slot is not None:
        game.load_game(slot)            # resume where the player left off
        game.active_save_slot = slot
    else:
        game.save_game(0)               # brand-new character: seed an initial save
        game.active_save_slot = 0
    game.run()

if __name__ == "__main__":
    main()
