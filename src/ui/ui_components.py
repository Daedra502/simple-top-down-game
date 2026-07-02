import pygame
import math

from src.ui.skill_icons import render_skill_icon


class SkillBarUI:
    """Bottom-of-screen skill bar showing every usable active skill.

    Driven directly by the game's SkillManager (data/skills.json) so that all
    selectable skills (1-8) appear, each with a procedural emblem icon, hotkey
    number, level, cooldown sweep and a mana-affordability tint. The currently
    selected skill is highlighted.
    """

    SLOT_SIZE = 58
    SLOT_GAP = 8
    PAD = 8

    def __init__(self, x, y, width, height):
        # x/y/width/height describe the available band; the bar itself is
        # centered within it and sized to the number of skills.
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.font = pygame.font.Font(None, 20)
        self.small_font = pygame.font.Font(None, 16)
        self.tiny_font = pygame.font.Font(None, 14)
        # Hover support: rebuilt each draw as [(rect, skill)].
        self.slot_rects = []

    def update(self, player):
        """Kept for API compatibility; per-frame state is read in draw()."""
        return

    def skill_at(self, pos):
        """Return the skill whose slot contains pos, or None (for tooltips)."""
        for rect, skill in self.slot_rects:
            if rect.collidepoint(pos):
                return skill
        return None

    def draw(self, surface, skill_manager=None, player=None):
        """Draw the skill bar. Falls back to a no-op if not wired up yet."""
        self.slot_rects = []
        if skill_manager is None or player is None:
            return

        slots = skill_manager.slots
        n = len(slots)
        if n == 0:
            return

        bar_w = n * self.SLOT_SIZE + (n - 1) * self.SLOT_GAP + 2 * self.PAD
        bar_h = self.SLOT_SIZE + 2 * self.PAD
        bar_x = self.x + (self.width - bar_w) // 2
        bar_y = self.y + (self.height - bar_h) // 2

        # Backing panel
        panel = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
        pygame.draw.rect(surface, (18, 18, 28), panel, border_radius=6)
        pygame.draw.rect(surface, (90, 90, 130), panel, 2, border_radius=6)

        active_idx = getattr(player, "active_skill", 0)
        icon_size = self.SLOT_SIZE - 16
        sx = bar_x + self.PAD
        sy = bar_y + self.PAD

        for i, skill_id in enumerate(slots):
            skill = skill_manager.skills[skill_id]
            slot = pygame.Rect(sx, sy, self.SLOT_SIZE, self.SLOT_SIZE)
            is_active = (i == active_idx)
            affordable = player.mana >= skill.mana_cost
            on_cd = getattr(skill, "cd_remaining", 0) > 0

            # Slot background + border
            pygame.draw.rect(surface, (38, 44, 60) if is_active else (26, 28, 40),
                             slot, border_radius=5)

            # Emblem icon (dimmed when unusable)
            icon = render_skill_icon(skill_id, icon_size, skill.color)
            if not affordable or on_cd:
                icon = icon.copy()
                icon.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(icon, (sx + 8, sy + 6))

            # Cooldown sweep: dark overlay shrinking from the top as it recovers.
            if on_cd and skill.cooldown > 0:
                frac = max(0.0, min(1.0, skill.cd_remaining / skill.cooldown))
                ov_h = int((self.SLOT_SIZE - 4) * frac)
                if ov_h > 0:
                    ov = pygame.Surface((self.SLOT_SIZE - 4, ov_h), pygame.SRCALPHA)
                    ov.fill((0, 0, 0, 150))
                    surface.blit(ov, (sx + 2, sy + 2))
                cd_txt = self.small_font.render(f"{skill.cd_remaining:.1f}", True, (255, 210, 210))
                surface.blit(cd_txt, cd_txt.get_rect(center=slot.center))
            elif not affordable:
                # Red mana cue when the skill is ready but unaffordable.
                no_mana = self.tiny_font.render("mana", True, (255, 120, 120))
                surface.blit(no_mana, no_mana.get_rect(center=(slot.centerx, slot.bottom - 9)))

            # Hotkey number (top-left)
            key_txt = self.tiny_font.render(str(i + 1), True, (255, 215, 120))
            surface.blit(key_txt, (sx + 3, sy + 2))

            # Skill level (bottom-right)
            lvl_txt = self.tiny_font.render(f"L{skill.level}", True, (180, 200, 230))
            surface.blit(lvl_txt, lvl_txt.get_rect(bottomright=(slot.right - 3, slot.bottom - 2)))

            # Active highlight border drawn last so it sits on top.
            pygame.draw.rect(surface, (255, 205, 0) if is_active else (70, 74, 96),
                             slot, 3 if is_active else 1, border_radius=5)

            self.slot_rects.append((slot, skill))
            sx += self.SLOT_SIZE + self.SLOT_GAP

