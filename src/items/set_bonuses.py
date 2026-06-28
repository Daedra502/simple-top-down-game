"""
Set bonus system - calculates bonuses from synergistic item sets.

Set bonuses are applied when the player equips multiple pieces from the same set.
Each set has bonuses that increase with more pieces equipped (2pc, 3pc, 4pc).
"""

from collections import defaultdict


class SetBonusCalculator:
    """Calculates and manages item set bonuses."""
    
    def __init__(self):
        """Initialize the set bonus calculator."""
        self.active_sets = defaultdict(int)  # set_name -> piece_count
        self.applied_bonuses = {}  # Bonuses currently applied
    
    def calculate_set_bonuses(self, equipped_items):
        """
        Calculate all active set bonuses from equipped items.
        
        Args:
            equipped_items: List of all equipped Item objects
        
        Returns:
            Dict with set_name -> {'pieces': count, 'bonuses': dict}
        """
        # Reset active sets
        self.active_sets.clear()
        
        # Count pieces per set
        for item in equipped_items:
            if item and hasattr(item, 'set_name') and item.set_name:
                self.active_sets[item.set_name] += 1
        
        # Build results with actual bonuses
        result = {}
        for set_name, piece_count in self.active_sets.items():
            bonuses = self._get_set_bonuses(set_name, piece_count)
            result[set_name] = {
                'pieces': piece_count,
                'bonuses': bonuses,
                'total_pieces': 4,  # Assume 4-piece sets
            }
        
        return result
    
    def _get_set_bonuses(self, set_name, piece_count):
        """Get bonuses for a specific set at a specific piece count."""
        # Import here to avoid circular imports
        from src.items.synergistic_items import SynergisticItemFactory
        
        # Get or create the sets
        factory = SynergisticItemFactory()
        if not factory.item_sets:
            factory.create_all_sets()
        
        # Find the set by name
        if set_name in factory.item_sets:
            item_set = factory.item_sets[set_name]
            # Get the bonus for this piece count
            if piece_count >= 2:
                return item_set.get_set_bonus(piece_count)
        
        # Fallback to empty if set not found
        return {}
    
    def get_total_bonuses(self, set_bonuses_data):
        """
        Aggregate all set bonuses into a single bonus dict.
        
        Args:
            set_bonuses_data: Dict returned from calculate_set_bonuses
        
        Returns:
            Aggregated bonus dict
        """
        total_bonuses = {}
        
        for set_name, set_info in set_bonuses_data.items():
            for bonus_key, bonus_value in set_info['bonuses'].items():
                if bonus_key not in total_bonuses:
                    total_bonuses[bonus_key] = 0
                
                # Handle both additive and multiplicative bonuses
                if isinstance(bonus_value, (int, float)):
                    total_bonuses[bonus_key] += bonus_value
                elif isinstance(bonus_value, dict):
                    if bonus_key not in total_bonuses:
                        total_bonuses[bonus_key] = {}
                    for sub_key, sub_value in bonus_value.items():
                        if sub_key not in total_bonuses[bonus_key]:
                            total_bonuses[bonus_key][sub_key] = 0
                        total_bonuses[bonus_key][sub_key] += sub_value
        
        return total_bonuses
    
    def apply_set_bonuses_to_player(self, player, set_bonuses_data):
        """
        Apply all calculated set bonuses to the player.
        
        Args:
            player: The Player object
            set_bonuses_data: Dict from calculate_set_bonuses
        """
        total_bonuses = self.get_total_bonuses(set_bonuses_data)
        
        # Apply bonuses to player
        for bonus_key, bonus_value in total_bonuses.items():
            if bonus_key == 'health':
                player.max_health += bonus_value
                player.health = min(player.health + bonus_value, player.max_health)
            elif bonus_key == 'max_health':
                player.max_health += bonus_value
                player.health = min(player.health, player.max_health)
            elif bonus_key == 'mana':
                player.max_mana += bonus_value
                player.mana = min(player.mana + bonus_value, player.max_mana)
            elif bonus_key == 'max_mana':
                player.max_mana += bonus_value
                player.mana = min(player.mana, player.max_mana)
            elif bonus_key == 'damage':
                player.damage += bonus_value
            elif bonus_key == 'attack_speed':
                player.attack_speed += bonus_value
            elif bonus_key == 'armor':
                if not hasattr(player, 'armor'):
                    player.armor = 0
                player.armor += bonus_value
            elif bonus_key.endswith('_damage'):
                # Spell-specific bonuses
                if bonus_key not in player.skill_tree_bonuses:
                    player.skill_tree_bonuses[bonus_key] = 0
                player.skill_tree_bonuses[bonus_key] += bonus_value
        
        # Store for later reference
        self.applied_bonuses = total_bonuses
    
    def get_active_sets(self):
        """Get list of active sets with their piece counts."""
        return dict(self.active_sets)
    
    def get_applied_bonuses(self):
        """Get the bonuses currently applied."""
        return self.applied_bonuses.copy()
    
    def has_set_pieces(self, set_name, min_pieces=2):
        """Check if a set has the minimum number of pieces."""
        return self.active_sets.get(set_name, 0) >= min_pieces
    
    def get_set_progress(self, set_name, total_pieces=4):
        """
        Get progress towards completing a set.
        
        Returns:
            (current_pieces, total_pieces)
        """
        current = self.active_sets.get(set_name, 0)
        return (current, total_pieces)


class SetBonusTracker:
    """Tracks set bonuses in the character sheet and UI."""
    
    def __init__(self):
        """Initialize the tracker."""
        self.calculator = SetBonusCalculator()
    
    def update(self, equipped_items):
        """Update set bonus calculations with current equipment."""
        return self.calculator.calculate_set_bonuses(equipped_items)
    
    def get_summary(self):
        """Get a summary of active sets for display."""
        summary = []
        for set_name, piece_count in self.calculator.get_active_sets().items():
            progress = self.calculator.get_set_progress(set_name)
            summary.append({
                'name': set_name,
                'current': progress[0],
                'total': progress[1],
                'active': piece_count >= 2,
            })
        return summary
