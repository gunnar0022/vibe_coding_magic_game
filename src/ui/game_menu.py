"""
Game menu - vertical menu on right side of screen.
Handles settings, save, load, exit, bag, journal, quests.
"""
import pygame


class GameMenu:
    """
    Vertical game menu on the right side of the screen.
    Supports keyboard (WASD/E) and mouse navigation.
    """

    # Menu items with their properties
    MENU_ITEMS = [
        {"id": "resume", "label": "Resume", "enabled": True},
        {"id": "bag", "label": "Bag", "enabled": False},
        {"id": "journal", "label": "Spell Journal", "enabled": True},
        {"id": "customize_spells", "label": "Customize Spells", "enabled": True},
        {"id": "quests", "label": "Quest Log", "enabled": False},
        {"id": "settings", "label": "Settings", "enabled": True},
        {"id": "save", "label": "Save Game", "enabled": True},
        {"id": "load", "label": "Load Game", "enabled": True},
        {"id": "exit", "label": "Return to Title", "enabled": True},
    ]

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Menu state
        self.is_open = False
        self.selected_index = 0
        self.hovered_index = -1

        # Confirmation dialog state
        self.confirming = False
        self.confirm_action = None
        self.confirm_message = ""
        self.confirm_selected = 0  # 0 = No, 1 = Yes

        # Visual properties
        self.menu_width = 200
        self.menu_x = screen_width - self.menu_width - 20  # 20px from right edge
        self.item_height = 45
        self.menu_padding = 15
        self.menu_y = 80  # Start below top UI

        # Colors
        self.bg_color = (25, 28, 35)
        self.bg_border_color = (60, 65, 80)
        self.item_color = (40, 45, 55)
        self.item_hover_color = (55, 65, 85)
        self.item_selected_color = (70, 90, 130)
        self.item_disabled_color = (35, 38, 45)
        self.text_color = (220, 220, 220)
        self.text_disabled_color = (100, 100, 110)
        self.text_selected_color = (255, 255, 255)
        self.confirm_bg_color = (30, 35, 45)
        self.confirm_yes_color = (60, 120, 80)
        self.confirm_no_color = (120, 60, 60)

        # Fonts
        self.font = None
        self.title_font = None

    def _init_fonts(self):
        """Initialize fonts if needed."""
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 26)
            self.title_font = pygame.font.Font(None, 32)

    def open(self):
        """Open the game menu."""
        self._init_fonts()
        self.is_open = True
        self.selected_index = 0
        self.hovered_index = -1
        self.confirming = False
        self.confirm_action = None

    def close(self):
        """Close the game menu."""
        self.is_open = False
        self.confirming = False
        self.confirm_action = None

    def toggle(self):
        """Toggle menu open/closed."""
        if self.is_open:
            self.close()
        else:
            self.open()

    def _get_menu_rect(self):
        """Get the full menu rectangle."""
        total_height = (len(self.MENU_ITEMS) * self.item_height +
                        self.menu_padding * 2 + 40)  # 40 for title
        return pygame.Rect(self.menu_x, self.menu_y,
                           self.menu_width, total_height)

    def _get_item_rect(self, index):
        """Get rectangle for a menu item."""
        y = self.menu_y + self.menu_padding + 40 + (index * self.item_height)
        return pygame.Rect(self.menu_x + 10, y,
                           self.menu_width - 20, self.item_height - 5)

    def _get_item_at_position(self, mouse_x, mouse_y):
        """Get menu item index at mouse position, or -1."""
        for i in range(len(self.MENU_ITEMS)):
            rect = self._get_item_rect(i)
            if rect.collidepoint(mouse_x, mouse_y):
                return i
        return -1

    def handle_input(self, input_handler):
        """
        Handle input for the menu.
        Returns action string if an action should be performed, None otherwise.
        """
        if not self.is_open:
            return None

        mouse_x, mouse_y = input_handler.get_mouse_position()

        # Handle confirmation dialog
        if self.confirming:
            return self._handle_confirm_input(input_handler, mouse_x, mouse_y)

        # Update hover state
        self.hovered_index = self._get_item_at_position(mouse_x, mouse_y)

        # Keyboard navigation (W/S or Up/Down)
        if input_handler.was_key_pressed(pygame.K_w) or input_handler.was_key_pressed(pygame.K_UP):
            self._move_selection(-1)
        if input_handler.was_key_pressed(pygame.K_s) or input_handler.was_key_pressed(pygame.K_DOWN):
            self._move_selection(1)

        # Confirm with E or Enter
        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            return self._select_current()

        # Mouse click
        if input_handler.mouse_clicked:
            if self.hovered_index >= 0:
                self.selected_index = self.hovered_index
                return self._select_current()

        # Cancel with Escape
        if input_handler.cancel:
            self.close()
            return "resume"

        return None

    def _move_selection(self, direction):
        """Move selection up or down, skipping disabled items."""
        new_index = self.selected_index
        attempts = 0

        while attempts < len(self.MENU_ITEMS):
            new_index = (new_index + direction) % len(self.MENU_ITEMS)
            if self.MENU_ITEMS[new_index]["enabled"]:
                self.selected_index = new_index
                break
            attempts += 1

    def _select_current(self):
        """Select the current menu item."""
        item = self.MENU_ITEMS[self.selected_index]

        if not item["enabled"]:
            return None

        action_id = item["id"]

        # Actions that need confirmation
        if action_id == "save":
            self._show_confirmation("save", "Save current game?")
            return None
        elif action_id == "load":
            self._show_confirmation("load", "Load saved game?\nUnsaved progress will be lost.")
            return None
        elif action_id == "exit":
            self._show_confirmation("exit", "Return to title screen?\nUnsaved progress will be lost.")
            return None
        elif action_id == "resume":
            self.close()
            return "resume"
        elif action_id == "journal":
            self.close()
            return "journal"
        elif action_id == "customize_spells":
            self.close()
            return "customize_spells"
        elif action_id == "settings":
            self.close()
            return "settings"
        else:
            # Non-functional items
            return None

    def _show_confirmation(self, action, message):
        """Show confirmation dialog."""
        self.confirming = True
        self.confirm_action = action
        self.confirm_message = message
        self.confirm_selected = 0  # Default to "No"

    def _handle_confirm_input(self, input_handler, mouse_x, mouse_y):
        """Handle input for confirmation dialog."""
        # Keyboard: A/D or Left/Right to switch, E/Enter to confirm
        if input_handler.was_key_pressed(pygame.K_a) or input_handler.was_key_pressed(pygame.K_LEFT):
            self.confirm_selected = 0
        if input_handler.was_key_pressed(pygame.K_d) or input_handler.was_key_pressed(pygame.K_RIGHT):
            self.confirm_selected = 1

        # Confirm
        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            return self._confirm_selection()

        # Cancel
        if input_handler.cancel:
            self.confirming = False
            return None

        # Mouse click on buttons
        if input_handler.mouse_clicked:
            no_rect, yes_rect = self._get_confirm_button_rects()
            if no_rect.collidepoint(mouse_x, mouse_y):
                self.confirm_selected = 0
                return self._confirm_selection()
            elif yes_rect.collidepoint(mouse_x, mouse_y):
                self.confirm_selected = 1
                return self._confirm_selection()

        return None

    def _confirm_selection(self):
        """Process the confirmation selection."""
        if self.confirm_selected == 1:  # Yes
            action = self.confirm_action
            self.confirming = False
            if action == "exit":
                self.close()
            return action
        else:  # No
            self.confirming = False
            return None

    def _get_confirm_button_rects(self):
        """Get rectangles for confirmation buttons."""
        dialog_rect = self._get_confirm_dialog_rect()
        button_width = 80
        button_height = 35
        button_y = dialog_rect.bottom - 50

        no_rect = pygame.Rect(
            dialog_rect.centerx - button_width - 10,
            button_y,
            button_width,
            button_height
        )
        yes_rect = pygame.Rect(
            dialog_rect.centerx + 10,
            button_y,
            button_width,
            button_height
        )
        return no_rect, yes_rect

    def _get_confirm_dialog_rect(self):
        """Get rectangle for confirmation dialog."""
        width = 280
        height = 140
        x = (self.screen_width - width) // 2
        y = (self.screen_height - height) // 2
        return pygame.Rect(x, y, width, height)

    def render(self, screen):
        """Render the game menu."""
        if not self.is_open:
            return

        self._init_fonts()

        # Draw menu background
        menu_rect = self._get_menu_rect()
        pygame.draw.rect(screen, self.bg_color, menu_rect, border_radius=8)
        pygame.draw.rect(screen, self.bg_border_color, menu_rect, 2, border_radius=8)

        # Draw title
        title_surf = self.title_font.render("MENU", True, self.text_color)
        title_rect = title_surf.get_rect(
            centerx=menu_rect.centerx,
            top=menu_rect.top + self.menu_padding
        )
        screen.blit(title_surf, title_rect)

        # Draw menu items
        for i, item in enumerate(self.MENU_ITEMS):
            self._render_item(screen, i, item)

        # Draw confirmation dialog if active
        if self.confirming:
            self._render_confirmation(screen)

    def _render_item(self, screen, index, item):
        """Render a single menu item."""
        rect = self._get_item_rect(index)
        is_selected = index == self.selected_index
        is_hovered = index == self.hovered_index
        is_enabled = item["enabled"]

        # Determine background color
        if not is_enabled:
            bg_color = self.item_disabled_color
        elif is_selected:
            bg_color = self.item_selected_color
        elif is_hovered:
            bg_color = self.item_hover_color
        else:
            bg_color = self.item_color

        # Draw background
        pygame.draw.rect(screen, bg_color, rect, border_radius=5)

        # Selection indicator
        if is_selected and is_enabled:
            pygame.draw.rect(screen, (100, 140, 200), rect, 2, border_radius=5)

        # Determine text color
        if not is_enabled:
            text_color = self.text_disabled_color
        elif is_selected:
            text_color = self.text_selected_color
        else:
            text_color = self.text_color

        # Draw label
        label_surf = self.font.render(item["label"], True, text_color)
        label_rect = label_surf.get_rect(
            centery=rect.centery,
            left=rect.left + 15
        )
        screen.blit(label_surf, label_rect)

        # Draw "coming soon" for disabled items
        if not is_enabled:
            soon_surf = pygame.font.Font(None, 18).render("soon", True, (80, 80, 90))
            soon_rect = soon_surf.get_rect(
                centery=rect.centery,
                right=rect.right - 10
            )
            screen.blit(soon_surf, soon_rect)

    def _render_confirmation(self, screen):
        """Render the confirmation dialog."""
        # Dim background
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Dialog box
        dialog_rect = self._get_confirm_dialog_rect()
        pygame.draw.rect(screen, self.confirm_bg_color, dialog_rect, border_radius=10)
        pygame.draw.rect(screen, self.bg_border_color, dialog_rect, 2, border_radius=10)

        # Message text (support multiline)
        lines = self.confirm_message.split('\n')
        y_offset = dialog_rect.top + 25
        for line in lines:
            msg_surf = self.font.render(line, True, self.text_color)
            msg_rect = msg_surf.get_rect(centerx=dialog_rect.centerx, top=y_offset)
            screen.blit(msg_surf, msg_rect)
            y_offset += 25

        # Buttons
        no_rect, yes_rect = self._get_confirm_button_rects()

        # No button
        no_color = self.confirm_no_color if self.confirm_selected == 0 else self.item_color
        pygame.draw.rect(screen, no_color, no_rect, border_radius=5)
        if self.confirm_selected == 0:
            pygame.draw.rect(screen, (180, 100, 100), no_rect, 2, border_radius=5)
        no_text = self.font.render("No", True, self.text_color)
        screen.blit(no_text, no_text.get_rect(center=no_rect.center))

        # Yes button
        yes_color = self.confirm_yes_color if self.confirm_selected == 1 else self.item_color
        pygame.draw.rect(screen, yes_color, yes_rect, border_radius=5)
        if self.confirm_selected == 1:
            pygame.draw.rect(screen, (100, 180, 120), yes_rect, 2, border_radius=5)
        yes_text = self.font.render("Yes", True, self.text_color)
        screen.blit(yes_text, yes_text.get_rect(center=yes_rect.center))

        # Instructions
        inst_text = "A/D to select, E to confirm, ESC to cancel"
        inst_surf = pygame.font.Font(None, 18).render(inst_text, True, (120, 120, 130))
        inst_rect = inst_surf.get_rect(centerx=dialog_rect.centerx, bottom=dialog_rect.bottom - 8)
        screen.blit(inst_surf, inst_rect)