class SkillTreeUI:
    """Interactive UI for the PoE2-style radial skill tree.

    World->screen transform is ``screen = node.pos * zoom + offset``; the view
    starts centered on the root and supports right-drag panning and
    mouse-wheel zoom (toward the cursor). Region labels come from
    data/skill_tree_regions.json (written by tools/build_skill_tree.py).
    """

    ZOOM_MIN, ZOOM_MAX = 0.35, 1.8

    def __init__(self, skill_tree, width, height):
        self.skill_tree = skill_tree
        self.width = width
        self.height = height
        self.zoom = 0.75
        root = skill_tree.root_node
        self.offset_x = width / 2 - root.x * self.zoom
        self.offset_y = height / 2 - root.y * self.zoom
        self.dragging = False
        self.drag_start = (0, 0)
        self.hovered_node = None
        self.font = pygame.font.Font(None, 16)
        self.title_font = pygame.font.Font(None, 32)
        self.region_font = pygame.font.Font(None, 26)
        try:
            from src.core.data_loader import load_json
            self.regions = load_json("skill_tree_regions.json")
        except Exception:
            self.regions = []

    def _to_screen(self, x, y):
        return x * self.zoom + self.offset_x, y * self.zoom + self.offset_y

    def handle_zoom(self, wheel_y, pos):
        """Mouse-wheel zoom, keeping the point under the cursor fixed."""
        old = self.zoom
        self.zoom = max(self.ZOOM_MIN, min(self.ZOOM_MAX, old * (1.1 ** wheel_y)))
        if self.zoom != old:
            scale = self.zoom / old
            self.offset_x = pos[0] - (pos[0] - self.offset_x) * scale
            self.offset_y = pos[1] - (pos[1] - self.offset_y) * scale

    def handle_mouse_motion(self, pos, buttons):
        """Handle mouse motion for hovering and panning."""
        # Check for hovered nodes
        self.hovered_node = None
        for node_id, node in self.skill_tree.nodes.items():
            screen_x, screen_y = self._to_screen(node.x, node.y)
            distance = math.hypot(pos[0] - screen_x, pos[1] - screen_y)
            if distance < node.radius * self.zoom + 5:
                self.hovered_node = node_id
                break

        # Pan on right click drag
        if buttons[2]:  # Right click
            if not self.dragging:
                self.dragging = True
                self.drag_start = pos
            else:
                dx = pos[0] - self.drag_start[0]
                dy = pos[1] - self.drag_start[1]
                self.offset_x += dx
                self.offset_y += dy
                self.drag_start = pos
        else:
            self.dragging = False

    def handle_click(self, pos, player):
        """Handle clicking on skill nodes."""
        for node_id, node in self.skill_tree.nodes.items():
            screen_x, screen_y = self._to_screen(node.x, node.y)
            distance = math.hypot(pos[0] - screen_x, pos[1] - screen_y)
            if distance < max(6, node.radius * self.zoom):
                # Left click: allocate
                if not node.allocated and node.can_allocate(self.skill_tree.allocations):
                    if player.skill_points > 0:
                        self.skill_tree.allocate_node(node_id)
                        player.skill_points -= 1
                # Right click: deallocate
                else:
                    if self.skill_tree.deallocate_node(node_id):
                        player.skill_points += 1
                break
    
    def draw(self, surface, player):
        """Draw the skill tree UI."""
        # Background
        surface.fill((10, 10, 20))
        
        # Title
        title = self.title_font.render("Skill Tree", True, (255, 200, 0))
        title_rect = title.get_rect(center=(self.width // 2, 30))
        surface.blit(title, title_rect)
        
        # Region labels behind everything (faint, at each slice's rim).
        for region in self.regions:
            rx, ry = self._to_screen(region["pos"][0], region["pos"][1])
            if -100 < rx < self.width + 100 and -40 < ry < self.height + 40:
                col = tuple(int(c * 0.6) for c in region["color"])
                text = self.region_font.render(region["name"], True, col)
                surface.blit(text, text.get_rect(center=(rx, ry)))

        # Draw connections between nodes first
        for node_id, node in self.skill_tree.nodes.items():
            for child_id in node.children:
                child = self.skill_tree.nodes[child_id]

                x1, y1 = self._to_screen(node.x, node.y)
                x2, y2 = self._to_screen(child.x, child.y)

                # Connection color based on allocation status
                if node.allocated and child.allocated:
                    color = (100, 255, 100)
                elif node.allocated or child.allocated:
                    color = (100, 150, 150)
                else:
                    color = (50, 50, 50)

                pygame.draw.line(surface, color, (x1, y1), (x2, y2), 2)

        # Draw nodes
        for node_id, node in self.skill_tree.nodes.items():
            screen_x, screen_y = self._to_screen(node.x, node.y)

            # Skip if off-screen
            if screen_x < -30 or screen_x > self.width + 30 or \
               screen_y < -30 or screen_y > self.height + 30:
                continue

            radius = max(4, int(node.radius * self.zoom))

            # Draw node circle
            if node.allocated:
                color = node.allocated_color
            else:
                color = node.unallocated_color

            # Highlight hovered node
            if node_id == self.hovered_node:
                pygame.draw.circle(surface, (255, 255, 100),
                                   (screen_x, screen_y), radius + 3, 2)

            pygame.draw.circle(surface, color, (screen_x, screen_y), radius)

            # Border: allocated bright; keystones get a golden double ring.
            border_color = (255, 255, 255) if node.allocated else (100, 100, 100)
            pygame.draw.circle(surface, border_color, (screen_x, screen_y), radius, 2)
            if node.tier == "keystone":
                pygame.draw.circle(surface, (230, 190, 90),
                                   (screen_x, screen_y), radius + 4, 2)

            # Name initial only when zoomed in enough to read it.
            if self.zoom >= 0.6:
                text = self.font.render(node.name[0], True, (255, 255, 255))
                surface.blit(text, text.get_rect(center=(screen_x, screen_y)))

        # Draw info panel
        self._draw_info_panel(surface, player)

        # Instructions
        instr = self.font.render(
            "Left Click: Allocate | Right Click: Deallocate | Right Drag: Pan | Wheel: Zoom",
            True, (200, 200, 200))
        surface.blit(instr, (10, self.height - 25))
    
    def _draw_info_panel(self, surface, player):
        """Draw the info panel with player stats."""
        panel_width = 300
        panel_height = 150
        x = self.width - panel_width - 10
        y = 70
        
        # Panel background
        panel_rect = pygame.Rect(x, y, panel_width, panel_height)
        pygame.draw.rect(surface, (20, 20, 40), panel_rect)
        pygame.draw.rect(surface, (100, 150, 200), panel_rect, 2)
        
        # Player info
        lines = [
            f"Level: {player.level}",
            f"Skill Points: {player.skill_points}",
            f"Allocated Nodes: {self.skill_tree.get_allocated_count()}",
            f"HP: {int(player.health)}/{int(player.max_health)}",
            f"Mana: {int(player.mana)}/{int(player.max_mana)}",
        ]
        
        y_offset = y + 10
        for line in lines:
            text = self.font.render(line, True, (255, 255, 255))
            surface.blit(text, (x + 10, y_offset))
            y_offset += 25
        
        # Hovered node info
        if self.hovered_node:
            node = self.skill_tree.nodes[self.hovered_node]
            hover_x = x
            hover_y = y + panel_height + 10
            hover_width = panel_width
            hover_height = 120
            
            hover_rect = pygame.Rect(hover_x, hover_y, hover_width, hover_height)
            pygame.draw.rect(surface, (30, 30, 50), hover_rect)
            pygame.draw.rect(surface, (150, 200, 150), hover_rect, 2)
            
            # Node info
            name_text = self.font.render(node.name, True, (255, 255, 100))
            surface.blit(name_text, (hover_x + 10, hover_y + 5))
            
            y_offset = hover_y + 25
            for effect, value in node.effects.items():
                if isinstance(value, float):
                    effect_str = f"{effect}: +{value:.1%}"
                else:
                    effect_str = f"{effect}: +{value}"
                text = self.font.render(effect_str, True, (200, 200, 255))
                surface.blit(text, (hover_x + 10, y_offset))
                y_offset += 20
