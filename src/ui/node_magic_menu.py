"""
Node-based magic menu - freeform spell selection via clickable nodes.
Activated by holding SPACE, interacted with via mouse click.
Implements the same interface as RadialMagicMenu for SpellHandler compatibility.
"""
import pygame
import math
from ..magic import MagicSystem
from .node_menu_layout import NodeMenuLayout, CANVAS_WIDTH, CANVAS_HEIGHT, CENTER_NODE_ID


class NodeMagicMenu:
    """
    A freeform node-based menu for selecting magic symbols.
    - Opens when SPACE is held
    - Mouse click selects spell nodes (up to 2)
    - Click off canvas stows UI and locks selection
    - Right click cancels
    - Releasing SPACE launches spell

    Node positions are frozen during casting (no physics).
    """

    NODE_RADIUS = 35  # Fixed generous size for click targets

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Menu state (same interface as RadialMagicMenu)
        self.is_open = False
        self.is_stowed = False
        self.selected_symbols = []  # Up to 2: [{"id", "character", "name"}, ...]
        self.hovered_node = None  # spell_id of hovered node

        # Layout
        self.layout = NodeMenuLayout()

        # Canvas bounds (centered on screen)
        self.canvas_x = (screen_width - CANVAS_WIDTH) // 2
        self.canvas_y = (screen_height - CANVAS_HEIGHT) // 2

        # Settings
        self.casting_reset_enabled = True

        # Fonts (lazy init)
        self.font = None
        self.symbol_font = None
        self.small_font = None

        # Colors
        self.bg_color = (30, 30, 40, 160)
        self.node_color = (50, 60, 80)
        self.node_hover_color = (70, 90, 120)
        self.node_selected_color = (100, 150, 200)
        self.connection_color = (60, 65, 80, 150)
        self.text_color = (220, 220, 220)
        self.symbol_color = (180, 200, 255)
        self.center_color = (40, 45, 55)

    def _init_fonts(self):
        """Initialize fonts if not already done."""
        if self.font is not None:
            return
        pygame.font.init()
        self.font = pygame.font.Font(None, 20)
        self.small_font = pygame.font.Font(None, 16)

        cjk_fonts = [
            "microsoftyahei", "yugothic", "msgothic", "simsun", "arialunicodems",
        ]
        self.symbol_font = None
        for font_name in cjk_fonts:
            try:
                self.symbol_font = pygame.font.SysFont(font_name, 36)
                test_surf = self.symbol_font.render("\u706b", True, (255, 255, 255))
                if test_surf.get_width() > 5:
                    break
            except Exception:
                continue
        if self.symbol_font is None:
            self.symbol_font = pygame.font.Font(None, 36)

    # --- Interface methods matching RadialMagicMenu ---

    def open(self, player_screen_x=None, player_screen_y=None):
        """Open the node menu."""
        self._init_fonts()
        self.is_open = True
        self.is_stowed = False
        self.selected_symbols = []
        self.hovered_node = None

    def close(self):
        """Close and reset the menu."""
        self.is_open = False
        self.is_stowed = False
        self.selected_symbols = []
        self.hovered_node = None

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

    def set_layout(self, layout):
        """Set the NodeMenuLayout."""
        if layout is not None:
            self.layout = layout

    def set_casting_reset(self, enabled):
        """Set whether selecting a spell resets state."""
        self.casting_reset_enabled = enabled

    def update_known_symbols(self, known_symbol_ids):
        """Auto-populate layout if empty."""
        if self.layout:
            assigned = self.layout.get_all_assigned_spells()
            if not assigned and known_symbol_ids:
                self.layout.auto_populate_from_spells(known_symbol_ids)

    def update(self, mouse_x, mouse_y):
        """Update hover state based on mouse position."""
        if not self.is_open:
            self.hovered_node = None
            return
        self.hovered_node = self._get_node_at_position(mouse_x, mouse_y)

    def handle_click(self, mouse_x, mouse_y):
        """
        Handle mouse click.
        Returns: "symbol_selected", "stow", or None
        """
        if not self.is_open:
            return None

        clicked_node = self._get_node_at_position(mouse_x, mouse_y)

        if clicked_node is not None:
            return self._select_spell(clicked_node)
        else:
            # Clicked off nodes — stow and lock selection
            if self.has_selection():
                self.stow()
                return "stow"
            else:
                self.close()
                return None

    def get_cast_direction_from_mouse(self, mouse_x, mouse_y):
        """Get 8-directional cast direction based on mouse position relative to screen center."""
        cx = self.screen_width // 2
        cy = self.screen_height // 2
        dx = mouse_x - cx
        dy = mouse_y - cy

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

    # --- Internal methods ---

    def _get_node_at_position(self, mouse_x, mouse_y):
        """Get which spell node the mouse is over, or None.
        Skips the center anchor node (not a spell)."""
        if not self.layout:
            return None

        for spell_id, pos in self.layout.nodes.items():
            if spell_id == CENTER_NODE_ID:
                continue
            nx = self.canvas_x + pos["x"]
            ny = self.canvas_y + pos["y"]
            dx = mouse_x - nx
            dy = mouse_y - ny
            if dx * dx + dy * dy <= self.NODE_RADIUS * self.NODE_RADIUS:
                return spell_id
        return None

    def _select_spell(self, spell_id):
        """Select a spell from a clicked node."""
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

        # Auto-stow after second symbol
        if len(self.selected_symbols) >= 2:
            self.stow()
            return "stow"

        return "symbol_selected"

    def render(self, screen):
        """Render the node canvas with connections and spell nodes."""
        if not self.is_open:
            return

        self._init_fonts()

        if not self.layout:
            return

        # Full-screen semi-transparent overlay (player concentrating on spells)
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((20, 20, 30, 120))
        screen.blit(overlay, (0, 0))

        # Draw connection lines
        for spell_a, spell_b in self.layout.connections:
            pos_a = self.layout.nodes.get(spell_a)
            pos_b = self.layout.nodes.get(spell_b)
            if pos_a and pos_b:
                ax = int(self.canvas_x + pos_a["x"])
                ay = int(self.canvas_y + pos_a["y"])
                bx = int(self.canvas_x + pos_b["x"])
                by = int(self.canvas_y + pos_b["y"])
                pygame.draw.line(screen, (60, 65, 80), (ax, ay), (bx, by), 2)

        # Draw each node
        for spell_id, pos in self.layout.nodes.items():
            nx = int(self.canvas_x + pos["x"])
            ny = int(self.canvas_y + pos["y"])

            # Center anchor — subtle presence during casting, not clickable
            if spell_id == CENTER_NODE_ID:
                anchor_surf = pygame.Surface(
                    (self.NODE_RADIUS * 2 + 4, self.NODE_RADIUS * 2 + 4),
                    pygame.SRCALPHA
                )
                pygame.draw.circle(anchor_surf, (55, 65, 85, 100),
                                   (self.NODE_RADIUS + 2, self.NODE_RADIUS + 2),
                                   self.NODE_RADIUS)
                pygame.draw.circle(anchor_surf, (80, 90, 110, 130),
                                   (self.NODE_RADIUS + 2, self.NODE_RADIUS + 2),
                                   self.NODE_RADIUS, 2)
                screen.blit(anchor_surf,
                            (nx - self.NODE_RADIUS - 2, ny - self.NODE_RADIUS - 2))
                # Small crosshair
                pygame.draw.circle(screen, (90, 100, 130), (nx, ny), 5)
                continue

            # Determine color for spell nodes
            is_selected = any(s["id"] == spell_id for s in self.selected_symbols)
            is_hovered = self.hovered_node == spell_id

            if is_selected:
                color = self.node_selected_color
            elif is_hovered:
                color = self.node_hover_color
            else:
                color = self.node_color

            # Draw node circle with alpha
            node_surf = pygame.Surface(
                (self.NODE_RADIUS * 2 + 4, self.NODE_RADIUS * 2 + 4),
                pygame.SRCALPHA
            )
            pygame.draw.circle(node_surf, (*color, 180),
                               (self.NODE_RADIUS + 2, self.NODE_RADIUS + 2),
                               self.NODE_RADIUS)
            pygame.draw.circle(node_surf, (100, 110, 130, 220),
                               (self.NODE_RADIUS + 2, self.NODE_RADIUS + 2),
                               self.NODE_RADIUS, 2)
            screen.blit(node_surf,
                        (nx - self.NODE_RADIUS - 2, ny - self.NODE_RADIUS - 2))

            # Draw kanji symbol
            symbol = MagicSystem.get_symbol(spell_id)
            if symbol:
                char_surf = self.symbol_font.render(symbol.character, True, self.symbol_color)
                char_rect = char_surf.get_rect(center=(nx, ny))
                screen.blit(char_surf, char_rect)

        # Draw selected symbols indicator at top center
        if self.selected_symbols:
            selected_text = " + ".join(s["character"] for s in self.selected_symbols)
            text_surf = self.symbol_font.render(selected_text, True, self.symbol_color)
            text_rect = text_surf.get_rect(
                centerx=self.screen_width // 2,
                top=self.canvas_y - 50
            )
            # Background for readability
            bg_rect = text_rect.inflate(20, 10)
            bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(bg_surf, (30, 30, 40, 200), bg_surf.get_rect(), border_radius=8)
            screen.blit(bg_surf, bg_rect)
            screen.blit(text_surf, text_rect)
