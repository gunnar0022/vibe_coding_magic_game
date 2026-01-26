"""
Main game class - handles game loop and state management.
"""
import pygame
from .settings import Settings
from .camera import Camera
from ..world import World, MapLoader
from ..entities import Player, create_npc_from_template
from ..systems import InputHandler, Renderer, SaveSystem, create_save_data, apply_save_data
from ..ui import Notebook, MagicMenu
from ..magic import MagicSystem


class Game:
    """Main game class managing the game loop and systems."""

    def __init__(self):
        pygame.init()

        # Display setup
        self.screen = pygame.display.set_mode(
            (Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(Settings.TITLE)

        # Clock for frame timing
        self.clock = pygame.time.Clock()

        # Core systems
        self.input = InputHandler()
        self.camera = Camera()
        self.renderer = Renderer(self.screen)
        self.save_system = SaveSystem()

        # World and entities
        self.world = World()
        self.player = None

        # Player systems
        self.notebook = Notebook()
        self.magic_menu = MagicMenu(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)

        # Game state
        self.running = True
        self.paused = False
        self.current_message = ""
        self.message_timer = 0

        # UI state
        self.notebook_open = False
        self.magic_menu_open = False

        # Game state dict for UI
        self.game_state = {
            "fps": 0,
            "entity_count": 0,
            "effect_count": 0,
        }

        # Initialize world
        self._init_world()

    def _init_world(self):
        """Initialize the game world."""
        # Load test map
        player_spawn = MapLoader.create_test_map(self.world)

        # Create player at spawn point
        self.player = Player(player_spawn[0], player_spawn[1])
        self.world.add_entity(self.player)

        # Set camera to follow player
        self.camera.set_target(self.player)

        # Add a test NPC
        elder = create_npc_from_template("village_elder", player_spawn[0] + 3, player_spawn[1])
        self.world.add_entity(elder)

        # Give player some starting symbols for testing
        self._learn_symbol_with_notebook("fire", "Starting knowledge", "Your home village")
        self._learn_symbol_with_notebook("water", "Starting knowledge", "Your home village")
        self._learn_symbol_with_notebook("force", "Starting knowledge", "Your home village")

        self.show_message("Welcome to the world of magic. (Press H for help)")

    def _learn_symbol_with_notebook(self, symbol_id, context="", location=""):
        """Learn a symbol and record it in the notebook."""
        if self.player.learn_symbol(symbol_id):
            symbol = MagicSystem.get_symbol(symbol_id)
            symbol_data = symbol.to_dict() if symbol else {}
            self.notebook.record_symbol_discovery(symbol_id, context, location, symbol_data)
            return True
        return False

    def run(self):
        """Main game loop."""
        while self.running:
            # Calculate delta time
            dt = self.clock.tick(Settings.FPS) / 1000.0

            # Handle events
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            # Update input
            self.input.update(events)

            # Handle global input
            self._handle_global_input()

            # Update game state
            if not self.paused and not self.magic_menu_open:
                self.update(dt)
            elif self.magic_menu_open:
                self._handle_magic_menu_input()

            # Render
            self.render()

            # Update display
            pygame.display.flip()

        pygame.quit()

    def _handle_global_input(self):
        """Handle input that works regardless of game state."""
        # Escape closes menus or exits
        if self.input.cancel:
            if self.magic_menu_open:
                self.magic_menu.close()
                self.magic_menu_open = False
            elif self.notebook_open:
                self.notebook_open = False
            else:
                self.running = False

        # Help
        if self.input.was_key_pressed(pygame.K_h):
            self._show_help()

        # Quick save (F5)
        if self.input.was_key_pressed(pygame.K_F5):
            self._quick_save()

        # Quick load (F9)
        if self.input.was_key_pressed(pygame.K_F9):
            self._quick_load()

        # Toggle magic menu (Tab or M)
        if self.input.was_key_pressed(pygame.K_TAB) or self.input.was_key_pressed(pygame.K_m):
            self._toggle_magic_menu()

        # Toggle notebook (N)
        if self.input.was_key_pressed(pygame.K_n):
            self.notebook_open = not self.notebook_open
            if self.notebook_open:
                self.show_message("Notebook opened (placeholder UI)")

    def _handle_magic_menu_input(self):
        """Handle input when magic menu is open."""
        if self.input.was_key_pressed(pygame.K_UP) or self.input.was_key_pressed(pygame.K_w):
            self.magic_menu.navigate("up")
        elif self.input.was_key_pressed(pygame.K_DOWN) or self.input.was_key_pressed(pygame.K_s):
            self.magic_menu.navigate("down")
        elif self.input.was_key_pressed(pygame.K_RETURN) or self.input.was_key_pressed(pygame.K_e):
            result = self.magic_menu.select()
            if result:
                action, value = result
                if action == "symbol":
                    self.player.select_symbol(value)
                    self.show_message(f"Selected: {value}")
                    # Close menu after second symbol or if casting single
                    if len(self.player.selected_symbols) >= 2:
                        self.magic_menu.close()
                        self.magic_menu_open = False
                elif action == "folder":
                    # Refresh menu with folder contents
                    symbol_data = {s.id: s.to_dict() for s in MagicSystem.get_all_symbols().values()}
                    self.magic_menu._refresh_items(self.player.known_symbols, symbol_data)
                elif action == "back":
                    symbol_data = {s.id: s.to_dict() for s in MagicSystem.get_all_symbols().values()}
                    self.magic_menu._refresh_items(self.player.known_symbols, symbol_data)

    def _toggle_magic_menu(self):
        """Toggle the magic selection menu."""
        if self.magic_menu_open:
            self.magic_menu.close()
            self.magic_menu_open = False
        else:
            symbol_data = {s.id: s.to_dict() for s in MagicSystem.get_all_symbols().values()}
            self.magic_menu.open(self.player.known_symbols, symbol_data)
            self.magic_menu_open = True

    def _show_help(self):
        """Show help message."""
        help_text = (
            "Controls: WASD=Move, 1-9=Select Symbol, 0=Clear, Space=Cast, "
            "E=Interact, Tab/M=Magic Menu, N=Notebook, F5=Save, F9=Load, ESC=Quit"
        )
        self.show_message(help_text, 5.0)

    def _quick_save(self):
        """Quick save the game."""
        save_data = create_save_data(self.player, self.world, self.notebook)
        success, result = self.save_system.save_game("quicksave", save_data)
        if success:
            self.show_message("Game saved.")
        else:
            self.show_message(f"Save failed: {result}")

    def _quick_load(self):
        """Quick load the game."""
        save_data, error = self.save_system.load_game("quicksave")
        if save_data:
            apply_save_data(save_data, self.player, self.notebook)
            self.show_message("Game loaded.")
        else:
            self.show_message(f"Load failed: {error}")

    def update(self, dt):
        """Update game state."""
        # Handle player movement
        if self.player and self.player.is_alive():
            dx, dy = self.input.get_movement_direction()
            if dx != 0 or dy != 0:
                old_x, old_y = self.player.x, self.player.y
                if self.player.try_move(dx, dy, self.world):
                    self.world.update_entity_position(self.player, old_x, old_y)

            # Handle casting
            if self.input.cast_magic and self.player.can_cast():
                self._handle_cast()

            # Handle interaction
            if self.input.interact:
                self._handle_interaction()

            # Symbol selection via number keys
            self._handle_symbol_selection()

        # Update world
        self.world.update(dt)

        # Update camera
        self.camera.update()

        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= dt

        # Update game state for UI
        self.game_state["fps"] = self.clock.get_fps()
        self.game_state["entity_count"] = len(self.world.entities)
        self.game_state["effect_count"] = len(self.world.active_effects)

    def _handle_symbol_selection(self):
        """Handle symbol selection via number keys."""
        symbols = list(self.player.known_symbols)
        symbols.sort()

        # Keys 1-9 select symbols
        for i, key in enumerate([pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4,
                                  pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]):
            if self.input.was_key_pressed(key) and i < len(symbols):
                symbol = symbols[i]
                self.player.select_symbol(symbol)
                self.show_message(f"Selected: {symbol}")

        # 0 clears selection
        if self.input.was_key_pressed(pygame.K_0):
            self.player.clear_symbol_selection()
            self.show_message("Selection cleared")

    def _handle_cast(self):
        """Handle magic casting."""
        symbols = self.player.get_cast_ready_symbols()
        if not symbols:
            self.show_message("No symbols selected")
            return

        # Get spell descriptor from magic system
        spell_descriptor = MagicSystem.resolve_spell(symbols)

        if spell_descriptor is None:
            self.show_message("Invalid combination")
            self.player.clear_symbol_selection()
            return

        # Check mana cost
        mana_cost = spell_descriptor.get("mana_cost", 10)
        if not self.player.stats.use_mana(mana_cost):
            self.show_message("Not enough mana")
            return

        # Create effect at target location (in front of player)
        target_x, target_y = self._get_target_position()

        from ..entities import EffectInstance
        effect = EffectInstance(
            target_x, target_y,
            spell_descriptor,
            duration=spell_descriptor.get("duration", 1.0),
            radius=spell_descriptor.get("radius", 0)
        )
        effect.caster = self.player

        self.world.spawn_effect(effect)

        # Apply immediately to entities at target
        results = effect.tick(self.world)

        # Show message
        spell_name = spell_descriptor.get("name", "Unknown spell")
        self.show_message(f"Cast: {spell_name}")

        # Show effect results
        for entity, result in results:
            for msg in result.get("messages", []):
                print(f"[Magic] {entity}: {msg}")  # Debug log

        # Clear selection after casting
        self.player.clear_symbol_selection()

    def _get_target_position(self):
        """Get target position based on player facing direction."""
        facing_offsets = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0)
        }

        # Use actor's facing direction
        facing = getattr(self.player, 'facing', 'down')

        # For now, use simple facing direction
        # Later this could use mouse targeting
        dx, dy = facing_offsets.get(facing, (0, 1))
        return self.player.x + dx, self.player.y + dy

    def _handle_interaction(self):
        """Handle player interaction with nearby entities."""
        # Get entities in interaction range
        nearby = self.world.get_entities_in_radius(self.player.x, self.player.y, 1)

        for entity in nearby:
            if entity.id == self.player.id:
                continue

            # Check for NPC interaction
            if entity.has_tag("npc"):
                self._interact_with_npc(entity)
                return

            # Check for regular interaction
            interaction = entity.get_component("InteractionComponent")
            if interaction:
                if interaction.can_examine:
                    self.show_message(interaction.examine_text)
                    return

    def _interact_with_npc(self, npc):
        """Handle interaction with an NPC."""
        # Show greeting
        self.show_message(npc.get_greeting(), 3.0)

        # Check if NPC can teach
        if npc.can_teach:
            teachable = npc.get_teachable_for_player(self.player)
            if teachable:
                # Teach first available symbol
                symbol_id = teachable[0]
                success, message, data = npc.teach_symbol(symbol_id, self.player)
                if success:
                    # Record in notebook
                    symbol = MagicSystem.get_symbol(symbol_id)
                    symbol_data = symbol.to_dict() if symbol else {}
                    self.notebook.record_symbol_discovery(
                        symbol_id,
                        data.get("context", ""),
                        f"Location: {self.player.x}, {self.player.y}",
                        symbol_data
                    )
                    self.show_message(f"Learned new symbol: {symbol_id}!", 3.0)

    def show_message(self, message, duration=2.0):
        """Show a temporary message on screen."""
        self.current_message = message
        self.message_timer = duration

    def render(self):
        """Render the game."""
        self.renderer.clear()
        self.renderer.render_world(self.world, self.camera)
        self.renderer.render_ui(self.player, self.game_state)

        if self.message_timer > 0:
            self.renderer.render_message(self.current_message, self.message_timer)

        # Render magic menu if open
        if self.magic_menu_open:
            symbol_data = {s.id: s.to_dict() for s in MagicSystem.get_all_symbols().values()}
            self.magic_menu.render(self.screen, self.player.known_symbols, symbol_data)
