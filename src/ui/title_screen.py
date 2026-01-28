"""
Title screen - the main menu shown when the game starts.
"""
import pygame
import math


class TitleScreen:
    """
    Title screen with New Game, Load, Settings, and Exit options.
    Supports keyboard (W/S/E) and mouse navigation.
    """

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.is_open = False
        self.selected_index = 0
        self.hovered_index = -1

        # Menu items - "load" will be dynamically enabled/disabled
        self.menu_items = [
            {"id": "new_game", "label": "New Game"},
            {"id": "load", "label": "Load Game"},
            {"id": "settings", "label": "Settings"},
            {"id": "exit", "label": "Exit Game"},
        ]

        # Whether a save exists (controls load option availability)
        self.has_save = False

        # Confirmation dialog state
        self.confirming = False
        self.confirm_action = None
        self.confirm_message = ""
        self.confirm_selected = 0  # 0 = No, 1 = Yes

        # Layout
        self.title_y = 180
        self.menu_start_y = 350
        self.item_width = 260
        self.item_height = 50
        self.item_spacing = 10
        self.menu_x = (screen_width - self.item_width) // 2

        # Colors
        self.bg_color = (15, 18, 25)
        self.title_color = (200, 180, 255)
        self.subtitle_color = (120, 110, 150)
        self.item_color = (35, 40, 55)
        self.item_hover_color = (50, 58, 80)
        self.item_selected_color = (65, 80, 120)
        self.item_disabled_color = (30, 32, 40)
        self.text_color = (210, 210, 220)
        self.text_selected_color = (255, 255, 255)
        self.text_disabled_color = (80, 80, 95)
        self.border_color = (80, 75, 120)
        self.confirm_bg_color = (30, 35, 45)
        self.confirm_border_color = (60, 65, 80)
        self.confirm_yes_color = (60, 120, 80)
        self.confirm_no_color = (120, 60, 60)

        # Fonts
        self.title_font = None
        self.subtitle_font = None
        self.menu_font = None
        self.small_font = None

        # Animation
        self._time = 0.0

    def _init_fonts(self):
        if self.title_font is None:
            pygame.font.init()
            self.title_font = pygame.font.Font(None, 72)
            self.subtitle_font = pygame.font.Font(None, 28)
            self.menu_font = pygame.font.Font(None, 30)
            self.small_font = pygame.font.Font(None, 20)

    def open(self, has_save=False):
        self._init_fonts()
        self.is_open = True
        self.selected_index = 0
        self.hovered_index = -1
        self.has_save = has_save
        self.confirming = False
        self.confirm_action = None
        self._time = 0.0

    def close(self):
        self.is_open = False
        self.confirming = False

    def _is_item_enabled(self, item):
        if item["id"] == "load":
            return self.has_save
        return True

    def _get_item_rect(self, index):
        y = self.menu_start_y + index * (self.item_height + self.item_spacing)
        return pygame.Rect(self.menu_x, y, self.item_width, self.item_height)

    def _get_item_at_position(self, mx, my):
        for i in range(len(self.menu_items)):
            if self._get_item_rect(i).collidepoint(mx, my):
                return i
        return -1

    def handle_input(self, input_handler):
        """
        Handle input. Returns action string or None.
        Actions: "new_game", "new_game_confirmed", "load", "settings", "exit"
        """
        if not self.is_open:
            return None

        mx, my = input_handler.get_mouse_position()

        # Confirmation dialog
        if self.confirming:
            return self._handle_confirm_input(input_handler, mx, my)

        # Mouse hover
        self.hovered_index = self._get_item_at_position(mx, my)

        # Keyboard navigation
        if input_handler.was_key_pressed(pygame.K_w) or input_handler.was_key_pressed(pygame.K_UP):
            self._move_selection(-1)
        if input_handler.was_key_pressed(pygame.K_s) or input_handler.was_key_pressed(pygame.K_DOWN):
            self._move_selection(1)

        # Select
        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            return self._select_current()

        # Mouse click
        if input_handler.mouse_clicked:
            if self.hovered_index >= 0:
                self.selected_index = self.hovered_index
                return self._select_current()

        return None

    def _move_selection(self, direction):
        new_index = self.selected_index
        attempts = 0
        while attempts < len(self.menu_items):
            new_index = (new_index + direction) % len(self.menu_items)
            if self._is_item_enabled(self.menu_items[new_index]):
                self.selected_index = new_index
                break
            attempts += 1

    def _select_current(self):
        item = self.menu_items[self.selected_index]
        if not self._is_item_enabled(item):
            return None

        action_id = item["id"]

        if action_id == "new_game":
            if self.has_save:
                # Confirm - will delete existing save
                self._show_confirmation(
                    "new_game",
                    "Start a new game?\nThis will delete your existing save."
                )
                return None
            else:
                return "new_game_confirmed"

        elif action_id == "load":
            return "load"

        elif action_id == "settings":
            return "settings"

        elif action_id == "exit":
            return "exit"

        return None

    def _show_confirmation(self, action, message):
        self.confirming = True
        self.confirm_action = action
        self.confirm_message = message
        self.confirm_selected = 0

    def _handle_confirm_input(self, input_handler, mx, my):
        if input_handler.was_key_pressed(pygame.K_a) or input_handler.was_key_pressed(pygame.K_LEFT):
            self.confirm_selected = 0
        if input_handler.was_key_pressed(pygame.K_d) or input_handler.was_key_pressed(pygame.K_RIGHT):
            self.confirm_selected = 1

        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            return self._confirm_result()

        if input_handler.cancel:
            self.confirming = False
            return None

        if input_handler.mouse_clicked:
            no_rect, yes_rect = self._get_confirm_button_rects()
            if no_rect.collidepoint(mx, my):
                self.confirm_selected = 0
                return self._confirm_result()
            elif yes_rect.collidepoint(mx, my):
                self.confirm_selected = 1
                return self._confirm_result()

        return None

    def _confirm_result(self):
        if self.confirm_selected == 1:
            action = self.confirm_action
            self.confirming = False
            if action == "new_game":
                return "new_game_confirmed"
        else:
            self.confirming = False
        return None

    def _get_confirm_dialog_rect(self):
        width = 320
        height = 150
        x = (self.screen_width - width) // 2
        y = (self.screen_height - height) // 2
        return pygame.Rect(x, y, width, height)

    def _get_confirm_button_rects(self):
        dialog_rect = self._get_confirm_dialog_rect()
        bw, bh = 80, 35
        by = dialog_rect.bottom - 50
        no_rect = pygame.Rect(dialog_rect.centerx - bw - 10, by, bw, bh)
        yes_rect = pygame.Rect(dialog_rect.centerx + 10, by, bw, bh)
        return no_rect, yes_rect

    def update(self, dt):
        self._time += dt

    def render(self, screen):
        if not self.is_open:
            return

        self._init_fonts()

        # Background
        screen.fill(self.bg_color)

        # Subtle animated background particles
        self._render_background_particles(screen)

        # Title
        title_surf = self.title_font.render("MAGIC ADVENT", True, self.title_color)
        title_rect = title_surf.get_rect(centerx=self.screen_width // 2, centery=self.title_y)
        screen.blit(title_surf, title_rect)

        # Subtitle
        sub_surf = self.subtitle_font.render("A systems-driven magic simulation", True, self.subtitle_color)
        sub_rect = sub_surf.get_rect(centerx=self.screen_width // 2, top=self.title_y + 40)
        screen.blit(sub_surf, sub_rect)

        # Menu items
        for i, item in enumerate(self.menu_items):
            self._render_item(screen, i, item)

        # Controls hint
        hint = "W/S: Navigate   E/Enter: Select"
        hint_surf = self.small_font.render(hint, True, (80, 80, 100))
        hint_rect = hint_surf.get_rect(
            centerx=self.screen_width // 2,
            bottom=self.screen_height - 30
        )
        screen.blit(hint_surf, hint_rect)

        # Confirmation dialog
        if self.confirming:
            self._render_confirmation(screen)

    def _render_background_particles(self, screen):
        """Render subtle floating particles for ambiance."""
        particle_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        for i in range(15):
            x = int((i * 97 + self._time * 8 * (1 + i % 3)) % self.screen_width)
            y = int((i * 73 + self._time * 12 * (1 + i % 2)) % self.screen_height)
            alpha = int(30 + 15 * math.sin(self._time * 2 + i))
            r = 2 + (i % 3)
            pygame.draw.circle(particle_surf, (120, 100, 180, alpha), (x, y), r)
        screen.blit(particle_surf, (0, 0))

    def _render_item(self, screen, index, item):
        rect = self._get_item_rect(index)
        enabled = self._is_item_enabled(item)
        is_selected = index == self.selected_index
        is_hovered = index == self.hovered_index

        if not enabled:
            bg = self.item_disabled_color
        elif is_selected:
            bg = self.item_selected_color
        elif is_hovered:
            bg = self.item_hover_color
        else:
            bg = self.item_color

        pygame.draw.rect(screen, bg, rect, border_radius=6)

        if is_selected and enabled:
            pygame.draw.rect(screen, self.border_color, rect, 2, border_radius=6)

        if not enabled:
            tc = self.text_disabled_color
        elif is_selected:
            tc = self.text_selected_color
        else:
            tc = self.text_color

        label_surf = self.menu_font.render(item["label"], True, tc)
        label_rect = label_surf.get_rect(center=rect.center)
        screen.blit(label_surf, label_rect)

    def _render_confirmation(self, screen):
        # Dim
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        dialog_rect = self._get_confirm_dialog_rect()
        pygame.draw.rect(screen, self.confirm_bg_color, dialog_rect, border_radius=10)
        pygame.draw.rect(screen, self.confirm_border_color, dialog_rect, 2, border_radius=10)

        # Message
        lines = self.confirm_message.split('\n')
        y_offset = dialog_rect.top + 25
        for line in lines:
            msg_surf = self.menu_font.render(line, True, self.text_color)
            msg_rect = msg_surf.get_rect(centerx=dialog_rect.centerx, top=y_offset)
            screen.blit(msg_surf, msg_rect)
            y_offset += 28

        # Buttons
        no_rect, yes_rect = self._get_confirm_button_rects()

        no_color = self.confirm_no_color if self.confirm_selected == 0 else self.item_color
        pygame.draw.rect(screen, no_color, no_rect, border_radius=5)
        if self.confirm_selected == 0:
            pygame.draw.rect(screen, (180, 100, 100), no_rect, 2, border_radius=5)
        no_text = self.menu_font.render("No", True, self.text_color)
        screen.blit(no_text, no_text.get_rect(center=no_rect.center))

        yes_color = self.confirm_yes_color if self.confirm_selected == 1 else self.item_color
        pygame.draw.rect(screen, yes_color, yes_rect, border_radius=5)
        if self.confirm_selected == 1:
            pygame.draw.rect(screen, (100, 180, 120), yes_rect, 2, border_radius=5)
        yes_text = self.menu_font.render("Yes", True, self.text_color)
        screen.blit(yes_text, yes_text.get_rect(center=yes_rect.center))

        inst = "A/D to select, E to confirm, ESC to cancel"
        inst_surf = self.small_font.render(inst, True, (120, 120, 130))
        inst_rect = inst_surf.get_rect(centerx=dialog_rect.centerx, bottom=dialog_rect.bottom - 8)
        screen.blit(inst_surf, inst_rect)
