"""
Settings menu - configurable game options.
Displays settings with Yes/No toggles and description dialogue at bottom.
"""
import pygame


class SettingsMenu:
    """
    Settings menu with toggle options.
    Top: Compact settings box with setting name on left, toggle on right
    Bottom: Dialogue box showing description of selected setting
    Navigation: W/S to select, A/D to toggle, E to save, ESC/TAB to cancel
    """

    # Settings definition
    SETTINGS = [
        {
            "id": "casting_reset",
            "label": "Casting Reset",
            "description": "When enabled, selecting a spell symbol returns you to the root of the magic menu. When disabled, you stay in the current node until you select a second symbol.",
            "default": True,
        },
    ]

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Menu state
        self.is_open = False
        self.selected_index = 0

        # Current values (copy of settings with current values)
        self.current_values = {}
        self._init_default_values()

        # Visual properties - compact settings box
        self.menu_width = 350
        self.item_height = 45
        self.padding = 15
        self.menu_x = (screen_width - self.menu_width) // 2

        # Calculate menu height based on number of settings + title + instructions
        title_height = 50
        instructions_height = 35
        settings_height = len(self.SETTINGS) * self.item_height + self.padding * 2
        self.menu_height = title_height + settings_height + instructions_height
        self.menu_y = 80  # Near top of screen

        # Description dialogue box at bottom
        self.desc_width = 500
        self.desc_height = 100
        self.desc_x = (screen_width - self.desc_width) // 2
        self.desc_y = screen_height - self.desc_height - 40

        # Colors
        self.bg_color = (25, 28, 35)
        self.bg_border_color = (60, 65, 80)
        self.item_color = (40, 45, 55)
        self.item_selected_color = (70, 90, 130)
        self.text_color = (220, 220, 220)
        self.text_selected_color = (255, 255, 255)
        self.toggle_yes_color = (80, 160, 100)
        self.toggle_no_color = (160, 80, 80)
        self.desc_bg_color = (30, 35, 45)
        self.instruction_color = (140, 140, 150)

        # Fonts
        self.font = None
        self.title_font = None
        self.small_font = None
        self.desc_font = None

    def _init_fonts(self):
        """Initialize fonts if needed."""
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 26)
            self.title_font = pygame.font.Font(None, 36)
            self.small_font = pygame.font.Font(None, 20)
            self.desc_font = pygame.font.Font(None, 22)

    def _init_default_values(self):
        """Initialize settings with default values."""
        for setting in self.SETTINGS:
            self.current_values[setting["id"]] = setting["default"]

    def get_setting(self, setting_id):
        """Get the current value of a setting."""
        return self.current_values.get(setting_id, None)

    def set_setting(self, setting_id, value):
        """Set the value of a setting."""
        self.current_values[setting_id] = value

    def open(self):
        """Open the settings menu."""
        self._init_fonts()
        self.is_open = True
        self.selected_index = 0
        # Store a backup to restore on cancel
        self._backup_values = self.current_values.copy()

    def close(self, save=True):
        """Close the settings menu."""
        if not save and hasattr(self, '_backup_values'):
            # Restore backup on cancel
            self.current_values = self._backup_values
        self.is_open = False

    def handle_input(self, input_handler):
        """
        Handle input for the settings menu.
        Returns: "save" if saved, "cancel" if cancelled, None otherwise
        """
        if not self.is_open:
            return None

        # Navigate up/down
        if input_handler.was_key_pressed(pygame.K_w) or input_handler.was_key_pressed(pygame.K_UP):
            self.selected_index = (self.selected_index - 1) % len(self.SETTINGS)
        if input_handler.was_key_pressed(pygame.K_s) or input_handler.was_key_pressed(pygame.K_DOWN):
            self.selected_index = (self.selected_index + 1) % len(self.SETTINGS)

        # Toggle value with A/D
        if input_handler.was_key_pressed(pygame.K_a) or input_handler.was_key_pressed(pygame.K_LEFT):
            self._toggle_current(False)
        if input_handler.was_key_pressed(pygame.K_d) or input_handler.was_key_pressed(pygame.K_RIGHT):
            self._toggle_current(True)

        # Save with E or Enter
        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            self.close(save=True)
            return "save"

        # Cancel with Escape or TAB - both return to menu
        if input_handler.cancel or input_handler.open_menu:
            self.close(save=False)
            return "cancel"

        return None

    def _toggle_current(self, value):
        """Set the current setting to a specific value."""
        setting = self.SETTINGS[self.selected_index]
        self.current_values[setting["id"]] = value

    def render(self, screen):
        """Render the settings menu."""
        if not self.is_open:
            return

        self._init_fonts()

        # Dim background
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Render the compact settings box at top
        self._render_settings_box(screen)

        # Render the description dialogue box at bottom
        self._render_description_dialogue(screen)

    def _render_settings_box(self, screen):
        """Render the compact settings box."""
        menu_rect = pygame.Rect(self.menu_x, self.menu_y, self.menu_width, self.menu_height)
        pygame.draw.rect(screen, self.bg_color, menu_rect, border_radius=10)
        pygame.draw.rect(screen, self.bg_border_color, menu_rect, 2, border_radius=10)

        # Title
        title_surf = self.title_font.render("SETTINGS", True, self.text_color)
        title_rect = title_surf.get_rect(centerx=menu_rect.centerx, top=menu_rect.top + 12)
        screen.blit(title_surf, title_rect)

        # Settings list starts below title
        list_y = self.menu_y + 50

        for i, setting in enumerate(self.SETTINGS):
            is_selected = i == self.selected_index
            item_rect = pygame.Rect(
                self.menu_x + self.padding,
                list_y + i * self.item_height,
                self.menu_width - self.padding * 2,
                self.item_height - 5
            )

            # Background
            bg_color = self.item_selected_color if is_selected else self.item_color
            pygame.draw.rect(screen, bg_color, item_rect, border_radius=5)

            if is_selected:
                pygame.draw.rect(screen, (100, 140, 200), item_rect, 2, border_radius=5)

            # Setting label on left
            text_color = self.text_selected_color if is_selected else self.text_color
            label_surf = self.font.render(setting["label"], True, text_color)
            label_rect = label_surf.get_rect(left=item_rect.left + 15, centery=item_rect.centery)
            screen.blit(label_surf, label_rect)

            # Toggle state on right - "Yes" or "No"
            value = self.current_values.get(setting["id"], setting["default"])
            toggle_text = "Yes" if value else "No"
            toggle_color = self.toggle_yes_color if value else self.toggle_no_color
            toggle_surf = self.font.render(toggle_text, True, toggle_color)
            toggle_rect = toggle_surf.get_rect(right=item_rect.right - 15, centery=item_rect.centery)
            screen.blit(toggle_surf, toggle_rect)

        # Instructions at bottom of settings box
        instructions = "W/S: Select   A/D: Toggle   E: Save   ESC: Back"
        inst_surf = self.small_font.render(instructions, True, self.instruction_color)
        inst_rect = inst_surf.get_rect(centerx=menu_rect.centerx, bottom=menu_rect.bottom - 10)
        screen.blit(inst_surf, inst_rect)

    def _render_description_dialogue(self, screen):
        """Render the description dialogue box at the bottom of the screen."""
        desc_rect = pygame.Rect(self.desc_x, self.desc_y, self.desc_width, self.desc_height)
        pygame.draw.rect(screen, self.desc_bg_color, desc_rect, border_radius=8)
        pygame.draw.rect(screen, self.bg_border_color, desc_rect, 2, border_radius=8)

        # Get current setting description
        setting = self.SETTINGS[self.selected_index]
        description = setting["description"]

        # Wrap text for the dialogue box
        wrapped_lines = self._wrap_text(description, self.desc_width - 30)

        # Render wrapped text centered vertically
        line_height = 24
        total_text_height = len(wrapped_lines) * line_height
        text_y = desc_rect.centery - total_text_height // 2

        for line in wrapped_lines:
            line_surf = self.desc_font.render(line, True, self.text_color)
            line_rect = line_surf.get_rect(centerx=desc_rect.centerx, top=text_y)
            screen.blit(line_surf, line_rect)
            text_y += line_height

    def _wrap_text(self, text, max_width):
        """Wrap text to fit within max_width."""
        words = text.split(' ')
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            test_surf = self.desc_font.render(test_line, True, (255, 255, 255))
            if test_surf.get_width() <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def to_dict(self):
        """Serialize settings to a dictionary for saving."""
        return self.current_values.copy()

    def from_dict(self, data):
        """Load settings from a dictionary."""
        if data:
            for key, value in data.items():
                if key in self.current_values:
                    self.current_values[key] = value
