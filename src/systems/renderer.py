"""
Rendering system for the game.
"""
import pygame
from ..core.settings import Settings
from .asset_manager import get_asset_manager
from .animation_manager import get_animation_manager, resolve_animation_state


class Renderer:
    """Handles all rendering operations."""

    def __init__(self, screen):
        self.screen = screen
        self.font = None
        self.small_font = None
        self.assets = get_asset_manager()
        self._init_fonts()

    def _init_fonts(self):
        """Initialize fonts."""
        pygame.font.init()
        self.assets.initialize()
        self.font = self.assets.get_font("default", 24)
        self.small_font = self.assets.get_font("default", 18)

    def clear(self):
        """Clear the screen."""
        self.screen.fill(Settings.COLOR_BG)

    def render_world(self, world, camera):
        """Render the world tiles and entities."""
        tile_size = Settings.TILE_SIZE

        # Calculate visible tile range
        start_x = max(0, int(camera.offset_x // tile_size) - 1)
        start_y = max(0, int(camera.offset_y // tile_size) - 1)
        end_x = min(world.width, start_x + (Settings.SCREEN_WIDTH // tile_size) + 3)
        end_y = min(world.height, start_y + (Settings.SCREEN_HEIGHT // tile_size) + 3)

        # Render tiles
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = world.get_tile(x, y)
                if tile:
                    screen_x, screen_y = camera.grid_to_screen(x, y)
                    rect = pygame.Rect(screen_x, screen_y, tile_size, tile_size)
                    pygame.draw.rect(self.screen, tile.color, rect)

        # Render grid lines if debug mode
        if Settings.SHOW_GRID:
            self._render_grid(world, camera, start_x, start_y, end_x, end_y)

        # Render entities (sorted by y for depth)
        visible_entities = []
        for entity in world.entities.values():
            if not entity.active:
                continue
            # Get screen position as float for smooth rendering
            screen_x, screen_y = camera.grid_to_screen(entity.x, entity.y)
            if -tile_size < screen_x < Settings.SCREEN_WIDTH + tile_size:
                if -tile_size < screen_y < Settings.SCREEN_HEIGHT + tile_size:
                    visible_entities.append((entity, screen_x, screen_y))

        # Sort by y position for proper depth
        visible_entities.sort(key=lambda e: e[0].y)

        for entity, screen_x, screen_y in visible_entities:
            # Projectiles use float coords for smooth AA rendering;
            # other entities use int coords (pixel-aligned shapes)
            if entity.has_tag("projectile"):
                self._render_entity(entity, screen_x, screen_y)
            else:
                self._render_entity(entity, int(screen_x), int(screen_y))

    def _render_grid(self, world, camera, start_x, start_y, end_x, end_y):
        """Render grid lines."""
        tile_size = Settings.TILE_SIZE
        grid_color = Settings.COLOR_GRID

        for y in range(start_y, end_y + 1):
            screen_y = y * tile_size - camera.offset_y
            pygame.draw.line(self.screen, grid_color,
                             (0, screen_y),
                             (Settings.SCREEN_WIDTH, screen_y))

        for x in range(start_x, end_x + 1):
            screen_x = x * tile_size - camera.offset_x
            pygame.draw.line(self.screen, grid_color,
                             (screen_x, 0),
                             (screen_x, Settings.SCREEN_HEIGHT))

    def _render_entity(self, entity, screen_x, screen_y):
        """Render a single entity."""
        tile_size = Settings.TILE_SIZE
        padding = 2

        # Different rendering based on entity type
        if entity.has_tag("player"):
            # Iframe blink for player
            if getattr(entity, 'iframe_timer', 0) > 0:
                if int(getattr(entity, 'iframe_timer', 0) / 0.05) % 2 == 0:
                    # Skip body rendering on blink frames, still render health bar
                    return

            # Try sprite-sheet frame first
            anim_mgr = get_animation_manager()
            frame = anim_mgr.get_player_frame(entity)
            if frame is not None:
                sprite_size = tile_size * 2
                scaled = anim_mgr.get_scaled_frame(frame, (sprite_size, sprite_size))
                offset = (sprite_size - tile_size) // 2
                self.screen.blit(scaled, (screen_x - offset, screen_y - offset))
            else:
                # Fallback: Player as circle
                center_x = screen_x + tile_size // 2
                center_y = screen_y + tile_size // 2
                pygame.draw.circle(self.screen, entity.color, (center_x, center_y), tile_size // 2 - padding)

                # Direction indicator
                facing_offsets = {
                    "up": (0, -8),
                    "down": (0, 8),
                    "left": (-8, 0),
                    "right": (8, 0)
                }
                if hasattr(entity, 'controller'):
                    facing = getattr(entity, 'facing', 'down')
                    offset = facing_offsets.get(facing, (0, 0))
                    indicator_x = center_x + offset[0]
                    indicator_y = center_y + offset[1]
                    pygame.draw.circle(self.screen, (255, 255, 255), (indicator_x, indicator_y), 3)

        elif entity.has_tag("effect"):
            # Effects as semi-transparent circles
            center_x = screen_x + tile_size // 2
            center_y = screen_y + tile_size // 2

            # Create a surface for transparency
            effect_surface = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
            color_with_alpha = entity.color + (128,)  # 50% transparent
            pygame.draw.circle(effect_surface, color_with_alpha,
                               (tile_size // 2, tile_size // 2), tile_size // 2 - padding)
            self.screen.blit(effect_surface, (screen_x, screen_y))

        elif entity.has_tag("tree"):
            # Tree as triangle (simple tree shape)
            points = [
                (screen_x + tile_size // 2, screen_y + padding),
                (screen_x + padding, screen_y + tile_size - padding),
                (screen_x + tile_size - padding, screen_y + tile_size - padding)
            ]
            pygame.draw.polygon(self.screen, entity.color, points)

        elif entity.has_tag("rock"):
            # Rock as octagon-ish shape
            rect = pygame.Rect(screen_x + padding * 2, screen_y + padding * 2,
                               tile_size - padding * 4, tile_size - padding * 4)
            pygame.draw.rect(self.screen, entity.color, rect, border_radius=6)

        elif entity.has_tag("log"):
            # Log as horizontal brown rectangle
            log_height = tile_size // 3
            log_y = screen_y + (tile_size - log_height) // 2
            rect = pygame.Rect(screen_x + padding, log_y, tile_size - padding * 2, log_height)
            pygame.draw.rect(self.screen, entity.color, rect, border_radius=4)
            # End circles for 3D effect
            pygame.draw.circle(self.screen, (120, 75, 35),
                             (screen_x + padding + 4, screen_y + tile_size // 2),
                             log_height // 2 - 2)
            pygame.draw.circle(self.screen, (120, 75, 35),
                             (screen_x + tile_size - padding - 4, screen_y + tile_size // 2),
                             log_height // 2 - 2)

        elif entity.has_tag("water"):
            # Water already rendered as tile, but add wave effect
            pass

        elif entity.has_tag("bush"):
            # Bush as small circle
            center_x = screen_x + tile_size // 2
            center_y = screen_y + tile_size // 2
            pygame.draw.circle(self.screen, entity.color, (center_x, center_y), tile_size // 3)

        elif entity.has_tag("npc"):
            # Try sprite-sheet frame first
            anim_mgr = get_animation_manager()
            frame = anim_mgr.get_npc_frame(entity)
            if frame is not None:
                sprite_size = tile_size * 2
                scaled = anim_mgr.get_scaled_frame(frame, (sprite_size, sprite_size))
                offset = (sprite_size - tile_size) // 2
                self.screen.blit(scaled, (screen_x - offset, screen_y - offset))
            else:
                # Fallback: NPC as diamond shape
                center_x = screen_x + tile_size // 2
                center_y = screen_y + tile_size // 2
                half = tile_size // 2 - padding
                points = [
                    (center_x, center_y - half),      # Top
                    (center_x + half, center_y),      # Right
                    (center_x, center_y + half),      # Bottom
                    (center_x - half, center_y),      # Left
                ]
                pygame.draw.polygon(self.screen, entity.color, points)
                # Add inner highlight
                inner_half = half - 4
                inner_points = [
                    (center_x, center_y - inner_half),
                    (center_x + inner_half, center_y),
                    (center_x, center_y + inner_half),
                    (center_x - inner_half, center_y),
                ]
                highlight_color = tuple(min(255, c + 40) for c in entity.color)
                pygame.draw.polygon(self.screen, highlight_color, inner_points)

        elif entity.has_tag("ground_item"):
            # Ground item as small colored diamond (1/4 tile size)
            center_x = screen_x + tile_size // 2
            center_y = screen_y + tile_size // 2
            half = tile_size // 4
            points = [
                (center_x, center_y - half),
                (center_x + half, center_y),
                (center_x, center_y + half),
                (center_x - half, center_y),
            ]
            pygame.draw.polygon(self.screen, entity.color, points)
            # Light outline for visibility
            outline_color = tuple(min(255, c + 60) for c in entity.color)
            pygame.draw.polygon(self.screen, outline_color, points, 1)

        elif entity.has_tag("rune_stone"):
            # Rune stone as glowing octagon
            center_x = screen_x + tile_size // 2
            center_y = screen_y + tile_size // 2
            radius = tile_size // 2 - padding
            # Draw octagon
            import math
            points = []
            for i in range(8):
                angle = math.pi / 8 + i * math.pi / 4  # Offset to have flat top
                px = center_x + int(radius * math.cos(angle))
                py = center_y + int(radius * math.sin(angle))
                points.append((px, py))
            pygame.draw.polygon(self.screen, entity.color, points)
            # Draw inner glow (if not dormant)
            if not getattr(entity, 'is_activated', False):
                glow_color = tuple(min(255, c + 60) for c in entity.color)
                inner_radius = radius - 6
                inner_points = []
                for i in range(8):
                    angle = math.pi / 8 + i * math.pi / 4
                    px = center_x + int(inner_radius * math.cos(angle))
                    py = center_y + int(inner_radius * math.sin(angle))
                    inner_points.append((px, py))
                pygame.draw.polygon(self.screen, glow_color, inner_points)

        elif entity.has_tag("projectile"):
            # Projectile as anti-aliased oriented line with arrowhead
            import math
            angle = getattr(entity, 'angle', 0)
            # Projectile position is already the precise world point (center of
            # the spawning entity), so grid_to_screen gives the exact pixel — no
            # additional tile-center offset needed.
            cx = screen_x
            cy = screen_y
            length = 10.0
            # Line from tail to tip (float coords for AA)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            tail_x = cx - cos_a * length * 0.5
            tail_y = cy - sin_a * length * 0.5
            tip_x = cx + cos_a * length * 0.5
            tip_y = cy + sin_a * length * 0.5
            # Anti-aliased main line
            pygame.draw.aaline(self.screen, entity.color, (tail_x, tail_y), (tip_x, tip_y))
            # Draw a second AA line offset by 1px for thickness
            perp_x = -sin_a * 0.5
            perp_y = cos_a * 0.5
            pygame.draw.aaline(self.screen, entity.color,
                               (tail_x + perp_x, tail_y + perp_y),
                               (tip_x + perp_x, tip_y + perp_y))
            pygame.draw.aaline(self.screen, entity.color,
                               (tail_x - perp_x, tail_y - perp_y),
                               (tip_x - perp_x, tip_y - perp_y))
            # Arrowhead circle at tip
            pygame.draw.circle(self.screen, (220, 200, 140), (int(tip_x), int(tip_y)), 3)

        elif entity.has_tag("enemy"):
            # Resolve sprite animation state (safe no-op if no controller)
            resolve_animation_state(entity)

            # Iframe blink: skip rendering every other frame during iframes
            show_body = True
            if getattr(entity, 'iframe_timer', 0) > 0:
                if int(getattr(entity, 'iframe_timer', 0) / 0.05) % 2 == 0:
                    show_body = False

            if show_body:
                # Try sprite-sheet frame first
                anim_mgr = get_animation_manager()
                frame = anim_mgr.get_current_frame(entity)
                if frame is not None:
                    self._render_enemy_sprite(entity, screen_x, screen_y, tile_size, frame)

            # Attack windup telegraph
            self._render_enemy_telegraph(entity, screen_x, screen_y, tile_size)

            # Health bar for enemies
            if hasattr(entity, 'stats'):
                size_mult = getattr(entity, 'size_multiplier', 1.0)
                bar_tile = int(tile_size * size_mult)
                health_pct = entity.stats.health / entity.stats.max_health
                bar_width = bar_tile - padding * 2
                bar_height = 4
                bar_x = screen_x + padding
                bar_y = screen_y - 6

                # Background
                pygame.draw.rect(self.screen, (50, 50, 50),
                               (bar_x, bar_y, bar_width, bar_height))
                # Health fill - flash red briefly on hit (iframe active)
                bar_color = (255, 80, 80) if getattr(entity, 'iframe_timer', 0) > 0 else (200, 50, 50)
                fill_width = int(bar_width * health_pct)
                if fill_width > 0:
                    pygame.draw.rect(self.screen, bar_color,
                                   (bar_x, bar_y, fill_width, bar_height))

        elif entity.has_tag("door"):
            # Door as rectangle with darker inner area
            rect = pygame.Rect(screen_x + padding, screen_y + padding,
                               tile_size - padding * 2, tile_size - padding * 2)
            pygame.draw.rect(self.screen, entity.color, rect)
            # Inner darker rectangle for depth
            inner_rect = pygame.Rect(screen_x + padding + 4, screen_y + padding + 4,
                                     tile_size - padding * 2 - 8, tile_size - padding * 2 - 8)
            darker_color = tuple(max(0, c - 30) for c in entity.color)
            pygame.draw.rect(self.screen, darker_color, inner_rect)
            # Door handle
            handle_x = screen_x + tile_size - padding - 8
            handle_y = screen_y + tile_size // 2
            pygame.draw.circle(self.screen, (180, 140, 80), (handle_x, handle_y), 3)

        elif entity.has_tag("fence"):
            # Fence as vertical bars
            bar_width = 3
            gap = 5
            for i in range(4):
                bar_x = screen_x + padding + i * (bar_width + gap)
                bar_rect = pygame.Rect(bar_x, screen_y + padding,
                                       bar_width, tile_size - padding * 2)
                pygame.draw.rect(self.screen, entity.color, bar_rect)
            # Horizontal bar across middle
            cross_rect = pygame.Rect(screen_x + padding, screen_y + tile_size // 2 - 2,
                                     tile_size - padding * 2, 4)
            pygame.draw.rect(self.screen, entity.color, cross_rect)

        elif entity.has_tag("well"):
            # Well as circle with dark center
            center_x = screen_x + tile_size // 2
            center_y = screen_y + tile_size // 2
            # Stone rim
            pygame.draw.circle(self.screen, entity.color, (center_x, center_y), tile_size // 2 - padding)
            # Dark water inside
            pygame.draw.circle(self.screen, (30, 40, 60), (center_x, center_y), tile_size // 3)

        elif entity.has_tag("crate"):
            # Crate as square with cross pattern
            rect = pygame.Rect(screen_x + padding, screen_y + padding,
                               tile_size - padding * 2, tile_size - padding * 2)
            pygame.draw.rect(self.screen, entity.color, rect)
            # Cross lines
            line_color = tuple(max(0, c - 40) for c in entity.color)
            # Vertical
            pygame.draw.line(self.screen, line_color,
                           (screen_x + tile_size // 2, screen_y + padding),
                           (screen_x + tile_size // 2, screen_y + tile_size - padding), 2)
            # Horizontal
            pygame.draw.line(self.screen, line_color,
                           (screen_x + padding, screen_y + tile_size // 2),
                           (screen_x + tile_size - padding, screen_y + tile_size // 2), 2)

        elif entity.has_tag("table"):
            # Table as rectangle with legs
            table_top = pygame.Rect(screen_x + padding, screen_y + padding + 6,
                                    tile_size - padding * 2, tile_size // 2)
            pygame.draw.rect(self.screen, entity.color, table_top)
            # Legs
            leg_color = tuple(max(0, c - 20) for c in entity.color)
            leg_width = 4
            leg_height = tile_size // 3
            leg_y = screen_y + tile_size // 2 + 6
            # Four legs
            pygame.draw.rect(self.screen, leg_color, (screen_x + padding + 2, leg_y, leg_width, leg_height))
            pygame.draw.rect(self.screen, leg_color, (screen_x + tile_size - padding - 6, leg_y, leg_width, leg_height))

        elif entity.has_tag("chair"):
            # Chair as smaller rectangle with back
            seat = pygame.Rect(screen_x + padding + 4, screen_y + tile_size // 2,
                               tile_size - padding * 2 - 8, tile_size // 4)
            pygame.draw.rect(self.screen, entity.color, seat)
            # Back
            back = pygame.Rect(screen_x + padding + 4, screen_y + padding + 4,
                               tile_size - padding * 2 - 8, tile_size // 4)
            pygame.draw.rect(self.screen, entity.color, back)
            # Legs
            leg_color = tuple(max(0, c - 20) for c in entity.color)
            leg_y = screen_y + tile_size // 2 + tile_size // 4
            pygame.draw.rect(self.screen, leg_color, (screen_x + padding + 6, leg_y, 3, tile_size // 4 - 2))
            pygame.draw.rect(self.screen, leg_color, (screen_x + tile_size - padding - 9, leg_y, 3, tile_size // 4 - 2))

        elif entity.has_tag("sign"):
            # Sign as rectangle on post
            post_x = screen_x + tile_size // 2 - 2
            post_rect = pygame.Rect(post_x, screen_y + tile_size // 2,
                                    4, tile_size // 2 - padding)
            pygame.draw.rect(self.screen, entity.color, post_rect)
            # Sign board
            board_rect = pygame.Rect(screen_x + padding, screen_y + padding,
                                     tile_size - padding * 2, tile_size // 2)
            pygame.draw.rect(self.screen, entity.color, board_rect)
            # Text lines (decoration)
            line_color = tuple(max(0, c - 60) for c in entity.color)
            pygame.draw.line(self.screen, line_color,
                           (screen_x + padding + 4, screen_y + padding + 8),
                           (screen_x + tile_size - padding - 4, screen_y + padding + 8), 2)
            pygame.draw.line(self.screen, line_color,
                           (screen_x + padding + 4, screen_y + padding + 14),
                           (screen_x + tile_size - padding - 8, screen_y + padding + 14), 2)

        elif entity.has_tag("enemy_spawner") or entity.has_tag("zone_transition"):
            # Invisible entities — no visual rendering
            pass

        else:
            # Default: colored rectangle
            rect = pygame.Rect(screen_x + padding, screen_y + padding,
                               tile_size - padding * 2, tile_size - padding * 2)
            pygame.draw.rect(self.screen, entity.color, rect)

        # Render burning effect
        if entity.has_component("EnvironmentalComponent"):
            env = entity.get_component("EnvironmentalComponent")
            if env.state == "burning":
                # Draw fire particles
                center_x = screen_x + tile_size // 2
                center_y = screen_y + tile_size // 4
                pygame.draw.circle(self.screen, (255, 100, 0), (center_x, center_y), 5)
                pygame.draw.circle(self.screen, (255, 200, 0), (center_x - 3, center_y + 3), 3)
                pygame.draw.circle(self.screen, (255, 150, 0), (center_x + 4, center_y + 2), 4)

    def _render_enemy_sprite(self, entity, screen_x, screen_y, tile_size, frame):
        """Render an enemy using a sprite-sheet frame."""
        anim_mgr = get_animation_manager()
        size_mult = getattr(entity, 'size_multiplier', 1.0)
        sprite_size = int(tile_size * 4 * size_mult)
        scaled = anim_mgr.get_scaled_frame(frame, (sprite_size, sprite_size))
        # Centre the larger sprite on the 1-tile collision position
        offset = (sprite_size - tile_size) // 2
        self.screen.blit(scaled, (screen_x - offset, screen_y - offset))

    def _render_enemy_telegraph(self, entity, screen_x, screen_y, tile_size):
        """Render attack windup telegraph for enemies."""
        if not hasattr(entity, 'brain'):
            return

        brain = entity.brain
        slot = brain.current_attack_slot
        if slot is None or not slot.is_winding_up:
            return

        attack_def = slot.attack_def
        telegraph_color = attack_def.get("telegraph_color", (255, 200, 100))
        attack_type = attack_def.get("type", "contact")

        center_x = screen_x + tile_size // 2
        center_y = screen_y + tile_size // 2

        # Windup progress (0 to 1)
        total_windup = attack_def.get("windup", 0.5)
        if total_windup > 0:
            progress = 1.0 - (slot.windup_timer / total_windup)
        else:
            progress = 1.0

        if attack_type == "aoe":
            # Pulsing ring at aoe_radius distance
            aoe_radius = attack_def.get("aoe_radius", 2.0)
            pixel_radius = int(aoe_radius * tile_size * progress)
            if pixel_radius > 0:
                telegraph_surf = pygame.Surface(
                    (pixel_radius * 2 + 4, pixel_radius * 2 + 4), pygame.SRCALPHA)
                alpha = int(120 * progress)
                color_a = telegraph_color + (alpha,)
                pygame.draw.circle(telegraph_surf, color_a,
                                 (pixel_radius + 2, pixel_radius + 2), pixel_radius, 3)
                self.screen.blit(telegraph_surf,
                               (center_x - pixel_radius - 2, center_y - pixel_radius - 2))
        elif attack_type == "projectile":
            # Aim line toward player (brief flash)
            if hasattr(entity, 'brain') and entity.brain.owner:
                import math
                world = None
                # Draw a short aim line in the facing direction
                facing = getattr(entity, 'facing', 'down')
                dir_map = {
                    "up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0),
                    "up_right": (1, -1), "up_left": (-1, -1),
                    "down_right": (1, 1), "down_left": (-1, 1),
                }
                dx, dy = dir_map.get(facing, (0, 1))
                line_len = int(tile_size * 1.5 * progress)
                alpha = int(180 * progress)
                end_x = center_x + dx * line_len
                end_y = center_y + dy * line_len
                telegraph_surf = pygame.Surface(
                    (abs(dx * line_len) + tile_size, abs(dy * line_len) + tile_size),
                    pygame.SRCALPHA)
                # Anti-aliased aim line
                pygame.draw.aaline(self.screen, telegraph_color,
                               (center_x, center_y), (end_x, end_y))
        else:
            # Melee/contact: expanding circle around enemy
            max_radius = int(tile_size * 0.8)
            current_radius = int(max_radius * progress)
            if current_radius > 0:
                telegraph_surf = pygame.Surface(
                    (current_radius * 2 + 4, current_radius * 2 + 4), pygame.SRCALPHA)
                alpha = int(100 * progress)
                color_a = telegraph_color + (alpha,)
                pygame.draw.circle(telegraph_surf, color_a,
                                 (current_radius + 2, current_radius + 2), current_radius, 2)
                self.screen.blit(telegraph_surf,
                               (center_x - current_radius - 2, center_y - current_radius - 2))

    def render_ui(self, player, game_state):
        """Render UI elements."""
        if player is None:
            return

        # Stats bar at bottom
        self._render_stats_bar(player)

        # Debug info
        if Settings.DEBUG_MODE:
            self._render_debug_info(player, game_state)

    def _render_stats_bar(self, player):
        """Render player stats bar."""
        bar_height = 85
        bar_y = Settings.SCREEN_HEIGHT - bar_height

        # Background
        bar_rect = pygame.Rect(0, bar_y, Settings.SCREEN_WIDTH, bar_height)
        pygame.draw.rect(self.screen, (30, 30, 35), bar_rect)
        pygame.draw.line(self.screen, (60, 60, 70), (0, bar_y), (Settings.SCREEN_WIDTH, bar_y), 2)

        stats = player.stats

        # Health bar - flash red on hit
        hp_color = (255, 80, 80) if getattr(player, 'iframe_timer', 0) > 0 else (200, 50, 50)
        self._render_bar(10, bar_y + 10, 200, 15, stats.health, stats.max_health,
                         hp_color, "HP")

        # Mana bar
        self._render_bar(10, bar_y + 35, 200, 15, stats.mana, stats.max_mana,
                         (50, 100, 200), "MP")

        # Stamina bar
        self._render_bar(10, bar_y + 60, 200, 15, stats.stamina, stats.max_stamina,
                         (50, 180, 50), "SP")

        # Selected symbols display
        symbols_text = "Magic: "
        if player.selected_symbols:
            symbols_text += " + ".join(player.selected_symbols)
        else:
            symbols_text += "(none selected)"

        symbol_surface = self.font.render(symbols_text, True, (200, 200, 200))
        self.screen.blit(symbol_surface, (230, bar_y + 32))

    def _render_bar(self, x, y, width, height, current, maximum, color, label):
        """Render a status bar."""
        # Background
        bg_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (50, 50, 55), bg_rect)

        # Fill
        if maximum > 0:
            fill_width = int((current / maximum) * width)
            fill_rect = pygame.Rect(x, y, fill_width, height)
            pygame.draw.rect(self.screen, color, fill_rect)

        # Border
        pygame.draw.rect(self.screen, (100, 100, 105), bg_rect, 1)

        # Label
        label_surface = self.small_font.render(f"{label}: {int(current)}/{int(maximum)}", True, (255, 255, 255))
        self.screen.blit(label_surface, (x + 5, y + 1))

    def _render_debug_info(self, player, game_state):
        """Render debug information."""
        # Show both float and tile positions for debugging
        tile_x, tile_y = player.get_tile()
        debug_lines = [
            f"FPS: {game_state.get('fps', 0):.0f}",
            f"Pos: ({player.x:.2f}, {player.y:.2f}) Tile: ({tile_x}, {tile_y})",
            f"Entities: {game_state.get('entity_count', 0)}",
            f"Effects: {game_state.get('effect_count', 0)}",
        ]

        y = 10
        for line in debug_lines:
            surface = self.small_font.render(line, True, (150, 150, 150))
            self.screen.blit(surface, (10, y))
            y += 16

    def render_message(self, message, duration_remaining=0):
        """Render a temporary message on screen."""
        if not message:
            return

        alpha = min(255, int(duration_remaining * 255))
        text_surface = self.font.render(message, True, (255, 255, 255))

        # Center horizontally
        x = (Settings.SCREEN_WIDTH - text_surface.get_width()) // 2
        y = Settings.SCREEN_HEIGHT // 3

        # Background
        padding = 10
        bg_rect = pygame.Rect(x - padding, y - padding,
                              text_surface.get_width() + padding * 2,
                              text_surface.get_height() + padding * 2)
        pygame.draw.rect(self.screen, (40, 40, 45), bg_rect, border_radius=5)
        pygame.draw.rect(self.screen, (80, 80, 85), bg_rect, 2, border_radius=5)

        self.screen.blit(text_surface, (x, y))
