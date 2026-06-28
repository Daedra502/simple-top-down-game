"""Character sheet UI component for displaying player stats and progression."""

import pygame


class CharacterSheetUI:
    """Displays comprehensive character information."""
    
    def __init__(self, player, skill_tree, item_manager, x=50, y=50, width=700, height=600):
        """
        Initialize character sheet UI.
        
        Args:
            player: Player entity with stats
            skill_tree: Skill tree with allocated nodes
            item_manager: Item manager with equipment
            x, y: Position on screen
            width, height: Size of the sheet
        """
        self.player = player
        self.skill_tree = skill_tree
        self.item_manager = item_manager
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
        # Font
        self.large_font = pygame.font.Font(None, 28)
        self.normal_font = pygame.font.Font(None, 20)
        self.small_font = pygame.font.Font(None, 16)
    
    def draw(self, surface):
        """Draw the character sheet."""
        # Background panel
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(surface, (20, 20, 40), panel_rect)
        pygame.draw.rect(surface, (100, 150, 200), panel_rect, 3)
        
        # Title
        title = self.large_font.render("CHARACTER SHEET", True, (255, 200, 0))
        title_rect = title.get_rect(center=(self.x + self.width // 2, self.y + 15))
        surface.blit(title, title_rect)
        
        y_offset = self.y + 50
        col_width = self.width // 2
        
        # Left column: Player stats
        self._draw_player_stats(surface, self.x + 20, y_offset)
        
        # Right column: Skill tree and bonuses
        self._draw_skill_tree_bonuses(surface, self.x + col_width, y_offset)
        
        # Bottom: Equipment and set bonuses
        self._draw_equipment_info(surface, self.x + 20, self.y + 350)
    
    def _draw_player_stats(self, surface, x, y):
        """Draw main player stats."""
        stats_text = [
            (f"Level: {self.player.level}/{self.player.max_level}", (100, 200, 255)),
            (f"Health: {int(self.player.health)}/{int(self.player.max_health)}", (255, 100, 100)),
            (f"Mana: {int(self.player.mana)}/{int(self.player.max_mana)}", (100, 100, 255)),
            (f"XP: {int(self.player.experience)}/{int(self.player.xp_to_level)}", (255, 200, 0)),
            ("", None),  # Spacer
            (f"Damage: {self.player.damage}", (255, 100, 100)),
            (f"Attack Speed: {self.player.attack_speed:.2f}x", (200, 200, 0)),
            (f"Mana Regen: {self.player.mana_regen:.2f}/s", (100, 200, 100)),
            ("", None),  # Spacer
            (f"Skill Points: {self.player.skill_points}", (200, 255, 100)),
            (f"Wand Level: {self.player.wand_level}", (255, 150, 0)),
        ]
        
        y_pos = y
        for stat_text, color in stats_text:
            if stat_text:
                text_surf = self.normal_font.render(stat_text, True, color or (255, 255, 255))
                surface.blit(text_surf, (x, y_pos))
            y_pos += 25
    
    def _draw_skill_tree_bonuses(self, surface, x, y):
        """Draw skill tree bonuses."""
        title = self.normal_font.render("Skill Tree Bonuses:", True, (100, 255, 100))
        surface.blit(title, (x, y))
        
        effects = self.skill_tree.get_active_effects()
        y_pos = y + 30
        
        if not effects:
            no_text = self.small_font.render("(No bonuses allocated)", True, (150, 150, 150))
            surface.blit(no_text, (x, y_pos))
            return
        
        # Group effects by type
        effect_groups = {}
        for effect_name, value in effects.items():
            if effect_name.endswith('_damage'):
                group = 'Damage Bonuses'
            elif effect_name in ['max_health', 'max_mana', 'armor']:
                group = 'Defense'
            elif effect_name in ['attack_speed', 'mana_regen']:
                group = 'Misc'
            else:
                group = 'Other'
            
            if group not in effect_groups:
                effect_groups[group] = []
            effect_groups[group].append((effect_name, value))
        
        # Display grouped effects
        for group_name, group_effects in sorted(effect_groups.items()):
            group_text = self.small_font.render(f"{group_name}:", True, (150, 200, 255))
            surface.blit(group_text, (x, y_pos))
            y_pos += 20
            
            for effect_name, value in group_effects:
                if isinstance(value, float) and value < 10:
                    effect_text = f"  +{value:.2f} {effect_name.replace('_', ' ')}"
                else:
                    effect_text = f"  +{int(value)} {effect_name.replace('_', ' ')}"
                
                text_surf = self.small_font.render(effect_text, True, (200, 200, 100))
                surface.blit(text_surf, (x, y_pos))
                y_pos += 18
    
    def _draw_equipment_info(self, surface, x, y):
        """Draw equipment and set bonus information."""
        title = self.normal_font.render("Equipment & Sets:", True, (100, 255, 100))
        surface.blit(title, (x, y))
        
        equipped = self.item_manager.equipment.get_all_equipped_items()
        
        if not equipped:
            no_text = self.small_font.render("(No items equipped)", True, (150, 150, 150))
            surface.blit(no_text, (x, y + 30))
            return
        
        y_pos = y + 30
        
        # Display equipped items
        for item in equipped[:5]:
            item_color = item.get_color()
            item_text = f"- {item.name} ({item.rarity.name})"
            text_surf = self.small_font.render(item_text, True, item_color)
            surface.blit(text_surf, (x, y_pos))
            y_pos += 20
        
        # Display set bonuses with actual bonuses from SetBonusCalculator
        y_pos += 10
        set_text = self.small_font.render("Set Bonuses:", True, (255, 150, 0))
        surface.blit(set_text, (x, y_pos))
        
        # Get set bonus summary from item manager
        set_summary = self.item_manager.get_set_bonus_summary()
        
        if set_summary:
            y_pos += 20
            for set_info in set_summary:
                # Determine color based on active status
                color = (100, 255, 100) if set_info['active'] else (150, 150, 150)
                
                set_bonus_text = f"  {set_info['name']}: {set_info['current']}/{set_info['total']}"
                text_surf = self.small_font.render(set_bonus_text, True, color)
                surface.blit(text_surf, (x, y_pos))
                
                # Show bonuses if set is active (2+ pieces)
                if set_info['active'] and set_info['current'] >= 2:
                    # Get the actual bonuses from the ItemManager
                    active_bonuses = self.item_manager.get_active_set_bonuses()
                    for set_name, set_data in active_bonuses.items():
                        if set_name == set_info['name']:
                            y_pos += 16
                            for bonus_key, bonus_value in set_data['bonuses'].items():
                                bonus_text = f"    • {bonus_key.replace('_', ' ')}: +{bonus_value}"
                                bonus_surf = self.small_font.render(bonus_text, True, (200, 255, 150))
                                surface.blit(bonus_surf, (x, y_pos))
                                y_pos += 16
                            break
                
                y_pos += 2
        else:
            y_pos += 20
            no_sets = self.small_font.render("(No set bonuses)", True, (150, 150, 150))
            surface.blit(no_sets, (x, y_pos))
    
    def get_stat_breakdown(self):
        """Get a detailed breakdown of all player stats."""
        breakdown = {
            'player_stats': {
                'level': self.player.level,
                'health': self.player.health,
                'max_health': self.player.max_health,
                'mana': self.player.mana,
                'max_mana': self.player.max_mana,
                'damage': self.player.damage,
                'attack_speed': self.player.attack_speed,
                'experience': self.player.experience,
            },
            'skill_tree_bonuses': self.skill_tree.get_active_effects(),
            'equipment': {
                'equipped_count': len(self.item_manager.equipment.get_all_equipped_items()),
                'inventory_count': len(self.item_manager.inventory.items),
            },
            'wallet': {
                'copper': self.player.copper,
                'silver': self.player.silver,
                'gold': self.player.gold,
                'diamond': self.player.diamond,
            }
        }
        
        return breakdown


class StatTooltip:
    """Tooltip showing what contributes to each stat."""
    
    def __init__(self):
        self.font = pygame.font.Font(None, 18)
    
    def get_stat_sources(self, stat_name, player, skill_tree, item_manager):
        """Get all sources contributing to a stat."""
        sources = []
        
        if stat_name == 'max_health':
            sources.append(('Base', 100))
            effects = skill_tree.get_active_effects()
            if 'max_health' in effects:
                sources.append(('Skill Tree', effects['max_health']))
        
        elif stat_name == 'damage':
            sources.append(('Base', player.damage))
            effects = skill_tree.get_active_effects()
            if 'damage' in effects:
                sources.append(('Skill Tree', effects['damage']))
        
        elif stat_name == 'attack_speed':
            sources.append(('Base', 1.0))
            effects = skill_tree.get_active_effects()
            if 'attack_speed' in effects:
                sources.append(('Skill Tree', effects['attack_speed']))
        
        return sources
