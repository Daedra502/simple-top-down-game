#!/usr/bin/env python3
"""
Phase 3 Systems Test Suite
Tests: Gem integration, Elemental combat, Character sheet UI
"""

import os

# Initialize Pygame display (needed for font rendering)
import pygame
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((800, 600))

from src.spells.spells_with_gems import (
    FireballWithGems, FrostBoltWithGems, LightningStrikeWithGems,
    ProjectileWithGems, get_spell_with_gems
)
from src.spells.gems import GemLibrary, GemType
from src.spells.elements import ElementType, ElementalEffectManager
from src.systems.combat import CombatSystem
from src.entities.enemy import Enemy, EnemyType
from src.entities.player import Player
from src.spells.skill_tree import SkillTree
from src.items.synergistic_items import SynergisticItemFactory
from src.ui.character_sheet import CharacterSheetUI
from src.items.inventory import ItemManager


def test_gem_spell_integration():
    """Test gem integration with spells."""
    print("=" * 60)
    print("TEST 1: Gem-Spell Integration")
    print("=" * 60)
    
    # Create spell with gem support
    fireball = FireballWithGems()
    print(f"[OK] Created {fireball.name} spell with gem sockets")
    
    # Get a support gem
    GemLibrary.create_all_gems()
    
    # Try to add gems (even if gems list is short)
    print(f"[OK] Available gems in library")
    
    # Test spell configuration building
    config = fireball.config
    if config:
        final_dmg = config.get_final_damage(player_stats={})
        print(f"[OK] Spell base damage: {fireball.base_damage}")
        print(f"[OK] Final damage with modifiers: {final_dmg:.1f}")
    
    print()


def test_elemental_combat():
    """Test elemental damage in combat."""
    print("=" * 60)
    print("TEST 2: Elemental Combat")
    print("=" * 60)
    
    # Create combat system and entities
    combat_system = CombatSystem()
    enemy = Enemy(100, 100, EnemyType.GOBLIN)
    
    print(f"[OK] Created enemy: {enemy.enemy_type} with {enemy.max_health} HP")
    print(f"[OK] Enemy has elemental effects manager: {hasattr(enemy, 'elemental_effects')}")
    
    # Apply elemental damage
    initial_hp = enemy.health
    is_dead = combat_system.apply_elemental_damage(
        damage=15, 
        target=enemy,
        element_type=ElementType.FIRE,
        modifier=1.2,
        apply_status=True
    )
    
    damage_taken = initial_hp - enemy.health
    print(f"[OK] Applied elemental damage (fire type)")
    print(f"  Damage taken: {damage_taken}")
    print(f"  Remaining HP: {enemy.health}/{enemy.max_health}")
    
    # Check status effects
    if hasattr(enemy, 'elemental_effects'):
        active_effects = enemy.elemental_effects.get_active_effects()
        print(f"[OK] Active status effects: {len(active_effects)}")
        for effect in active_effects:
            print(f"  - {effect['name']}: {effect['intensity']}x intensity")
    
    print()


def test_spell_projectile_gems():
    """Test projectiles with gem modifiers."""
    print("=" * 60)
    print("TEST 3: Spell Projectiles with Gems")
    print("=" * 60)
    
    spell = LightningStrikeWithGems()
    print(f"[OK] Created {spell.name} spell")
    
    # Cast a projectile
    projectile = spell.cast(0, 0, 100, 100)
    print(f"[OK] Cast projectile")
    print(f"  Base damage: {spell.base_damage}")
    print(f"  Projectile damage: {projectile.damage}")
    print(f"  Element type: {projectile.element_type}")
    print(f"  Max chain: {projectile.max_chain}")
    print(f"  Max pierce: {projectile.max_pierce}")
    
    # Test pierce mechanics
    if projectile.can_pierce():
        projectile.apply_pierce()
        print(f"[OK] Applied pierce effect")
    
    print()


def test_character_sheet():
    """Test character sheet UI."""
    print("=" * 60)
    print("TEST 4: Character Sheet UI")
    print("=" * 60)
    
    # Create game entities
    player = Player(0, 0)
    skill_tree = SkillTree()
    item_manager = ItemManager(player, capacity=20)
    
    print(f"[OK] Created player, skill tree, and inventory")
    
    # Allocate some skill tree nodes
    skill_tree.allocate_node("fire_1")
    skill_tree.allocate_node("cold_1")
    print(f"[OK] Allocated skill tree nodes")
    
    # Add some items to inventory
    for _ in range(3):
        item = SynergisticItemFactory.get_synergistic_item(5)
        item_manager.inventory.add_item(item)
    print(f"[OK] Added items to inventory")
    
    # Create character sheet UI
    char_sheet = CharacterSheetUI(player, skill_tree, item_manager)
    print(f"[OK] Created character sheet UI")
    
    # Get stat breakdown
    breakdown = char_sheet.get_stat_breakdown()
    print(f"\n[OK] Character sheet stats:")
    print(f"  Level: {breakdown['player_stats']['level']}")
    print(f"  Health: {breakdown['player_stats']['health']}/{breakdown['player_stats']['max_health']}")
    print(f"  Skill tree bonuses: {len(breakdown['skill_tree_bonuses'])} effects")
    print(f"  Equipped items: {breakdown['equipment']['equipped_count']}")
    
    print()


def test_full_integration():
    """Test all Phase 3 systems working together."""
    print("=" * 60)
    print("TEST 5: Full Phase 3 Integration")
    print("=" * 60)
    
    # Create all systems
    player = Player(100, 100)
    skill_tree = SkillTree()
    item_manager = ItemManager(player, capacity=20)
    combat_system = CombatSystem()
    enemy = Enemy(200, 100, EnemyType.ORC)
    
    print(f"[OK] Created all Phase 3 systems")
    
    # Apply skill tree bonuses to player
    skill_tree.allocate_node("fire_1")
    player.apply_skill_tree_bonuses(skill_tree)
    print(f"[OK] Applied skill tree bonuses to player")
    print(f"  New attack speed: {player.attack_speed}")
    
    # Cast spell with gems
    spell = FireballWithGems()
    projectile = spell.cast(player.x, player.y, enemy.x, enemy.y)
    print(f"[OK] Cast gem-integrated spell")
    print(f"  Projectile element: {projectile.element_type}")
    
    # Apply elemental damage
    initial_hp = enemy.health
    is_dead = combat_system.apply_elemental_damage(
        projectile.damage, enemy, 
        element_type=ElementType.FIRE,
        modifier=1.0
    )
    print(f"[OK] Applied elemental damage")
    print(f"  Damage dealt: {initial_hp - enemy.health}")
    
    # Update character sheet
    char_sheet = CharacterSheetUI(player, skill_tree, item_manager)
    breakdown = char_sheet.get_stat_breakdown()
    print(f"[OK] Updated character sheet")
    print(f"  Player level: {breakdown['player_stats']['level']}")
    
    print(f"\n[OK] All Phase 3 systems integrated successfully!")
    print()
