"""
Node Menu Editor - Full-screen customization UI for the node-based spell menu.
Allows freeform placement of spell nodes, connection drawing, and soft physics.
"""
import pygame
import math
import time
from ..magic import MagicSystem
from .node_menu_layout import NodeMenuLayout, CANVAS_WIDTH, CANVAS_HEIGHT, CENTER_NODE_ID


# Node geometry
NODE_RADIUS = 35
BOUNDARY_MARGIN = NODE_RADIUS + 10
CONNECTION_HIT_DISTANCE = 10  # px tolerance for clicking a connection line

# =============================================================================
# Force-directed graph physics (d3-force model)
# Four independent, additive forces + alpha temperature for settling.
# =============================================================================

# Center force — pulls every node toward canvas center (linear spring)
CENTER_STRENGTH = 0.011

# Repel force — inverse-square repulsion between all node pairs (charge)
REPEL_STRENGTH = 5000.0

# Link force — Hooke's law spring on connected nodes toward LINK_DISTANCE
LINK_STRENGTH = 0.063
LINK_DISTANCE = NODE_RADIUS * 4.0  # ~140px — target separation for connected nodes

# Velocity decay — friction multiplier per frame (lower = more friction)
VELOCITY_DECAY = 0.55

# Alpha (simulation temperature) — forces get multiplied by alpha each tick.
# Alpha decays toward ALPHA_MIN; once it reaches ALPHA_MIN the sim is frozen.
ALPHA_START = 0.0           # Start frozen — existing layouts don't explode on open
ALPHA_MIN = 0.001           # Freeze threshold — effectively zero
ALPHA_DECAY = 0.02          # Per-tick decay: alpha += (ALPHA_MIN - alpha) * ALPHA_DECAY
ALPHA_REHEAT = 0.35         # Value alpha jumps to on user interaction

# Safety cap
MAX_VELOCITY = 300.0


