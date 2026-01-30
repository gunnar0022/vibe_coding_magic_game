"""
Inventory UI - simple text-list inventory panel.
Follows GameMenu visual style (same color palette, panel approach).
"""
import pygame


class InventoryUI:
    """
    Text-list inventory panel.
    Arrow keys navigate, Enter equips, Q drops, ESC/TAB/I/close button closes.
    E on consumables prompts for confirmation before use.
    """

    # Modes
    MODE_BROWSE = "browse"
    MODE_CONFIRM_USE = "confirm_use"

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.is_open = False
        self.mode = self.MODE_BROWSE
        self.selected_index = 0
        self.inventory = None  # InventoryComponent reference

        # Confirmation state
        self.pending_item = None  # Item awaiting confirmation
        self.pending_backpack_index = -1
        self.confirm_selected = 0  # 0 = Yes, 1 = No

        # Panel dimensions
        self.panel_width = 350
        self.panel_height = 450
        self.panel_x = (screen_width - self.panel_width) // 2
        self.panel_y = (screen_height - self.panel_height) // 2

        # Close button (top-right of panel)
        self.close_btn_size = 24
        self.close_btn_padding = 8
        self.close_btn_hovered = False

        # Colors (matching GameMenu palette)
        self.bg_color = (25, 28, 35)
        self.border_color = (60, 65, 80)
        self.item_color = (40, 45, 55)
        self.item_selected_color = (70, 90, 130)
        self.item_equipped_color = (40, 70, 50)
        self.text_color = (220, 220, 220)
        self.text_dim_color = (140, 140, 150)
        self.text_selected_color = (255, 255, 255)
        self.equipped_tag_color = (100, 200, 120)
        self.title_color = (220, 220, 220)
        self.close_btn_color = (140, 140, 150)
        self.close_btn_hover_color = (220, 80, 80)
        self.confirm_yes_color = (100, 180, 100)
        self.confirm_no_color = (180, 100, 100)

        # Layout
        self.item_height = 32
        self.header_height = 50
        self.footer_height = 50
        self.scroll_offset = 0

        # Fonts
        self.font = None
        self.title_font = None
        self.small_font = None

    def _init_fonts(self):
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 24)
            self.title_font = pygame.font.Font(None, 30)
            self.small_font = pygame.font.Font(None, 20)

    def open(self, inventory):
        self._init_fonts()
        self.is_open = True
        self.mode = self.MODE_BROWSE
        self.inventory = inventory
        self.selected_index = 0
        self.scroll_offset = 0
        self._clear_confirmation()

    def close(self):
        self.is_open = False
        self.mode = self.MODE_BROWSE
        self.inventory = None
        self._clear_confirmation()

    def _clear_confirmation(self):
        """Clear confirmation state."""
        self.pending_item = None
        self.pending_backpack_index = -1
        self.confirm_selected = 0

    def handle_back(self):
        """
        Handle a back action (Tab/Esc from game.py).
        Returns True if handled internally (should stay open), False if should close.
        """
        if self.mode == self.MODE_CONFIRM_USE:
            # Exit confirmation mode, return to browse
            self._clear_confirmation()
            self.mode = self.MODE_BROWSE
            return True  # Stay open
        return False  # Should close

    def toggle(self, inventory):
        if self.is_open:
            self.close()
        else:
            self.open(inventory)

    def _get_close_btn_rect(self):
        """Get the close button rect (top-right corner of panel)."""
        x = self.panel_x + self.panel_width - self.close_btn_size - self.close_btn_padding
        y = self.panel_y + self.close_btn_padding
        return pygame.Rect(x, y, self.close_btn_size, self.close_btn_size)

    def _build_item_list(self):
        """Build display list: equipped weapon first, then backpack items."""
        items = []
        if self.inventory is None:
            return items

        # Equipped weapon first
        if self.inventory.equipped_weapon is not None:
            items.append({"item": self.inventory.equipped_weapon, "equipped": True, "backpack_index": -1})

        # Backpack items
        for i, item in enumerate(self.inventory.items):
            items.append({"item": item, "equipped": False, "backpack_index": i})

        return items

    def handle_input(self, input_handler):
        """
        Handle input. Returns action dict or None.
        Actions: {"type": "equip"|"drop"|"use"|"close", "item": ItemInstance, ...}
        """
        if not self.is_open:
            return None

        # Update close button hover state
        mx, my = input_handler.get_mouse_position()
        self.close_btn_hovered = self._get_close_btn_rect().collidepoint(mx, my)

        # Close button click (works in any mode)
        if input_handler.mouse_clicked and self.close_btn_hovered:
            self.close()
            return {"type": "close"}

        # Handle confirmation mode
        if self.mode == self.MODE_CONFIRM_USE:
            return self._handle_confirm_input(input_handler)

        # Browse mode
        return self._handle_browse_input(input_handler)

    def _handle_browse_input(self, input_handler):
        """Handle input in browse mode."""
        items = self._build_item_list()
        item_count = len(items)

        # Navigation
        if input_handler.was_key_pressed(pygame.K_UP) or input_handler.was_key_pressed(pygame.K_w):
            if item_count > 0:
                self.selected_index = (self.selected_index - 1) % item_count
                self._ensure_visible()
        if input_handler.was_key_pressed(pygame.K_DOWN) or input_handler.was_key_pressed(pygame.K_s):
            if item_count > 0:
                self.selected_index = (self.selected_index + 1) % item_count
                self._ensure_visible()

        # Use consumable (E key) - opens confirmation dialog
        if input_handler.was_key_pressed(pygame.K_e):
            if 0 <= self.selected_index < item_count:
                entry = items[self.selected_index]
                if entry["item"].is_consumable:
                    # Enter confirmation mode
                    self.pending_item = entry["item"]
                    self.pending_backpack_index = entry["backpack_index"]
                    self.confirm_selected = 0  # Default to Yes
                    self.mode = self.MODE_CONFIRM_USE
                    return None

        # Equip / Stow / Unstow (Enter)
        if input_handler.was_key_pressed(pygame.K_RETURN):
            if 0 <= self.selected_index < item_count:
                entry = items[self.selected_index]
                if entry["equipped"] and entry["item"].is_weapon:
                    # Stow equipped weapon into backpack
                    return {"type": "stow", "item": entry["item"], "equipped": True,
                            "backpack_index": entry["backpack_index"]}
                elif not entry["equipped"] and entry["item"].is_weapon:
                    # Unstow weapon from backpack to hands
                    return {"type": "unstow", "item": entry["item"], "equipped": False,
                            "backpack_index": entry["backpack_index"]}
                else:
                    return {"type": "equip", "item": entry["item"], "equipped": entry["equipped"],
                            "backpack_index": entry["backpack_index"]}

        # Drop (Q)
        if input_handler.was_key_pressed(pygame.K_q):
            if 0 <= self.selected_index < item_count:
                entry = items[self.selected_index]
                return {"type": "drop", "item": entry["item"], "equipped": entry["equipped"],
                        "backpack_index": entry["backpack_index"]}

        # Close (I key only - ESC and TAB are handled by game.py before reaching here)
        if input_handler.was_key_pressed(pygame.K_i):
            self.close()
            return {"type": "close"}

        return None

    def _handle_confirm_input(self, input_handler):
        """Handle input in confirmation mode."""
        # Navigate between Yes/No
        if (input_handler.was_key_pressed(pygame.K_LEFT) or
            input_handler.was_key_pressed(pygame.K_a) or
            input_handler.was_key_pressed(pygame.K_UP) or
            input_handler.was_key_pressed(pygame.K_w)):
            self.confirm_selected = 0  # Yes
        if (input_handler.was_key_pressed(pygame.K_RIGHT) or
            input_handler.was_key_pressed(pygame.K_d) or
            input_handler.was_key_pressed(pygame.K_DOWN) or
            input_handler.was_key_pressed(pygame.K_s)):
            self.confirm_selected = 1  # No

        # Confirm selection (E or Enter)
        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            if self.confirm_selected == 0:  # Yes
                # Use the item
                item = self.pending_item
                backpack_index = self.pending_backpack_index
                self._clear_confirmation()
                self.mode = self.MODE_BROWSE
                return {"type": "use", "item": item, "equipped": False,
                        "backpack_index": backpack_index}
            else:  # No
                self._clear_confirmation()
                self.mode = self.MODE_BROWSE
                return None

        # Cancel (Tab, Escape handled by game.py, but also allow direct cancel here)
        if input_handler.was_key_pressed(pygame.K_i):
            self._clear_confirmation()
            self.mode = self.MODE_BROWSE
            return None

        return None

    def _ensure_visible(self):
        """Ensure selected item is visible in scrollable area."""
        visible_count = self._get_visible_count()
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + visible_count:
            self.scroll_offset = self.selected_index - visible_count + 1

    def _get_visible_count(self):
        """Number of items visible in the list area."""
        list_height = self.panel_height - self.header_height - self.footer_height
        return max(1, list_height // self.item_height)

    def render(self, screen):
        if not self.is_open or self.inventory is None:
            return

        self._init_fonts()
        items = self._build_item_list()

        # Dim background
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        # Panel background
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        pygame.draw.rect(screen, self.bg_color, panel_rect, border_radius=8)
        pygame.draw.rect(screen, self.border_color, panel_rect, 2, border_radius=8)

        # Close button (X) in top-right
        close_rect = self._get_close_btn_rect()
        btn_color = self.close_btn_hover_color if self.close_btn_hovered else self.close_btn_color
        # Draw X lines
        margin = 6
        pygame.draw.line(screen, btn_color,
                         (close_rect.left + margin, close_rect.top + margin),
                         (close_rect.right - margin, close_rect.bottom - margin), 2)
        pygame.draw.line(screen, btn_color,
                         (close_rect.right - margin, close_rect.top + margin),
                         (close_rect.left + margin, close_rect.bottom - margin), 2)

        # Title
        title_surf = self.title_font.render("INVENTORY", True, self.title_color)
        title_rect = title_surf.get_rect(centerx=panel_rect.centerx, top=panel_rect.top + 12)
        screen.blit(title_surf, title_rect)

        # Controls hint
        hint_text = "W/S: Nav | Enter: Stow/Equip | E: Use | Q: Drop | I/ESC: Close"
        hint_surf = self.small_font.render(hint_text, True, self.text_dim_color)
        hint_rect = hint_surf.get_rect(centerx=panel_rect.centerx, top=panel_rect.top + 36)
        screen.blit(hint_surf, hint_rect)

        # Item list area
        list_y = self.panel_y + self.header_height
        visible_count = self._get_visible_count()

        if not items:
            empty_surf = self.font.render("Inventory is empty", True, self.text_dim_color)
            empty_rect = empty_surf.get_rect(centerx=panel_rect.centerx,
                                              centery=self.panel_y + self.panel_height // 2)
            screen.blit(empty_surf, empty_rect)
        else:
            end_idx = min(self.scroll_offset + visible_count, len(items))
            for draw_i, item_i in enumerate(range(self.scroll_offset, end_idx)):
                entry = items[item_i]
                y = list_y + draw_i * self.item_height
                self._render_item_row(screen, entry, y, item_i == self.selected_index)

        # Footer: item count
        count_text = f"{len(self.inventory.items)}/{self.inventory.capacity}"
        if self.inventory.equipped_weapon:
            count_text = f"Equipped + {count_text}"
        count_surf = self.small_font.render(count_text, True, self.text_dim_color)
        count_rect = count_surf.get_rect(right=panel_rect.right - 15,
                                          bottom=panel_rect.bottom - 12)
        screen.blit(count_surf, count_rect)

        # Render confirmation dialog on top if in confirm mode
        if self.mode == self.MODE_CONFIRM_USE and self.pending_item:
            self._render_confirmation_dialog(screen, panel_rect)

    def _render_item_row(self, screen, entry, y, is_selected):
        item = entry["item"]
        is_equipped = entry["equipped"]

        row_rect = pygame.Rect(self.panel_x + 10, y, self.panel_width - 20, self.item_height - 2)

        # Background
        if is_selected:
            bg = self.item_selected_color
        elif is_equipped:
            bg = self.item_equipped_color
        else:
            bg = self.item_color
        pygame.draw.rect(screen, bg, row_rect, border_radius=4)

        if is_selected:
            pygame.draw.rect(screen, (100, 140, 200), row_rect, 2, border_radius=4)

        # Text color
        text_color = self.text_selected_color if is_selected else self.text_color

        # Build label
        label = ""
        if is_equipped:
            label = "[E] "
        elif item.is_weapon:
            label = "[S] "
        label += item.name
        if item.stackable and item.quantity > 1:
            label += f" x{item.quantity}"

        label_surf = self.font.render(label, True, text_color)
        screen.blit(label_surf, (row_rect.left + 8, row_rect.centery - label_surf.get_height() // 2))

        # Item stats on right side
        stats_text = None
        if item.is_weapon:
            stats_text = f"DMG:{item.damage} CD:{item.cooldown}s"
        elif item.is_consumable:
            if item.effect_type == "heal_health":
                stats_text = f"+{item.effect_amount} HP"
            elif item.effect_type == "heal_mana":
                stats_text = f"+{item.effect_amount} MP"
            else:
                stats_text = "Use"
        elif item.sell_price > 0:
            stats_text = f"Sell: {item.sell_price}g"

        if stats_text:
            stats_surf = self.small_font.render(stats_text, True, self.text_dim_color)
            screen.blit(stats_surf, (row_rect.right - stats_surf.get_width() - 8,
                                      row_rect.centery - stats_surf.get_height() // 2))

    def _render_confirmation_dialog(self, screen, panel_rect):
        """Render the use item confirmation dialog overlay."""
        # Semi-transparent overlay on top of inventory panel
        dialog_overlay = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        dialog_overlay.fill((0, 0, 0, 180))
        screen.blit(dialog_overlay, (panel_rect.left, panel_rect.top))

        # Dialog box dimensions
        dialog_width = 280
        dialog_height = 120
        dialog_x = panel_rect.centerx - dialog_width // 2
        dialog_y = panel_rect.centery - dialog_height // 2

        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)

        # Dialog background
        pygame.draw.rect(screen, self.bg_color, dialog_rect, border_radius=8)
        pygame.draw.rect(screen, (100, 110, 130), dialog_rect, 2, border_radius=8)

        # Question text
        item_name = self.pending_item.name if self.pending_item else "item"
        question = f"Use {item_name}?"
        question_surf = self.font.render(question, True, self.text_color)
        question_rect = question_surf.get_rect(centerx=dialog_rect.centerx, top=dialog_rect.top + 20)
        screen.blit(question_surf, question_rect)

        # Effect preview
        effect_text = ""
        if self.pending_item:
            if self.pending_item.effect_type == "heal_health":
                effect_text = f"(Restores {self.pending_item.effect_amount} HP)"
            elif self.pending_item.effect_type == "heal_mana":
                effect_text = f"(Restores {self.pending_item.effect_amount} MP)"
        if effect_text:
            effect_surf = self.small_font.render(effect_text, True, self.text_dim_color)
            effect_rect = effect_surf.get_rect(centerx=dialog_rect.centerx, top=question_rect.bottom + 5)
            screen.blit(effect_surf, effect_rect)

        # Yes/No buttons
        button_width = 80
        button_height = 32
        button_y = dialog_rect.bottom - button_height - 15
        yes_x = dialog_rect.centerx - button_width - 15
        no_x = dialog_rect.centerx + 15

        # Yes button
        yes_rect = pygame.Rect(yes_x, button_y, button_width, button_height)
        yes_bg = self.confirm_yes_color if self.confirm_selected == 0 else self.item_color
        pygame.draw.rect(screen, yes_bg, yes_rect, border_radius=4)
        if self.confirm_selected == 0:
            pygame.draw.rect(screen, (150, 220, 150), yes_rect, 2, border_radius=4)
        yes_text = self.font.render("Yes", True, self.text_color)
        yes_text_rect = yes_text.get_rect(center=yes_rect.center)
        screen.blit(yes_text, yes_text_rect)

        # No button
        no_rect = pygame.Rect(no_x, button_y, button_width, button_height)
        no_bg = self.confirm_no_color if self.confirm_selected == 1 else self.item_color
        pygame.draw.rect(screen, no_bg, no_rect, border_radius=4)
        if self.confirm_selected == 1:
            pygame.draw.rect(screen, (220, 150, 150), no_rect, 2, border_radius=4)
        no_text = self.font.render("No", True, self.text_color)
        no_text_rect = no_text.get_rect(center=no_rect.center)
        screen.blit(no_text, no_text_rect)

        # Controls hint
        hint = "A/D: Select | E: Confirm"
        hint_surf = self.small_font.render(hint, True, self.text_dim_color)
        hint_rect = hint_surf.get_rect(centerx=dialog_rect.centerx, bottom=dialog_rect.bottom - 3)
        screen.blit(hint_surf, hint_rect)
