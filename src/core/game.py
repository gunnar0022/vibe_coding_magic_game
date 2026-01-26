"""
Main game class - handles game loop and state management.
Updated with radial magic menu, dialogue box, introspection, and mana regen.
"""
import pygame
from .settings import Settings
from .camera import Camera
from ..world import World, MapLoader
from ..entities import Player, create_npc_from_template, EffectInstance, RuneStone
from ..systems import InputHandler, Renderer, SaveSystem, create_save_data, apply_save_data
from ..ui import Notebook, RadialMagicMenu, DialogueBox, GameMenu, SpellNotebook, RadialMenuEditor, RadialMenuLayout
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

        # UI systems
        self.radial_menu = RadialMagicMenu(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.dialogue_box = DialogueBox(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.game_menu = GameMenu(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.spell_notebook = SpellNotebook(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.radial_menu_editor = RadialMenuEditor(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)

        # Game state
        self.running = True
        self.paused = False
        self.current_message = ""
        self.message_timer = 0
        self.current_events = []  # Store events for systems that need raw event access

        # Introspection state (I key - recent spell log)
        self.last_spell_cast = None  # Stores info about most recent spell
        self.last_spell_time = 0  # Time since last spell
        self.introspection_message = ""
        self.introspection_timer = 0
        self.introspection_decay = 4.0  # Seconds before introspection decays

        # Combat state (for disabling introspection during combat)
        self.in_combat = False

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

        # Give player starting symbols (fire and water only - force learned from NPC)
        self._learn_symbol_with_notebook("fire", "Starting knowledge", "Your home village")
        self._learn_symbol_with_notebook("water", "Starting knowledge", "Your home village")

        # Initialize radial menu layout for player
        self._init_player_radial_layout()

        self.show_message("Hold SPACE for magic. ESC for menu. H for help.")

    def _init_player_radial_layout(self):
        """Initialize player's radial menu layout if needed."""
        if self.player.radial_menu_layout is None:
            self.player.radial_menu_layout = RadialMenuLayout()
            # Auto-populate with known spells for new players
            self.player.radial_menu_layout.auto_populate_from_spells(
                self.player.get_known_symbols_ordered()
            )
        # Sync layout to the radial menu
        self.radial_menu.set_layout(self.player.radial_menu_layout)

    def _learn_symbol_with_notebook(self, symbol_id, context="", location=""):
        """Learn a symbol and record it in the notebook and spell journal."""
        if self.player.learn_symbol(symbol_id):
            symbol = MagicSystem.get_symbol(symbol_id)
            symbol_data = symbol.to_dict() if symbol else {}
            self.notebook.record_symbol_discovery(symbol_id, context, location, symbol_data)
            # Also add to the spell notebook (journal)
            self.spell_notebook.learn_spell(symbol_id)
            return True
        return False

    def run(self):
        """Main game loop."""
        while self.running:
            # Calculate delta time
            dt = self.clock.tick(Settings.FPS) / 1000.0

            # Handle events
            events = pygame.event.get()
            self.current_events = events  # Store for systems needing raw event access
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            # Update input
            self.input.update(events)

            # Update game state
            self.update(dt)

            # Render
            self.render()

            # Update display
            pygame.display.flip()

        pygame.quit()

    def update(self, dt):
        """Update game state."""
        # Handle dialogue box first (blocks other input when active)
        if self.dialogue_box.is_active:
            self.dialogue_box.update(dt)
            if self.input.interact or self.input.space_just_pressed:
                self.dialogue_box.handle_input()
            return

        # Handle game menu (blocks gameplay when open)
        if self.game_menu.is_open:
            action = self.game_menu.handle_input(self.input)
            if action:
                self._handle_menu_action(action)
            return

        # Handle spell notebook/journal (does NOT pause game, but captures input)
        if self.spell_notebook.is_open:
            self.spell_notebook.handle_input(self.input, self.current_events)
            # Continue with game updates - notebook doesn't pause
            # But skip player input handling while notebook is open
            self._update_world_only(dt)
            return

        # Handle radial menu editor (full-screen, pauses game)
        if self.radial_menu_editor.is_open:
            result = self.radial_menu_editor.handle_input(self.input, self.current_events)
            if result in ("close", "cancel"):
                # Sync the edited layout to the radial menu
                self._sync_radial_menu_layout()
            return

        # Handle global input
        self._handle_global_input()

        # Handle radial magic menu
        self._handle_radial_menu()

        # Player can move even while radial menu is open
        if self.player and self.player.is_alive():
            # Movement (always allowed)
            dx, dy = self.input.get_movement_direction()
            if dx != 0 or dy != 0:
                old_x, old_y = self.player.x, self.player.y
                if self.player.try_move(dx, dy, self.world):
                    self.world.update_entity_position(self.player, old_x, old_y)

            # Handle interaction (E key)
            if self.input.interact and not self.radial_menu.is_open:
                self._handle_interaction()

            # Handle introspection (I key)
            if self.input.introspect and not self.in_combat:
                self._handle_introspection()

        # Update mana regeneration
        if self.player:
            self.player.stats.update(dt)

        # Update world (handles burning, entity removal, etc.)
        self.world.update(dt)

        # Update camera
        self.camera.update()

        # Update timers
        if self.message_timer > 0:
            self.message_timer -= dt
        if self.introspection_timer > 0:
            self.introspection_timer -= dt
        self.last_spell_time += dt

        # Update game state for UI
        self.game_state["fps"] = self.clock.get_fps()
        self.game_state["entity_count"] = len(self.world.entities)
        self.game_state["effect_count"] = len(self.world.active_effects)

    def _update_world_only(self, dt):
        """Update world systems without player input (used when notebook is open)."""
        # Update mana regeneration
        if self.player:
            self.player.stats.update(dt)

        # Update world (handles burning, entity removal, etc.)
        self.world.update(dt)

        # Update camera
        self.camera.update()

        # Update timers
        if self.message_timer > 0:
            self.message_timer -= dt
        if self.introspection_timer > 0:
            self.introspection_timer -= dt
        self.last_spell_time += dt

        # Update game state for UI
        self.game_state["fps"] = self.clock.get_fps()
        self.game_state["entity_count"] = len(self.world.entities)
        self.game_state["effect_count"] = len(self.world.active_effects)

    def _handle_global_input(self):
        """Handle input that works regardless of game state."""
        # Escape opens game menu or closes other menus
        if self.input.cancel:
            if self.spell_notebook.is_open:
                self.spell_notebook.close()
                return
            if self.radial_menu.is_open or self.radial_menu.is_stowed:
                self.radial_menu.cancel()
            elif not self.game_menu.is_open:
                self.game_menu.open()
            return

        # J key opens spell journal directly
        if self.input.was_key_pressed(pygame.K_j):
            if not self.spell_notebook.is_open and not self.game_menu.is_open:
                self.spell_notebook.open()
            return

        # Help
        if self.input.was_key_pressed(pygame.K_h):
            self._show_help()

    def _handle_radial_menu(self):
        """
        Handle the radial magic menu.
        - Hold SPACE opens menu
        - Mouse click selects symbols
        - Click off menu stows UI and locks selection (mana deducted)
        - Right click cancels
        - Release SPACE launches spell
        """
        mouse_x, mouse_y = self.input.get_mouse_position()

        # SPACE just pressed - open menu
        if self.input.space_just_pressed and not self.radial_menu.is_open and not self.radial_menu.is_stowed:
            # Update radial menu with player's known symbols (in order learned)
            self.radial_menu.update_known_symbols(self.player.get_known_symbols_ordered())
            self.radial_menu.open()

        # Menu is open - handle interactions
        if self.radial_menu.is_open:
            # Update hover state
            self.radial_menu.update(mouse_x, mouse_y)

            # Left click - select symbol or stow
            if self.input.mouse_clicked:
                result = self.radial_menu.handle_click(mouse_x, mouse_y)
                if result == "symbol_selected":
                    symbols = self.radial_menu.get_selected_symbols()
                    if symbols:
                        self.show_message(f"Selected: {', '.join(symbols)}", 1.0)
                elif result == "stow":
                    # Mana is deducted when menu is stowed
                    self._deduct_mana_for_spell()

            # Right click - cancel
            if self.input.mouse_right_clicked:
                self.radial_menu.cancel()
                self.show_message("Spell cancelled", 1.0)

        # SPACE released - launch spell if ready
        if self.input.space_just_released:
            if self.radial_menu.is_open:
                # Still open means they released without clicking off
                # Stow and cast immediately if they have selection
                if self.radial_menu.has_selection():
                    self._deduct_mana_for_spell()
                    self.radial_menu.stow()
                    self._cast_spell(mouse_x, mouse_y)
                else:
                    self.radial_menu.close()
            elif self.radial_menu.is_stowed:
                # Menu was stowed, now cast
                self._cast_spell(mouse_x, mouse_y)

    def _deduct_mana_for_spell(self):
        """Deduct mana cost when spell is stowed (locked in)."""
        symbols = self.radial_menu.get_selected_symbols()
        if not symbols:
            return False

        spell_descriptor = MagicSystem.resolve_spell(symbols)
        if spell_descriptor is None:
            return False

        mana_cost = spell_descriptor.get("mana_cost", 10)
        if not self.player.stats.use_mana(mana_cost):
            self.show_message("Not enough mana")
            self.radial_menu.cancel()
            return False

        return True

    def _cast_spell(self, mouse_x, mouse_y):
        """Cast the prepared spell in direction of mouse."""
        symbols = self.radial_menu.get_selected_symbols()
        if not symbols:
            self.radial_menu.close()
            return

        # Get spell descriptor
        spell_descriptor = MagicSystem.resolve_spell(symbols)
        if spell_descriptor is None:
            self.show_message("Invalid combination")
            self.radial_menu.close()
            return

        # Get 8-directional cast direction from mouse position
        cast_dir = self.radial_menu.get_cast_direction_from_mouse(mouse_x, mouse_y)

        # Calculate target position
        target_x = self.player.x + cast_dir[0]
        target_y = self.player.y + cast_dir[1]

        # Create effect at target location
        effect = EffectInstance(
            target_x, target_y,
            spell_descriptor,
            duration=spell_descriptor.get("duration", 1.0),
            radius=spell_descriptor.get("radius", 0)
        )
        effect.caster = self.player

        self.world.spawn_effect(effect)

        # Apply to entities at target, passing cast direction for push effects
        context = {"cast_direction": cast_dir}
        results = self._apply_effect_with_context(effect, context)

        # Process results (handle push requests, log messages)
        self._process_spell_results(results, cast_dir)

        # Record for introspection
        self._record_spell_cast(spell_descriptor, results)

        # Show message
        spell_name = spell_descriptor.get("name", "Unknown spell")
        self.show_message(f"Cast: {spell_name}", 1.5)

        # Clear radial menu
        self.radial_menu.close()

    def _apply_effect_with_context(self, effect, context):
        """Apply effect to entities with additional context (cast direction)."""
        results = []
        affected_tiles = effect.get_affected_tiles()

        for tile_x, tile_y in affected_tiles:
            entities = self.world.get_entities_at(tile_x, tile_y)

            for entity in entities:
                if entity.id == effect.id:
                    continue
                if effect.caster and entity.id == effect.caster.id:
                    if not effect.spell_descriptor.get("affects_caster", False):
                        continue

                result = entity.on_magic_applied(effect.spell_descriptor, context)
                if result.get("affected"):
                    results.append((entity, result))

        return results

    def _process_spell_results(self, results, cast_dir):
        """Process results from spell application (push rocks, log messages)."""
        for entity, result in results:
            # Handle push requests (force spells on rocks)
            push_request = result.get("push_request")
            if push_request:
                dx = push_request.get("dx", 0)
                dy = push_request.get("dy", 0)
                if dx != 0 or dy != 0:
                    success = self.world.try_push_entity(entity, dx, dy)
                    if success:
                        print(f"[Magic] Pushed {entity.object_type} to ({entity.x}, {entity.y})")
                    else:
                        print(f"[Magic] {entity.object_type} blocked, cannot push")

            # Log messages
            for msg in result.get("messages", []):
                print(f"[Magic] {entity}: {msg}")

    def _record_spell_cast(self, spell_descriptor, results):
        """Record spell for introspection."""
        self.last_spell_cast = {
            "name": spell_descriptor.get("name", "Unknown"),
            "element": spell_descriptor.get("element", "none"),
            "category": spell_descriptor.get("category", "none"),
            "affected_count": len(results),
            "results": results,
        }
        self.last_spell_time = 0

    def _handle_introspection(self):
        """Handle introspection (I key) - show recent spell log."""
        if self.in_combat:
            self.show_message("Cannot reflect during combat.")
            return

        if self.last_spell_cast is None or self.last_spell_time > 30:
            # No recent spell or too long ago
            self.introspection_message = "Your mind is clear. There is nothing recent to reflect upon."
        else:
            # Generate diegetic description without numbers
            spell = self.last_spell_cast
            msg = self._generate_introspection_text(spell)
            self.introspection_message = msg

        self.introspection_timer = self.introspection_decay

    def _generate_introspection_text(self, spell):
        """Generate vague, diegetic introspection text."""
        name = spell.get("name", "something")
        element = spell.get("element", "unknown")
        affected = spell.get("affected_count", 0)
        results = spell.get("results", [])

        # Base description
        if element == "fire":
            desc = f"You recall the warmth of {name}. Heat lingered in the air."
        elif element == "water":
            desc = f"You remember the flow of {name}. The moisture felt refreshing."
        elif element == "physical":
            desc = f"You sense the echo of {name}. The force was tangible."
        else:
            desc = f"You reflect on {name}. Its nature remains somewhat mysterious."

        # Add effect observations
        if affected > 0:
            desc += " Something was affected."
            # Check for specific outcomes
            for entity, result in results:
                if result.get("state_changed"):
                    if hasattr(entity, 'object_type'):
                        desc += f" The {entity.object_type} seemed to change."
                if result.get("push_request"):
                    desc += " You felt resistance give way."
        else:
            desc += " Nothing seemed to respond."

        return desc

    def _handle_interaction(self):
        """Handle player interaction with nearby entities."""
        nearby = self.world.get_entities_in_radius(self.player.x, self.player.y, 1)

        for entity in nearby:
            if entity.id == self.player.id:
                continue

            # Check for NPC interaction
            if entity.has_tag("npc"):
                self._interact_with_npc(entity)
                return

            # Check for rune stone interaction
            if entity.has_tag("rune_stone"):
                self._interact_with_rune_stone(entity)
                return

            # Check for regular interaction
            interaction = entity.get_component("InteractionComponent")
            if interaction and interaction.can_examine:
                self.dialogue_box.show(interaction.examine_text)
                return

    def _interact_with_npc(self, npc):
        """Handle interaction with an NPC using dialogue box."""
        dialogue_lines = []

        # Add greeting (pass player so NPC can customize based on taught status)
        dialogue_lines.append(npc.get_greeting(self.player))

        # Check if NPC can teach
        if npc.can_teach:
            teachable = npc.get_teachable_for_player(self.player)
            if teachable:
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
                    # Also add to spell notebook (journal)
                    self.spell_notebook.learn_spell(symbol_id)
                    dialogue_lines.append(f"Let me teach you the symbol of {symbol_id}...")
                    dialogue_lines.append(f"You have learned: {symbol_id}!")
            else:
                dialogue_lines.append("I have taught you all I know.")

        # Show dialogue
        self.dialogue_box.show(dialogue_lines, npc.get_display_name())

    def _interact_with_rune_stone(self, rune_stone):
        """Handle interaction with a rune stone."""
        dialogue_lines = []

        if rune_stone.can_teach(self.player):
            success, messages = rune_stone.teach(self.player)
            dialogue_lines.extend(messages)

            if success:
                # Record in notebook
                symbol = MagicSystem.get_symbol(rune_stone.symbol_id)
                symbol_data = symbol.to_dict() if symbol else {}
                self.notebook.record_symbol_discovery(
                    rune_stone.symbol_id,
                    rune_stone.teaching_context,
                    f"Location: {self.player.x}, {self.player.y}",
                    symbol_data
                )
                # Also add to spell notebook (journal)
                self.spell_notebook.learn_spell(rune_stone.symbol_id)
        else:
            # Stone is dormant or player already knows the symbol
            interaction = rune_stone.get_component("InteractionComponent")
            if interaction:
                dialogue_lines.append(interaction.examine_text)

        self.dialogue_box.show(dialogue_lines, "Rune Stone")

    def _show_help(self):
        """Show help message."""
        help_text = (
            "Hold SPACE=Magic Menu, Mouse=Select/Aim, "
            "WASD=Move, E=Interact, I=Introspect, J=Journal, ESC=Menu"
        )
        self.show_message(help_text, 5.0)

    def _quick_save(self):
        """Quick save the game."""
        save_data = create_save_data(self.player, self.world, self.notebook, self.spell_notebook)
        success, result = self.save_system.save_game("quicksave", save_data)
        if success:
            self.show_message("Game saved.")
        else:
            self.show_message(f"Save failed: {result}")

    def _quick_load(self):
        """Quick load the game."""
        save_data, error = self.save_system.load_game("quicksave")
        if save_data:
            apply_save_data(save_data, self.player, self.notebook, self.spell_notebook)
            # Sync radial menu layout after loading
            self._init_player_radial_layout()
            self.show_message("Game loaded.")
        else:
            self.show_message(f"Load failed: {error}")

    def _handle_menu_action(self, action):
        """Handle actions from the game menu."""
        if action == "save":
            self._quick_save()
            self.game_menu.close()
        elif action == "load":
            self._quick_load()
            self.game_menu.close()
        elif action == "exit":
            self.running = False
        elif action == "resume":
            pass  # Menu already closed itself
        elif action == "journal":
            self.spell_notebook.open()
        elif action == "customize_spells":
            self._open_radial_menu_editor()

    def _open_radial_menu_editor(self):
        """Open the radial menu customization editor."""
        # Ensure player has a layout
        if not hasattr(self.player, 'radial_menu_layout') or self.player.radial_menu_layout is None:
            self.player.radial_menu_layout = RadialMenuLayout()
            # Auto-populate with known spells if new
            self.player.radial_menu_layout.auto_populate_from_spells(
                self.player.get_known_symbols_ordered()
            )

        # Open editor with the player's layout and known spells
        self.radial_menu_editor.open(
            self.player.radial_menu_layout,
            self.player.get_known_symbols_ordered()
        )

    def _sync_radial_menu_layout(self):
        """Sync the edited layout to the radial menu and player."""
        if self.radial_menu_editor.layout:
            self.player.radial_menu_layout = self.radial_menu_editor.layout
            self.radial_menu.set_layout(self.player.radial_menu_layout)

    def show_message(self, message, duration=2.0):
        """Show a temporary message on screen."""
        self.current_message = message
        self.message_timer = duration

    def render(self):
        """Render the game."""
        self.renderer.clear()
        self.renderer.render_world(self.world, self.camera)
        self.renderer.render_ui(self.player, self.game_state)

        # Render temporary messages
        if self.message_timer > 0:
            self.renderer.render_message(self.current_message, self.message_timer)

        # Render introspection message
        if self.introspection_timer > 0:
            self._render_introspection()

        # Render radial magic menu
        if self.radial_menu.is_open:
            self.radial_menu.render(self.screen)

        # Render spell-ready indicator when stowed
        if self.radial_menu.is_stowed:
            self._render_spell_ready_indicator()

        # Render dialogue box
        if self.dialogue_box.is_active:
            self.dialogue_box.render(self.screen)

        # Render spell notebook/journal
        if self.spell_notebook.is_open:
            self.spell_notebook.render(self.screen)

        # Render game menu (on top of everything)
        if self.game_menu.is_open:
            self.game_menu.render(self.screen)

        # Render radial menu editor (full-screen overlay)
        if self.radial_menu_editor.is_open:
            self.radial_menu_editor.render(self.screen)

    def _render_introspection(self):
        """Render introspection text."""
        if not self.introspection_message:
            return

        font = pygame.font.Font(None, 22)

        # Fade based on timer
        alpha = min(255, int((self.introspection_timer / self.introspection_decay) * 255))

        # Create text surface
        text_surf = font.render(self.introspection_message, True, (200, 200, 180))

        # Position at top-center
        x = (Settings.SCREEN_WIDTH - text_surf.get_width()) // 2
        y = 50

        # Background
        padding = 8
        bg_rect = pygame.Rect(x - padding, y - padding,
                              text_surf.get_width() + padding * 2,
                              text_surf.get_height() + padding * 2)
        bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surf.fill((30, 30, 40, min(200, alpha)))
        self.screen.blit(bg_surf, bg_rect.topleft)

        self.screen.blit(text_surf, (x, y))

    def _render_spell_ready_indicator(self):
        """Render indicator that spell is ready to cast."""
        symbols = self.radial_menu.get_selected_symbols()
        if not symbols:
            return

        font = pygame.font.Font(None, 24)
        text = f"Spell Ready: {' + '.join(symbols)} (Release SPACE to cast)"
        text_surf = font.render(text, True, (150, 200, 255))

        x = (Settings.SCREEN_WIDTH - text_surf.get_width()) // 2
        y = Settings.SCREEN_HEIGHT // 2 - 100

        # Background
        padding = 6
        bg_rect = pygame.Rect(x - padding, y - padding,
                              text_surf.get_width() + padding * 2,
                              text_surf.get_height() + padding * 2)
        pygame.draw.rect(self.screen, (30, 40, 60), bg_rect, border_radius=4)
        pygame.draw.rect(self.screen, (80, 100, 140), bg_rect, 2, border_radius=4)

        self.screen.blit(text_surf, (x, y))