class NodeMenuEditor:
    """
    Full-screen editor for customizing the node-based spell menu.

    Layout:
    - Left panel: Searchable spell list (drag to add to canvas)
    - Center: Node canvas with physics simulation

    Interactions:
    - Left-click drag node to reposition
    - Drag spell from list onto canvas to add
    - Drag node off canvas / back to list to remove (or hover X button)
    - Right-click drag from node to node to create connection
    - Right-click on connection line to delete it
    - Left-click drag connection line to detach
    """

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Editor state
        self.is_open = False
        self.layout = None  # NodeMenuLayout being edited
        self.original_layout = None
        self.known_spells = []

        # Physics state (d3-force model)
        self.node_velocities = {}  # spell_id -> [vx, vy]
        self.alpha = ALPHA_START   # Simulation temperature — decays toward ALPHA_MIN

        # Panel layout: [left spell list] [canvas] [right force sliders]
        self.panel_width = 220
        self.right_panel_width = 180
        self.left_panel_x = 20
        canvas_area_left = self.panel_width + 30
        self.right_panel_x = screen_width - self.right_panel_width - 10
        canvas_area_right = self.right_panel_x - 10
        available_width = canvas_area_right - canvas_area_left
        # Clamp canvas to available space (shrinks on small screens)
        effective_canvas_w = min(CANVAS_WIDTH, available_width)
        self.canvas_x = canvas_area_left + (available_width - effective_canvas_w) // 2
        self.canvas_y = (screen_height - CANVAS_HEIGHT) // 2

        # Force slider state (live-tunable, initialized from module defaults)
        self.force_center = CENTER_STRENGTH
        self.force_repel = REPEL_STRENGTH
        self.force_link = LINK_STRENGTH
        self.force_link_dist = LINK_DISTANCE

        # Slider definitions: (attr_name, label, min, max, default)
        self._slider_defs = [
            ("force_center",    "Center Force",   0.0,    0.05,   CENTER_STRENGTH),
            ("force_repel",     "Repel Force",    0.0,    15000.0, REPEL_STRENGTH),
            ("force_link",      "Link Force",     0.0,    0.2,    LINK_STRENGTH),
            ("force_link_dist", "Link Distance",  50.0,   300.0,  LINK_DISTANCE),
        ]
        self._slider_rects = {}   # attr_name -> pygame.Rect (track area)
        self._dragging_slider = None  # attr_name of slider being dragged

        # Drag state
        self.dragging_node = None  # spell_id being dragged on canvas
        self.dragging_from_list = None  # spell_id being dragged from spell list
        self.drag_pos = (0, 0)

        # Connection drawing (right-click drag)
        self.drawing_connection_from = None  # spell_id

        # Hover state
        self.hovered_node = None  # spell_id
        self.hovered_spell_index = -1
        self.hovered_connection = None  # (spell_id_a, spell_id_b)

        # Search state
        self.search_text = ""
        self.search_active = False

        # Scroll state for spell list
        self.spell_list_scroll = 0
        self.max_visible_spells = 8

        # Double-click detection
        self.last_click_time = 0
        self.last_click_pos = (0, 0)

        # Colors
        self.bg_color = (20, 22, 28)
        self.panel_bg = (30, 35, 45)
        self.panel_border = (50, 60, 80)
        self.text_color = (220, 220, 220)
        self.text_dim = (140, 140, 150)
        self.accent_color = (80, 120, 200)
        self.node_color = (60, 70, 90)
        self.node_hover_color = (80, 100, 140)
        self.node_selected_color = (100, 150, 220)
        self.connection_color = (70, 80, 100)
        self.connection_hover_color = (150, 100, 100)
        self.drawing_connection_color = (100, 200, 150)
        self.canvas_bg_color = (25, 28, 35)
        self.canvas_border_color = (50, 55, 70)
        self.button_color = (50, 60, 80)
        self.button_hover_color = (70, 85, 115)
        self.symbol_color = (180, 200, 255)
        self.search_bg_color = (40, 45, 55)
        self.warning_color = (200, 120, 80)
        self.x_button_color = (180, 80, 80)

        # Fonts (lazy init)
        self.font = None
        self.title_font = None
        self.symbol_font = None
        self.small_font = None

        # Clickable regions (populated during render)
        self.spell_list_rects = []
        self.button_rects = {}

    def _init_fonts(self):
        """Initialize fonts if needed."""
        if self.font is not None:
            return
        pygame.font.init()
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 20)

        cjk_fonts = ["microsoftyahei", "yugothic", "msgothic", "simsun"]
        self.symbol_font = None
        for font_name in cjk_fonts:
            try:
                self.symbol_font = pygame.font.SysFont(font_name, 36)
                test = self.symbol_font.render("\u706b", True, (255, 255, 255))
                if test.get_width() > 5:
                    break
            except Exception:
                continue
        if self.symbol_font is None:
            self.symbol_font = pygame.font.Font(None, 36)

    def open(self, layout, known_spell_ids):
        """Open the editor with a NodeMenuLayout to edit."""
        self._init_fonts()
        self.is_open = True
        self.layout = layout
        self.original_layout = layout.copy()
        self.known_spells = list(known_spell_ids)

        self.dragging_node = None
        self.dragging_from_list = None
        self.drawing_connection_from = None
        self.hovered_node = None
        self.hovered_spell_index = -1
        self.hovered_connection = None
        self.spell_list_scroll = 0
        self.search_text = ""
        self.search_active = False

        # Initialize velocities for existing nodes and start simulation frozen
        self.node_velocities = {sid: [0.0, 0.0] for sid in self.layout.nodes}
        self.alpha = ALPHA_START
        self._dragging_slider = None

    def close(self, save=True):
        """Close the editor."""
        self.is_open = False
        self.layout = None
        self.original_layout = None
        self.search_active = False

    def handle_input(self, input_handler, events):
        """Handle input for the editor. Returns action string or None."""
        if not self.is_open:
            return None

        mouse_x, mouse_y = input_handler.get_mouse_position()

        # Handle text input for search
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.search_active:
                    self._handle_search_input(event)

        # Handle slider dragging (must be before other click handling)
        if self._dragging_slider is not None:
            # Continue dragging as long as mouse is held
            if pygame.mouse.get_pressed()[0]:
                self._update_slider_value(self._dragging_slider, mouse_x)
                self._reheat_alpha()
                return None
            else:
                self._dragging_slider = None

        # Update hover states
        self._update_hover(mouse_x, mouse_y)

        # Update physics
        self._update_physics()

        # ESC handling
        if input_handler.toggle_pause:
            if self.search_active:
                self.search_active = False
                self.search_text = ""
                return None
            if self.dragging_node or self.dragging_from_list:
                self._cancel_drag()
                return None
            if self.drawing_connection_from:
                self.drawing_connection_from = None
                return None
            self.close(save=True)
            return "back_to_menu"

        # Handle connection drawing (right-click drag)
        if self.drawing_connection_from is not None:
            self.drag_pos = (mouse_x, mouse_y)
            if not pygame.mouse.get_pressed()[2]:
                # Right mouse released — check if over a node
                target = self._get_node_at(mouse_x, mouse_y)
                if target and target != self.drawing_connection_from:
                    self.layout.add_connection(self.drawing_connection_from, target)
                    self._reheat_alpha()
                self.drawing_connection_from = None
            return None

        # Handle node dragging
        if self.dragging_node is not None:
            # Move the node to follow mouse (relative to canvas)
            nx = mouse_x - self.canvas_x
            ny = mouse_y - self.canvas_y

            if self._is_over_canvas(mouse_x, mouse_y):
                # Clamp to canvas bounds only while inside — node stays in bounds
                nx = max(BOUNDARY_MARGIN, min(CANVAS_WIDTH - BOUNDARY_MARGIN, nx))
                ny = max(BOUNDARY_MARGIN, min(CANVAS_HEIGHT - BOUNDARY_MARGIN, ny))
            # When outside canvas, let the node follow freely (visual feedback for deletion)

            self.layout.move_spell(self.dragging_node, nx, ny)
            self.node_velocities[self.dragging_node] = [0.0, 0.0]

            if not pygame.mouse.get_pressed()[0]:
                # Mouse released — check if dropped off canvas (delete the node)
                if not self._is_over_canvas(mouse_x, mouse_y):
                    self.layout.remove_spell(self.dragging_node)
                    self.node_velocities.pop(self.dragging_node, None)
                else:
                    # Snap back into bounds if somehow slightly outside
                    pos = self.layout.nodes.get(self.dragging_node)
                    if pos:
                        pos["x"] = max(BOUNDARY_MARGIN, min(CANVAS_WIDTH - BOUNDARY_MARGIN, pos["x"]))
                        pos["y"] = max(BOUNDARY_MARGIN, min(CANVAS_HEIGHT - BOUNDARY_MARGIN, pos["y"]))
                self._reheat_alpha()
                self.dragging_node = None
            return None

        # Handle drag from spell list
        if self.dragging_from_list is not None:
            self.drag_pos = (mouse_x, mouse_y)

            if not pygame.mouse.get_pressed()[0]:
                # Mouse released — check if dropped on canvas
                if self._is_over_canvas(mouse_x, mouse_y):
                    nx = mouse_x - self.canvas_x
                    ny = mouse_y - self.canvas_y
                    if self.layout.add_spell(self.dragging_from_list, nx, ny):
                        self.node_velocities[self.dragging_from_list] = [0.0, 0.0]
                        self._reheat_alpha()
                self.dragging_from_list = None
            return None

        # Right-click handling
        if input_handler.mouse_right_clicked:
            # Check if right-clicking a node (start connection drawing)
            node = self._get_node_at(mouse_x, mouse_y)
            if node:
                self.drawing_connection_from = node
                self.drag_pos = (mouse_x, mouse_y)
                return None

            # Check if right-clicking a connection line (delete it)
            conn = self._find_connection_at(mouse_x, mouse_y)
            if conn:
                self.layout.remove_connection(conn[0], conn[1])
                self._reheat_alpha()
                return None

        # Left-click handling
        if input_handler.mouse_clicked:
            # Check search box
            search_rect = self.button_rects.get("search_box")
            if search_rect and search_rect.collidepoint(mouse_x, mouse_y):
                self.search_active = True
                return None

            if self.search_active:
                self.search_active = False

            # Check slider tracks — start dragging
            for attr, (hit_rect, track_rect) in self._slider_rects.items():
                if hit_rect.collidepoint(mouse_x, mouse_y):
                    self._dragging_slider = attr
                    self._update_slider_value(attr, mouse_x)
                    self._reheat_alpha()
                    return None

            # Check buttons
            for name, rect in self.button_rects.items():
                if name == "search_box":
                    continue
                if rect.collidepoint(mouse_x, mouse_y):
                    return self._handle_button_click(name)

            # Check if clicking X button on a hovered node (delete it)
            x_node = self._get_x_button_at(mouse_x, mouse_y)
            if x_node and self.hovered_node == x_node:
                self.layout.remove_spell(x_node)
                self.node_velocities.pop(x_node, None)
                self.hovered_node = None
                self._reheat_alpha()
                return None

            # Check if clicking a node on canvas (start dragging — center node is pinned)
            node = self._get_node_at(mouse_x, mouse_y)
            if node and node != CENTER_NODE_ID:
                self.dragging_node = node
                self._reheat_alpha()  # Neighbors should react while dragging
                return None

            # Check if clicking a connection line (left-click drag to detach)
            conn = self._find_connection_at(mouse_x, mouse_y)
            if conn:
                # Remove the connection on left click
                self.layout.remove_connection(conn[0], conn[1])
                self._reheat_alpha()
                return None

            # Check spell list (start drag from list)
            for rect, spell_id in self.spell_list_rects:
                if rect.collidepoint(mouse_x, mouse_y):
                    if not self.layout.has_spell(spell_id):
                        self.dragging_from_list = spell_id
                        self.drag_pos = (mouse_x, mouse_y)
                    return None

        # Scroll wheel for spell list
        for event in events:
            if event.type == pygame.MOUSEWHEEL:
                if self._is_over_spell_list(mouse_x, mouse_y):
                    self._scroll_spell_list(event.y)

        return None

    def _cancel_drag(self):
        """Cancel any active drag operation."""
        if self.dragging_node and self.dragging_node in self.layout.nodes:
            # Return node to its position (already there)
            pass
        self.dragging_node = None
        self.dragging_from_list = None
        self.drawing_connection_from = None

    def _handle_search_input(self, event):
        """Handle keyboard input for search."""
        if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
            self.search_active = False
        elif event.key == pygame.K_BACKSPACE:
            self.search_text = self.search_text[:-1]
        elif event.unicode and len(self.search_text) < 20:
            if event.unicode.isprintable():
                self.search_text += event.unicode

    def _handle_button_click(self, name):
        """Handle button clicks."""
        if name == "done":
            self.close(save=True)
            return "back_to_menu"
        elif name == "switch_to_dial":
            self.close(save=True)
            return "switch_to_dial"
        elif name == "clear_all":
            self.layout.nodes.clear()
            self.layout.connections.clear()
            self.node_velocities.clear()
            self.layout._ensure_center_node()  # Re-add the permanent center node
        elif name == "reset_forces":
            for attr, _label, _mn, _mx, default in self._slider_defs:
                setattr(self, attr, default)
            self._reheat_alpha()
        return None

    def _update_slider_value(self, attr_name, mouse_x):
        """Update a force slider based on mouse x position on its track."""
        entry = self._slider_rects.get(attr_name)
        if not entry:
            return
        _hit_rect, track_rect = entry

        # Map mouse_x to 0..1 along the track
        t = (mouse_x - track_rect.left) / max(track_rect.width, 1)
        t = max(0.0, min(1.0, t))

        # Find this slider's min/max
        for attr, _label, val_min, val_max, _default in self._slider_defs:
            if attr == attr_name:
                setattr(self, attr, val_min + t * (val_max - val_min))
                break

    def _scroll_spell_list(self, direction):
        """Scroll the spell list."""
        filtered = self._get_filtered_spells()
        self.spell_list_scroll -= direction * 2
        max_scroll = max(0, len(filtered) - self.max_visible_spells)
        self.spell_list_scroll = max(0, min(self.spell_list_scroll, max_scroll))

    def _update_hover(self, mouse_x, mouse_y):
        """Update hover states.

        The hover hitbox for nodes is extended to include the X button area
        (top-right corner, slightly outside the node circle) so the X button
        doesn't disappear before the user can click it.
        """
        self.hovered_node = self._get_node_at_extended(mouse_x, mouse_y)
        self.hovered_connection = None
        self.hovered_spell_index = -1

        if not self.hovered_node and self.dragging_node is None:
            self.hovered_connection = self._find_connection_at(mouse_x, mouse_y)

        if self.dragging_node is None and self.dragging_from_list is None:
            for i, (rect, spell_id) in enumerate(self.spell_list_rects):
                if rect.collidepoint(mouse_x, mouse_y):
                    self.hovered_spell_index = i
                    break

    def _is_over_canvas(self, mouse_x, mouse_y):
        """Check if mouse is over the canvas area."""
        return (self.canvas_x <= mouse_x <= self.canvas_x + CANVAS_WIDTH and
                self.canvas_y <= mouse_y <= self.canvas_y + CANVAS_HEIGHT)

    def _is_over_spell_list(self, mouse_x, mouse_y):
        """Check if mouse is over the spell list panel."""
        return pygame.Rect(self.left_panel_x, 100, self.panel_width, 400).collidepoint(mouse_x, mouse_y)

    def _get_node_at(self, mouse_x, mouse_y):
        """Get the spell_id of the node at mouse position (circle hitbox), or None."""
        if not self.layout:
            return None
        for spell_id, pos in self.layout.nodes.items():
            nx = self.canvas_x + pos["x"]
            ny = self.canvas_y + pos["y"]
            dx = mouse_x - nx
            dy = mouse_y - ny
            if dx * dx + dy * dy <= NODE_RADIUS * NODE_RADIUS:
                return spell_id
        return None

    def _get_node_at_extended(self, mouse_x, mouse_y):
        """Get node at mouse position, with extended hitbox that includes the X button area."""
        # First check the standard circle hitbox
        node = self._get_node_at(mouse_x, mouse_y)
        if node:
            return node

        # Check extended area around each node's X button (top-right, 10px radius circle)
        # Center node has no X button, so skip it
        if not self.layout:
            return None
        for spell_id, pos in self.layout.nodes.items():
            if spell_id == CENTER_NODE_ID:
                continue
            nx = self.canvas_x + pos["x"]
            ny = self.canvas_y + pos["y"]
            x_cx = nx + NODE_RADIUS - 8
            x_cy = ny - NODE_RADIUS + 8
            dx = mouse_x - x_cx
            dy = mouse_y - x_cy
            # 14px radius hit area around the X button (a bit generous)
            if dx * dx + dy * dy <= 14 * 14:
                return spell_id
        return None

    def _get_x_button_at(self, mouse_x, mouse_y):
        """Check if the mouse is over a node's X (delete) button. Returns spell_id or None.
        Center node has no X button."""
        if not self.layout:
            return None
        for spell_id, pos in self.layout.nodes.items():
            if spell_id == CENTER_NODE_ID:
                continue  # Center node can't be deleted
            nx = self.canvas_x + pos["x"]
            ny = self.canvas_y + pos["y"]
            x_cx = nx + NODE_RADIUS - 8
            x_cy = ny - NODE_RADIUS + 8
            dx = mouse_x - x_cx
            dy = mouse_y - x_cy
            if dx * dx + dy * dy <= 12 * 12:
                return spell_id
        return None

    def _find_connection_at(self, mouse_x, mouse_y):
        """Find a connection line near the mouse. Returns (id_a, id_b) or None."""
        if not self.layout:
            return None

        for spell_a, spell_b in self.layout.connections:
            pos_a = self.layout.nodes.get(spell_a)
            pos_b = self.layout.nodes.get(spell_b)
            if not pos_a or not pos_b:
                continue

            ax = self.canvas_x + pos_a["x"]
            ay = self.canvas_y + pos_a["y"]
            bx = self.canvas_x + pos_b["x"]
            by = self.canvas_y + pos_b["y"]

            dist = _point_to_segment_distance(mouse_x, mouse_y, ax, ay, bx, by)
            if dist <= CONNECTION_HIT_DISTANCE:
                return (spell_a, spell_b)
        return None

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
            if (search_lower in spell_id.lower() or
                    search_lower in symbol.name.lower() or
                    search_lower in symbol.character):
                results.append(spell_id)
        return results

    # --- Physics (d3-force model) ---

    def _reheat_alpha(self, value=None):
        """Kick simulation temperature back up so the graph reorganizes.

        Called on any user interaction that changes the graph topology or
        positions (add/remove node, add/remove connection, drag release, etc.).
        """
        self.alpha = max(self.alpha, value if value is not None else ALPHA_REHEAT)

    def _update_physics(self, dt=0.016):
        """Force-directed graph layout, modeled after d3-force / Obsidian graph.

        Four independent forces, all scaled by alpha (simulation temperature):
          1. Center force  — linear pull toward canvas center
          2. Repel force   — inverse-square push between every node pair
          3. Link force    — Hooke spring along connections toward LINK_DISTANCE
          4. (Implicit)    — velocity decay acts as friction each frame

        Alpha decays each tick toward ALPHA_MIN.  Once alpha ≈ 0, forces are
        effectively zero and the graph freezes in place.  User interactions
        call _reheat_alpha() to restart the simulation.
        """
        if not self.layout or len(self.layout.nodes) == 0:
            return

        # --- Alpha decay ---
        self.alpha += (ALPHA_MIN - self.alpha) * ALPHA_DECAY
        if self.alpha < ALPHA_MIN:
            self.alpha = ALPHA_MIN
            return  # Simulation frozen — skip all force computation

        node_ids = list(self.layout.nodes.keys())
        center_x = CANVAS_WIDTH / 2.0
        center_y = CANVAS_HEIGHT / 2.0

        for spell_id in node_ids:
            # Skip immovable nodes: center anchor is pinned, dragged node follows mouse
            if spell_id == CENTER_NODE_ID or spell_id == self.dragging_node:
                continue

            pos = self.layout.nodes.get(spell_id)
            if not pos:
                continue

            fx, fy = 0.0, 0.0

            # ---- 1. Center force ----
            # Linear pull toward canvas center, strength proportional to distance
            dx_c = center_x - pos["x"]
            dy_c = center_y - pos["y"]
            fx += dx_c * self.force_center
            fy += dy_c * self.force_center

            # ---- 2. Repel force (charge) ----
            # Inverse-square repulsion from every other node.  Always pushes,
            # just falls off naturally with distance — no threshold switching.
            for other_id in node_ids:
                if other_id == spell_id:
                    continue
                other_pos = self.layout.nodes.get(other_id)
                if not other_pos:
                    continue

                dx = pos["x"] - other_pos["x"]
                dy = pos["y"] - other_pos["y"]
                dist_sq = dx * dx + dy * dy
                dist = max(math.sqrt(dist_sq), 1.0)

                # Force magnitude: repel / dist².  Capped to avoid explosion.
                force = min(self.force_repel / max(dist_sq, 100.0), 600.0)
                fx += (dx / dist) * force
                fy += (dy / dist) * force

            # ---- 3. Link force (springs on connections) ----
            # Hooke's law: force = LINK_STRENGTH * (distance - LINK_DISTANCE)
            # Pulls if too far, pushes if too close.
            for conn in self.layout.connections:
                if spell_id not in conn:
                    continue
                other_id = conn[0] if conn[1] == spell_id else conn[1]
                other_pos = self.layout.nodes.get(other_id)
                if not other_pos:
                    continue

                dx = other_pos["x"] - pos["x"]
                dy = other_pos["y"] - pos["y"]
                dist = max(math.sqrt(dx * dx + dy * dy), 1.0)
                displacement = dist - self.force_link_dist
                # Spring force toward the target distance
                force = displacement * self.force_link
                fx += (dx / dist) * force
                fy += (dy / dist) * force

            # ---- Apply forces (scaled by alpha) + velocity decay ----
            vel = self.node_velocities.get(spell_id)
            if vel is None:
                vel = [0.0, 0.0]
                self.node_velocities[spell_id] = vel

            vel[0] = (vel[0] + fx * self.alpha) * VELOCITY_DECAY
            vel[1] = (vel[1] + fy * self.alpha) * VELOCITY_DECAY

            # Clamp velocity
            speed = math.sqrt(vel[0] * vel[0] + vel[1] * vel[1])
            if speed > MAX_VELOCITY:
                vel[0] *= MAX_VELOCITY / speed
                vel[1] *= MAX_VELOCITY / speed

            # Update position (clamped to canvas)
            pos["x"] = max(BOUNDARY_MARGIN, min(CANVAS_WIDTH - BOUNDARY_MARGIN,
                                                 pos["x"] + vel[0]))
            pos["y"] = max(BOUNDARY_MARGIN, min(CANVAS_HEIGHT - BOUNDARY_MARGIN,
                                                 pos["y"] + vel[1]))

    # --- Rendering ---

    def render(self, screen):
        """Render the editor."""
        if not self.is_open:
            return

        self._init_fonts()

        # Clear clickable regions
        self.spell_list_rects = []
        self.button_rects = {}

        # Background
        screen.fill(self.bg_color)

        # Title
        title = self.title_font.render("Node Spell Layout", True, self.text_color)
        screen.blit(title, (self.screen_width // 2 - title.get_width() // 2, 15))

        # Panels
        self._render_spell_list(screen)
        self._render_canvas(screen)
        self._render_force_sliders(screen)
        self._render_buttons(screen)
        self._render_instructions(screen)

        # Drag preview
        if self.dragging_from_list:
            self._render_drag_preview(screen)

        # Connection being drawn
        if self.drawing_connection_from is not None:
            self._render_drawing_connection(screen)

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

        search_display = self.search_text if self.search_text else "Search spells..."
        search_color = self.text_color if self.search_text else self.text_dim
        search_surf = self.small_font.render(search_display, True, search_color)
        screen.blit(search_surf, (search_rect.left + 8, search_rect.centery - search_surf.get_height() // 2))

        if self.search_active:
            cursor_x = search_rect.left + 8 + self.small_font.size(self.search_text)[0]
            pygame.draw.line(screen, self.text_color, (cursor_x, search_rect.top + 5),
                             (cursor_x, search_rect.bottom - 5), 2)

        self.button_rects["search_box"] = search_rect

        # Counts
        assigned = self.layout.get_all_assigned_spells() if self.layout else set()
        count_text = f"{len(assigned)}/{NodeMenuLayout.MAX_SPELLS} placed"
        count_surf = self.small_font.render(count_text, True, self.text_dim)
        screen.blit(count_surf, (panel_rect.centerx - count_surf.get_width() // 2, search_y + 32))

        # Spell list items
        list_y = search_y + 55
        item_height = 45

        filtered = self._get_filtered_spells()
        visible_start = self.spell_list_scroll
        visible_end = visible_start + self.max_visible_spells

        for i, spell_id in enumerate(filtered[visible_start:visible_end]):
            actual_index = visible_start + i
            y = list_y + i * item_height

            symbol = MagicSystem.get_symbol(spell_id)
            if not symbol:
                continue

            is_assigned = spell_id in assigned
            item_rect = pygame.Rect(panel_rect.left + 10, y, panel_rect.width - 20, item_height - 5)

            if actual_index == self.hovered_spell_index and self.dragging_node is None:
                bg = self.node_hover_color
            elif is_assigned:
                bg = (40, 45, 55)
            else:
                bg = self.node_color

            pygame.draw.rect(screen, bg, item_rect, border_radius=5)

            char_surf = self.symbol_font.render(symbol.character, True,
                                                 self.text_dim if is_assigned else self.symbol_color)
            screen.blit(char_surf, (item_rect.left + 5, item_rect.centery - char_surf.get_height() // 2))

            name_color = self.text_dim if is_assigned else self.text_color
            name_surf = self.small_font.render(symbol.name[:12], True, name_color)
            screen.blit(name_surf, (item_rect.left + 42, item_rect.centery - name_surf.get_height() // 2))

            if is_assigned:
                used_surf = self.small_font.render("(placed)", True, self.text_dim)
                screen.blit(used_surf, (item_rect.right - used_surf.get_width() - 5,
                                        item_rect.centery - used_surf.get_height() // 2))

            self.spell_list_rects.append((item_rect, spell_id))

        # Scroll indicators
        if self.spell_list_scroll > 0:
            up_surf = self.small_font.render("^ scroll up ^", True, self.text_dim)
            screen.blit(up_surf, (panel_rect.centerx - up_surf.get_width() // 2, list_y - 15))

        if visible_end < len(filtered):
            down_surf = self.small_font.render("v scroll down v", True, self.text_dim)
            screen.blit(down_surf, (panel_rect.centerx - down_surf.get_width() // 2,
                                    panel_rect.bottom - 20))

    def _render_canvas(self, screen):
        """Render the node canvas with nodes and connections."""
        if not self.layout:
            return

        # Canvas background
        canvas_rect = pygame.Rect(self.canvas_x, self.canvas_y, CANVAS_WIDTH, CANVAS_HEIGHT)
        pygame.draw.rect(screen, self.canvas_bg_color, canvas_rect, border_radius=10)
        pygame.draw.rect(screen, self.canvas_border_color, canvas_rect, 2, border_radius=10)

        # Draw connections
        for spell_a, spell_b in self.layout.connections:
            pos_a = self.layout.nodes.get(spell_a)
            pos_b = self.layout.nodes.get(spell_b)
            if not pos_a or not pos_b:
                continue

            ax = int(self.canvas_x + pos_a["x"])
            ay = int(self.canvas_y + pos_a["y"])
            bx = int(self.canvas_x + pos_b["x"])
            by = int(self.canvas_y + pos_b["y"])

            is_hovered = (self.hovered_connection and
                          set(self.hovered_connection) == {spell_a, spell_b})
            color = self.connection_hover_color if is_hovered else self.connection_color
            width = 3 if is_hovered else 2

            pygame.draw.line(screen, color, (ax, ay), (bx, by), width)

        # Draw nodes
        for spell_id, pos in self.layout.nodes.items():
            nx = int(self.canvas_x + pos["x"])
            ny = int(self.canvas_y + pos["y"])

            # --- Center anchor node: same size, distinct look, no kanji, no X ---
            if spell_id == CENTER_NODE_ID:
                is_hovered = self.hovered_node == spell_id
                center_color = (65, 75, 100) if not is_hovered else (85, 100, 135)
                pygame.draw.circle(screen, center_color, (nx, ny), NODE_RADIUS)
                pygame.draw.circle(screen, (90, 100, 130), (nx, ny), NODE_RADIUS, 2)
                # Small crosshair / dot pattern to mark it as the anchor
                pygame.draw.circle(screen, (110, 120, 150), (nx, ny), 6)
                pygame.draw.line(screen, (90, 100, 130), (nx - 12, ny), (nx + 12, ny), 1)
                pygame.draw.line(screen, (90, 100, 130), (nx, ny - 12), (nx, ny + 12), 1)
                continue

            is_hovered = self.hovered_node == spell_id
            is_dragging = self.dragging_node == spell_id

            if is_dragging:
                color = self.node_selected_color
            elif is_hovered:
                color = self.node_hover_color
            else:
                color = self.node_color

            # Node circle
            pygame.draw.circle(screen, color, (nx, ny), NODE_RADIUS)
            pygame.draw.circle(screen, self.panel_border, (nx, ny), NODE_RADIUS, 2)

            # Kanji symbol
            symbol = MagicSystem.get_symbol(spell_id)
            if symbol:
                char_surf = self.symbol_font.render(symbol.character, True, self.symbol_color)
                char_rect = char_surf.get_rect(center=(nx, ny))
                screen.blit(char_surf, char_rect)

            # X button on hover (top-right of node)
            if is_hovered and not self.dragging_node:
                x_cx = nx + NODE_RADIUS - 8
                x_cy = ny - NODE_RADIUS + 8
                pygame.draw.circle(screen, self.x_button_color, (x_cx, x_cy), 10)
                x_surf = self.small_font.render("x", True, self.text_color)
                screen.blit(x_surf, x_surf.get_rect(center=(x_cx, x_cy)))

        # Node count (exclude center anchor)
        spell_node_count = sum(1 for k in self.layout.nodes if k != CENTER_NODE_ID)
        count_text = f"{spell_node_count}/{NodeMenuLayout.MAX_SPELLS} nodes"
        count_surf = self.small_font.render(count_text, True, self.text_dim)
        screen.blit(count_surf, (self.canvas_x + 10, self.canvas_y + CANVAS_HEIGHT + 5))

    def _render_buttons(self, screen):
        """Render control buttons."""
        # Switch to Dial View button (top right)
        switch_rect = pygame.Rect(self.screen_width - 180, 15, 160, 30)
        pygame.draw.rect(screen, self.button_color, switch_rect, border_radius=5)
        switch_surf = self.small_font.render("Switch to Dial View", True, self.text_color)
        screen.blit(switch_surf, switch_surf.get_rect(center=switch_rect.center))
        self.button_rects["switch_to_dial"] = switch_rect

        # Clear All button
        clear_rect = pygame.Rect(self.canvas_x + CANVAS_WIDTH - 130, self.canvas_y + CANVAS_HEIGHT + 5, 120, 25)
        pygame.draw.rect(screen, self.warning_color, clear_rect, border_radius=5)
        clear_surf = self.small_font.render("Clear All", True, self.text_color)
        screen.blit(clear_surf, clear_surf.get_rect(center=clear_rect.center))
        self.button_rects["clear_all"] = clear_rect

        # Done button (bottom center)
        done_rect = pygame.Rect(self.screen_width // 2 - 50, self.screen_height - 50, 100, 35)
        pygame.draw.rect(screen, (60, 120, 80), done_rect, border_radius=5)
        done_surf = self.font.render("Done", True, self.text_color)
        screen.blit(done_surf, done_surf.get_rect(center=done_rect.center))
        self.button_rects["done"] = done_rect

        # Auto-save indicator
        auto_text = self.small_font.render("(changes save automatically)", True, self.text_dim)
        screen.blit(auto_text, (self.screen_width // 2 - auto_text.get_width() // 2,
                                self.screen_height - 12))

    def _render_force_sliders(self, screen):
        """Render the right-side panel with force adjustment sliders."""
        panel_rect = pygame.Rect(
            self.right_panel_x, 50,
            self.right_panel_width, self.screen_height - 100
        )
        pygame.draw.rect(screen, self.panel_bg, panel_rect, border_radius=8)
        pygame.draw.rect(screen, self.panel_border, panel_rect, 2, border_radius=8)

        # Panel title
        title = self.font.render("Forces", True, self.text_color)
        screen.blit(title, (panel_rect.centerx - title.get_width() // 2, panel_rect.top + 10))

        # Slider layout
        slider_y = panel_rect.top + 42
        slider_margin_x = 15
        slider_width = self.right_panel_width - slider_margin_x * 2
        track_height = 6
        thumb_radius = 8
        slider_spacing = 72

        for attr, label, val_min, val_max, default in self._slider_defs:
            current_val = getattr(self, attr)

            # Label
            label_surf = self.small_font.render(label, True, self.text_color)
            screen.blit(label_surf, (panel_rect.left + slider_margin_x, slider_y))

            # Value display
            if val_max >= 100:
                val_text = f"{current_val:.0f}"
            else:
                val_text = f"{current_val:.4f}"
            val_surf = self.small_font.render(val_text, True, self.text_dim)
            screen.blit(val_surf, (
                panel_rect.right - slider_margin_x - val_surf.get_width(),
                slider_y
            ))

            # Track
            track_y = slider_y + 22
            track_rect = pygame.Rect(
                panel_rect.left + slider_margin_x, track_y,
                slider_width, track_height
            )
            pygame.draw.rect(screen, (45, 50, 65), track_rect, border_radius=3)

            # Filled portion
            if val_max > val_min:
                t = (current_val - val_min) / (val_max - val_min)
            else:
                t = 0.0
            t = max(0.0, min(1.0, t))
            filled_width = int(slider_width * t)
            if filled_width > 0:
                filled_rect = pygame.Rect(
                    track_rect.left, track_y,
                    filled_width, track_height
                )
                pygame.draw.rect(screen, self.accent_color, filled_rect, border_radius=3)

            # Thumb
            thumb_x = track_rect.left + int(slider_width * t)
            thumb_y = track_y + track_height // 2
            is_active = self._dragging_slider == attr
            thumb_color = (120, 160, 240) if is_active else (100, 130, 200)
            pygame.draw.circle(screen, thumb_color, (thumb_x, thumb_y), thumb_radius)
            pygame.draw.circle(screen, self.text_color, (thumb_x, thumb_y), thumb_radius, 1)

            # Store track rect for hit detection (expanded vertically for easier clicking)
            hit_rect = pygame.Rect(
                track_rect.left - thumb_radius,
                track_y - thumb_radius - 4,
                slider_width + thumb_radius * 2,
                track_height + thumb_radius * 2 + 8
            )
            self._slider_rects[attr] = (hit_rect, track_rect)

            # Default marker (thin tick)
            if val_max > val_min:
                default_t = (default - val_min) / (val_max - val_min)
                default_x = track_rect.left + int(slider_width * default_t)
                pygame.draw.line(screen, self.text_dim,
                                 (default_x, track_y - 3),
                                 (default_x, track_y + track_height + 3), 1)

            slider_y += slider_spacing

        # Reset button
        reset_y = slider_y + 10
        reset_rect = pygame.Rect(
            panel_rect.left + slider_margin_x, reset_y,
            slider_width, 25
        )
        pygame.draw.rect(screen, self.button_color, reset_rect, border_radius=5)
        reset_surf = self.small_font.render("Reset Defaults", True, self.text_color)
        screen.blit(reset_surf, reset_surf.get_rect(center=reset_rect.center))
        self.button_rects["reset_forces"] = reset_rect

    def _render_instructions(self, screen):
        """Render usage instructions."""
        instructions = [
            "Drag spells from list onto canvas | Drag nodes off canvas to remove",
            "Right-click drag between nodes to connect | Right-click connection to delete",
            "Left-click connection to remove | Physics auto-arranges nodes",
        ]
        y = self.screen_height - 80
        for text in instructions:
            surf = self.small_font.render(text, True, self.text_dim)
            screen.blit(surf, (self.screen_width // 2 - surf.get_width() // 2, y))
            y += 16

    def _render_drag_preview(self, screen):
        """Render the spell being dragged from the list."""
        if not self.dragging_from_list:
            return

        x, y = self.drag_pos
        preview_surf = pygame.Surface((70, 70), pygame.SRCALPHA)
        pygame.draw.circle(preview_surf, (*self.node_color, 180), (35, 35), 30)

        symbol = MagicSystem.get_symbol(self.dragging_from_list)
        if symbol:
            char_surf = self.symbol_font.render(symbol.character, True, self.symbol_color)
            preview_surf.blit(char_surf, (35 - char_surf.get_width() // 2,
                                          35 - char_surf.get_height() // 2))

        screen.blit(preview_surf, (x - 35, y - 35))

    def _render_drawing_connection(self, screen):
        """Render the connection line being drawn."""
        if not self.drawing_connection_from:
            return

        pos = self.layout.nodes.get(self.drawing_connection_from)
        if not pos:
            return

        start_x = int(self.canvas_x + pos["x"])
        start_y = int(self.canvas_y + pos["y"])
        end_x, end_y = self.drag_pos

        pygame.draw.line(screen, self.drawing_connection_color,
                         (start_x, start_y), (end_x, end_y), 2)


def _point_to_segment_distance(px, py, ax, ay, bx, by):
    """Calculate the distance from point (px,py) to line segment (ax,ay)-(bx,by)."""
    dx = bx - ax
    dy = by - ay
    len_sq = dx * dx + dy * dy

    if len_sq == 0:
        # Segment is a point
        return math.sqrt((px - ax) ** 2 + (py - ay) ** 2)

    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len_sq))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return math.sqrt((px - proj_x) ** 2 + (py - proj_y) ** 2)
