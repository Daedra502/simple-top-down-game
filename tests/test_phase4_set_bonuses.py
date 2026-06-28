#!/usr/bin/env python3
"""
Phase 4 Systems Test Suite - Set Bonus Calculation
Tests set bonus tracking, calculation, and application
"""

import os

# Initialize Pygame display
import pygame
os.environ['SDL_VIDEODRIVER'] = 'dummy'
pygame.init()
pygame.display.set_mode((800, 600))

from src.items.set_bonuses import SetBonusCalculator, SetBonusTracker
from src.items.inventory import ItemManager
from src.items.synergistic_items import SynergisticItemFactory
from src.entities.player import Player


def test_set_bonus_calculation():
    """Test basic set bonus calculations."""
    print("=" * 60)
    print("TEST 1: Set Bonus Calculation")
    print("=" * 60)
    
    calculator = SetBonusCalculator()
    print(f"[OK] Created SetBonusCalculator")
    
    # Create item sets via factory
    factory = SynergisticItemFactory()
    factory.create_all_sets()
    all_sets = factory.item_sets.values()
    
    print(f"[OK] Created {len(all_sets)} item sets")
    for item_set in all_sets:
        print(f"  - {item_set.set_name}: {len(item_set.items)} items")
    
    print()


def test_set_bonus_tracking():
    """Test tracking equipped items by set."""
    print("=" * 60)
    print("TEST 2: Set Bonus Tracking")
    print("=" * 60)
    
    calculator = SetBonusCalculator()
    
    # Create test items
    factory = SynergisticItemFactory()
    factory.create_all_sets()
    items = []
    
    # Get items from the Inferno set
    for _ in range(2):
        item = factory.get_synergistic_item(5, preferred_element="fire")
        if item:
            items.append(item)
    
    print(f"[OK] Created {len(items)} test items")
    
    # Calculate set bonuses
    set_bonuses = calculator.calculate_set_bonuses(items)
    print(f"[OK] Calculated set bonuses")
    print(f"  Active sets: {len(set_bonuses)}")
    
    for set_name, set_info in set_bonuses.items():
        print(f"  - {set_name}: {set_info['pieces']}/{set_info['total_pieces']} pieces")
        if set_info['bonuses']:
            for bonus, value in set_info['bonuses'].items():
                print(f"    * {bonus}: +{value}")
    
    print()


def test_set_bonus_aggregation():
    """Test aggregating bonuses from multiple sets."""
    print("=" * 60)
    print("TEST 3: Set Bonus Aggregation")
    print("=" * 60)
    
    calculator = SetBonusCalculator()
    
    # Create items from multiple sets
    factory = SynergisticItemFactory()
    factory.create_all_sets()
    items = []
    
    # Fire items
    for _ in range(2):
        item = factory.get_synergistic_item(5, preferred_element="fire")
        if item:
            items.append(item)
    
    # Cold items
    for _ in range(2):
        item = factory.get_synergistic_item(5, preferred_element="cold")
        if item:
            items.append(item)
    
    print(f"[OK] Created items from multiple sets: {len(items)} total")
    
    # Calculate and aggregate
    set_bonuses = calculator.calculate_set_bonuses(items)
    total_bonuses = calculator.get_total_bonuses(set_bonuses)
    
    print(f"[OK] Active sets: {len(set_bonuses)}")
    print(f"[OK] Aggregated bonuses:")
    for bonus_key, bonus_value in total_bonuses.items():
        print(f"  - {bonus_key}: +{bonus_value}")
    
    print()


