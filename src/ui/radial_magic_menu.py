"""
Radial magic menu - 8-directional symbol selection via mouse.
Activated by holding SPACE, interacted with via mouse click.
Supports nested nodes (submenus) with automatic return slots.
"""
import pygame
import math
from ..magic import MagicSystem
from .radial_menu_layout import RadialMenuLayout, DIRECTIONS, OPPOSITE_DIRECTION


class RadialMagicMenu:
    """
    An eight-directional radial menu for selecting magic symbols.
    - Opens when SPACE is held
    - Mouse click selects symbols or enters nodes
    - Click off menu stows UI and locks selection
    - Right click cancels
    - Releasing SPACE launches spell

    Supports nested menus (nodes) with automatic return navigation.
    """

    # Direction angles in radians (clockwise from top)
    # N=0, NE=45, E=90, SE=135, S=180, SW=225, W=270, NW=315
    DIRECTION_ANGLES = {
        "n": -math.pi / 2,           # -90 degrees (up)
        "ne": -math.pi / 4,          # -45 degrees
        "e": 0,                       # 0 degrees (right)
        "se": math.pi / 4,           # 45 degrees
        "s": math.pi / 2,            # 90 degrees (down)
        "sw": 3 * math.pi / 4,       # 135 degrees
        "w": math.pi,                 # 180 degrees (left)
        "nw": -3 * math.pi / 4,      # -135 degrees
    }

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Menu state
        self.is_open = False
        self.is_stowed = False  # UI hidden but spell locked
        self.selected_symbols = []  # Up to 2 symbols
        self.hovered_slot = None

        # Node navigation
        self.layout = RadialMenuLayout()  # Menu structure
        self.current_node_id = "root"
        self.entry_direction = None  # How we entered current node (None for root)
        self.navigation_stack = []  # Stack of (node_id, entry_direction) for back navigation

        # Settings
        self.casting_reset_enabled = True  # Default: return to root after selecting a spell

        # Visual properties
        self.center_x = screen_width // 2
        self.center_y = screen_height // 2
        self.slot_radius = 40  # Slightly smaller for 8 slots
        self.slot_distance = 110  # Distance from center to slot center

        # Colors
        self.bg_color = (30, 30, 40, 200)
        self.slot_color = (50, 60, 80)
        self.slot_hover_color = (70, 90, 120)
        self.slot_selected_color = (100, 150, 200)
        self.slot_empty_color = (40, 45, 55)
        self.slot_node_color = (80, 70, 100)  # Purple-ish for nodes
        self.slot_return_color = (70, 80, 70)  # Green-ish for return
        self.text_color = (220, 220, 220)
        self.symbol_color = (180, 200, 255)
        self.center_color = (40, 45, 55)

        # Cached slot positions (calculated once)
        self._slot_positions = None

        # Font (initialized on first render)
        self.font = None
        self.symbol_font = None
        self.small_font = None

    def _calculate_slot_positions(self):
        """Calculate screen positions for all 8 slots."""
        positions = {}
        for direction in DIRECTIONS:
            angle = self.DIRECTION_ANGLES[direction]
            x = int(self.slot_distance * math.cos(angle))
            y = int(self.slot_distance * math.sin(angle))
            positions[direction] = (x, y)
        return positions

    @property
    def slot_positions(self):
        """Get slot positions (cached)."""
        if self._slot_positions is None:
            self._slot_positions = self._calculate_slot_positions()
        return self._slot_positions

    def set_layout(self, layout):
        """Set the menu layout from player configuration."""
        self.layout = layout

    def set_casting_reset(self, enabled):
        """Set whether selecting a spell returns to root (True) or stays in current node (False)."""
        self.casting_reset_enabled = enabled

    def update_known_symbols(self, known_symbol_ids):
        """
        Update the layout to include player's known symbols.
        If layout is empty/default, auto-populate with known symbols.
        """
        # Check if layout is essentially empty (no spells assigned)
        assigned = self.layout.get_all_assigned_spells()
        if not assigned:
            # Auto-populate with known spells
            self.layout.auto_populate_from_spells(known_symbol_ids)

    def _init_fonts(self):
        """Initialize fonts if not already done."""
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 20)
            self.small_font = pygame.font.Font(None, 16)

            # Use a system font that supports CJK characters
            cjk_fonts = [
                "microsoftyahei",
                "yugothic",
                "msgothic",
                "simsun",
                "arialunicodems",
            ]

            self.symbol_font = None
            for font_name in cjk_fonts:
                try:
                    self.symbol_font = pygame.font.SysFont(font_name, 36)
                    test_surf = self.symbol_font.render("\u706b", True, (255, 255, 255))
                    if test_surf.get_width() > 5:
                        break
                except:
                    continue

            if self.symbol_font is None:
                self.symbol_font = pygame.font.Font(None, 36)

    def open(self, player_screen_x=None, player_screen_y=None):
        """Open the radial menu at root."""
        self._init_fonts()
        self.is_open = True
        self.is_stowed = False
        self.selected_symbols = []
        self.hovered_slot = None
        self.current_node_id = "root"
        self.entry_direction = None
        self.navigation_stack = []

    def close(self):
        """Close and reset the menu."""
        self.is_open = False
        self.is_stowed = False
        self.selected_symbols = []
        self.hovered_slot = None
        self.current_node_id = "root"
        self.entry_direction = None
        self.navigation_stack = []

    def stow(self):
        """Stow the UI (hide it but keep selection locked)."""
        self.is_open = False
        self.is_stowed = True

    def cancel(self):
        """Cancel selection via right click."""
        self.selected_symbols = []
        self.is_open = False
        self.is_stowed = False

    def get_selected_symbols(self):
        """Get the currently selected symbol IDs."""
        return [s["id"] for s in self.selected_symbols]

    def has_selection(self):
        """Check if any symbols are selected."""
        return len(self.selected_symbols) > 0

    def is_ready_to_cast(self):
        """Check if spell is ready (stowed with selection)."""
        return self.is_stowed and self.has_selection()

    def update(self, mouse_x, mouse_y):
        """Update hover state based on mouse position."""
        if not self.is_open:
            self.hovered_slot = None
            return

        self.hovered_slot = self._get_slot_at_position(mouse_x, mouse_y)

    def _get_slot_at_position(self, mouse_x, mouse_y):
        """Get which slot the mouse is over using pie-slice hit areas.

        Each of the 8 directions owns a 45-degree wedge extending from a
        small inner dead zone out to the outer edge of the menu.  This is
        much more forgiving than requiring the cursor to land inside the
        small circle of a single slot.
        """
        dx = mouse_x - self.center_x
        dy = mouse_y - self.center_y
        distance = math.sqrt(dx * dx + dy * dy)

        # Must be outside the inner dead zone and inside the outer edge
        inner_radius = 30  # matches center zone size
        outer_radius = self.slot_distance + self.slot_radius  # ~150 px
        if distance < inner_radius or distance > outer_radius:
            return None

        # Compute angle and map to one of 8 sectors (each 45 degrees)
        angle = math.atan2(dy, dx)  # -pi .. pi

        # Each direction has a canonical angle; find the closest one
        best_direction = None
        best_diff = float("inf")
        for direction, slot_angle in self.DIRECTION_ANGLES.items():
            diff = abs(self._angle_diff(angle, slot_angle))
            if diff < best_diff:
                best_diff = diff
                best_direction = direction

        # 45-degree half-sector = pi/4; allow up to half that (pi/4 ≈ 0.785)
        if best_diff <= math.pi / 4:
            return best_direction

        return None

    @staticmethod
    def _angle_diff(a, b):
        """Signed shortest-path difference between two angles (result in -pi..pi)."""
        d = a - b
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        return d

    def handle_click(self, mouse_x, mouse_y):
        """
        Handle mouse click.
        Returns: "symbol_selected", "stow", "node_entered", or None
        """
        if not self.is_open:
            return None

        clicked_slot = self._get_slot_at_position(mouse_x, mouse_y)

        if clicked_slot is not None:
            return self._handle_slot_click(clicked_slot)
        else:
            # Clicked off menu - stow and lock selection
            if self.has_selection():
                self.stow()
                return "stow"
            else:
                self.close()
                return None

        return None

    def _handle_slot_click(self, direction):
        """Handle clicking on a specific slot."""
        current_node = self.layout.get_node(self.current_node_id)
        if not current_node:
            return None

        # Check if this is the return slot
        if self.entry_direction and direction == OPPOSITE_DIRECTION.get(self.entry_direction):
            return self._navigate_back()

        slot_content = current_node.get_slot(direction)

        if slot_content is None:
            # Empty slot - do nothing
            return None

        if slot_content.startswith("node:"):
            # Node slot - enter the submenu
            return self._enter_node(slot_content[5:], direction)
        else:
            # Spell slot - select the spell
            return self._select_spell(slot_content)

    def _enter_node(self, node_id, entry_direction):
        """Enter a nested node/submenu."""
        node = self.layout.get_node(node_id)
        if not node:
            return None

        # Push current state to stack
        self.navigation_stack.append((self.current_node_id, self.entry_direction))

        # Enter the new node
        self.current_node_id = node_id
        self.entry_direction = entry_direction

        return "node_entered"

    def _navigate_back(self):
        """Navigate back to parent menu."""
        if not self.navigation_stack:
            # Already at root, close menu
            self.close()
            return None

        # Pop from stack
        self.current_node_id, self.entry_direction = self.navigation_stack.pop()
        return "node_exited"

    def _select_spell(self, spell_id):
        """Select a spell from the current slot."""
        symbol = MagicSystem.get_symbol(spell_id)
        if not symbol:
            return None

        slot_data = {
            "id": spell_id,
            "character": symbol.character,
            "name": symbol.name,
        }

        # Limit to 2 symbols
        if len(self.selected_symbols) >= 2:
            self.selected_symbols.pop(0)

        self.selected_symbols.append(slot_data)

        # Return to root after selecting a spell (if setting enabled)
        if self.casting_reset_enabled:
            self.current_node_id = "root"
            self.entry_direction = None
            self.navigation_stack = []

        # Auto-stow after second symbol (always happens regardless of setting)
        if len(self.selected_symbols) >= 2:
            self.stow()
            return "stow"

        return "symbol_selected"

    def _is_in_center_zone(self, mouse_x, mouse_y):
        """Check if mouse is in the center zone."""
        dx = mouse_x - self.center_x
        dy = mouse_y - self.center_y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= 30

    def render(self, screen):
        """Render the radial menu."""
        if not self.is_open:
            return

        self._init_fonts()

        slot_alpha = 150
        center_alpha = 140

        # Draw center circle
        center_surf = pygame.Surface((82, 82), pygame.SRCALPHA)
        pygame.draw.circle(center_surf, (*self.center_color, center_alpha), (41, 41), 40)
        pygame.draw.circle(center_surf, (80, 85, 100, 200), (41, 41), 40, 2)
        screen.blit(center_surf, (self.center_x - 41, self.center_y - 41))

        # Draw selected symbols in center
        if self.selected_symbols:
            selected_text = " + ".join(s["character"] for s in self.selected_symbols)
            text_surf = self.symbol_font.render(selected_text, True, self.symbol_color)
            text_rect = text_surf.get_rect(center=(self.center_x, self.center_y))
            screen.blit(text_surf, text_rect)
        else:
            # Show current node name if not at root
            current_node = self.layout.get_node(self.current_node_id)
            if current_node and self.current_node_id != "root":
                name_surf = self.font.render(current_node.name, True, self.text_color)
                name_rect = name_surf.get_rect(center=(self.center_x, self.center_y))
                screen.blit(name_surf, name_rect)

        # Get current node for slot rendering
        current_node = self.layout.get_node(self.current_node_id)
        if not current_node:
            return

        # Draw each slot
        for direction, offset in self.slot_positions.items():
            slot_x = self.center_x + offset[0]
            slot_y = self.center_y + offset[1]

            slot_content = current_node.get_slot(direction)
            is_return_slot = (self.entry_direction and
                              direction == OPPOSITE_DIRECTION.get(self.entry_direction))

            # Determine slot appearance
            color, content_text, is_node = self._get_slot_appearance(
                direction, slot_content, is_return_slot
            )

            # Hover effect
            if self.hovered_slot == direction:
                color = self.slot_hover_color

            # Selected effect (for spells)
            if slot_content and not slot_content.startswith("node:"):
                if any(s["id"] == slot_content for s in self.selected_symbols):
                    color = self.slot_selected_color

            # Draw slot background
            slot_surf = pygame.Surface(
                (self.slot_radius * 2 + 4, self.slot_radius * 2 + 4),
                pygame.SRCALPHA
            )

            if slot_content is None and not is_return_slot:
                # Empty slot - dotted circle
                self._draw_dotted_circle(slot_surf, self.slot_radius + 2,
                                         self.slot_radius + 2, self.slot_radius,
                                         (*self.slot_empty_color, 100))
            else:
                pygame.draw.circle(slot_surf, (*color, slot_alpha),
                                   (self.slot_radius + 2, self.slot_radius + 2),
                                   self.slot_radius)
                pygame.draw.circle(slot_surf, (100, 110, 130, 200),
                                   (self.slot_radius + 2, self.slot_radius + 2),
                                   self.slot_radius, 2)

            screen.blit(slot_surf,
                        (slot_x - self.slot_radius - 2, slot_y - self.slot_radius - 2))

            # Draw content
            if is_return_slot:
                # Draw return arrow
                self._draw_return_icon(screen, slot_x, slot_y)
            elif content_text:
                if is_node:
                    # Draw folder icon for nodes
                    self._draw_node_icon(screen, slot_x, slot_y, content_text)
                else:
                    # Draw spell character
                    char_surf = self.symbol_font.render(content_text, True, self.symbol_color)
                    char_rect = char_surf.get_rect(center=(slot_x, slot_y))
                    screen.blit(char_surf, char_rect)

    def _get_slot_appearance(self, direction, slot_content, is_return_slot):
        """Get color and content for a slot."""
        if is_return_slot:
            return self.slot_return_color, "<", False

        if slot_content is None:
            return self.slot_empty_color, None, False

        if slot_content.startswith("node:"):
            node_id = slot_content[5:]
            node = self.layout.get_node(node_id)
            name = node.name if node else "?"
            return self.slot_node_color, name, True
        else:
            # Spell
            symbol = MagicSystem.get_symbol(slot_content)
            if symbol:
                return self.slot_color, symbol.character, False
            return self.slot_color, "?", False

    def _draw_dotted_circle(self, surface, cx, cy, radius, color):
        """Draw a dotted circle for empty slots."""
        num_dots = 12
        dot_radius = 3
        for i in range(num_dots):
            angle = 2 * math.pi * i / num_dots
            x = int(cx + radius * 0.8 * math.cos(angle))
            y = int(cy + radius * 0.8 * math.sin(angle))
            pygame.draw.circle(surface, color, (x, y), dot_radius)

    def _draw_return_icon(self, screen, cx, cy):
        """Draw a return/back arrow icon."""
        # Simple left-pointing arrow
        arrow_size = 15
        points = [
            (cx - arrow_size, cy),
            (cx + arrow_size // 2, cy - arrow_size),
            (cx + arrow_size // 2, cy + arrow_size),
        ]
        pygame.draw.polygon(screen, self.text_color, points)

    def _draw_node_icon(self, screen, cx, cy, name):
        """Draw a folder/node icon with abbreviated name."""
        # Small folder shape
        folder_w, folder_h = 24, 18
        pygame.draw.rect(screen, self.text_color,
                         (cx - folder_w // 2, cy - folder_h // 2 - 5,
                          folder_w, folder_h), border_radius=3)

        # Node name (abbreviated)
        abbrev = name[:3] if len(name) > 3 else name
        name_surf = self.small_font.render(abbrev, True, self.center_color)
        name_rect = name_surf.get_rect(center=(cx, cy + 12))
        screen.blit(name_surf, name_rect)

    def get_cast_direction_from_mouse(self, mouse_x, mouse_y):
        """Get 8-directional cast direction based on mouse position."""
        dx = mouse_x - self.center_x
        dy = mouse_y - self.center_y

        if dx == 0 and dy == 0:
            return (0, 1)

        angle = math.atan2(dy, dx)
        if angle < 0:
            angle += 2 * math.pi

        sector = int((angle + math.pi / 8) / (math.pi / 4)) % 8

        direction_map = {
            0: (1, 0),
            1: (1, 1),
            2: (0, 1),
            3: (-1, 1),
            4: (-1, 0),
            5: (-1, -1),
            6: (0, -1),
            7: (1, -1),
        }

        return direction_map.get(sector, (0, 1))
