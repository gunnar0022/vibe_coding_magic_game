"""
Shop UI - handles merchant buy/sell interface.
Two modes: browse merchant wares (buy) and browse player inventory (sell).
Each has a quantity sub-mode for selecting how many to buy/sell.
"""
import pygame
from ..items.item_instance import ItemInstance
from ..items.item_defs import ITEM_DEFS


class ShopUI:
    """
    Shop interface for buying and selling items.
    Modes: 'menu' (main options), 'buy' (browse wares), 'buy_qty' (select quantity),
           'sell' (browse inventory), 'sell_qty' (select quantity)
    """

    MODE_MENU = "menu"
    MODE_BUY = "buy"
    MODE_BUY_QTY = "buy_qty"
    MODE_SELL = "sell"
    MODE_SELL_QTY = "sell_qty"

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.is_open = False
        self.mode = self.MODE_MENU
        self.merchant_npc = None
        self.player_inventory = None
        self.player_gold = 0

        # Selection state
        self.menu_index = 0  # For main menu
        self.item_index = 0  # For buy/sell lists
        self.quantity = 1
        self.scroll_offset = 0

        # Panel dimensions
        self.panel_width = 400
        self.panel_height = 500
        self.panel_x = (screen_width - self.panel_width) // 2
        self.panel_y = (screen_height - self.panel_height) // 2

        # Colors
        self.bg_color = (30, 28, 35)
        self.border_color = (80, 70, 60)
        self.item_color = (45, 42, 50)
        self.item_selected_color = (70, 90, 130)
        self.text_color = (220, 220, 220)
        self.text_dim_color = (140, 140, 150)
        self.gold_color = (220, 180, 60)
        self.buy_color = (100, 180, 100)
        self.sell_color = (180, 140, 100)
        self.close_btn_color = (140, 140, 150)
        self.close_btn_hover_color = (220, 80, 80)

        # Layout
        self.item_height = 36
        self.header_height = 80
        self.footer_height = 100

        # Fonts
        self.font = None
        self.title_font = None
        self.small_font = None

        # Close button
        self.close_btn_size = 24
        self.close_btn_padding = 8
        self.close_btn_hovered = False

        # Menu options
        self.menu_options = [
            {"label": "See Wares", "action": "buy"},
            {"label": "Sell Items", "action": "sell"},
            {"label": "Chat", "action": "chat"},
            {"label": "Leave", "action": "leave"},
        ]

        # Callback for closing
        self.on_close_callback = None

    def _init_fonts(self):
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 24)
            self.title_font = pygame.font.Font(None, 32)
            self.small_font = pygame.font.Font(None, 20)

    def open(self, merchant_npc, player_inventory, player_gold, on_close=None):
        """Open shop with a merchant."""
        self._init_fonts()
        self.is_open = True
        self.mode = self.MODE_MENU
        self.merchant_npc = merchant_npc
        self.player_inventory = player_inventory
        self.player_gold = player_gold
        self.menu_index = 0
        self.item_index = 0
        self.quantity = 1
        self.scroll_offset = 0
        self.on_close_callback = on_close

    def close(self):
        """Close the shop UI."""
        self.is_open = False
        if self.on_close_callback:
            self.on_close_callback()
        self.merchant_npc = None
        self.player_inventory = None

    def _get_close_btn_rect(self):
        x = self.panel_x + self.panel_width - self.close_btn_size - self.close_btn_padding
        y = self.panel_y + self.close_btn_padding
        return pygame.Rect(x, y, self.close_btn_size, self.close_btn_size)

    def _get_merchant_items(self):
        """Get list of items the merchant sells."""
        if not self.merchant_npc:
            return []
        # Build ItemInstance list from trade_inventory
        items = []
        trade_inv = getattr(self.merchant_npc, 'trade_inventory', [])
        for entry in trade_inv:
            if isinstance(entry, dict):
                item_id = entry.get("item_id")
                stock = entry.get("stock", 99)
                if item_id and item_id in ITEM_DEFS:
                    items.append({"item_id": item_id, "stock": stock})
            elif isinstance(entry, str) and entry in ITEM_DEFS:
                items.append({"item_id": entry, "stock": 99})
        return items

    def _get_sellable_items(self):
        """Get list of player items that can be sold."""
        if not self.player_inventory:
            return []
        items = []
        for i, item in enumerate(self.player_inventory.items):
            if item.sell_price > 0:
                items.append({"item": item, "index": i})
        return items

    def _max_affordable(self, item_id):
        """How many of this item can the player afford?"""
        item_def = ITEM_DEFS.get(item_id, {})
        price = item_def.get("buy_price", 0)
        if price <= 0:
            return 0
        return self.player_gold // price

    def handle_input(self, input_handler):
        """
        Handle input. Returns action dict or None.
        Actions: {"type": "buy"|"sell"|"chat"|"close", ...}
        """
        if not self.is_open:
            return None

        # Update close button hover state
        mx, my = input_handler.get_mouse_position()
        self.close_btn_hovered = self._get_close_btn_rect().collidepoint(mx, my)

        # Close button click
        if input_handler.mouse_clicked and self.close_btn_hovered:
            self.close()
            return {"type": "close"}

        # Escape/Tab/X to go back or close
        if (input_handler.was_key_pressed(pygame.K_ESCAPE) or
            input_handler.was_key_pressed(pygame.K_TAB) or
            input_handler.was_key_pressed(pygame.K_x)):
            return self._handle_back()

        if self.mode == self.MODE_MENU:
            return self._handle_menu_input(input_handler)
        elif self.mode == self.MODE_BUY:
            return self._handle_buy_input(input_handler)
        elif self.mode == self.MODE_BUY_QTY:
            return self._handle_buy_qty_input(input_handler)
        elif self.mode == self.MODE_SELL:
            return self._handle_sell_input(input_handler)
        elif self.mode == self.MODE_SELL_QTY:
            return self._handle_sell_qty_input(input_handler)

        return None

    def _handle_back(self):
        """Handle back navigation. Returns action dict or None."""
        if self.mode == self.MODE_MENU:
            self.close()
            return {"type": "close"}
        elif self.mode == self.MODE_BUY_QTY:
            # Go back to buy browse
            self.mode = self.MODE_BUY
            return None
        elif self.mode == self.MODE_SELL_QTY:
            # Go back to sell browse
            self.mode = self.MODE_SELL
            return None
        else:
            # Go back to menu from buy/sell browse
            self.mode = self.MODE_MENU
            self.menu_index = 0
            return None

    def _handle_menu_input(self, input_handler):
        """Handle main menu input."""
        # Navigation
        if input_handler.was_key_pressed(pygame.K_UP) or input_handler.was_key_pressed(pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(self.menu_options)
        if input_handler.was_key_pressed(pygame.K_DOWN) or input_handler.was_key_pressed(pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(self.menu_options)

        # Select
        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            option = self.menu_options[self.menu_index]
            action = option["action"]

            if action == "buy":
                self.mode = self.MODE_BUY
                self.item_index = 0
                self.scroll_offset = 0
            elif action == "sell":
                self.mode = self.MODE_SELL
                self.item_index = 0
                self.scroll_offset = 0
            elif action == "chat":
                return {"type": "chat"}
            elif action == "leave":
                self.close()
                return {"type": "close"}

        return None

    def _handle_buy_input(self, input_handler):
        """Handle buy browse mode input."""
        items = self._get_merchant_items()
        if not items:
            return None

        item_count = len(items)

        # Item navigation
        if input_handler.was_key_pressed(pygame.K_UP) or input_handler.was_key_pressed(pygame.K_w):
            self.item_index = (self.item_index - 1) % item_count
            self._ensure_visible(item_count)
        if input_handler.was_key_pressed(pygame.K_DOWN) or input_handler.was_key_pressed(pygame.K_s):
            self.item_index = (self.item_index + 1) % item_count
            self._ensure_visible(item_count)

        # Select item to enter quantity mode (E or Enter)
        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            if self.item_index < item_count:
                current_item = items[self.item_index]
                max_qty = self._max_affordable(current_item["item_id"])
                max_qty = min(max_qty, current_item["stock"])
                if max_qty > 0:
                    self.quantity = 1
                    self.mode = self.MODE_BUY_QTY
                # If can't afford any, do nothing

        return None

    def _handle_buy_qty_input(self, input_handler):
        """Handle buy quantity selection input."""
        items = self._get_merchant_items()
        if not items or self.item_index >= len(items):
            self.mode = self.MODE_BUY
            return None

        current_item = items[self.item_index]
        max_qty = self._max_affordable(current_item["item_id"])
        max_qty = min(max_qty, current_item["stock"])

        # Quantity adjustment (W/S or Up/Down)
        if input_handler.was_key_pressed(pygame.K_UP) or input_handler.was_key_pressed(pygame.K_w):
            self.quantity = min(self.quantity + 1, max_qty)
        if input_handler.was_key_pressed(pygame.K_DOWN) or input_handler.was_key_pressed(pygame.K_s):
            self.quantity = max(1, self.quantity - 1)

        # Larger adjustments (A/D or Left/Right for +/- 10)
        if input_handler.was_key_pressed(pygame.K_LEFT) or input_handler.was_key_pressed(pygame.K_a):
            self.quantity = max(1, self.quantity - 10)
        if input_handler.was_key_pressed(pygame.K_RIGHT) or input_handler.was_key_pressed(pygame.K_d):
            self.quantity = min(self.quantity + 10, max_qty)

        # Confirm purchase (E or Enter)
        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            if self.quantity > 0:
                item_def = ITEM_DEFS.get(current_item["item_id"], {})
                total_cost = item_def.get("buy_price", 0) * self.quantity
                # Return to browse mode after purchase
                self.mode = self.MODE_BUY
                return {
                    "type": "buy",
                    "item_id": current_item["item_id"],
                    "quantity": self.quantity,
                    "total_cost": total_cost
                }

        return None

    def _handle_sell_input(self, input_handler):
        """Handle sell browse mode input."""
        items = self._get_sellable_items()
        if not items:
            return None

        item_count = len(items)

        # Item navigation
        if input_handler.was_key_pressed(pygame.K_UP) or input_handler.was_key_pressed(pygame.K_w):
            self.item_index = (self.item_index - 1) % item_count
            self._ensure_visible(item_count)
        if input_handler.was_key_pressed(pygame.K_DOWN) or input_handler.was_key_pressed(pygame.K_s):
            self.item_index = (self.item_index + 1) % item_count
            self._ensure_visible(item_count)

        # Select item to enter quantity mode (E or Enter)
        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            if self.item_index < item_count:
                self.quantity = 1
                self.mode = self.MODE_SELL_QTY

        return None

    def _handle_sell_qty_input(self, input_handler):
        """Handle sell quantity selection input."""
        items = self._get_sellable_items()
        if not items or self.item_index >= len(items):
            self.mode = self.MODE_SELL
            return None

        current_entry = items[self.item_index]
        max_qty = current_entry["item"].quantity

        # Quantity adjustment (W/S or Up/Down)
        if input_handler.was_key_pressed(pygame.K_UP) or input_handler.was_key_pressed(pygame.K_w):
            self.quantity = min(self.quantity + 1, max_qty)
        if input_handler.was_key_pressed(pygame.K_DOWN) or input_handler.was_key_pressed(pygame.K_s):
            self.quantity = max(1, self.quantity - 1)

        # Larger adjustments (A/D or Left/Right for +/- 10)
        if input_handler.was_key_pressed(pygame.K_LEFT) or input_handler.was_key_pressed(pygame.K_a):
            self.quantity = max(1, self.quantity - 10)
        if input_handler.was_key_pressed(pygame.K_RIGHT) or input_handler.was_key_pressed(pygame.K_d):
            self.quantity = min(self.quantity + 10, max_qty)

        # Confirm sale (E or Enter)
        if input_handler.was_key_pressed(pygame.K_e) or input_handler.was_key_pressed(pygame.K_RETURN):
            if self.quantity > 0:
                item = current_entry["item"]
                total_value = item.sell_price * self.quantity
                # Return to browse mode after sale
                self.mode = self.MODE_SELL
                return {
                    "type": "sell",
                    "backpack_index": current_entry["index"],
                    "quantity": self.quantity,
                    "total_value": total_value
                }

        return None

    def _ensure_visible(self, item_count):
        """Ensure selected item is visible in scrollable area."""
        visible_count = self._get_visible_count()
        if self.item_index < self.scroll_offset:
            self.scroll_offset = self.item_index
        elif self.item_index >= self.scroll_offset + visible_count:
            self.scroll_offset = self.item_index - visible_count + 1

    def _get_visible_count(self):
        """Number of items visible in the list area."""
        list_height = self.panel_height - self.header_height - self.footer_height
        return max(1, list_height // self.item_height)

    def update_gold(self, gold):
        """Update player gold display."""
        self.player_gold = gold

    def render(self, screen):
        if not self.is_open:
            return

        self._init_fonts()

        # Dim background
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))

        # Panel background
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        pygame.draw.rect(screen, self.bg_color, panel_rect, border_radius=8)
        pygame.draw.rect(screen, self.border_color, panel_rect, 2, border_radius=8)

        # Close button (X)
        close_rect = self._get_close_btn_rect()
        btn_color = self.close_btn_hover_color if self.close_btn_hovered else self.close_btn_color
        margin = 6
        pygame.draw.line(screen, btn_color,
                         (close_rect.left + margin, close_rect.top + margin),
                         (close_rect.right - margin, close_rect.bottom - margin), 2)
        pygame.draw.line(screen, btn_color,
                         (close_rect.right - margin, close_rect.top + margin),
                         (close_rect.left + margin, close_rect.bottom - margin), 2)

        # Title
        merchant_name = self.merchant_npc.name if self.merchant_npc else "Shop"
        title_surf = self.title_font.render(merchant_name + "'s Shop", True, self.text_color)
        title_rect = title_surf.get_rect(centerx=panel_rect.centerx, top=panel_rect.top + 12)
        screen.blit(title_surf, title_rect)

        # Gold display
        gold_surf = self.font.render(f"Gold: {self.player_gold}", True, self.gold_color)
        gold_rect = gold_surf.get_rect(centerx=panel_rect.centerx, top=panel_rect.top + 45)
        screen.blit(gold_surf, gold_rect)

        # Mode-specific rendering
        if self.mode == self.MODE_MENU:
            self._render_menu(screen, panel_rect)
        elif self.mode == self.MODE_BUY:
            self._render_buy(screen, panel_rect)
        elif self.mode == self.MODE_BUY_QTY:
            self._render_buy_qty(screen, panel_rect)
        elif self.mode == self.MODE_SELL:
            self._render_sell(screen, panel_rect)
        elif self.mode == self.MODE_SELL_QTY:
            self._render_sell_qty(screen, panel_rect)

    def _render_menu(self, screen, panel_rect):
        """Render main menu options."""
        start_y = self.panel_y + self.header_height + 20

        for i, option in enumerate(self.menu_options):
            y = start_y + i * 45
            is_selected = (i == self.menu_index)

            # Option background
            opt_rect = pygame.Rect(self.panel_x + 40, y, self.panel_width - 80, 38)
            bg = self.item_selected_color if is_selected else self.item_color
            pygame.draw.rect(screen, bg, opt_rect, border_radius=4)
            if is_selected:
                pygame.draw.rect(screen, (100, 140, 200), opt_rect, 2, border_radius=4)

            # Option text
            text_color = (255, 255, 255) if is_selected else self.text_color
            label_surf = self.font.render(option["label"], True, text_color)
            screen.blit(label_surf, (opt_rect.left + 15, opt_rect.centery - label_surf.get_height() // 2))

        # Controls hint
        hint = "W/S: Navigate | E: Select | Tab/Esc: Close"
        hint_surf = self.small_font.render(hint, True, self.text_dim_color)
        hint_rect = hint_surf.get_rect(centerx=panel_rect.centerx, bottom=panel_rect.bottom - 15)
        screen.blit(hint_surf, hint_rect)

    def _render_buy(self, screen, panel_rect):
        """Render buy browse mode (merchant wares)."""
        items = self._get_merchant_items()
        list_y = self.panel_y + self.header_height

        # Mode label
        mode_surf = self.font.render("- Merchant Wares -", True, self.buy_color)
        mode_rect = mode_surf.get_rect(centerx=panel_rect.centerx, top=list_y - 20)
        screen.blit(mode_surf, mode_rect)

        if not items:
            empty_surf = self.font.render("No items for sale", True, self.text_dim_color)
            empty_rect = empty_surf.get_rect(centerx=panel_rect.centerx,
                                              centery=self.panel_y + self.panel_height // 2)
            screen.blit(empty_surf, empty_rect)
        else:
            visible_count = self._get_visible_count()
            end_idx = min(self.scroll_offset + visible_count, len(items))

            for draw_i, item_i in enumerate(range(self.scroll_offset, end_idx)):
                y = list_y + draw_i * self.item_height
                self._render_buy_item(screen, items[item_i], y, item_i == self.item_index)

        # Controls hint
        hint = "W/S: Browse | E: Select | Tab: Back"
        hint_surf = self.small_font.render(hint, True, self.text_dim_color)
        hint_rect = hint_surf.get_rect(centerx=panel_rect.centerx, bottom=panel_rect.bottom - 15)
        screen.blit(hint_surf, hint_rect)

    def _render_buy_qty(self, screen, panel_rect):
        """Render buy quantity selection mode."""
        items = self._get_merchant_items()
        if not items or self.item_index >= len(items):
            return

        current = items[self.item_index]
        item_def = ITEM_DEFS.get(current["item_id"], {})
        item_name = item_def.get("name", current["item_id"])
        price = item_def.get("buy_price", 0)
        max_qty = self._max_affordable(current["item_id"])
        max_qty = min(max_qty, current["stock"])
        total = price * self.quantity

        # Mode label
        list_y = self.panel_y + self.header_height
        mode_surf = self.font.render("- Select Quantity -", True, self.buy_color)
        mode_rect = mode_surf.get_rect(centerx=panel_rect.centerx, top=list_y - 20)
        screen.blit(mode_surf, mode_rect)

        # Item name
        center_y = self.panel_y + self.panel_height // 2 - 40
        name_surf = self.title_font.render(item_name, True, self.text_color)
        name_rect = name_surf.get_rect(centerx=panel_rect.centerx, top=center_y)
        screen.blit(name_surf, name_rect)

        # Price per item
        price_surf = self.font.render(f"{price}g each", True, self.gold_color)
        price_rect = price_surf.get_rect(centerx=panel_rect.centerx, top=center_y + 35)
        screen.blit(price_surf, price_rect)

        # Quantity selector
        qty_text = f"< {self.quantity} / {max_qty} >"
        qty_surf = self.title_font.render(qty_text, True, self.text_color)
        qty_rect = qty_surf.get_rect(centerx=panel_rect.centerx, top=center_y + 75)
        screen.blit(qty_surf, qty_rect)

        # Total cost
        total_surf = self.font.render(f"Total: {total}g", True, self.gold_color)
        total_rect = total_surf.get_rect(centerx=panel_rect.centerx, top=center_y + 115)
        screen.blit(total_surf, total_rect)

        # Controls hint
        hint = "W/S: +/- 1 | A/D: +/- 10 | E: Confirm | Tab: Back"
        hint_surf = self.small_font.render(hint, True, self.text_dim_color)
        hint_rect = hint_surf.get_rect(centerx=panel_rect.centerx, bottom=panel_rect.bottom - 15)
        screen.blit(hint_surf, hint_rect)

    def _render_buy_item(self, screen, item_data, y, is_selected):
        """Render a single buy item row."""
        item_id = item_data["item_id"]
        item_def = ITEM_DEFS.get(item_id, {})
        name = item_def.get("name", item_id)
        price = item_def.get("buy_price", 0)
        stock = item_data.get("stock", 99)

        row_rect = pygame.Rect(self.panel_x + 10, y, self.panel_width - 20, self.item_height - 2)

        # Background
        bg = self.item_selected_color if is_selected else self.item_color
        pygame.draw.rect(screen, bg, row_rect, border_radius=4)
        if is_selected:
            pygame.draw.rect(screen, (100, 140, 200), row_rect, 2, border_radius=4)

        # Item name
        text_color = (255, 255, 255) if is_selected else self.text_color
        name_surf = self.font.render(name, True, text_color)
        screen.blit(name_surf, (row_rect.left + 10, row_rect.centery - name_surf.get_height() // 2))

        # Price
        price_text = f"{price}g"
        if stock < 99:
            price_text += f" (x{stock})"
        price_surf = self.small_font.render(price_text, True, self.gold_color)
        screen.blit(price_surf, (row_rect.right - price_surf.get_width() - 10,
                                  row_rect.centery - price_surf.get_height() // 2))

    def _render_sell(self, screen, panel_rect):
        """Render sell browse mode (player inventory)."""
        items = self._get_sellable_items()
        list_y = self.panel_y + self.header_height

        # Mode label
        mode_surf = self.font.render("- Your Items -", True, self.sell_color)
        mode_rect = mode_surf.get_rect(centerx=panel_rect.centerx, top=list_y - 20)
        screen.blit(mode_surf, mode_rect)

        if not items:
            empty_surf = self.font.render("Nothing to sell", True, self.text_dim_color)
            empty_rect = empty_surf.get_rect(centerx=panel_rect.centerx,
                                              centery=self.panel_y + self.panel_height // 2)
            screen.blit(empty_surf, empty_rect)
        else:
            visible_count = self._get_visible_count()
            end_idx = min(self.scroll_offset + visible_count, len(items))

            for draw_i, item_i in enumerate(range(self.scroll_offset, end_idx)):
                y = list_y + draw_i * self.item_height
                self._render_sell_item(screen, items[item_i], y, item_i == self.item_index)

        # Controls hint
        hint = "W/S: Browse | E: Select | Tab: Back"
        hint_surf = self.small_font.render(hint, True, self.text_dim_color)
        hint_rect = hint_surf.get_rect(centerx=panel_rect.centerx, bottom=panel_rect.bottom - 15)
        screen.blit(hint_surf, hint_rect)

    def _render_sell_qty(self, screen, panel_rect):
        """Render sell quantity selection mode."""
        items = self._get_sellable_items()
        if not items or self.item_index >= len(items):
            return

        current = items[self.item_index]
        item = current["item"]
        item_name = item.name
        price = item.sell_price
        max_qty = item.quantity
        total = price * self.quantity

        # Mode label
        list_y = self.panel_y + self.header_height
        mode_surf = self.font.render("- Select Quantity -", True, self.sell_color)
        mode_rect = mode_surf.get_rect(centerx=panel_rect.centerx, top=list_y - 20)
        screen.blit(mode_surf, mode_rect)

        # Item name
        center_y = self.panel_y + self.panel_height // 2 - 40
        name_surf = self.title_font.render(item_name, True, self.text_color)
        name_rect = name_surf.get_rect(centerx=panel_rect.centerx, top=center_y)
        screen.blit(name_surf, name_rect)

        # Price per item
        price_surf = self.font.render(f"{price}g each", True, self.sell_color)
        price_rect = price_surf.get_rect(centerx=panel_rect.centerx, top=center_y + 35)
        screen.blit(price_surf, price_rect)

        # Quantity selector
        qty_text = f"< {self.quantity} / {max_qty} >"
        qty_surf = self.title_font.render(qty_text, True, self.text_color)
        qty_rect = qty_surf.get_rect(centerx=panel_rect.centerx, top=center_y + 75)
        screen.blit(qty_surf, qty_rect)

        # Total profit
        total_surf = self.font.render(f"Profit: {total}g", True, self.sell_color)
        total_rect = total_surf.get_rect(centerx=panel_rect.centerx, top=center_y + 115)
        screen.blit(total_surf, total_rect)

        # Controls hint
        hint = "W/S: +/- 1 | A/D: +/- 10 | E: Confirm | Tab: Back"
        hint_surf = self.small_font.render(hint, True, self.text_dim_color)
        hint_rect = hint_surf.get_rect(centerx=panel_rect.centerx, bottom=panel_rect.bottom - 15)
        screen.blit(hint_surf, hint_rect)

    def _render_sell_item(self, screen, item_data, y, is_selected):
        """Render a single sell item row."""
        item = item_data["item"]

        row_rect = pygame.Rect(self.panel_x + 10, y, self.panel_width - 20, self.item_height - 2)

        # Background
        bg = self.item_selected_color if is_selected else self.item_color
        pygame.draw.rect(screen, bg, row_rect, border_radius=4)
        if is_selected:
            pygame.draw.rect(screen, (100, 140, 200), row_rect, 2, border_radius=4)

        # Item name with quantity
        text_color = (255, 255, 255) if is_selected else self.text_color
        name = item.name
        if item.quantity > 1:
            name += f" x{item.quantity}"
        name_surf = self.font.render(name, True, text_color)
        screen.blit(name_surf, (row_rect.left + 10, row_rect.centery - name_surf.get_height() // 2))

        # Sell price
        price_text = f"{item.sell_price}g each"
        price_surf = self.small_font.render(price_text, True, self.sell_color)
        screen.blit(price_surf, (row_rect.right - price_surf.get_width() - 10,
                                  row_rect.centery - price_surf.get_height() // 2))
