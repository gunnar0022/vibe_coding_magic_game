"""
Radial magic menu - 4-directional symbol selection via mouse.
Activated by holding SPACE, interacted with via mouse click.
Structured to support nested folders later (not implemented now).
"""
import pygame
import math
from ..magic import MagicSystem


class RadialMagicMenu:
    """
    A four-directional radial menu for selecting magic symbols.
    - Opens when SPACE is held
    - Mouse click selects symbols
    - Click off menu stows UI and locks selection
    - Right click cancels
    - Releasing SPACE launches spell

    The menu dynamically shows only the player's known symbols.
    """

    # Slot position order for assigning symbols
    SLOT_ORDER = ["up", "right", "down", "left"]

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Menu state
        self.is_open = False
        self.is_stowed = False  # UI hidden but spell locked
        self.selected_symbols = []  # Up to 2 symbols
        self.hovered_slot = None

        # Visual properties
        self.center_x = screen_width // 2
        self.center_y = screen_height // 2
        self.slot_radius = 50  # Size of each slot circle
        self.slot_distance = 100  # Distance from center to slot center

        # Colors
        self.bg_color = (30, 30, 40, 200)
        self.slot_color = (50, 60, 80)
        self.slot_hover_color = (70, 90, 120)
        self.slot_selected_color = (100, 150, 200)
        self.text_color = (220, 220, 220)
        self.symbol_color = (180, 200, 255)
        self.center_color = (40, 45, 55)

        # Slot positions (calculated from center)
        self.slot_positions = {
            "up": (0, -self.slot_distance),
            "right": (self.slot_distance, 0),
            "down": (0, self.slot_distance),
            "left": (-self.slot_distance, 0),
        }

        # Font (initialized on first render)
        self.font = None
        self.symbol_font = None

        # Dynamic symbol slots (populated from player's known symbols)
        self.symbol_slots = {}  # slot_name -> {"id", "character", "name"}

        # Folder support structure (for future, not implemented)
        self.current_folder = None  # None = root menu
        self.folder_structure = {}  # folder_id -> list of items

    def update_known_symbols(self, known_symbol_ids):
        """
        Update the menu to show only the player's known symbols.
        Symbols are assigned to slots in the order: up, right, down, left.
        """
        self.symbol_slots = {}

        for i, symbol_id in enumerate(known_symbol_ids):
            if i >= len(self.SLOT_ORDER):
                break  # Only 4 slots available

            slot_name = self.SLOT_ORDER[i]
            symbol = MagicSystem.get_symbol(symbol_id)

            if symbol:
                self.symbol_slots[slot_name] = {
                    "id": symbol_id,
                    "character": symbol.character,
                    "name": symbol.name,
                }

    def _init_fonts(self):
        """Initialize fonts if not already done."""
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 20)

            # Use a system font that supports CJK characters
            # Try common Windows fonts with CJK support
            cjk_fonts = [
                "microsoftyahei",  # Microsoft YaHei (Win Vista+)
                "yugothic",        # Yu Gothic (Win 8.1+)
                "msgothic",        # MS Gothic
                "simsun",          # SimSun
                "arialunicodems",  # Arial Unicode MS
            ]

            self.symbol_font = None
            for font_name in cjk_fonts:
                try:
                    self.symbol_font = pygame.font.SysFont(font_name, 48)
                    # Test if it can render a CJK character
                    test_surf = self.symbol_font.render("\u706b", True, (255, 255, 255))
                    if test_surf.get_width() > 5:  # Valid render
                        break
                except:
                    continue

            # Fallback to default if no CJK font found
            if self.symbol_font is None:
                self.symbol_font = pygame.font.Font(None, 48)

    def open(self, player_screen_x=None, player_screen_y=None):
        """
        Open the radial menu.
        Centers on screen (spells target from player, not menu position).
        """
        self._init_fonts()
        self.is_open = True
        self.is_stowed = False
        self.selected_symbols = []
        self.hovered_slot = None
        self.current_folder = None  # Always return to root on open

    def close(self):
        """Close and reset the menu."""
        self.is_open = False
        self.is_stowed = False
        self.selected_symbols = []
        self.hovered_slot = None

    def stow(self):
        """
        Stow the UI (hide it but keep selection locked).
        Mana is deducted at this point.
        """
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

        # Check which slot (if any) the mouse is over
        self.hovered_slot = self._get_slot_at_position(mouse_x, mouse_y)

    def _get_slot_at_position(self, mouse_x, mouse_y):
        """Get which slot the mouse is over, or None."""
        for slot_name, offset in self.slot_positions.items():
            slot_x = self.center_x + offset[0]
            slot_y = self.center_y + offset[1]

            # Check if mouse is within slot radius
            dx = mouse_x - slot_x
            dy = mouse_y - slot_y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance <= self.slot_radius:
                return slot_name

        return None

    def handle_click(self, mouse_x, mouse_y):
        """
        Handle mouse click.
        Returns: "symbol_selected", "stow", or None
        """
        if not self.is_open:
            return None

        clicked_slot = self._get_slot_at_position(mouse_x, mouse_y)

        if clicked_slot is not None:
            # Clicked on a slot - select the symbol
            slot_data = self.symbol_slots.get(clicked_slot)
            if slot_data:
                return self._select_symbol(slot_data)
        else:
            # Clicked off menu - stow and lock selection
            if self.has_selection():
                self.stow()
                return "stow"
            else:
                # No selection, just close
                self.close()
                return None

        return None

    def _select_symbol(self, slot_data):
        """
        Select a symbol from a slot.
        After selection, always returns to root menu.
        Auto-stows after second symbol is selected for clearer aiming.
        """
        # Check if already selected (limit 2)
        if len(self.selected_symbols) >= 2:
            # Replace oldest selection
            self.selected_symbols.pop(0)

        self.selected_symbols.append(slot_data)

        # Return to root menu after selection (per spec)
        self.current_folder = None

        # Auto-stow after second symbol for clear aiming
        if len(self.selected_symbols) >= 2:
            self.stow()
            return "stow"

        return "symbol_selected"

    def _is_in_center_zone(self, mouse_x, mouse_y):
        """Check if mouse is in the center zone."""
        dx = mouse_x - self.center_x
        dy = mouse_y - self.center_y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= 30  # Center zone radius

    def render(self, screen):
        """Render the radial menu."""
        if not self.is_open:
            return

        self._init_fonts()

        # No overlay - keep full visibility of the game world

        # Transparency level for menu elements (0-255, lower = more transparent)
        slot_alpha = 150
        center_alpha = 140

        # Draw center circle with transparency (shows selected symbols)
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

        # Draw each slot with transparency
        for slot_name, offset in self.slot_positions.items():
            slot_x = self.center_x + offset[0]
            slot_y = self.center_y + offset[1]

            slot_data = self.symbol_slots.get(slot_name)
            if not slot_data:
                continue

            # Determine slot color
            if self.hovered_slot == slot_name:
                color = self.slot_hover_color
            elif any(s["id"] == slot_data["id"] for s in self.selected_symbols):
                color = self.slot_selected_color
            else:
                color = self.slot_color

            # Draw slot background with transparency
            slot_surf = pygame.Surface((self.slot_radius * 2 + 4, self.slot_radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(slot_surf, (*color, slot_alpha),
                               (self.slot_radius + 2, self.slot_radius + 2), self.slot_radius)
            pygame.draw.circle(slot_surf, (100, 110, 130, 200),
                               (self.slot_radius + 2, self.slot_radius + 2), self.slot_radius, 2)
            screen.blit(slot_surf, (slot_x - self.slot_radius - 2, slot_y - self.slot_radius - 2))

            # Draw symbol character (centered)
            char_surf = self.symbol_font.render(slot_data["character"], True, self.symbol_color)
            char_rect = char_surf.get_rect(center=(slot_x, slot_y))
            screen.blit(char_surf, char_rect)

        # No connecting lines - keep UI minimal for better visibility

    def get_cast_direction_from_mouse(self, mouse_x, mouse_y):
        """
        Get 8-directional cast direction based on mouse position.
        Returns (dx, dy) for the direction.
        """
        # Calculate angle from screen center to mouse
        dx = mouse_x - self.center_x
        dy = mouse_y - self.center_y

        # Handle zero case
        if dx == 0 and dy == 0:
            return (0, 1)  # Default down

        # Calculate angle in radians, then convert to 8 directions
        angle = math.atan2(dy, dx)
        # Normalize to 0-2pi
        if angle < 0:
            angle += 2 * math.pi

        # Divide into 8 sectors (each 45 degrees = pi/4 radians)
        # Offset by half a sector to center directions
        sector = int((angle + math.pi / 8) / (math.pi / 4)) % 8

        # Map sectors to directions
        # 0 = right, 1 = down-right, 2 = down, 3 = down-left,
        # 4 = left, 5 = up-left, 6 = up, 7 = up-right
        direction_map = {
            0: (1, 0),    # Right
            1: (1, 1),    # Down-right
            2: (0, 1),    # Down
            3: (-1, 1),   # Down-left
            4: (-1, 0),   # Left
            5: (-1, -1),  # Up-left
            6: (0, -1),   # Up
            7: (1, -1),   # Up-right
        }

        return direction_map.get(sector, (0, 1))