def test_set_bonus_with_item_manager():
    """Test set bonus integration with ItemManager."""
    print("=" * 60)
    print("TEST 4: Set Bonus with ItemManager")
    print("=" * 60)
    
    player = Player(100, 100)
    item_manager = ItemManager(player, capacity=20)
    
    print(f"[OK] Created player and ItemManager")
    
    # Get items to equip
    factory = SynergisticItemFactory()
    factory.create_all_sets()
    items_to_equip = []
    
    for _ in range(2):
        item = factory.get_synergistic_item(5, preferred_element="fire")
        if item:
            items_to_equip.append(item)
    
    print(f"[OK] Created {len(items_to_equip)} items to equip")
    
    # Add to inventory first
    for item in items_to_equip:
        item_manager.inventory.add_item(item)
    
    print(f"[OK] Added items to inventory")
    
    # Equip items
    equipped_count = 0
    for item in items_to_equip:
        result = item_manager.try_equip_item(item)
        if item_manager.equipment.get_equipped_item(item.slot):
            equipped_count += 1
    
    print(f"[OK] Equipped {equipped_count} items")
    
    # Update and get set bonuses
    set_bonuses = item_manager.update_set_bonuses()
    print(f"[OK] Updated set bonuses")
    print(f"  Active sets: {len(set_bonuses)}")
    
    for set_name, set_info in set_bonuses.items():
        print(f"  - {set_name}: {set_info['pieces']}/{set_info['total_pieces']} pieces")
    
    print()


def test_set_bonus_summary():
    """Test set bonus summary for UI display."""
    print("=" * 60)
    print("TEST 5: Set Bonus Summary for UI")
    print("=" * 60)
    
    player = Player(100, 100)
    item_manager = ItemManager(player, capacity=20)
    
    # Create and equip items
    factory = SynergisticItemFactory()
    factory.create_all_sets()
    for _ in range(3):
        item = factory.get_synergistic_item(5, preferred_element="fire")
        if item:
            item_manager.inventory.add_item(item)
            item_manager.try_equip_item(item)
    
    print(f"[OK] Equipped 3 fire items")
    
    # Get summary
    summary = item_manager.get_set_bonus_summary()
    print(f"[OK] Got set bonus summary:")
    
    for set_info in summary:
        status = "ACTIVE" if set_info['active'] else "inactive"
        print(f"  - {set_info['name']}: {set_info['current']}/{set_info['total']} ({status})")
    
    print()


def test_empty_set_bonus():
    """Test set bonuses with no equipped items."""
    print("=" * 60)
    print("TEST 6: Empty Set Bonus (No Equipment)")
    print("=" * 60)
    
    calculator = SetBonusCalculator()
    
    # Calculate with empty list
    set_bonuses = calculator.calculate_set_bonuses([])
    
    print(f"[OK] Calculated set bonuses with no items")
    print(f"  Active sets: {len(set_bonuses)}")
    assert len(set_bonuses) == 0, "Should have no active sets"
    
    # Get total bonuses
    total = calculator.get_total_bonuses(set_bonuses)
    print(f"  Total bonuses: {len(total)}")
    assert len(total) == 0, "Should have no bonuses"
    
    print()


def test_set_bonus_progression():
    """Test bonus changes as more pieces are equipped."""
    print("=" * 60)
    print("TEST 7: Set Bonus Progression (2pc -> 3pc -> 4pc)")
    print("=" * 60)
    
    calculator = SetBonusCalculator()
    factory = SynergisticItemFactory()
    factory.create_all_sets()
    
    # Test with different piece counts
    for piece_count in [1, 2, 3, 4]:
        items = []
        for _ in range(piece_count):
            item = factory.get_synergistic_item(5, preferred_element="fire")
            if item:
                items.append(item)
        
        set_bonuses = calculator.calculate_set_bonuses(items)
        total_bonuses = calculator.get_total_bonuses(set_bonuses)
        
        print(f"[OK] {piece_count} pieces equipped:")
        if set_bonuses:
            for set_name, set_info in set_bonuses.items():
                print(f"  Set: {set_name}")
                if set_info['bonuses']:
                    for bonus, value in set_info['bonuses'].items():
                        print(f"    - {bonus}: +{value}")
        else:
            print(f"  (No set bonuses yet)")
    
    print()
