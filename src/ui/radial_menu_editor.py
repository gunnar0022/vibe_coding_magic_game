"""
Radial Menu Editor - Full-screen customization UI for the spell radial menu.
Allows drag-and-drop spell assignment, node creation/deletion, and layout preview.
"""
import pygame
import math
import re
import time
from ..magic import MagicSystem
from .radial_menu_layout import RadialMenuLayout, RadialMenuNode, DIRECTIONS, OPPOSITE_DIRECTION


class RadialMenuEditor:
    """
    Full-screen editor for customizing the radial spell menu layout.

    Features:
    - Left panel: List of all known spells with search (drag to assign)
    - Center: Visual radial layout preview (drag-and-drop slots)
    - Right panel: Node tree for nested menu navigation
    - Add/remove/rename nodes
    - Return slots locked in nested menus
    - Double-click to enter nodes or start dragging
    """

    # Direction angles for radial display (same as RadialMagicMenu)
    DIRECTION_ANGLES = {
        "n": -math.pi / 2,
        "ne": -math.pi / 4,
        "e": 0,
        "se": math.pi / 4,
        "s": math.pi / 2,
        "sw": 3 * math.pi / 4,
        "w": math.pi,
        "nw": -3 * math.pi / 4,
    }

    # Characters allowed in node names (alphanumeric, spaces, some punctuation)
    ALLOWED_NAME_CHARS = re.compile(r'^[a-zA-Z0-9 _\-\.]+$')
    MAX_NODE_NAME_LENGTH = 12

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Editor state
        self.is_open = False
        self.layout = None  # RadialMenuLayout being edited
        self.original_layout = None  # For cancel/revert
        self.known_spells = []  # List of spell IDs player knows

        # Selection state
        self.selected_node_id = "root"  # Node being viewed/edited
        self.hovered_slot = None  # Direction of hovered slot
        self.hovered_spell_index = -1  # Index of hovered spell in list

        # Drag state
        self.dragging = False
        self.drag_content = None  # spell_id or "node:node_id"
        self.drag_source = None  # ("list", spell_id) or ("slot", direction) or None
        self.drag_pos = (0, 0)

        # Double-click detection
        self.last_click_time = 0
        self.last_click_pos = (0, 0)
        self.double_click_threshold = 0.3  # seconds

        # Search state
        self.search_text = ""
        self.search_active = False

        # Rename state
        self.renaming_node_id = None
        self.rename_text = ""
        self.rename_cursor = 0

        # Scroll state for spell list
        self.spell_list_scroll = 0
        self.max_visible_spells = 8  # Reduced to make room for search

        # Layout dimensions
        self.panel_width = 220
        self.left_panel_x = 20
        self.right_panel_x = screen_width - self.panel_width - 20

        # Radial preview settings
        self.radial_center_x = screen_width // 2
        self.radial_center_y = screen_height // 2
        self.radial_slot_radius = 45
        self.radial_slot_distance = 130

        # Colors
        self.bg_color = (20, 22, 28)
        self.panel_bg = (30, 35, 45)
        self.panel_border = (50, 60, 80)
        self.text_color = (220, 220, 220)
        self.text_dim = (140, 140, 150)
        self.accent_color = (80, 120, 200)
        self.slot_empty_color = (45, 50, 60)
        self.slot_filled_color = (60, 70, 90)
        self.slot_hover_color = (80, 100, 140)
        self.slot_node_color = (90, 70, 120)
        self.slot_return_color = (70, 90, 70)  # Green-ish for return
        self.slot_locked_color = (50, 55, 50)  # Dimmer locked appearance
        self.selected_color = (100, 150, 220)
        self.button_color = (50, 60, 80)
        self.button_hover_color = (70, 85, 115)
        self.symbol_color = (180, 200, 255)
        self.warning_color = (200, 120, 80)
        self.search_bg_color = (40, 45, 55)

        # Fonts (initialized on first render)
        self.font = None
        self.title_font = None
        self.symbol_font = None
        self.small_font = None

        # Clickable regions (populated during render)
        self.spell_list_rects = []  # [(rect, spell_id), ...]
        self.slot_rects = {}  # direction -> rect
        self.node_tree_rects = []  # [(rect, node_id), ...]
        self.button_rects = {}  # name -> rect

        # Confirmation dialog
        self.confirming = False
        self.confirm_action = None
        self.confirm_message = ""
        self.confirm_data = None

    def _init_fonts(self):
        """Initialize fonts if needed."""
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 24)
            self.title_font = pygame.font.Font(None, 32)
            self.small_font = pygame.font.Font(None, 20)

            # CJK font for symbols
            cjk_fonts = ["microsoftyahei", "yugothic", "msgothic", "simsun"]
            self.symbol_font = None
            for font_name in cjk_fonts:
                try:
                    self.symbol_font = pygame.font.SysFont(font_name, 36)
                    test = self.symbol_font.render("\u706b", True, (255, 255, 255))
                    if test.get_width() > 5:
                        break
                except:
                    continue
            if self.symbol_font is None:
                self.symbol_font = pygame.font.Font(None, 36)

    def open(self, layout, known_spell_ids):
        """Open the editor with a layout to edit."""
        self._init_fonts()
        self.is_open = True
        self.layout = layout
        self.original_layout = layout.copy()
        self.known_spells = list(known_spell_ids)

        self.selected_node_id = "root"
        self.hovered_slot = None
        self.hovered_spell_index = -1
        self.spell_list_scroll = 0
        self.confirming = False
        self.dragging = False
        self.drag_content = None
        self.drag_source = None
        self.search_text = ""
        self.search_active = False
        self.renaming_node_id = None

    def close(self, save=True):
        """Close the editor. Changes are always auto-saved."""
        # Changes are applied directly to layout, so no need for explicit save
        self.is_open = False
        self.layout = None
        self.original_layout = None
        self.renaming_node_id = None
        self.search_active = False

    def get_layout(self):
        """Get the edited layout."""
        return self.layout

    def _get_return_direction(self):
        """Get the return direction for the current node (None for root)."""
        if self.selected_node_id == "root":
            return None
        # Find how we entered this node
        for parent_id, parent_node in self.layout.nodes.items():
            for direction in DIRECTIONS:
                content = parent_node.get_slot(direction)
                if content == f"node:{self.selected_node_id}":
                    return OPPOSITE_DIRECTION.get(direction)
        return None

    def _is_return_slot(self, direction):
        """Check if a direction is the return slot for current node."""
        return direction == self._get_return_direction()

    def _get_available_slot_count(self):
        """Get number of available slots (7 for nested, 8 for root)."""
        if self.selected_node_id == "root":
            return 8
        return 7  # One slot reserved for return

    def handle_input(self, input_handler, events):
        """Handle input for the editor."""
        if not self.is_open:
            return None

        mouse_x, mouse_y = input_handler.get_mouse_position()

        # Handle text input for search or rename
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.search_active:
                    self._handle_search_input(event)
                elif self.renaming_node_id:
                    self._handle_rename_input(event)

        # Handle confirmation dialog
        if self.confirming:
            return self._handle_confirm_input(input_handler, mouse_x, mouse_y)

        # Update hover states
        self._update_hover(mouse_x, mouse_y)

        # ESC handling (acts as back button)
        if input_handler.toggle_pause:
            if self.search_active:
                self.search_active = False
                self.search_text = ""
                return None
            if self.renaming_node_id:
                self.renaming_node_id = None
                return None
            if self.dragging:
                self.dragging = False
                self.drag_content = None
                self.drag_source = None
                return None
            # Close editor and return to menu (changes auto-saved)
            self.close(save=True)
            return "back_to_menu"

        # Handle dragging
        if self.dragging:
            self.drag_pos = (mouse_x, mouse_y)

            # Mouse released - complete drag
            if not pygame.mouse.get_pressed()[0]:
                return self._complete_drag(mouse_x, mouse_y)

            return None

        # Mouse click handling
        if input_handler.mouse_clicked:
            current_time = time.time()

            # Check for double-click
            is_double_click = (
                current_time - self.last_click_time < self.double_click_threshold and
                abs(mouse_x - self.last_click_pos[0]) < 10 and
                abs(mouse_y - self.last_click_pos[1]) < 10
            )

            self.last_click_time = current_time
            self.last_click_pos = (mouse_x, mouse_y)

            if is_double_click:
                return self._handle_double_click(mouse_x, mouse_y)
            else:
                return self._handle_click(mouse_x, mouse_y)

        # Right click to deselect or cancel
        if input_handler.mouse_right_clicked:
            return self._handle_right_click(mouse_x, mouse_y)

        # Scroll wheel for spell list
        for event in events:
            if event.type == pygame.MOUSEWHEEL:
                if self._is_over_spell_list(mouse_x, mouse_y):
                    self._scroll_spell_list(event.y)

        return None

    def _handle_search_input(self, event):
        """Handle keyboard input for search."""
        if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
            self.search_active = False
        elif event.key == pygame.K_BACKSPACE:
            self.search_text = self.search_text[:-1]
        elif event.unicode and len(self.search_text) < 20:
            # Only allow printable characters
            if event.unicode.isprintable():
                self.search_text += event.unicode

    def _handle_rename_input(self, event):
        """Handle keyboard input for node renaming."""
        if event.key == pygame.K_RETURN:
            # Apply rename
            self._apply_rename()
        elif event.key == pygame.K_ESCAPE:
            self.renaming_node_id = None
        elif event.key == pygame.K_BACKSPACE:
            if self.rename_cursor > 0:
                self.rename_text = self.rename_text[:self.rename_cursor-1] + self.rename_text[self.rename_cursor:]
                self.rename_cursor -= 1
        elif event.key == pygame.K_DELETE:
            self.rename_text = self.rename_text[:self.rename_cursor] + self.rename_text[self.rename_cursor+1:]
        elif event.key == pygame.K_LEFT:
            self.rename_cursor = max(0, self.rename_cursor - 1)
        elif event.key == pygame.K_RIGHT:
            self.rename_cursor = min(len(self.rename_text), self.rename_cursor + 1)
        elif event.key == pygame.K_HOME:
            self.rename_cursor = 0
        elif event.key == pygame.K_END:
            self.rename_cursor = len(self.rename_text)
        elif event.unicode and len(self.rename_text) < self.MAX_NODE_NAME_LENGTH:
            # Sanitize input - only allow safe characters
            char = event.unicode
            if char.isalnum() or char in ' _-.':
                self.rename_text = self.rename_text[:self.rename_cursor] + char + self.rename_text[self.rename_cursor:]
                self.rename_cursor += 1

    def _apply_rename(self):
        """Apply the rename to the node."""
        if self.renaming_node_id and self.rename_text.strip():
            node = self.layout.get_node(self.renaming_node_id)
            if node:
                # Sanitize and trim
                new_name = self.rename_text.strip()[:self.MAX_NODE_NAME_LENGTH]
                # Additional sanitization - remove any potentially problematic chars
                new_name = re.sub(r'[^\w\s\-\.]', '', new_name)
                if new_name:
                    node.name = new_name
        self.renaming_node_id = None

    def _scroll_spell_list(self, direction):
        """Scroll the spell list."""
        filtered = self._get_filtered_spells()
        self.spell_list_scroll -= direction * 2
        max_scroll = max(0, len(filtered) - self.max_visible_spells)
        self.spell_list_scroll = max(0, min(self.spell_list_scroll, max_scroll))

    def _update_hover(self, mouse_x, mouse_y):
        """Update hover states based on mouse position."""
        self.hovered_slot = None
        self.hovered_spell_index = -1

        # Check slot hovers (skip return slot) - also track during dragging
        for direction, rect in self.slot_rects.items():
            if self._is_return_slot(direction):
                continue
            if rect.collidepoint(mouse_x, mouse_y):
                self.hovered_slot = direction
                break

        # Check spell list hovers (only when not dragging)
        if not self.dragging:
            for i, (rect, spell_id) in enumerate(self.spell_list_rects):
                if rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_spell_index = i
                    break

    def _is_over_spell_list(self, mouse_x, mouse_y):
        """Check if mouse is over spell list panel."""
        list_rect = pygame.Rect(self.left_panel_x, 100, self.panel_width, 400)
        return list_rect.collidepoint(mouse_x, mouse_y)

    def _is_over_radial_menu(self, mouse_x, mouse_y):
        """Check if mouse is over the radial menu area."""
        dx = mouse_x - self.radial_center_x
        dy = mouse_y - self.radial_center_y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self.radial_slot_distance + self.radial_slot_radius + 30

    def _get_filtered_spells(self):
        """Get list of spells filtered by search text."""
        if not self.search_text:
            return self.known_spells

        search_lower = self.search_text.lower()
        results = []

        for spell_id in self.known_spells:
            symbol = MagicSystem.get_symbol(spell_id)
            if not symbol:
                continue

            # Check if search matches id, name, or character
            if (search_lower in spell_id.lower() or
                search_lower in symbol.name.lower() or
                search_lower in symbol.character):
                results.append(spell_id)

        return results

    def _get_all_spells_for_list(self):
        """Get filtered spells with assignment status."""
        assigned = self.layout.get_all_assigned_spells()
        filtered = self._get_filtered_spells()
        return [(s, s in assigned) for s in filtered]

    def _handle_click(self, mouse_x, mouse_y):
        """Handle single left mouse click."""
        # Check search box first (before general buttons)
        search_rect = self.button_rects.get("search_box")
        if search_rect and search_rect.collidepoint(mouse_x, mouse_y):
            self.search_active = True
            return None

        # Deactivate search if clicking elsewhere
        if self.search_active:
            self.search_active = False

        # Check other buttons
        for name, rect in self.button_rects.items():
            if name == "search_box":
                continue  # Already handled above
            if rect.collidepoint(mouse_x, mouse_y):
                return self._handle_button_click(name)

        # Check spell list - start drag
        for rect, spell_id in self.spell_list_rects:
            if rect.collidepoint(mouse_x, mouse_y):
                self._start_drag(spell_id, ("list", spell_id), mouse_x, mouse_y)
                return None

        # Check radial slots
        for direction, rect in self.slot_rects.items():
            if rect.collidepoint(mouse_x, mouse_y):
                # Can't interact with return slot
                if self._is_return_slot(direction):
                    continue
                return self._handle_slot_click(direction, mouse_x, mouse_y)

        # Check node tree - select or start rename
        for rect, node_id in self.node_tree_rects:
            if rect.collidepoint(mouse_x, mouse_y):
                self.selected_node_id = node_id
                return None

        return None

    def _handle_double_click(self, mouse_x, mouse_y):
        """Handle double-click."""
        # Double-click on slot - enter node or start drag
        for direction, rect in self.slot_rects.items():
            if rect.collidepoint(mouse_x, mouse_y):
                if self._is_return_slot(direction):
                    # Double-click return slot navigates back
                    return self._navigate_to_parent()

                current_node = self.layout.get_node(self.selected_node_id)
                if not current_node:
                    return None

                slot_content = current_node.get_slot(direction)

                if slot_content and slot_content.startswith("node:"):
                    # Enter the node
                    self.selected_node_id = slot_content[5:]
                    return None
                elif slot_content:
                    # Start dragging the spell
                    self._start_drag(slot_content, ("slot", direction), mouse_x, mouse_y)
                    return None

        # Double-click on node in tree - start rename
        for rect, node_id in self.node_tree_rects:
            if rect.collidepoint(mouse_x, mouse_y):
                self._start_rename(node_id)
                return None

        return None

    def _start_rename(self, node_id):
        """Start renaming a node."""
        node = self.layout.get_node(node_id)
        if node:
            self.renaming_node_id = node_id
            self.rename_text = node.name
            self.rename_cursor = len(self.rename_text)

    def _navigate_to_parent(self):
        """Navigate to parent node."""
        if self.selected_node_id == "root":
            return None

        # Find parent
        for parent_id, parent_node in self.layout.nodes.items():
            for direction in DIRECTIONS:
                content = parent_node.get_slot(direction)
                if content == f"node:{self.selected_node_id}":
                    self.selected_node_id = parent_id
                    return None

        # Fallback to root
        self.selected_node_id = "root"
        return None

    def _handle_right_click(self, mouse_x, mouse_y):
        """Handle right mouse click."""
        # Check if clicking a slot - clear it (and delete node if applicable)
        for direction, rect in self.slot_rects.items():
            if rect.collidepoint(mouse_x, mouse_y):
                if self._is_return_slot(direction):
                    continue
                self._clear_slot_with_cleanup(self.selected_node_id, direction)
                return None

        return None

    def _clear_slot_with_cleanup(self, node_id, direction):
        """Clear a slot and delete the node if it contained one."""
        node = self.layout.get_node(node_id)
        if not node:
            return

        slot_content = node.get_slot(direction)

        # If it's a node, delete the node data too
        if slot_content and slot_content.startswith("node:"):
            child_node_id = slot_content[5:]
            self.layout.delete_node(child_node_id)
        else:
            # Just clear the slot
            node.clear_slot(direction)

    def _handle_slot_click(self, direction, mouse_x, mouse_y):
        """Handle clicking on a radial slot."""
        current_node = self.layout.get_node(self.selected_node_id)
        if not current_node:
            return None

        slot_content = current_node.get_slot(direction)

        if slot_content:
            # Single click on any filled slot (spell OR node) - start drag
            # Double-click is required to enter a node
            self._start_drag(slot_content, ("slot", direction), mouse_x, mouse_y)
            return None

        return None

    def _start_drag(self, content, source, mouse_x, mouse_y):
        """Start dragging content."""
        self.dragging = True
        self.drag_content = content
        self.drag_source = source
        self.drag_pos = (mouse_x, mouse_y)

        # If dragging from slot, clear the slot
        if source[0] == "slot":
            direction = source[1]
            current_node = self.layout.get_node(self.selected_node_id)
            if current_node:
                current_node.clear_slot(direction)

    def _complete_drag(self, mouse_x, mouse_y):
        """Complete a drag operation."""
        if not self.dragging or not self.drag_content:
            self.dragging = False
            return None

        content = self.drag_content
        source = self.drag_source

        # Check if dropped on a slot
        dropped_on_slot = None
        for direction, rect in self.slot_rects.items():
            if rect.collidepoint(mouse_x, mouse_y):
                if not self._is_return_slot(direction):
                    dropped_on_slot = direction
                break

        if dropped_on_slot:
            # Drop on slot
            current_node = self.layout.get_node(self.selected_node_id)
            if current_node:
                # Check if slot already has content
                existing = current_node.get_slot(dropped_on_slot)
                if existing:
                    # Swap if dragging from another slot
                    if source and source[0] == "slot":
                        # The source slot was already cleared, put existing there
                        orig_node = self.layout.get_node(self.selected_node_id)
                        if orig_node:
                            orig_node.set_slot(source[1], existing)

                # Assign the dragged content
                current_node.set_slot(dropped_on_slot, content)
        else:
            # Dropped outside radial menu - delete the content
            if not self._is_over_radial_menu(mouse_x, mouse_y):
                # If it was a node, also delete node data
                if content.startswith("node:"):
                    node_id = content[5:]
                    self.layout.delete_node(node_id)
                # Otherwise content is just discarded (spell returns to unassigned)
            else:
                # Dropped inside menu but not on slot - return to source if it was a slot
                if source and source[0] == "slot":
                    current_node = self.layout.get_node(self.selected_node_id)
                    if current_node:
                        current_node.set_slot(source[1], content)

        self.dragging = False
        self.drag_content = None
        self.drag_source = None
        return None

    def _handle_button_click(self, button_name):
        """Handle button clicks."""
        if button_name == "done":
            self.close(save=True)
            return "back_to_menu"

        elif button_name == "add_node":
            return self._add_node()

        elif button_name == "remove_node":
            if self.selected_node_id != "root":
                self._show_confirmation(
                    "remove_node",
                    "Delete this submenu?",
                    self.selected_node_id
                )
            return None

        elif button_name == "back_to_root":
            self.selected_node_id = "root"
            return None

        elif button_name == "clear_all":
            self._show_confirmation(
                "clear_all",
                "Clear all from this menu?",
                self.selected_node_id
            )
            return None

        elif button_name == "rename_node":
            if self.selected_node_id:
                self._start_rename(self.selected_node_id)
            return None

        return None

    def _add_node(self):
        """Add a new nested node."""
        new_node = self.layout.create_node()

        # Find first empty slot in current node (skip return slot)
        current_node = self.layout.get_node(self.selected_node_id)
        if current_node:
            return_dir = self._get_return_direction()
            for direction in DIRECTIONS:
                if direction == return_dir:
                    continue
                if current_node.get_slot(direction) is None:
                    self.layout.assign_node_to_slot(
                        self.selected_node_id,
                        direction,
                        new_node.node_id
                    )
                    break

        return None

    def _show_confirmation(self, action, message, data=None):
        """Show confirmation dialog."""
        self.confirming = True
        self.confirm_action = action
        self.confirm_message = message
        self.confirm_data = data

    def _handle_confirm_input(self, input_handler, mouse_x, mouse_y):
        """Handle input for confirmation dialog."""
        if input_handler.cancel:
            self.confirming = False
            return None

        if input_handler.mouse_clicked:
            yes_rect = self.button_rects.get("confirm_yes")
            no_rect = self.button_rects.get("confirm_no")

            if yes_rect and yes_rect.collidepoint(mouse_x, mouse_y):
                return self._confirm_action()
            if no_rect and no_rect.collidepoint(mouse_x, mouse_y):
                self.confirming = False
                return None

        return None

    def _confirm_action(self):
        """Execute confirmed action."""
        action = self.confirm_action
        data = self.confirm_data
        self.confirming = False

        if action == "remove_node":
            if data and data != "root":
                self.layout.delete_node(data)
                self.selected_node_id = "root"

        elif action == "clear_all":
            node = self.layout.get_node(data)
            if node:
                return_dir = self._get_return_direction() if data != "root" else None
                for direction in DIRECTIONS:
                    if direction == return_dir:
                        continue
                    # Clear with cleanup (deletes nested nodes)
                    self._clear_slot_with_cleanup(data, direction)

        return None

    def render(self, screen):
        """Render the editor."""
        if not self.is_open:
            return

        self._init_fonts()

        # Clear clickable regions
        self.spell_list_rects = []
        self.slot_rects = {}
        self.node_tree_rects = []
        self.button_rects = {}

        # Draw background
        screen.fill(self.bg_color)

        # Draw title
        title = self.title_font.render("Spell Menu Customization", True, self.text_color)
        screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, 15))

        # Draw panels
        self._render_spell_list(screen)
        self._render_radial_preview(screen)
        self._render_node_tree(screen)
        self._render_buttons(screen)

        # Draw instructions
        self._render_instructions(screen)

        # Draw drag preview
        if self.dragging:
            self._render_drag_preview(screen)

        # Draw rename dialog
        if self.renaming_node_id:
            self._render_rename_dialog(screen)

        # Draw confirmation dialog if active
        if self.confirming:
            self._render_confirmation(screen)

    def _render_spell_list(self, screen):
        """Render the left panel with known spells and search."""
        panel_rect = pygame.Rect(self.left_panel_x, 50, self.panel_width, self.screen_height - 100)
        pygame.draw.rect(screen, self.panel_bg, panel_rect, border_radius=8)
        pygame.draw.rect(screen, self.panel_border, panel_rect, 2, border_radius=8)

        # Panel title
        title = self.font.render("Known Spells", True, self.text_color)
        screen.blit(title, (panel_rect.centerx - title.get_width() // 2, panel_rect.top + 10))

        # Search box
        search_y = panel_rect.top + 38
        search_rect = pygame.Rect(panel_rect.left + 10, search_y, panel_rect.width - 20, 28)
        pygame.draw.rect(screen, self.search_bg_color, search_rect, border_radius=4)

        if self.search_active:
            pygame.draw.rect(screen, self.accent_color, search_rect, 2, border_radius=4)
        else:
            pygame.draw.rect(screen, self.panel_border, search_rect, 1, border_radius=4)

        # Search text or placeholder
        search_display = self.search_text if self.search_text else "Search spells..."
        search_color = self.text_color if self.search_text else self.text_dim
        search_surf = self.small_font.render(search_display, True, search_color)
        screen.blit(search_surf, (search_rect.left + 8, search_rect.centery - search_surf.get_height() // 2))

        # Search cursor
        if self.search_active:
            cursor_x = search_rect.left + 8 + self.small_font.size(self.search_text)[0]
            pygame.draw.line(screen, self.text_color, (cursor_x, search_rect.top + 5),
                           (cursor_x, search_rect.bottom - 5), 2)

        self.button_rects["search_box"] = search_rect

        # Unassigned count
        assigned = self.layout.get_all_assigned_spells()
        unassigned_count = len([s for s in self.known_spells if s not in assigned])
        subtitle = self.small_font.render(f"({unassigned_count} unassigned)", True, self.text_dim)
        screen.blit(subtitle, (panel_rect.centerx - subtitle.get_width() // 2, search_y + 32))

        # Spell list
        list_y = search_y + 55
        item_height = 45

        all_spells = self._get_all_spells_for_list()
        visible_start = self.spell_list_scroll
        visible_end = visible_start + self.max_visible_spells

        for i, (spell_id, is_assigned) in enumerate(all_spells[visible_start:visible_end]):
            actual_index = visible_start + i
            y = list_y + i * item_height

            symbol = MagicSystem.get_symbol(spell_id)
            if not symbol:
                continue

            item_rect = pygame.Rect(panel_rect.left + 10, y, panel_rect.width - 20, item_height - 5)

            # Background color
            if actual_index == self.hovered_spell_index and not self.dragging:
                bg_color = self.slot_hover_color
            elif is_assigned:
                bg_color = (40, 45, 55)
            else:
                bg_color = self.slot_filled_color

            pygame.draw.rect(screen, bg_color, item_rect, border_radius=5)

            # Symbol character
            char_surf = self.symbol_font.render(symbol.character, True,
                                                self.text_dim if is_assigned else self.symbol_color)
            screen.blit(char_surf, (item_rect.left + 5, item_rect.centery - char_surf.get_height() // 2))

            # Spell name
            name_color = self.text_dim if is_assigned else self.text_color
            name_surf = self.small_font.render(symbol.name[:12], True, name_color)
            screen.blit(name_surf, (item_rect.left + 42, item_rect.centery - name_surf.get_height() // 2))

            # "In use" indicator
            if is_assigned:
                used_surf = self.small_font.render("(used)", True, self.text_dim)
                screen.blit(used_surf, (item_rect.right - used_surf.get_width() - 5,
                                        item_rect.centery - used_surf.get_height() // 2))

            self.spell_list_rects.append((item_rect, spell_id))

        # Scroll indicators
        if self.spell_list_scroll > 0:
            up_surf = self.small_font.render("^ scroll up ^", True, self.text_dim)
            screen.blit(up_surf, (panel_rect.centerx - up_surf.get_width() // 2, list_y - 15))

        if visible_end < len(all_spells):
            down_surf = self.small_font.render("v scroll down v", True, self.text_dim)
            screen.blit(down_surf, (panel_rect.centerx - down_surf.get_width() // 2,
                                    panel_rect.bottom - 20))

    def _render_radial_preview(self, screen):
        """Render the center radial menu preview."""
        current_node = self.layout.get_node(self.selected_node_id)
        if not current_node:
            return

        return_direction = self._get_return_direction()

        # Center area background
        center_rect = pygame.Rect(
            self.radial_center_x - 200,
            self.radial_center_y - 200,
            400, 400
        )
        pygame.draw.rect(screen, self.panel_bg, center_rect, border_radius=200)
        pygame.draw.rect(screen, self.panel_border, center_rect, 2, border_radius=200)

        # Center circle showing current node name
        pygame.draw.circle(screen, (40, 45, 55),
                          (self.radial_center_x, self.radial_center_y), 50)
        pygame.draw.circle(screen, self.panel_border,
                          (self.radial_center_x, self.radial_center_y), 50, 2)

        node_name = current_node.name
        name_surf = self.font.render(node_name[:10], True, self.text_color)
        screen.blit(name_surf, (self.radial_center_x - name_surf.get_width() // 2,
                               self.radial_center_y - name_surf.get_height() // 2))

        # Slot count indicator
        used = len([d for d in DIRECTIONS if current_node.get_slot(d) is not None and d != return_direction])
        available = self._get_available_slot_count()
        count_text = f"{used}/{available} slots"
        count_surf = self.small_font.render(count_text, True, self.text_dim)
        screen.blit(count_surf, (self.radial_center_x - count_surf.get_width() // 2,
                                self.radial_center_y + 20))

        # Draw slots
        for direction in DIRECTIONS:
            angle = self.DIRECTION_ANGLES[direction]
            slot_x = int(self.radial_center_x + self.radial_slot_distance * math.cos(angle))
            slot_y = int(self.radial_center_y + self.radial_slot_distance * math.sin(angle))

            is_return = direction == return_direction
            slot_content = current_node.get_slot(direction)

            # Determine slot appearance
            if is_return:
                color = self.slot_return_color
            elif self.hovered_slot == direction and not self.dragging:
                color = self.slot_hover_color
            elif self.dragging and self.hovered_slot == direction:
                color = self.accent_color
            elif slot_content is None:
                color = self.slot_empty_color
            elif slot_content.startswith("node:"):
                color = self.slot_node_color
            else:
                color = self.slot_filled_color

            # Draw slot circle
            slot_rect = pygame.Rect(
                slot_x - self.radial_slot_radius,
                slot_y - self.radial_slot_radius,
                self.radial_slot_radius * 2,
                self.radial_slot_radius * 2
            )

            if is_return:
                # Return slot - solid with lock icon
                pygame.draw.circle(screen, color, (slot_x, slot_y), self.radial_slot_radius)
                pygame.draw.circle(screen, (100, 130, 100), (slot_x, slot_y),
                                  self.radial_slot_radius, 3)

                # Draw return arrow
                arrow_size = 15
                points = [
                    (slot_x - arrow_size, slot_y),
                    (slot_x + arrow_size // 2, slot_y - arrow_size),
                    (slot_x + arrow_size // 2, slot_y + arrow_size),
                ]
                pygame.draw.polygon(screen, self.text_color, points)

                # "BACK" label
                back_surf = self.small_font.render("BACK", True, self.text_color)
                screen.blit(back_surf, (slot_x - back_surf.get_width() // 2, slot_y + 18))

            elif slot_content is None:
                # Empty slot - dotted circle
                self._draw_dotted_circle(screen, slot_x, slot_y, self.radial_slot_radius, color)
            else:
                pygame.draw.circle(screen, color, (slot_x, slot_y), self.radial_slot_radius)
                pygame.draw.circle(screen, self.panel_border, (slot_x, slot_y),
                                  self.radial_slot_radius, 2)

                # Draw content
                if slot_content.startswith("node:"):
                    node_id = slot_content[5:]
                    child_node = self.layout.get_node(node_id)
                    node_name = child_node.name if child_node else "?"

                    # Folder icon
                    folder_surf = self.font.render("[+]", True, self.text_color)
                    screen.blit(folder_surf, (slot_x - folder_surf.get_width() // 2, slot_y - 12))

                    # Abbreviated name
                    abbr = node_name[:5] if len(node_name) > 5 else node_name
                    abbr_surf = self.small_font.render(abbr, True, self.text_color)
                    screen.blit(abbr_surf, (slot_x - abbr_surf.get_width() // 2, slot_y + 10))
                else:
                    # Spell symbol
                    symbol = MagicSystem.get_symbol(slot_content)
                    if symbol:
                        char_surf = self.symbol_font.render(symbol.character, True, self.symbol_color)
                        screen.blit(char_surf, (slot_x - char_surf.get_width() // 2,
                                               slot_y - char_surf.get_height() // 2))

            # Direction label
            dir_label = self.small_font.render(direction.upper(), True, self.text_dim)
            label_dist = self.radial_slot_distance + self.radial_slot_radius + 15
            label_x = int(self.radial_center_x + label_dist * math.cos(angle))
            label_y = int(self.radial_center_y + label_dist * math.sin(angle))
            screen.blit(dir_label, (label_x - dir_label.get_width() // 2,
                                   label_y - dir_label.get_height() // 2))

            self.slot_rects[direction] = slot_rect

    def _draw_dotted_circle(self, screen, cx, cy, radius, color):
        """Draw a dotted circle for empty slots."""
        num_dots = 12
        dot_radius = 3
        for i in range(num_dots):
            angle = 2 * math.pi * i / num_dots
            x = int(cx + radius * 0.8 * math.cos(angle))
            y = int(cy + radius * 0.8 * math.sin(angle))
            pygame.draw.circle(screen, color, (x, y), dot_radius)

    def _render_node_tree(self, screen):
        """Render the right panel with node tree."""
        panel_rect = pygame.Rect(self.right_panel_x, 50, self.panel_width, 320)
        pygame.draw.rect(screen, self.panel_bg, panel_rect, border_radius=8)
        pygame.draw.rect(screen, self.panel_border, panel_rect, 2, border_radius=8)

        # Panel title
        title = self.font.render("Menu Structure", True, self.text_color)
        screen.blit(title, (panel_rect.centerx - title.get_width() // 2, panel_rect.top + 10))

        # Instruction
        hint = self.small_font.render("Double-click to rename", True, self.text_dim)
        screen.blit(hint, (panel_rect.centerx - hint.get_width() // 2, panel_rect.top + 32))

        # Node list
        y = panel_rect.top + 55
        item_height = 35

        for node_id, node in self.layout.nodes.items():
            if y > panel_rect.bottom - 50:
                break

            item_rect = pygame.Rect(panel_rect.left + 10, y, panel_rect.width - 20, item_height - 5)

            # Highlight selected node
            is_selected = node_id == self.selected_node_id
            bg_color = self.selected_color if is_selected else self.slot_filled_color

            pygame.draw.rect(screen, bg_color, item_rect, border_radius=5)

            # Node icon and name
            icon = "[*]" if node_id == "root" else "[+]"
            icon_surf = self.small_font.render(icon, True, self.text_color)
            screen.blit(icon_surf, (item_rect.left + 8, item_rect.centery - icon_surf.get_height() // 2))

            name_surf = self.font.render(node.name[:10], True, self.text_color)
            screen.blit(name_surf, (item_rect.left + 35, item_rect.centery - name_surf.get_height() // 2))

            # Slot count (show 7 for non-root, 8 for root)
            max_slots = 8 if node_id == "root" else 7
            used = len(node.get_used_slots())
            if node_id != "root":
                # Don't count return slot as "used" for display purposes
                # (it's not user-assignable)
                pass
            count_surf = self.small_font.render(f"{used}/{max_slots}", True, self.text_dim)
            screen.blit(count_surf, (item_rect.right - count_surf.get_width() - 8,
                                    item_rect.centery - count_surf.get_height() // 2))

            self.node_tree_rects.append((item_rect, node_id))
            y += item_height

    def _render_buttons(self, screen):
        """Render control buttons."""
        # Right panel buttons (under node tree)
        btn_y = 390
        btn_width = 100
        btn_height = 28

        # Add Node button
        add_rect = pygame.Rect(self.right_panel_x, btn_y, btn_width, btn_height)
        pygame.draw.rect(screen, self.button_color, add_rect, border_radius=5)
        add_surf = self.small_font.render("Add Submenu", True, self.text_color)
        screen.blit(add_surf, add_surf.get_rect(center=add_rect.center))
        self.button_rects["add_node"] = add_rect

        # Remove Node button
        remove_rect = pygame.Rect(self.right_panel_x + btn_width + 10, btn_y, btn_width, btn_height)
        can_remove = self.selected_node_id != "root"
        remove_color = self.button_color if can_remove else (35, 38, 45)
        pygame.draw.rect(screen, remove_color, remove_rect, border_radius=5)
        remove_surf = self.small_font.render("Delete Menu", True, self.text_color if can_remove else self.text_dim)
        screen.blit(remove_surf, remove_surf.get_rect(center=remove_rect.center))
        self.button_rects["remove_node"] = remove_rect

        # Rename button
        btn_y += 35
        rename_rect = pygame.Rect(self.right_panel_x, btn_y, btn_width, btn_height)
        pygame.draw.rect(screen, self.button_color, rename_rect, border_radius=5)
        rename_surf = self.small_font.render("Rename", True, self.text_color)
        screen.blit(rename_surf, rename_surf.get_rect(center=rename_rect.center))
        self.button_rects["rename_node"] = rename_rect

        # Back to Root button
        back_rect = pygame.Rect(self.right_panel_x + btn_width + 10, btn_y, btn_width, btn_height)
        pygame.draw.rect(screen, self.button_color, back_rect, border_radius=5)
        back_surf = self.small_font.render("< To Root", True, self.text_color)
        screen.blit(back_surf, back_surf.get_rect(center=back_rect.center))
        self.button_rects["back_to_root"] = back_rect

        # Clear All button
        btn_y += 35
        clear_rect = pygame.Rect(self.right_panel_x, btn_y, self.panel_width, btn_height)
        pygame.draw.rect(screen, self.warning_color, clear_rect, border_radius=5)
        clear_surf = self.small_font.render("Clear This Menu", True, self.text_color)
        screen.blit(clear_surf, clear_surf.get_rect(center=clear_rect.center))
        self.button_rects["clear_all"] = clear_rect

        # Bottom button (Done - changes auto-save)
        bottom_y = self.screen_height - 50

        done_rect = pygame.Rect(self.screen_width // 2 - 50, bottom_y, 100, 35)
        pygame.draw.rect(screen, (60, 120, 80), done_rect, border_radius=5)
        done_surf = self.font.render("Done", True, self.text_color)
        screen.blit(done_surf, done_surf.get_rect(center=done_rect.center))
        self.button_rects["done"] = done_rect

        # Auto-save indicator
        auto_text = self.small_font.render("(changes save automatically)", True, self.text_dim)
        screen.blit(auto_text, (self.screen_width // 2 - auto_text.get_width() // 2, bottom_y + 38))

    def _render_instructions(self, screen):
        """Render usage instructions."""
        instructions = [
            "Drag spells/nodes from list or slots | Drag between slots to swap",
            "Double-click node to enter | Drag off menu to delete",
            "Right-click slot to remove | BACK slot auto-updates when node moves",
        ]

        y = self.screen_height - 100
        for text in instructions:
            surf = self.small_font.render(text, True, self.text_dim)
            screen.blit(surf, (self.screen_width // 2 - surf.get_width() // 2, y))
            y += 16

    def _render_drag_preview(self, screen):
        """Render the item being dragged."""
        if not self.drag_content:
            return

        x, y = self.drag_pos

        # Draw a semi-transparent preview at cursor
        preview_surf = pygame.Surface((70, 70), pygame.SRCALPHA)

        if self.drag_content.startswith("node:"):
            # Node preview
            pygame.draw.circle(preview_surf, (*self.slot_node_color, 180), (35, 35), 30)
            node_id = self.drag_content[5:]
            node = self.layout.get_node(node_id)
            if node:
                name_surf = self.small_font.render(node.name[:4], True, self.text_color)
                preview_surf.blit(name_surf, (35 - name_surf.get_width() // 2, 25))
        else:
            # Spell preview
            pygame.draw.circle(preview_surf, (*self.slot_filled_color, 180), (35, 35), 30)
            symbol = MagicSystem.get_symbol(self.drag_content)
            if symbol:
                char_surf = self.symbol_font.render(symbol.character, True, self.symbol_color)
                preview_surf.blit(char_surf, (35 - char_surf.get_width() // 2,
                                             35 - char_surf.get_height() // 2))

        screen.blit(preview_surf, (x - 35, y - 35))

    def _render_rename_dialog(self, screen):
        """Render the rename dialog."""
        # Dim overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Dialog box
        dialog_width = 300
        dialog_height = 120
        dialog_rect = pygame.Rect(
            (self.screen_width - dialog_width) // 2,
            (self.screen_height - dialog_height) // 2,
            dialog_width,
            dialog_height
        )

        pygame.draw.rect(screen, self.panel_bg, dialog_rect, border_radius=10)
        pygame.draw.rect(screen, self.panel_border, dialog_rect, 2, border_radius=10)

        # Title
        title_surf = self.font.render("Rename Menu", True, self.text_color)
        screen.blit(title_surf, (dialog_rect.centerx - title_surf.get_width() // 2, dialog_rect.top + 15))

        # Text input
        input_rect = pygame.Rect(dialog_rect.left + 20, dialog_rect.top + 45,
                                dialog_width - 40, 30)
        pygame.draw.rect(screen, self.search_bg_color, input_rect, border_radius=4)
        pygame.draw.rect(screen, self.accent_color, input_rect, 2, border_radius=4)

        # Text
        text_surf = self.font.render(self.rename_text, True, self.text_color)
        screen.blit(text_surf, (input_rect.left + 8, input_rect.centery - text_surf.get_height() // 2))

        # Cursor
        cursor_x = input_rect.left + 8 + self.font.size(self.rename_text[:self.rename_cursor])[0]
        pygame.draw.line(screen, self.text_color, (cursor_x, input_rect.top + 5),
                        (cursor_x, input_rect.bottom - 5), 2)

        # Char count
        count_text = f"{len(self.rename_text)}/{self.MAX_NODE_NAME_LENGTH}"
        count_surf = self.small_font.render(count_text, True, self.text_dim)
        screen.blit(count_surf, (input_rect.right - count_surf.get_width(),
                                input_rect.bottom + 5))

        # Instructions
        inst_surf = self.small_font.render("Enter to confirm, ESC to cancel", True, self.text_dim)
        screen.blit(inst_surf, (dialog_rect.centerx - inst_surf.get_width() // 2,
                               dialog_rect.bottom - 25))

    def _render_confirmation(self, screen):
        """Render confirmation dialog."""
        overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        dialog_width = 300
        dialog_height = 130
        dialog_rect = pygame.Rect(
            (self.screen_width - dialog_width) // 2,
            (self.screen_height - dialog_height) // 2,
            dialog_width,
            dialog_height
        )

        pygame.draw.rect(screen, self.panel_bg, dialog_rect, border_radius=10)
        pygame.draw.rect(screen, self.panel_border, dialog_rect, 2, border_radius=10)

        msg_surf = self.font.render(self.confirm_message, True, self.text_color)
        screen.blit(msg_surf, (dialog_rect.centerx - msg_surf.get_width() // 2,
                              dialog_rect.top + 25))

        btn_width = 80
        btn_height = 35
        btn_y = dialog_rect.bottom - 50

        no_rect = pygame.Rect(dialog_rect.centerx - btn_width - 10, btn_y, btn_width, btn_height)
        pygame.draw.rect(screen, (120, 60, 60), no_rect, border_radius=5)
        no_surf = self.font.render("No", True, self.text_color)
        screen.blit(no_surf, no_surf.get_rect(center=no_rect.center))
        self.button_rects["confirm_no"] = no_rect

        yes_rect = pygame.Rect(dialog_rect.centerx + 10, btn_y, btn_width, btn_height)
        pygame.draw.rect(screen, (60, 120, 80), yes_rect, border_radius=5)
        yes_surf = self.font.render("Yes", True, self.text_color)
        screen.blit(yes_surf, yes_surf.get_rect(center=yes_rect.center))
        self.button_rects["confirm_yes"] = yes_rect
