"""
Rendering system for the game.
"""
import pygame
from ..core.settings import Settings
from .asset_manager import get_asset_manager


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
            screen_x, screen_y = camera.grid_to_screen(entity.x, entity.y)
            if -tile_size < screen_x < Settings.SCREEN_WIDTH + tile_size:
                if -tile_size < screen_y < Settings.SCREEN_HEIGHT + tile_size:
                    visible_entities.append((entity, screen_x, screen_y))

        # Sort by y position for proper depth
        visible_entities.sort(key=lambda e: e[0].y)

        for entity, screen_x, screen_y in visible_entities:
            self._render_entity(entity, screen_x, screen_y)

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
            # Player as circle
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
                # Get facing from actor
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
            # NPC as diamond shape
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
        bar_height = 60
        bar_y = Settings.SCREEN_HEIGHT - bar_height

        # Background
        bar_rect = pygame.Rect(0, bar_y, Settings.SCREEN_WIDTH, bar_height)
        pygame.draw.rect(self.screen, (30, 30, 35), bar_rect)
        pygame.draw.line(self.screen, (60, 60, 70), (0, bar_y), (Settings.SCREEN_WIDTH, bar_y), 2)

        stats = player.stats

        # Health bar
        self._render_bar(10, bar_y + 10, 200, 15, stats.health, stats.max_health,
                         (200, 50, 50), "HP")

        # Mana bar
        self._render_bar(10, bar_y + 35, 200, 15, stats.mana, stats.max_mana,
                         (50, 100, 200), "MP")

        # Selected symbols display
        symbols_text = "Magic: "
        if player.selected_symbols:
            symbols_text += " + ".join(player.selected_symbols)
        else:
            symbols_text += "(none selected)"

        symbol_surface = self.font.render(symbols_text, True, (200, 200, 200))
        self.screen.blit(symbol_surface, (230, bar_y + 20))

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
        debug_lines = [
            f"FPS: {game_state.get('fps', 0):.0f}",
            f"Pos: ({player.x}, {player.y})",
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
