"""
Magic casting menu UI - allows player to select and combine symbols.
"""
import pygame
import math


class MagicMenu:
    """
    A menu for selecting magic symbols to cast.
    Supports nested organization and quick loadouts.
    """

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Menu state
        self.is_open = False
        self.selected_index = 0
        self.current_folder = None  # None = root

        # Symbol organization
        self.folders = {}  # folder_name -> list of symbol_ids
        self.root_symbols = []  # Symbols not in any folder

        # Visual properties
        self.menu_width = 300
        self.menu_height = 400
        self.item_height = 40
        self.padding = 10

        # Colors
        self.bg_color = (30, 30, 35, 230)
        self.border_color = (80, 80, 90)
        self.text_color = (220, 220, 220)
        self.selected_color = (60, 100, 150)
        self.symbol_color = (150, 200, 255)
        self.folder_color = (200, 180, 100)

        # Font (will be initialized when needed)
        self.font = None
        self.symbol_font = None

        # Currently displayed items
        self._current_items = []
        self._scroll_offset = 0

    def _init_fonts(self):
        """Initialize fonts if not already done."""
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 24)
            # Try to use a font that supports Chinese characters
            try:
                self.symbol_font = pygame.font.Font(None, 32)
            except:
                self.symbol_font = self.font

    def open(self, known_symbols, symbol_data=None):
        """
        Open the magic menu with available symbols.

        known_symbols: set of symbol IDs the player knows
        symbol_data: dict of symbol_id -> symbol info (name, character)
        """
        self._init_fonts()
        self.is_open = True
        self.selected_index = 0
        self._scroll_offset = 0
        self.current_folder = None

        # Build display list
        self._refresh_items(known_symbols, symbol_data or {})

    def close(self):
        """Close the menu."""
        self.is_open = False
        self.current_folder = None

    def _refresh_items(self, known_symbols, symbol_data):
        """Refresh the list of displayed items."""
        self._current_items = []

        if self.current_folder is None:
            # Show root level
            # First show folders
            for folder_name in sorted(self.folders.keys()):
                self._current_items.append({
                    "type": "folder",
                    "name": folder_name,
                    "id": folder_name,
                })

            # Then show ungrouped symbols
            for symbol_id in sorted(known_symbols):
                if symbol_id not in self._get_all_folder_symbols():
                    info = symbol_data.get(symbol_id, {})
                    self._current_items.append({
                        "type": "symbol",
                        "id": symbol_id,
                        "name": info.get("name", symbol_id.title()),
                        "character": info.get("character", "?"),
                    })
        else:
            # Show folder contents
            # Add back option
            self._current_items.append({
                "type": "back",
                "name": ".. Back",
                "id": None,
            })

            folder_symbols = self.folders.get(self.current_folder, [])
            for symbol_id in folder_symbols:
                if symbol_id in known_symbols:
                    info = symbol_data.get(symbol_id, {})
                    self._current_items.append({
                        "type": "symbol",
                        "id": symbol_id,
                        "name": info.get("name", symbol_id.title()),
                        "character": info.get("character", "?"),
                    })

    def _get_all_folder_symbols(self):
        """Get set of all symbols in any folder."""
        result = set()
        for symbols in self.folders.values():
            result.update(symbols)
        return result

    def navigate(self, direction):
        """Navigate menu selection."""
        if not self.is_open or not self._current_items:
            return

        if direction == "up":
            self.selected_index = max(0, self.selected_index - 1)
        elif direction == "down":
            self.selected_index = min(len(self._current_items) - 1, self.selected_index + 1)

        # Adjust scroll
        visible_items = (self.menu_height - self.padding * 2) // self.item_height
        if self.selected_index < self._scroll_offset:
            self._scroll_offset = self.selected_index
        elif self.selected_index >= self._scroll_offset + visible_items:
            self._scroll_offset = self.selected_index - visible_items + 1

    def select(self):
        """
        Select current item.
        Returns symbol_id if a symbol was selected, None otherwise.
        """
        if not self.is_open or not self._current_items:
            return None

        item = self._current_items[self.selected_index]

        if item["type"] == "folder":
            self.current_folder = item["id"]
            self.selected_index = 0
            self._scroll_offset = 0
            # Need to refresh with same data - caller should handle this
            return ("folder", item["id"])

        elif item["type"] == "back":
            self.current_folder = None
            self.selected_index = 0
            self._scroll_offset = 0
            return ("back", None)

        elif item["type"] == "symbol":
            return ("symbol", item["id"])

        return None

    def create_folder(self, name, symbol_ids=None):
        """Create a new folder for organizing symbols."""
        self.folders[name] = list(symbol_ids) if symbol_ids else []

    def add_to_folder(self, folder_name, symbol_id):
        """Add a symbol to a folder."""
        if folder_name not in self.folders:
            self.folders[folder_name] = []
        if symbol_id not in self.folders[folder_name]:
            self.folders[folder_name].append(symbol_id)

    def remove_from_folder(self, folder_name, symbol_id):
        """Remove a symbol from a folder."""
        if folder_name in self.folders:
            if symbol_id in self.folders[folder_name]:
                self.folders[folder_name].remove(symbol_id)

    def render(self, screen, known_symbols=None, symbol_data=None):
        """Render the magic menu."""
        if not self.is_open:
            return

        self._init_fonts()

        # Refresh items if data provided
        if known_symbols is not None:
            self._refresh_items(known_symbols, symbol_data or {})

        # Calculate menu position (center of screen)
        menu_x = (self.screen_width - self.menu_width) // 2
        menu_y = (self.screen_height - self.menu_height) // 2

        # Create semi-transparent background surface
        menu_surface = pygame.Surface((self.menu_width, self.menu_height), pygame.SRCALPHA)
        menu_surface.fill(self.bg_color)

        # Draw border
        pygame.draw.rect(menu_surface, self.border_color,
                         (0, 0, self.menu_width, self.menu_height), 2)

        # Draw title
        title = "Magic" if self.current_folder is None else self.current_folder
        title_surface = self.font.render(title, True, self.text_color)
        menu_surface.blit(title_surface, (self.padding, self.padding))

        # Draw separator
        pygame.draw.line(menu_surface, self.border_color,
                         (self.padding, self.padding + 25),
                         (self.menu_width - self.padding, self.padding + 25))

        # Draw items
        start_y = self.padding + 35
        visible_items = (self.menu_height - start_y - self.padding) // self.item_height

        for i, item in enumerate(self._current_items[self._scroll_offset:self._scroll_offset + visible_items]):
            actual_index = i + self._scroll_offset
            item_y = start_y + i * self.item_height

            # Selection highlight
            if actual_index == self.selected_index:
                highlight_rect = pygame.Rect(self.padding, item_y,
                                             self.menu_width - self.padding * 2, self.item_height - 2)
                pygame.draw.rect(menu_surface, self.selected_color, highlight_rect, border_radius=3)

            # Item content
            if item["type"] == "folder":
                # Folder icon (simple bracket representation)
                folder_text = f"[{item['name']}]"
                text_surface = self.font.render(folder_text, True, self.folder_color)
                menu_surface.blit(text_surface, (self.padding + 10, item_y + 10))

            elif item["type"] == "back":
                text_surface = self.font.render(item["name"], True, self.text_color)
                menu_surface.blit(text_surface, (self.padding + 10, item_y + 10))

            elif item["type"] == "symbol":
                # Symbol character
                char_surface = self.symbol_font.render(item.get("character", "?"), True, self.symbol_color)
                menu_surface.blit(char_surface, (self.padding + 10, item_y + 5))

                # Symbol name
                name_surface = self.font.render(item["name"], True, self.text_color)
                menu_surface.blit(name_surface, (self.padding + 50, item_y + 10))

        # Draw scroll indicators if needed
        if self._scroll_offset > 0:
            pygame.draw.polygon(menu_surface, self.text_color, [
                (self.menu_width // 2, start_y - 15),
                (self.menu_width // 2 - 8, start_y - 5),
                (self.menu_width // 2 + 8, start_y - 5),
            ])

        if self._scroll_offset + visible_items < len(self._current_items):
            bottom_y = self.menu_height - self.padding
            pygame.draw.polygon(menu_surface, self.text_color, [
                (self.menu_width // 2, bottom_y + 5),
                (self.menu_width // 2 - 8, bottom_y - 5),
                (self.menu_width // 2 + 8, bottom_y - 5),
            ])

        # Blit menu to screen
        screen.blit(menu_surface, (menu_x, menu_y))

        # Draw instructions at bottom
        instructions = "Up/Down: Navigate | Enter: Select | Esc: Close"
        inst_surface = self.font.render(instructions, True, (150, 150, 150))
        inst_x = (self.screen_width - inst_surface.get_width()) // 2
        inst_y = menu_y + self.menu_height + 10
        screen.blit(inst_surface, (inst_x, inst_y))

    def serialize(self):
        """Serialize menu organization."""
        return {
            "folders": {k: list(v) for k, v in self.folders.items()},
        }

    def deserialize(self, data):
        """Load menu organization."""
        self.folders = {k: list(v) for k, v in data.get("folders", {}).items()}
