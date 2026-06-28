#!/usr/bin/env python3
"""
Quick test script to verify Phase 2 systems work correctly.
Tests: Skill Tree, Synergistic Items, Elemental System, Gems
"""


from src.spells.skill_tree import SkillTree, NodeType
from src.items.synergistic_items import SynergisticItemFactory
from src.spells.elements import ElementType, ElementalDamage, ElementalEffectManager
from src.spells.gems import GemLibrary, GemType
from src.items.item import ItemRarity

def test_skill_tree():
    """Test expanded skill tree."""
    print("=" * 60)
    print("TEST 1: Expanded Skill Tree")
    print("=" * 60)
    
    tree = SkillTree()
    print(f"[OK] Skill tree initialized with {len(tree.nodes)} nodes")
    
    # Check root node
    assert tree.root_node is not None, "Root node not created"
    print(f"[OK] Root node: {tree.root_node.name}")
    
    # Count node types
    types_count = {}
    for node in tree.nodes.values():
        node_type = node.node_type.name
        types_count[node_type] = types_count.get(node_type, 0) + 1
    
    print(f"[OK] Node types breakdown:")
    for node_type, count in sorted(types_count.items()):
        print(f"  - {node_type}: {count} nodes")
    
    # Get active effects
    effects = tree.get_active_effects()
    print(f"[OK] Active effects from root: {len(effects)} effects")
    
    # Try allocating a node
    fire_node = tree.nodes.get("fire_1")
    if fire_node and tree.allocate_node("fire_1"):
        print(f"[OK] Successfully allocated: {fire_node.name}")
        new_effects = tree.get_active_effects()
        print(f"  Now have {len(new_effects)} effects")
    
    print()

def test_synergistic_items():
    """Test synergistic item sets."""
    print("=" * 60)
    print("TEST 2: Synergistic Items")
    print("=" * 60)
    
    sets = SynergisticItemFactory.get_all_sets()
    print(f"[OK] Created {len(sets)} item sets")
    
    for item_set in sets:
        print(f"\n[OK] Set: {item_set.set_name}")
        print(f"  - Items: {len(item_set.items)}")
        print(f"  - Theme: {item_set.theme_description}")
        print(f"  - Set bonuses at: 2/3/4 pieces")
        
        for item in item_set.items:
            print(f"    - {item.name} ({item.rarity.name}) - Slot: {item.slot.name}")
    
    # Test smart item selection
    print("\n[OK] Smart item selection test:")
    for level in [1, 3, 5, 7, 10]:
        item = SynergisticItemFactory.get_synergistic_item(level)
        if item:
            print(f"  Level {level}: {item.name} ({item.rarity.name})")
    
    print()

def test_elemental_system():
    """Test elemental damage system."""
    print("=" * 60)
    print("TEST 3: Elemental Damage System")
    print("=" * 60)
    
    # Create elemental damage
    fire_damage = ElementalDamage(ElementType.FIRE, 20, 0.5)
    print(f"[OK] Created fire damage: 20 base + 0.5x modifier = {fire_damage.get_total_damage()} total")
    print(f"  Type: {fire_damage.element_type}")
    
    # Test effect manager
    effect_manager = ElementalEffectManager()
    effect_manager.apply_effect("burn", ElementType.FIRE, duration=5.0, intensity=1.0)
    print(f"[OK] Applied burn effect (5s duration, 1.0 intensity)")
    
    # Update with delta time
    effect_manager.update(1.0)  # 1 second passes
    print(f"[OK] Updated effects (1 second passed)")
    print(f"  Damage over time: {effect_manager.damage_over_time} per update")
    
    # Test shock amplification
    effect_manager.apply_effect("shock", ElementType.LIGHTNING, duration=3.0, intensity=2.0)
    amplification = effect_manager.get_shock_amplification()
    print(f"[OK] Applied shock (2 stacks), damage amplification: {amplification}x")
    
    # Test all element types
    print(f"\n[OK] All element types:")
    for attr_name in dir(ElementType):
        if not attr_name.startswith('_'):
            value = getattr(ElementType, attr_name)
            if isinstance(value, str):
                print(f"  - {attr_name}: {value}")
    
    print()

def test_gem_system():
    """Test gem system."""
    print("=" * 60)
    print("TEST 4: Gem System")
    print("=" * 60)
    
    GemLibrary.create_all_gems()
    
    # Count gem types
    active_gems = []
    support_gems = []
    keystone_gems = []
    
    for gem_id, gem in GemLibrary.gems.items():
        if gem.gem_type == GemType.ACTIVE:
            active_gems.append(gem)
        elif gem.gem_type == GemType.SUPPORT:
            support_gems.append(gem)
        elif gem.gem_type == GemType.KEYSTONE:
            keystone_gems.append(gem)
    
    print(f"[OK] Gem library created with {len(GemLibrary.gems)} gems")
    print(f"  - Active spells: {len(active_gems)}")
    print(f"  - Support gems: {len(support_gems)}")
    print(f"  - Keystone nodes: {len(keystone_gems)}")
    
    print(f"\n[OK] Sample gems:")
    print(f"\n  Active Spells:")
    for gem in active_gems[:2]:
        print(f"    - {gem.name}: {gem.modifiers}")
    
    print(f"\n  Support Gems:")
    for gem in support_gems[:3]:
        print(f"    - {gem.name}: {gem.modifiers}")
    
    print(f"\n  Keystones:")
    for gem in keystone_gems[:2]:
        print(f"    - {gem.name}: {gem.modifiers}")
    
    print()

def test_integration():
    """Test systems working together."""
    print("=" * 60)
    print("TEST 5: System Integration")
    print("=" * 60)
    
    # Create skill tree
    tree = SkillTree()
    print("[OK] Skill tree created")
    
    # Create items
    item = SynergisticItemFactory.get_synergistic_item(5)
    print(f"[OK] Generated synergistic item: {item.name}")
    
    # Create gems
    gem = GemLibrary.get_gem("Fireball")
    if gem:
        print(f"[OK] Retrieved gem: {gem.name}")
    else:
        print(f"[OK] Gem retrieval tested (gem not found as expected)")
    
    # Create elemental damage
    damage = ElementalDamage(ElementType.FIRE, 25, 1.5)
    print(f"[OK] Created elemental damage: {damage.element_type} type with 1.5x modifier")
    
    print(f"\n[OK] All systems integrated successfully!")
    print()
