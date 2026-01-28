"""
Death screen - popup shown when the player dies.
"""
import pygame
import math


class DeathScreen:
    """
    Death popup with Load Last Save and Return to Title options.
    Load option only shown if a save file exists.
    """

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.is_open = False
        self.selected_index = 0
        self.hovered_index = -1
        self.has_save = False

        # Animation
        self._time = 0.0
        self._fade_in = 0.0
        self._fade_duration = 1.0  # seconds to fade in

        # Layout
        self.dialog_width = 360
        self.dialog_height = 280
        self.dialog_x = (screen_width - self.dialog_width) // 2
        self.dialog_y = (screen_height - self.dialog_height) // 2

        self.item_width = 240
        self.item_height = 45
        self.item_spacing = 10

        # Colors
        self.overlay_color = (10, 0, 0)
        self.dialog_bg = (25, 15, 18)
        self.dialog_border = (120, 40, 40)
        self.title_color = (220, 60, 60)
        self.subtitle_color = (160, 120, 120)
        self.item_color = (40, 30, 35)
        self.item_hover_color = (55, 40, 48)
        self.item_selected_color = (75, 45, 55)
        self.item_disabled_color = (30, 25, 28)
        self.text_color = (200, 190, 190)
        self.text_selected_color = (255, 240, 240)
        self.text_disabled_color = (80, 70, 75)
        self.border_color = (140, 60, 70)

        # Fonts
        self.title_font = None
        self.subtitle_font = None
        self.menu_font = None
        self.small_font = None

    def _init_fonts(self):
        if self.title_font is None:
            pygame.font.init()
            self.title_font = pygame.font.Font(None, 64)
            self.subtitle_font = pygame.font.Font(None, 24)
            self.menu_font = pygame.font.Font(None, 28)
            self.small_font = pygame.font.Font(None, 20)

    def open(self, has_save=False):
        self._init_fonts()
        self.is_open = True
        self.has_save = has_save
        self.selected_index = 0 if has_save else 1
        self.hovered_index = -1
        self._time = 0.0
        self._fade_in = 0.0

    def close(self):
        self.is_open = False

    def _get_menu_items(self):
        items = []
        items.append({"id": "load", "label": "Load Last Save", "enabled": self.has_save})
        items.append({"id": "title", "label": "Return to Title", "enabled": True})
        return items

    def _get_item_rect(self, index):
        items = self._get_menu_items()
        total_h = len(items) * (self.item_height + self.item_spacing) - self.item_spacing
        start_y = self.dialog_y + self.dialog_height - 30 - total_h
        x = self.dialog_x + (self.dialog_width - self.item_width) // 2
        y = start_y + index * (self.item_height + self.item_spacing)
        return pygame.Rect(x, y, self.item_width, self.item_height)

    def _get_item_at_position(self, mx, my):
        items = self._get_menu_items()
        for i in range(len(items)):
            if self._get_item_rect(i).collidepoint(mx, my):
                return i
        return -1

    def handle_input(self, input_handler):
        """
        Handle input. Returns action string or None.
        Actions: "load", "title"
        """
        if not self.is_open:
            return None

        # Don't accept input during fade-in
        if self._fade_in < self._fade_duration:
            return None

        items = self._get_menu_items()
        mx, my = input_handler.get_mouse_position()

        self.hovered_index = self._get_item_at_position(mx, my)

        # Keyboard navigation
        if input_handler.was_key_pressed(pygame.K_w) or input_handler.was_key_pressed(pygame.K_UP):
            self._move_selection(-1, items)
        if input_handler.was_key_pressed(pygame.K_s) or input_handler.was_key_pressed(pygame.K_DOWN):
            self._move_selection(1, items)

        # Select
        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            return self._select_current(items)

        if input_handler.mouse_clicked:
            if self.hovered_index >= 0:
                self.selected_index = self.hovered_index
                return self._select_current(items)

        return None

    def _move_selection(self, direction, items):
        new_index = self.selected_index
        attempts = 0
        while attempts < len(items):
            new_index = (new_index + direction) % len(items)
            if items[new_index]["enabled"]:
                self.selected_index = new_index
                break
            attempts += 1

    def _select_current(self, items):
        item = items[self.selected_index]
        if not item["enabled"]:
            return None
        return item["id"]

    def update(self, dt):
        if not self.is_open:
            return
        self._time += dt
        if self._fade_in < self._fade_duration:
            self._fade_in += dt

    def render(self, screen):
        if not self.is_open:
            return

        self._init_fonts()

        # Fade progress (0 to 1)
        fade = min(1.0, self._fade_in / self._fade_duration)

        # Dark red overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        alpha = int(180 * fade)
        overlay.fill(self.overlay_color + (alpha,))
        screen.blit(overlay, (0, 0))

        if fade < 0.3:
            return  # Don't show dialog until overlay is partially visible

        # Dialog fade
        dialog_alpha = min(1.0, (fade - 0.3) / 0.7)

        # Dialog box
        dialog_rect = pygame.Rect(self.dialog_x, self.dialog_y,
                                  self.dialog_width, self.dialog_height)
        dialog_surf = pygame.Surface((self.dialog_width, self.dialog_height), pygame.SRCALPHA)
        bg_a = int(240 * dialog_alpha)
        pygame.draw.rect(dialog_surf, self.dialog_bg + (bg_a,),
                        (0, 0, self.dialog_width, self.dialog_height), border_radius=12)
        border_a = int(255 * dialog_alpha)
        pygame.draw.rect(dialog_surf, self.dialog_border + (border_a,),
                        (0, 0, self.dialog_width, self.dialog_height), 2, border_radius=12)
        screen.blit(dialog_surf, (self.dialog_x, self.dialog_y))

        # "You Died" title
        title_surf = self.title_font.render("You Died", True, self.title_color)
        title_rect = title_surf.get_rect(
            centerx=self.screen_width // 2,
            top=self.dialog_y + 30
        )
        # Apply alpha
        title_alpha_surf = pygame.Surface(title_surf.get_size(), pygame.SRCALPHA)
        title_alpha_surf.blit(title_surf, (0, 0))
        title_alpha_surf.set_alpha(int(255 * dialog_alpha))
        screen.blit(title_alpha_surf, title_rect)

        # Subtitle
        sub_text = "Your journey has come to an end..."
        sub_surf = self.subtitle_font.render(sub_text, True, self.subtitle_color)
        sub_rect = sub_surf.get_rect(
            centerx=self.screen_width // 2,
            top=self.dialog_y + 90
        )
        sub_alpha_surf = pygame.Surface(sub_surf.get_size(), pygame.SRCALPHA)
        sub_alpha_surf.blit(sub_surf, (0, 0))
        sub_alpha_surf.set_alpha(int(255 * dialog_alpha))
        screen.blit(sub_alpha_surf, sub_rect)

        # Menu items (only after full fade)
        if dialog_alpha >= 0.8:
            items = self._get_menu_items()
            for i, item in enumerate(items):
                self._render_item(screen, i, item)

            # Controls hint
            hint = "W/S: Navigate   E/Enter: Select"
            hint_surf = self.small_font.render(hint, True, (80, 65, 70))
            hint_rect = hint_surf.get_rect(
                centerx=self.screen_width // 2,
                bottom=self.dialog_y + self.dialog_height - 8
            )
            screen.blit(hint_surf, hint_rect)

    def _render_item(self, screen, index, item):
        rect = self._get_item_rect(index)
        enabled = item["enabled"]
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

        pygame.draw.rect(screen, bg, rect, border_radius=5)

        if is_selected and enabled:
            pygame.draw.rect(screen, self.border_color, rect, 2, border_radius=5)

        if not enabled:
            tc = self.text_disabled_color
        elif is_selected:
            tc = self.text_selected_color
        else:
            tc = self.text_color

        label_surf = self.menu_font.render(item["label"], True, tc)
        label_rect = label_surf.get_rect(center=rect.center)
        screen.blit(label_surf, label_rect)
