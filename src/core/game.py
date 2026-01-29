"""
Main game class - handles game loop and state management.
Updated with radial magic menu, dialogue box, introspection, and mana regen.
"""
import pygame
from .settings import Settings
from .camera import Camera
from ..world import World, MapLoader
from ..entities import Player, create_npc_from_template, EffectInstance, RuneStone, SummonedWeapon, WorldObject, Projectile, Enemy, GroundItem, PhysicalWeapon
from ..items import ItemInstance
from ..combat import check_contact_damage
from ..systems import InputHandler, Renderer, SaveSystem, create_save_data, apply_save_data, get_asset_manager
from ..ui import Notebook, RadialMagicMenu, DialogueBox, GameMenu, SpellNotebook, RadialMenuEditor, RadialMenuLayout, SettingsMenu, InventoryUI
from ..ui.title_screen import TitleScreen
from ..ui.death_screen import DeathScreen
from ..magic import MagicSystem
from .combat_handler import CombatHandler
from .interaction_handler import InteractionHandler
from .spell_handler import SpellHandler


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

        # Area tracking
        self.current_area_id = None
        self.current_area_data = None

        # Dialogue tree state
        self._active_dialogue_tree = None
        self._active_dialogue_npc = None
        self._pending_dialogue_continuation = None
        self._conversation_npc = None  # Track NPC in conversation for movement pause

        # Player systems
        self.notebook = Notebook()

        # UI systems
        self.radial_menu = RadialMagicMenu(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.dialogue_box = DialogueBox(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.game_menu = GameMenu(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.spell_notebook = SpellNotebook(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.radial_menu_editor = RadialMenuEditor(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.settings_menu = SettingsMenu(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.inventory_ui = InventoryUI(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)

        # Title and death screens
        self.title_screen = TitleScreen(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.death_screen = DeathScreen(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)

        # Modular handlers
        self.combat_handler = CombatHandler(self)
        self.interaction_handler = InteractionHandler(self)
        self.spell_handler = SpellHandler(self)

        # Game phase: "title", "playing", "dead"
        self.game_phase = "title"

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

        # Weapon swing visual feedback
        self.weapon_swing_effect = None
        self.weapon_swing_timer = 0

        # Projectile system
        self.active_projectiles = []

        # Bow draw state (click-hold-release mechanic)
        self.bow_drawing = False
        self.bow_draw_timer = 0.0
        self.bow_draw_time_required = 1.0  # seconds to fully draw

        # Arrow impact effects (list of {x, y, timer})
        self.arrow_impact_effects = []
        self.arrow_impact_duration = 0.15  # same as weapon swing

        # Game state dict for UI
        self.game_state = {
            "fps": 0,
            "entity_count": 0,
            "effect_count": 0,
        }

        # Open title screen (don't init world yet)
        self.title_screen.open(has_save=self._has_save())

    def _init_world(self):
        """Initialize the game world."""
        # Try to load home village, fall back to test map if it doesn't exist
        try:
            player_spawn = self.load_area("home_village")
        except (FileNotFoundError, ValueError):
            # Fall back to test map for development
            player_spawn = MapLoader.create_test_map(self.world)
            self.current_area_id = "test_map"
            self.current_area_data = {"entry_points": {"default": {"x": player_spawn[0], "y": player_spawn[1]}}}

        # Create player at spawn point
        self.player = Player(player_spawn[0], player_spawn[1])
        self.world.add_entity(self.player)

        # Set camera to follow player
        self.camera.set_target(self.player)

        # Give player starting symbols
        self._learn_symbol_with_notebook("fire", "Starting knowledge", "Your home village")
        self._learn_symbol_with_notebook("water", "Starting knowledge", "Your home village")
        self._learn_symbol_with_notebook("bullet", "Starting knowledge", "Your home village")
        self._learn_symbol_with_notebook("ice", "Starting knowledge", "Your home village")

        # Initialize radial menu layout for player
        self._init_player_radial_layout()

        self.show_message("Hold SPACE for magic. ESC for menu. H for help.")

    def load_area(self, area_id, entry_point="default"):
        """
        Load a new area, preserving the player.

        Args:
            area_id: The area ID to load from the registry
            entry_point: Named entry point for player spawn position

        Returns:
            Player spawn position tuple (x, y)
        """
        # Clear world entities but remember player reference
        player_ref = self.player
        has_player = player_ref is not None

        # Clear all entities from world
        self.world.clear()

        # Load the new area
        player_spawn, area_data = MapLoader.load_area(area_id, self.world)

        # Update area tracking
        self.current_area_id = area_id
        self.current_area_data = area_data

        # Get spawn position from named entry point
        if entry_point in area_data.get("entry_points", {}):
            ep = area_data["entry_points"][entry_point]
            player_spawn = (ep["x"], ep["y"])

        # If we have a player, reposition them in the new area
        if has_player and player_ref:
            player_ref.x = float(player_spawn[0])
            player_ref.y = float(player_spawn[1])
            self.world.add_entity(player_ref)

        return player_spawn

    def transition_to_area(self, target_area, target_entry="default"):
        """
        Transition to a new area via a door or portal.
        Handles the full transition including fade effect later.
        """
        try:
            self.load_area(target_area, target_entry)
            area_name = self.current_area_data.get("name", target_area)
            self.show_message(f"Entered {area_name}")
        except (FileNotFoundError, ValueError) as e:
            self.show_message(f"Cannot enter: {e}")

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
            self.current_events = events
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            # Update input
            self.input.update(events)

            # Dispatch based on game phase
            if self.game_phase == "title":
                self._update_title(dt)
                self._render_title()
            elif self.game_phase == "playing":
                self.update(dt)
                self.render()
            elif self.game_phase == "dead":
                self._update_dead(dt)
                self._render_dead()

            # Update display
            pygame.display.flip()

        pygame.quit()

    def _has_save(self):
        """Check if any save file exists."""
        saves = self.save_system.list_saves()
        return len(saves) > 0

    def _update_title(self, dt):
        """Update title screen."""
        self.title_screen.update(dt)

        # Handle settings menu on title screen
        if self.settings_menu.is_open:
            result = self.settings_menu.handle_input(self.input)
            if result == "save":
                self._apply_settings()
                self.title_screen.is_open = True
            elif result == "cancel":
                self.title_screen.is_open = True
            return

        action = self.title_screen.handle_input(self.input)
        if action == "new_game_confirmed":
            self._start_new_game()
        elif action == "load":
            self._load_game_from_title()
        elif action == "settings":
            self.title_screen.is_open = False
            self.settings_menu.open()
        elif action == "exit":
            self.running = False

    def _render_title(self):
        """Render title screen."""
        if self.settings_menu.is_open:
            # Render title as background, then settings overlay
            self.title_screen.render(self.screen)
            self.settings_menu.render(self.screen)
        else:
            self.title_screen.render(self.screen)

    def _start_new_game(self):
        """Start a new game, deleting existing saves."""
        # Delete existing saves
        saves = self.save_system.list_saves()
        for save_info in saves:
            self.save_system.delete_save(save_info["name"])

        # Reset and initialize world
        self._reset_world()
        self.title_screen.close()
        self.game_phase = "playing"

    def _load_game_from_title(self):
        """Load saved game from title screen."""
        # Init world first (so player exists to apply save data to)
        self._reset_world()
        self._quick_load()
        self.title_screen.close()
        self.game_phase = "playing"

    def _reset_world(self):
        """Reset the world and all game state for a fresh game."""
        # Clear existing world
        self.world.clear()
        self.active_projectiles = []

        # Reset UI state
        self.paused = False
        self.current_message = ""
        self.message_timer = 0
        self.bow_drawing = False
        self.bow_draw_timer = 0.0
        self.weapon_swing_timer = 0
        self.weapon_swing_effect = None
        self.arrow_impact_effects = []
        self.last_spell_cast = None
        self.introspection_message = ""
        self.introspection_timer = 0

        # Close all UI
        self.game_menu.close()
        self.spell_notebook.close()
        self.death_screen.close()
        if self.radial_menu_editor.is_open:
            self.radial_menu_editor.close(save=False)
        if self.settings_menu.is_open:
            self.settings_menu.close(save=False)
        if hasattr(self.radial_menu, 'cancel'):
            self.radial_menu.cancel()

        # Reinitialize world
        self.notebook = Notebook()
        self.spell_notebook = SpellNotebook(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self._init_world()

    def _go_to_title(self):
        """Transition back to the title screen."""
        self.game_phase = "title"
        self.death_screen.close()
        self.title_screen.open(has_save=self._has_save())

    def _update_dead(self, dt):
        """Update death screen."""
        self.death_screen.update(dt)
        action = self.death_screen.handle_input(self.input)
        if action == "load":
            self._load_game_from_death()
        elif action == "title":
            self._go_to_title()

    def _render_dead(self):
        """Render death screen on top of frozen game world."""
        # Render the game world frozen in the background
        self.renderer.clear()
        self.renderer.render_world(self.world, self.camera)
        self.renderer.render_ui(self.player, self.game_state)
        # Death screen overlay
        self.death_screen.render(self.screen)

    def _load_game_from_death(self):
        """Load saved game after dying."""
        self._reset_world()
        self._quick_load()
        self.death_screen.close()
        self.game_phase = "playing"

    def _trigger_death(self):
        """Called when the player dies. Transition to death phase."""
        self.game_phase = "dead"
        self.death_screen.open(has_save=self._has_save())

    def update(self, dt):
        """Update game state."""
        # Handle ESC as contextual back button / pause
        if self.input.toggle_pause:
            self._handle_escape_key()

        # Handle menu toggle (TAB) - works from anywhere except pause, editor, and settings
        # Menu can coexist with journal (side by side)
        if self.input.open_menu and not self.paused and not self.radial_menu_editor.is_open and not self.settings_menu.is_open:
            # If inventory is open, close it and open game menu
            if self.inventory_ui.is_open:
                self.inventory_ui.close()
                self.game_menu.open()
            elif self.game_menu.is_open:
                self.game_menu.close()
            else:
                self.game_menu.open()

        # If paused, don't update anything else
        if self.paused:
            return

        # Handle dialogue box (ESC/interact advances, world updates)
        if self.dialogue_box.is_active:
            self.dialogue_box.update(dt)
            # Handle navigation in choice mode (check key_just_pressed for single-step navigation)
            if self.dialogue_box.is_choice_mode:
                if pygame.K_w in self.input.key_just_pressed or pygame.K_UP in self.input.key_just_pressed:
                    self.dialogue_box.handle_navigation(-1)
                elif pygame.K_s in self.input.key_just_pressed or pygame.K_DOWN in self.input.key_just_pressed:
                    self.dialogue_box.handle_navigation(1)
                # Handle mouse click on choices
                if self.input.mouse_clicked:
                    was_active = self.dialogue_box.is_active
                    if self.dialogue_box.handle_mouse_click(self.input.mouse_x, self.input.mouse_y):
                        # Choice was clicked and confirmed
                        if was_active and not self.dialogue_box.is_active:
                            self.interaction_handler.on_dialogue_closed()
                        self._update_world_only(dt)
                        return
            # Advance/confirm on interact
            if self.input.interact or self.input.space_just_pressed:
                was_active = self.dialogue_box.is_active
                self.dialogue_box.handle_input(self.input)
                # Check for dialogue closing
                if was_active and not self.dialogue_box.is_active:
                    self.interaction_handler.on_dialogue_closed()
            self._update_world_only(dt)
            return

        # Handle radial menu editor (full-screen, pauses game)
        if self.radial_menu_editor.is_open:
            result = self.radial_menu_editor.handle_input(self.input, self.current_events)
            if result == "back_to_menu":
                self._sync_radial_menu_layout()
                self.game_menu.open()  # Return to game menu
            return

        # Handle settings menu (full-screen, pauses game)
        if self.settings_menu.is_open:
            result = self.settings_menu.handle_input(self.input)
            if result == "save":
                self._apply_settings()
                self.game_menu.open()  # Return to game menu
            elif result == "cancel":
                self.game_menu.open()  # Return to game menu
            return

        # Handle inventory UI (full-screen overlay, pauses gameplay)
        if self.inventory_ui.is_open:
            action = self.inventory_ui.handle_input(self.input)
            if action:
                self._handle_inventory_action(action)
            self._update_world_only(dt)
            return

        # Handle game menu and journal - can be open simultaneously (side by side)
        menu_or_journal_open = self.game_menu.is_open or self.spell_notebook.is_open

        if self.game_menu.is_open:
            action = self.game_menu.handle_input(self.input)
            if action:
                self._handle_menu_action(action)

        if self.spell_notebook.is_open:
            self.spell_notebook.handle_input(self.input, self.current_events)

        # If either menu or journal is open, update world but skip player input
        if menu_or_journal_open:
            self._update_world_only(dt)
            return

        # Handle global input (J for journal, H for help)
        self._handle_global_input()

        # Handle inventory open (I key)
        if self.input.open_inventory and self.player:
            self.inventory_ui.toggle(self.player.inventory)

        # Handle weapon dismissal (R key)
        if self.input.dismiss_weapon:
            self.combat_handler.handle_weapon_dismiss()

        # Handle weapon attack (left click when holding weapon and menu not open)
        if not self.radial_menu.is_open:
            self.combat_handler.handle_weapon_input()

        # Handle radial magic menu (only if player can open it)
        if self.player and self.player.can_open_spell_menu():
            self.spell_handler.handle_radial_menu()
        elif self.input.space_just_pressed and self.player:
            # Player tried to open menu but can't (hands full)
            weapon = self.player.hand_occupancy.get_weapon()
            if weapon and weapon.is_two_handed():
                self.show_message("Cannot cast spells with a two-handed weapon equipped!", 2.0)

        # Player can move even while radial menu is open
        if self.player and self.player.is_alive():
            # Movement (always allowed)
            dx, dy = self.input.get_movement_direction()
            if dx != 0 or dy != 0:
                old_x, old_y = self.player.x, self.player.y
                if self.player.try_move(dx, dy, self.world, dt=dt):
                    self.world.update_entity_position(self.player, old_x, old_y)

            # Handle interaction (E key)
            if self.input.interact and not self.radial_menu.is_open:
                self.interaction_handler.handle_interaction()

            # Handle introspection (T key)
            if self.input.introspect and not self.in_combat:
                self.spell_handler.handle_introspection()

        # Update mana regeneration
        if self.player:
            self.player.stats.update(dt)

        # Update weapon cooldown
        if self.player:
            weapon = self.player.hand_occupancy.get_weapon()
            if weapon:
                weapon.update(dt)

        # Update weapon swing visual timer
        if self.weapon_swing_timer > 0:
            self.weapon_swing_timer -= dt

        # Update bow draw timer
        if self.bow_drawing and self.input.mouse_held:
            self.bow_draw_timer += dt

        # Update world (handles burning, entity removal, etc.)
        self.world.update(dt)

        # Update enemy AI (needs player reference)
        self.combat_handler.update_enemy_ai(dt)

        # Check contact damage (enemies touching player)
        self.combat_handler.check_enemy_damage()

        # Update projectiles
        self.combat_handler.update_projectiles(dt)

        # Check player death
        if self.player and not self.player.is_alive():
            self._trigger_death()
            return

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

        # Update projectiles
        self.combat_handler.update_projectiles(dt)

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

    def _handle_escape_key(self):
        """Handle ESC key as contextual back button or pause toggle."""
        # Priority 1: If paused, unpause
        if self.paused:
            self.paused = False
            self.message_timer = 0
            return

        # Priority 2: Cancel radial magic menu if open
        if self.radial_menu.is_open or self.radial_menu.is_stowed:
            self.radial_menu.cancel()
            self.show_message("Spell cancelled", 1.0)
            return

        # Priority 3: Close dialogue
        if self.dialogue_box.is_active:
            self.dialogue_box.handle_input(self.input)  # Advance/close dialogue
            return

        # Priority 4: Radial menu editor handles ESC internally (returns to menu)
        if self.radial_menu_editor.is_open:
            return  # Editor handles it

        # Priority 5: Close game menu first (if both menu and journal open)
        if self.game_menu.is_open:
            self.game_menu.close()
            return

        # Priority 6: Close inventory UI -> return to game menu
        if self.inventory_ui.is_open:
            self.inventory_ui.close()
            self.game_menu.open()
            return

        # Priority 7: Close spell notebook
        if self.spell_notebook.is_open:
            self.spell_notebook.close()
            return

        # Priority 8: Nothing open - toggle pause
        self.paused = True
        self.show_message("PAUSED - Press ESC to resume", 0)

    def _handle_global_input(self):
        """Handle input that works regardless of game state."""
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

        # Snap player to face the cast direction (4-directional)
        cast_facing = self._get_facing_from_mouse(mouse_x, mouse_y, eight_dir=False)
        self.player.facing = cast_facing
        self.player.transform.facing = cast_facing

        # Check for weapon summon spells (special handling)
        if spell_descriptor.get("category") == "weapon_summon":
            self._handle_weapon_summon(spell_descriptor)
            self.radial_menu.close()
            return

        # Check for projectile spells (fires toward mouse, no grid snapping)
        if spell_descriptor.get("projectile_spell"):
            results = self._handle_projectile_spell(spell_descriptor, mouse_x, mouse_y)
            self._record_spell_cast(spell_descriptor, results)
            spell_name = spell_descriptor.get("name", "Unknown spell")
            self.show_message(f"Cast: {spell_name}", 1.5)
            self.radial_menu.close()
            return

        # Get 8-directional cast direction from mouse position
        cast_dir = self.radial_menu.get_cast_direction_from_mouse(mouse_x, mouse_y)

        # Calculate target position
        target_x = self.player.x + cast_dir[0]
        target_y = self.player.y + cast_dir[1]

        # Route to special spell handlers based on descriptor flags
        results = []

        if spell_descriptor.get("spawn_object"):
            # Summon Boulder: spawn a world object
            results = self._handle_boulder_summon(spell_descriptor, target_x, target_y)
        elif spell_descriptor.get("directional_shape"):
            # Magma Burst: + or X pattern based on facing
            results = self._handle_directional_spell(spell_descriptor, cast_dir)
        elif spell_descriptor.get("cone"):
            # Shadow Flame: 3-tile cone
            results = self._handle_cone_spell(spell_descriptor, cast_dir, target_x, target_y)
        elif spell_descriptor.get("path_effect"):
            # Blast: 3-tile line with push
            results = self._handle_path_spell(spell_descriptor, cast_dir)
        else:
            # Default: create single EffectInstance at target
            effect = EffectInstance(
                target_x, target_y,
                spell_descriptor,
                duration=spell_descriptor.get("duration", 1.0),
                radius=spell_descriptor.get("radius", 0)
            )
            effect.caster = self.player

            # Set tick interval for tick_heal spells
            if spell_descriptor.get("tick_heal"):
                effect.tick_interval = 1.0

            self.world.spawn_effect(effect)

            # Apply to entities at target, passing cast direction for push effects
            context = {"cast_direction": cast_dir}
            results = self._apply_effect_with_context(effect, context)

        # Process results (handle push requests, log messages)
        self._process_spell_results(results, cast_dir)

        # Apply post-spell effects (knockback, cleanse, dispel)
        self._apply_post_spell_effects(spell_descriptor, results, cast_dir)

        # Record for introspection
        self._record_spell_cast(spell_descriptor, results)

        # Show message
        spell_name = spell_descriptor.get("name", "Unknown spell")
        self.show_message(f"Cast: {spell_name}", 1.5)

        # Clear radial menu
        self.radial_menu.close()

    def _handle_weapon_summon(self, spell_descriptor):
        """
        Handle casting a weapon summon spell.
        Creates the weapon and equips it to the player.
        If a physical weapon is held, it gets dropped on the ground.
        """
        weapon_type = spell_descriptor.get("weapon_type")
        if not weapon_type:
            return False

        # Create the weapon
        weapon = SummonedWeapon(weapon_type, owner=self.player)

        # Equip it (returns dropped physical weapon if one was held)
        dropped_pw = self.player.hand_occupancy.equip_weapon(weapon)

        # If a physical weapon was dropped, spawn it on the ground
        if dropped_pw is not None:
            self._spawn_ground_item(dropped_pw.item_instance, self.player.x, self.player.y)
            self.player.inventory.equipped_weapon = None

        # Show message about the weapon
        hands_text = "two hands" if weapon.is_two_handed() else "one hand"
        self.show_message(f"Summoned {weapon.name}! ({hands_text})", 2.0)

        return True

    def _handle_boulder_summon(self, spell_descriptor, target_x, target_y):
        """Handle Summon Boulder spell - spawn a rock WorldObject at target tile."""
        tx = int(target_x)
        ty = int(target_y)

        if self.world.is_blocked(tx, ty):
            self.show_message("No space for boulder!", 1.5)
            return []

        rock = WorldObject(tx, ty, object_type="rock")
        self.world.add_entity(rock)
        print(f"[Magic] Spawned boulder at ({tx}, {ty})")
        return []

    def _handle_directional_spell(self, spell_descriptor, cast_dir):
        """
        Handle directional shape spells (Magma Burst).
        Creates + pattern for cardinal facing, X pattern for diagonal.
        """
        px = int(self.player.x)
        py = int(self.player.y)

        # Determine pattern based on cast direction
        dx, dy = cast_dir
        is_diagonal = (dx != 0 and dy != 0)

        if is_diagonal:
            # X pattern: center + 4 diagonal offsets
            offsets = [(0, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        else:
            # + pattern: center + 4 cardinal offsets
            offsets = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]

        all_results = []
        context = {"cast_direction": cast_dir}

        for ox, oy in offsets:
            ex, ey = px + ox, py + oy
            effect = EffectInstance(
                ex, ey,
                spell_descriptor,
                duration=spell_descriptor.get("duration", 3.0),
                radius=0
            )
            effect.caster = self.player
            # Set tick interval to 1.0s for tick_damage spells
            if spell_descriptor.get("tick_damage"):
                effect.tick_interval = 1.0

            self.world.spawn_effect(effect)

            # Apply to entities at this position
            results = self._apply_effect_with_context(effect, context)
            all_results.extend(results)

        return all_results

    def _handle_cone_spell(self, spell_descriptor, cast_dir, target_x, target_y):
        """
        Handle cone spells (Shadow Flame).
        Affects 3 tiles in a cone pattern toward the cast direction.
        """
        px = int(self.player.x)
        py = int(self.player.y)
        dx, dy = cast_dir

        is_diagonal = (dx != 0 and dy != 0)

        if is_diagonal:
            # Diagonal cone: target tile + two adjacent tiles along the diagonal
            tiles = [
                (px + dx, py + dy),
                (px + dx * 2, py + dy),
                (px + dx, py + dy * 2),
            ]
        else:
            # Cardinal cone: target tile + two perpendicular tiles
            if dx != 0:
                # Horizontal: fan vertically
                tiles = [
                    (px + dx, py),
                    (px + dx, py - 1),
                    (px + dx, py + 1),
                ]
            else:
                # Vertical: fan horizontally
                tiles = [
                    (px, py + dy),
                    (px - 1, py + dy),
                    (px + 1, py + dy),
                ]

        all_results = []
        context = {"cast_direction": cast_dir}

        for tx, ty in tiles:
            effect = EffectInstance(
                tx, ty,
                spell_descriptor,
                duration=spell_descriptor.get("duration", 0.3),
                radius=0
            )
            effect.caster = self.player
            self.world.spawn_effect(effect)

            results = self._apply_effect_with_context(effect, context)
            all_results.extend(results)

        return all_results

    def _handle_path_spell(self, spell_descriptor, cast_dir):
        """
        Handle path effect spells (Blast).
        Affects entities in a 3-tile line in front of the player and pushes them.
        """
        px = int(self.player.x)
        py = int(self.player.y)
        dx, dy = cast_dir

        push_force = spell_descriptor.get("push_force", 1)
        all_results = []
        context = {"cast_direction": cast_dir}

        for i in range(1, 4):  # 3 tiles in a line
            tx = px + dx * i
            ty = py + dy * i

            effect = EffectInstance(
                tx, ty,
                spell_descriptor,
                duration=spell_descriptor.get("duration", 0.2),
                radius=0
            )
            effect.caster = self.player
            self.world.spawn_effect(effect)

            # Get entities at this tile and push them
            entities = self.world.get_entities_in_rect(tx, ty, 1.0, 1.0)
            for entity in entities:
                if entity.id == self.player.id:
                    continue
                if entity.has_tag("effect"):
                    continue

                result = entity.on_magic_applied(spell_descriptor, context)
                if result.get("affected"):
                    all_results.append((entity, result))

                # Push entity in cast direction
                for _ in range(push_force):
                    self.world.try_push_entity(entity, dx, dy)

        return all_results

    def _handle_projectile_spell(self, spell_descriptor, mouse_x, mouse_y):
        """
        Handle projectile spells (bullet combos).
        Fires a Projectile toward the mouse cursor carrying the spell's
        element, damage, and status effects.
        """
        import math

        # Calculate angle from player center to mouse (screen coords)
        player_screen_x, player_screen_y = self.camera.grid_to_screen(
            self.player.x + 0.5, self.player.y + 0.5
        )
        dx = mouse_x - player_screen_x
        dy = mouse_y - player_screen_y
        angle = math.atan2(dy, dx)

        # Get spell properties
        speed = spell_descriptor.get("projectile_speed", 10.0)
        damage_info = spell_descriptor.get("damage", {})
        damage_amount = damage_info.get("amount", 10)
        damage_type = damage_info.get("type", "physical")
        max_range = spell_descriptor.get("projectile_range", 10.0)

        # Create projectile at player center
        projectile = Projectile(
            self.player.x + 0.5,
            self.player.y + 0.5,
            angle,
            speed,
            damage_amount,
            owner=self.player
        )

        # Set damage type
        projectile.damage_type = damage_type

        # Set max range
        projectile.max_range = max_range

        # Color based on element
        from ..reactions import ELEMENT_COLORS
        element = spell_descriptor.get("element", "physical")
        projectile.color = ELEMENT_COLORS.get(element, (200, 200, 200))

        # Set status effects
        status_effects = spell_descriptor.get("status_effects", [])
        if status_effects:
            projectile.arrow_status_effects = status_effects

        # Store full spell descriptor for on_magic_applied on hit
        projectile.spell_descriptor = spell_descriptor

        # Set knockback if spell has push_force
        if spell_descriptor.get("push_force", 0) > 0:
            projectile.arrow_knockback = True

        # Add to world and active projectiles
        self.world.add_entity(projectile)
        self.active_projectiles.append(projectile)

        # Update player facing toward mouse
        facing = self._get_facing_from_mouse(mouse_x, mouse_y)
        self.player.facing = facing
        self.player.transform.facing = facing

        return []

    def _apply_post_spell_effects(self, spell_descriptor, results, cast_dir):
        """Apply post-application spell effects: knockback, cleanse, dispel."""
        # Knockback / push_force
        push_force = spell_descriptor.get("push_force", 0)
        if spell_descriptor.get("knockback"):
            push_force = max(push_force, 1)

        if push_force > 0:
            self._apply_knockback(results, push_force, cast_dir)

        # Cleanses
        if spell_descriptor.get("cleanses"):
            self._apply_cleanse(spell_descriptor, results)

        # Dispel
        if spell_descriptor.get("dispels"):
            self._apply_dispel(spell_descriptor)

    def _apply_knockback(self, results, push_force, cast_dir):
        """Push hit entities away from caster."""
        for entity, result in results:
            if not hasattr(entity, 'stats'):
                continue
            # Calculate direction from caster to entity
            ex = entity.x - self.player.x
            ey = entity.y - self.player.y

            # Normalize to -1, 0, 1
            if ex != 0:
                push_dx = 1 if ex > 0 else -1
            else:
                push_dx = cast_dir[0]
            if ey != 0:
                push_dy = 1 if ey > 0 else -1
            else:
                push_dy = cast_dir[1]

            for _ in range(push_force):
                if not self.world.try_push_entity(entity, push_dx, push_dy):
                    break
            print(f"[Magic] Knocked back {entity} by {push_force}")

    def _apply_cleanse(self, spell_descriptor, results):
        """Remove negative status effects from hit entities."""
        from ..reactions import NEGATIVE_STATUSES

        # Cleanse hit entities
        for entity, result in results:
            if hasattr(entity, 'status'):
                for status_name in NEGATIVE_STATUSES:
                    if entity.status.has_flag(status_name):
                        entity.status.remove_effect(status_name)
                        print(f"[Cleanse] Removed {status_name} from {entity}")

        # Self-targeting spells also cleanse caster
        if spell_descriptor.get("affects_caster") or not results:
            if hasattr(self.player, 'status'):
                for status_name in NEGATIVE_STATUSES:
                    if self.player.status.has_flag(status_name):
                        self.player.status.remove_effect(status_name)
                        print(f"[Cleanse] Removed {status_name} from player")

    def _apply_dispel(self, spell_descriptor):
        """Remove all active spell effects (EffectInstances) in radius."""
        radius = spell_descriptor.get("radius", 2)
        target_x = self.player.x
        target_y = self.player.y

        effects_to_remove = []
        for effect in self.world.active_effects:
            dist = abs(effect.x - target_x) + abs(effect.y - target_y)
            if dist <= radius:
                effects_to_remove.append(effect)

        for effect in effects_to_remove:
            if effect in self.world.active_effects:
                self.world.active_effects.remove(effect)
            self.world.remove_entity(effect)
            print(f"[Dispel] Removed effect at ({effect.x}, {effect.y})")

    def _handle_weapon_dismiss(self):
        """Handle dismissing/dropping the currently held weapon (R key)."""
        if not self.player:
            return

        # Physical weapon: drop on ground (not vanish)
        if self.player.hand_occupancy.physical_weapon is not None:
            pw = self.player.hand_occupancy.drop_physical_weapon()
            if pw:
                self._spawn_ground_item(pw.item_instance, self.player.x, self.player.y)
                self.player.inventory.equipped_weapon = None
                self.show_message(f"Dropped {pw.name}", 1.5)
            return

        # Summoned weapon: dismiss (vanish)
        if self.player.hand_occupancy.summoned_weapon is not None:
            weapon = self.player.hand_occupancy.dismiss_weapon()
            if weapon:
                self.show_message(f"Dismissed {weapon.name}", 1.5)

    def _pickup_ground_item(self, ground_entity):
        """Pick up a ground item entity."""
        item_instance = ground_entity.item_instance

        # If weapon and no weapon held, auto-equip
        if (item_instance.is_weapon
                and not self.player.hand_occupancy.is_holding_weapon()):
            pw = PhysicalWeapon(item_instance, owner=self.player)
            self.player.hand_occupancy.equip_physical_weapon(pw)
            self.player.inventory.equipped_weapon = item_instance
            self.world.remove_entity(ground_entity)
            self.show_message(f"Equipped {item_instance.name}", 2.0)
        else:
            # Add to backpack
            if self.player.inventory.add_item(item_instance):
                self.world.remove_entity(ground_entity)
                self.show_message(f"Picked up {item_instance.name}", 1.5)
            else:
                self.show_message("Inventory full!", 1.5)

    def _handle_inventory_action(self, action):
        """Handle an action from the inventory UI."""
        action_type = action.get("type")

        if action_type == "close":
            return

        item = action.get("item")
        is_equipped = action.get("equipped", False)
        backpack_index = action.get("backpack_index", -1)

        if action_type == "equip":
            if not item or not item.is_weapon:
                return
            if is_equipped:
                # Already equipped - unequip to backpack
                pw = self.player.hand_occupancy.drop_physical_weapon()
                if pw:
                    self.player.inventory.equipped_weapon = None
                    self.player.inventory.add_item(pw.item_instance)
                    self.show_message(f"Unequipped {pw.name}", 1.5)
            else:
                # Equip from backpack
                removed = self.player.inventory.remove_item_at(backpack_index)
                if removed:
                    # Drop/dismiss current weapon if any
                    if self.player.hand_occupancy.physical_weapon is not None:
                        old_pw = self.player.hand_occupancy.drop_physical_weapon()
                        if old_pw:
                            self.player.inventory.add_item(old_pw.item_instance)
                        self.player.inventory.equipped_weapon = None
                    if self.player.hand_occupancy.summoned_weapon is not None:
                        self.player.hand_occupancy.dismiss_weapon()

                    pw = PhysicalWeapon(removed, owner=self.player)
                    self.player.hand_occupancy.equip_physical_weapon(pw)
                    self.player.inventory.equipped_weapon = removed
                    self.show_message(f"Equipped {removed.name}", 1.5)

        elif action_type == "drop":
            if is_equipped:
                # Drop equipped weapon on ground
                pw = self.player.hand_occupancy.drop_physical_weapon()
                if pw:
                    self._spawn_ground_item(pw.item_instance, self.player.x, self.player.y)
                    self.player.inventory.equipped_weapon = None
                    self.show_message(f"Dropped {pw.name}", 1.5)
            else:
                # Drop backpack item on ground
                removed = self.player.inventory.remove_item_at(backpack_index)
                if removed:
                    self._spawn_ground_item(removed, self.player.x, self.player.y)
                    self.show_message(f"Dropped {removed.name}", 1.5)

    def _spawn_ground_item(self, item_instance, x, y):
        """Create a GroundItem entity at the given position and add to world."""
        gi = GroundItem(x, y, item_instance)
        self.world.add_entity(gi)

    def _restore_equipped_physical_weapon(self):
        """Re-equip physical weapon from inventory after loading a save."""
        if not self.player:
            return
        equipped_item = self.player.inventory.equipped_weapon
        if equipped_item and equipped_item.is_weapon:
            pw = PhysicalWeapon(equipped_item, owner=self.player)
            self.player.hand_occupancy.equip_physical_weapon(pw)

    def _get_facing_from_mouse(self, mouse_x, mouse_y, eight_dir=True):
        """
        Get facing direction based on mouse position relative to player.

        Args:
            mouse_x, mouse_y: Mouse screen position
            eight_dir: If True, returns 8 directions (including diagonals)
                       If False, returns 4 directions only

        Returns:
            Direction string: "up", "down", "left", "right",
            or diagonals: "up_right", "up_left", "down_right", "down_left"
        """
        import math

        # Get player's screen position (center of player)
        player_screen_x, player_screen_y = self.camera.grid_to_screen(
            self.player.x + 0.5, self.player.y + 0.5
        )

        # Calculate direction from player to mouse
        dx = mouse_x - player_screen_x
        dy = mouse_y - player_screen_y

        if dx == 0 and dy == 0:
            return "down"

        if eight_dir:
            # Use angle to determine 8-directional facing
            angle = math.atan2(dy, dx)
            if angle < 0:
                angle += 2 * math.pi

            # 8 sectors, each 45 degrees (pi/4)
            sector = int((angle + math.pi / 8) / (math.pi / 4)) % 8

            direction_map = {
                0: "right",
                1: "down_right",
                2: "down",
                3: "down_left",
                4: "left",
                5: "up_left",
                6: "up",
                7: "up_right",
            }
            return direction_map.get(sector, "down")
        else:
            # 4-directional only
            if abs(dx) > abs(dy):
                return "right" if dx > 0 else "left"
            else:
                return "down" if dy > 0 else "up"

    def _handle_weapon_input(self):
        """Handle weapon input, branching between melee and ranged."""
        if not self.player:
            return

        weapon = self.player.hand_occupancy.get_weapon()
        if not weapon:
            return

        if weapon.is_ranged():
            self._handle_ranged_input(weapon)
        elif self.input.mouse_clicked:
            self._handle_melee_attack(weapon)

    def _handle_ranged_input(self, weapon):
        """
        Handle ranged weapon input with draw mechanic.
        Click to start drawing, release to fire after draw completes.
        """
        # Start drawing on click
        if self.input.mouse_clicked and not self.bow_drawing:
            if not weapon.can_swing():
                return
            if self.player.stats.mana < weapon.get_mana_per_shot():
                self.show_message("Not enough mana!", 1.0)
                return
            self.bow_drawing = True
            self.bow_draw_timer = 0.0
            self.bow_draw_time_required = weapon.get_draw_time()

        # Update player facing toward mouse while drawing
        if self.bow_drawing and self.input.mouse_held:
            mouse_x, mouse_y = self.input.get_mouse_position()
            facing = self._get_facing_from_mouse(mouse_x, mouse_y)
            self.player.facing = facing
            self.player.transform.facing = facing

        # Fire on release
        if self.bow_drawing and self.input.mouse_released:
            if self.bow_draw_timer >= self.bow_draw_time_required:
                self._fire_ranged_weapon(weapon)
            else:
                self.show_message("Draw cancelled - hold longer!", 1.0)
            self.bow_drawing = False
            self.bow_draw_timer = 0.0

    def _fire_ranged_weapon(self, weapon):
        """Fire a projectile from a ranged weapon."""
        import math

        # Deduct mana
        if not self.player.stats.use_mana(weapon.get_mana_per_shot()):
            self.show_message("Not enough mana!", 1.0)
            return

        # Start cooldown
        weapon.start_swing()

        # Calculate angle from player center to mouse
        mouse_x, mouse_y = self.input.get_mouse_position()
        player_screen_x, player_screen_y = self.camera.grid_to_screen(
            self.player.x + 0.5, self.player.y + 0.5
        )
        dx = mouse_x - player_screen_x
        dy = mouse_y - player_screen_y
        angle = math.atan2(dy, dx)

        # Create projectile at player center
        projectile = Projectile(
            self.player.x + 0.5,
            self.player.y + 0.5,
            angle,
            weapon.get_projectile_speed(),
            weapon.damage,
            owner=self.player
        )

        # Apply enchanted bow properties
        if weapon.is_enchanted():
            projectile.enchantment = weapon.get_enchantment()
            projectile.arrow_status_effects = weapon.get_arrow_status_effects()
            projectile.arrow_knockback = weapon.has_arrow_knockback()
            projectile.cleanses_caster_on_hit = weapon.cleanses_caster_on_hit()
            # Color arrows based on enchantment
            from ..reactions import ELEMENT_COLORS
            projectile.color = ELEMENT_COLORS.get(weapon.get_enchantment(), projectile.color)

        # Override max range if weapon specifies it
        max_range = weapon.get_max_range()
        if max_range != 15.0:
            projectile.max_range = max_range

        self.world.add_entity(projectile)
        self.active_projectiles.append(projectile)

        # Update player facing
        facing = self._get_facing_from_mouse(mouse_x, mouse_y)
        self.player.facing = facing
        self.player.transform.facing = facing

    def _handle_melee_attack(self, weapon):
        """Handle melee weapon attack (left-click when holding a melee weapon)."""
        # Check if weapon can swing (cooldown ready)
        if not weapon.can_swing():
            return

        # Start the swing
        weapon.start_swing()

        # Get attack direction from mouse position
        mouse_x, mouse_y = self.input.get_mouse_position()
        attack_facing = self._get_facing_from_mouse(mouse_x, mouse_y)

        # Update player facing to match attack direction
        self.player.facing = attack_facing
        self.player.transform.facing = attack_facing

        # Get all hitbox rectangles (supports arc for diagonal attacks)
        hitbox_rects = weapon.get_swing_hitbox_rects(
            self.player.x, self.player.y, attack_facing
        )

        # Collect all entities from all hitbox rectangles
        all_entities = {}
        for rect in hitbox_rects:
            hb_x, hb_y, hb_w, hb_h = rect
            entities = self.world.get_entities_in_rect(hb_x, hb_y, hb_w, hb_h)
            for entity in entities:
                all_entities[entity.id] = entity

        # Determine if enchantment is active (has mana)
        enchant_active = False
        if weapon.is_enchanted():
            mana_cost = weapon.get_mana_per_hit()
            if self.player.stats.mana >= mana_cost:
                enchant_active = True

        # Apply damage to entities in hit area
        total_hits = 0
        destroyed_trees = []

        for entity in all_entities.values():
            if entity.id == self.player.id:
                continue

            # Handle world objects (trees, etc.)
            if hasattr(entity, 'on_slashing_attack'):
                result = entity.on_slashing_attack(
                    weapon.get_slashing_power(),
                    weapon.get_swing_damage(),
                    {"attacker": self.player}
                )
                if result.get("affected"):
                    total_hits += 1
                    for msg in result.get("messages", []):
                        print(f"[Weapon] {msg}")

                    # Track destroyed trees for log spawning
                    if result.get("destroyed") and entity.object_type == "tree":
                        destroyed_trees.append(entity)

                    # Apply enchantment effects to world objects
                    if enchant_active:
                        enchant_element = weapon.get_enchantment()
                        if enchant_element:
                            enchant_descriptor = {
                                "element": enchant_element,
                                "status_effects": weapon.get_hit_status_effects(),
                            }
                            entity.on_magic_applied(enchant_descriptor)

            # Handle actors (NPCs, enemies)
            elif hasattr(entity, 'stats'):
                # Apply slashing damage to actors
                damage = weapon.get_swing_damage()
                actual_damage = entity.stats.take_damage(damage, "slashing")
                if actual_damage > 0:
                    total_hits += 1
                    print(f"[Weapon] Hit {entity} for {actual_damage} damage")

                    # Apply enchantment effects if active
                    if enchant_active:
                        self._apply_enchantment_on_hit(weapon, entity)

                        # Apply push force from enchanted weapons (gale/power)
                        push_force = weapon.get_push_force()
                        if push_force > 0:
                            ex = entity.x - self.player.x
                            ey = entity.y - self.player.y
                            push_dx = (1 if ex > 0 else -1) if ex != 0 else 0
                            push_dy = (1 if ey > 0 else -1) if ey != 0 else 0
                            for _ in range(push_force):
                                if not self.world.try_push_entity(entity, push_dx, push_dy):
                                    break

        # Deduct enchantment mana if any hits landed
        if enchant_active and total_hits > 0:
            self.player.stats.use_mana(weapon.get_mana_per_hit())
            # Cleanse caster if weapon has that property
            if weapon.cleanses_caster():
                self._cleanse_player_negative_status()

        # Spawn logs for destroyed trees
        for tree in destroyed_trees:
            if tree.spawn_on_destroy and tree.destruction_cause == "slashing":
                self._spawn_log_at(tree.x, tree.y)

        # Visual feedback
        if total_hits > 0:
            self.show_message(f"{weapon.name} strikes!", 0.5)
        else:
            self.show_message(f"{weapon.name} swings!", 0.3)

        # Store swing info for rendering (all rects for arc visual)
        self.weapon_swing_effect = {
            "rects": hitbox_rects,
            "timer": 0.15
        }
        self.weapon_swing_timer = 0.15

    def _update_enemy_ai(self, dt):
        """Update AI for all enemies and process pending enemy actions."""
        enemies = self.world.get_entities_by_tag("enemy")
        for enemy in enemies:
            if not enemy.active or not enemy.is_alive():
                continue
            if hasattr(enemy, 'update_ai'):
                enemy.update_ai(dt, self.world, self.player)

            # Process pending enemy projectiles
            if getattr(enemy, 'pending_projectile', None):
                self._spawn_enemy_projectile(enemy)
                enemy.pending_projectile = None

            # Process pending AoE visuals
            if getattr(enemy, 'pending_aoe', None):
                self._spawn_enemy_aoe_effect(enemy)
                enemy.pending_aoe = None

    def _spawn_enemy_projectile(self, enemy):
        """Create a projectile from an enemy's pending attack."""
        import math as m
        info = enemy.pending_projectile

        projectile = Projectile(
            enemy.x + 0.5,
            enemy.y + 0.5,
            info["angle"],
            info["speed"],
            info["damage"],
            owner=enemy
        )
        projectile.damage_type = info.get("damage_type", "physical")
        projectile.max_range = info.get("max_range", 10.0)

        # Color by element
        from ..reactions import ELEMENT_COLORS
        element = info.get("element", "physical")
        projectile.color = ELEMENT_COLORS.get(element, (200, 200, 200))

        # Status effects
        if info.get("status_effects"):
            projectile.arrow_status_effects = info["status_effects"]

        # Tag as enemy projectile
        projectile.add_tag("enemy_projectile")

        # Store knockback info
        projectile.knockback_multiplier = info.get("knockback_multiplier", 0.5)

        self.world.add_entity(projectile)
        self.active_projectiles.append(projectile)

    def _spawn_enemy_aoe_effect(self, enemy):
        """Spawn a brief AoE visual effect from an enemy attack."""
        info = enemy.pending_aoe
        effect = EffectInstance(
            info["x"], info["y"],
            {"element": info.get("element", "earth")},
            duration=0.5,
            radius=int(info.get("radius", 2))
        )
        effect.caster = enemy
        self.world.spawn_effect(effect)

    def _check_enemy_damage(self):
        """Check for contact damage between enemies and player."""
        hits = check_contact_damage(self.world)
        for enemy, attack_def in hits:
            name = attack_def.get("name", "Attack")
            damage = attack_def.get("damage", 0)
            self.show_message(f"{name}! (-{damage})", 1.0)

    def _update_projectiles(self, dt):
        """Update all active projectiles - movement, collision, cleanup."""
        to_remove = []

        for projectile in self.active_projectiles:
            if not projectile.alive:
                to_remove.append(projectile)
                continue

            # Update position
            projectile.update(dt)

            # Check tile collision
            if projectile.check_tile_collision(self.world):
                self._spawn_arrow_impact(projectile.x, projectile.y)
                # Find what solid entity the projectile hit (if any)
                tile_x = int(projectile.x)
                tile_y = int(projectile.y)
                tile_entity = None
                for e in self.world.get_entities_at(tile_x, tile_y):
                    if e.solid and not e.has_tag("projectile"):
                        tile_entity = e
                        break
                self._handle_projectile_impact(projectile, tile_entity)
                to_remove.append(projectile)
                continue

            # Check entity collision
            hit_entity = projectile.check_entity_collision(self.world)
            if hit_entity:
                self._spawn_arrow_impact(projectile.x, projectile.y)
                # Enemy projectile hitting player
                if projectile.has_tag("enemy_projectile") and hit_entity.has_tag("player"):
                    self._handle_enemy_projectile_hit(projectile, hit_entity)
                elif self._is_elemental_projectile(projectile):
                    # Elemental projectile - spawn AoE that handles
                    # damage + status for all entities in impact area
                    self._handle_projectile_impact(projectile, hit_entity)
                else:
                    # Plain arrow - just direct damage to hit entity
                    projectile.apply_damage(hit_entity)
                to_remove.append(projectile)
                continue

        # Remove dead projectiles
        for projectile in to_remove:
            if projectile in self.active_projectiles:
                self.active_projectiles.remove(projectile)
            if projectile.id in self.world.entities:
                self.world.remove_entity(projectile)

        # Update arrow impact effects
        remaining = []
        for effect in self.arrow_impact_effects:
            effect["timer"] -= dt
            if effect["timer"] > 0:
                remaining.append(effect)
        self.arrow_impact_effects = remaining

    def _handle_enemy_projectile_hit(self, projectile, player):
        """Handle an enemy projectile hitting the player."""
        import math as m
        dx = player.x - projectile.x
        dy = player.y - projectile.y
        length = m.sqrt(dx * dx + dy * dy)
        if length > 0:
            kb_dir = (dx / length, dy / length)
        else:
            kb_dir = (0, 1)

        kb_mult = getattr(projectile, 'knockback_multiplier', 0.5)
        status_effects = getattr(projectile, 'arrow_status_effects', [])

        player.take_hit(
            damage=projectile.damage,
            damage_type=projectile.damage_type,
            knockback_dir=kb_dir,
            knockback_multiplier=kb_mult,
            status_effects=status_effects,
        )
        projectile.alive = False
        self.show_message(f"Hit by projectile! (-{projectile.damage})", 1.0)

    def _spawn_arrow_impact(self, x, y):
        """Spawn a small visual impact effect at the arrow's hit location."""
        self.arrow_impact_effects.append({
            "x": x,
            "y": y,
            "timer": self.arrow_impact_duration,
        })

    def _is_elemental_projectile(self, projectile):
        """Check if a projectile carries elemental effects (spell or enchanted arrow)."""
        return (getattr(projectile, 'spell_descriptor', None) is not None
                or getattr(projectile, 'enchantment', None) is not None)

    def _handle_projectile_impact(self, projectile, hit_entity=None):
        """Spawn an elemental AoE at the projectile's impact point.

        Queries all entities in a small area and calls on_magic_applied on each,
        so trees catch fire, enemies take damage and receive status effects, etc.
        Also spawns a brief visual EffectInstance.

        Args:
            projectile: The projectile that hit something.
            hit_entity: The specific entity that was hit (if any). Used to
                        calculate the true impact point between the projectile
                        and the target, ensuring the AoE always overlaps.
        """
        spell_desc = getattr(projectile, 'spell_descriptor', None)
        enchant = getattr(projectile, 'enchantment', None)

        if spell_desc:
            # Spell projectile - use full spell descriptor
            impact_desc = spell_desc
            aoe_size = spell_desc.get("impact_radius", 0.5)
        elif enchant:
            # Enchanted arrow - construct descriptor from enchantment
            aoe_size = 0.5  # ~4 sub-grid cells
            impact_desc = {
                "element": enchant,
                "damage": {"amount": projectile.damage, "type": projectile.damage_type},
                "status_effects": getattr(projectile, 'arrow_status_effects', []),
            }
        else:
            return

        # Calculate impact point: if we hit a specific entity, use the
        # midpoint between projectile and entity center so the AoE always
        # overlaps the target. Otherwise use the projectile position.
        if hit_entity is not None:
            # Entity center (world objects sit at integer coords, center is +0.5)
            if getattr(hit_entity, 'uses_sub_grid', False):
                ex, ey = hit_entity.x + 0.5, hit_entity.y + 0.5
            else:
                ex = int(hit_entity.x) + 0.5
                ey = int(hit_entity.y) + 0.5
            # Midpoint between projectile and entity center
            impact_x = (projectile.x + ex) / 2.0
            impact_y = (projectile.y + ey) / 2.0
        else:
            impact_x = projectile.x
            impact_y = projectile.y

        # Query entities in AoE rect centered on impact point
        half = aoe_size / 2.0
        entities = self.world.get_entities_in_rect(
            impact_x - half, impact_y - half,
            aoe_size, aoe_size
        )

        context = {"world": self.world, "caster": projectile.owner}
        for entity in entities:
            if entity.id == projectile.id:
                continue
            if projectile.owner and entity.id == projectile.owner.id:
                continue
            if entity.has_tag("projectile") or entity.has_tag("effect") or entity.has_tag("rune_stone"):
                continue

            if hasattr(entity, 'on_magic_applied'):
                entity.on_magic_applied(impact_desc, context)

        # Spawn brief visual effect at impact point
        effect = EffectInstance(
            impact_x, impact_y,
            impact_desc,
            duration=0.3,
            radius=0
        )
        effect.caster = projectile.owner
        self.world.spawn_effect(effect)

        projectile.alive = False

        # Cleanse caster on hit (light bow)
        if getattr(projectile, 'cleanses_caster_on_hit', False):
            self._cleanse_player_negative_status()

    def _spawn_log_at(self, x, y):
        """Spawn a log at the given position."""
        log = WorldObject(x, y, object_type="log")
        self.world.add_entity(log)
        print(f"[World] Spawned log at ({x}, {y})")

    def _apply_enchantment_on_hit(self, weapon, entity):
        """Apply enchanted weapon effects to a hit entity."""
        # Apply status effects from enchantment
        if hasattr(entity, 'status'):
            for effect_data in weapon.get_hit_status_effects():
                entity.status.add_effect(
                    effect_data["name"],
                    duration=effect_data.get("duration", 3.0),
                    intensity=effect_data.get("intensity", 1.0),
                    source=weapon.get_enchantment()
                )
                print(f"[Enchant] Applied {effect_data['name']} to {entity}")

    def _cleanse_player_negative_status(self):
        """Remove one negative status effect from the player."""
        from ..reactions import NEGATIVE_STATUSES
        if not hasattr(self.player, 'status'):
            return
        for status_name in NEGATIVE_STATUSES:
            if self.player.status.has_flag(status_name):
                self.player.status.remove_effect(status_name)
                print(f"[Cleanse] Removed {status_name} from player")
                return

    def _apply_effect_with_context(self, effect, context):
        """Apply effect to entities with additional context (sub-grid aware)."""
        results = []

        # Use rect-based detection for precise sub-grid hitbox
        rect = effect.get_affected_rect()
        entities = self.world.get_entities_in_rect(*rect)

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

    def _get_interaction_rect(self, facing):
        """
        Get the interaction hitbox rectangle based on player position and facing.
        Uses a smaller 1x1 tile (8x8 sub-grid) area for precise interaction.

        Returns (x, y, width, height) in float tile units.
        """
        px, py = self.player.x, self.player.y
        cx, cy = px + 0.5, py + 0.5  # Player center

        # Interaction area: 1 tile in facing direction (8x8 fine grid)
        size = 1.0

        # Cardinal directions
        if facing == "right":
            return (px + 1.0, py, size, size)
        elif facing == "left":
            return (px - size, py, size, size)
        elif facing == "up":
            return (px, py - size, size, size)
        elif facing == "down":
            return (px, py + 1.0, size, size)

        # Diagonal directions
        if facing == "up_right":
            return (px + 1.0, py - size, size, size)
        elif facing == "up_left":
            return (px - size, py - size, size, size)
        elif facing == "down_right":
            return (px + 1.0, py + 1.0, size, size)
        elif facing == "down_left":
            return (px - size, py + 1.0, size, size)

        # Default
        return (px, py + 1.0, size, size)

    def _calculate_rect_overlap(self, rect1, rect2):
        """
        Calculate the overlap area between two rectangles.
        Returns the overlap area (0 if no overlap).

        Args:
            rect1, rect2: Tuples of (x, y, width, height)
        """
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2

        # Calculate overlap in each dimension
        overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))

        return overlap_x * overlap_y

    def _handle_interaction(self):
        """
        Handle player interaction with nearby entities.
        Uses mouse direction and picks entity with most overlap in the interaction area.
        """
        # Get interaction direction from mouse position (8-directional)
        mouse_x, mouse_y = self.input.get_mouse_position()
        interact_facing = self._get_facing_from_mouse(mouse_x, mouse_y)

        # Snap player to face the interaction direction (4-directional)
        four_dir_facing = self._get_facing_from_mouse(mouse_x, mouse_y, eight_dir=False)
        self.player.facing = four_dir_facing
        self.player.transform.facing = four_dir_facing

        # Get interaction rect in mouse direction (1x1 tile / 8x8 fine grid)
        interact_rect = self._get_interaction_rect(interact_facing)

        # Get entities in the interaction area
        rx, ry, rw, rh = interact_rect
        entities = self.world.get_entities_in_rect(rx, ry, rw, rh)

        # Check for ground items first (pickup priority)
        for entity in entities:
            if entity.id == self.player.id:
                continue
            if entity.has_tag("ground_item"):
                overlap = self._calculate_rect_overlap(interact_rect, (entity.x, entity.y, 1.0, 1.0))
                if overlap > 0:
                    self._pickup_ground_item(entity)
                    return

        # Find interactable entity with most overlap in the interaction area
        best_entity = None
        best_overlap = 0.0

        for entity in entities:
            if entity.id == self.player.id:
                continue

            # Check if entity is interactable
            is_interactable = False
            if entity.has_tag("npc") or entity.has_tag("rune_stone"):
                is_interactable = True
            else:
                interaction = entity.get_component("InteractionComponent")
                if interaction and interaction.can_examine:
                    is_interactable = True

            if not is_interactable:
                continue

            # Calculate entity's bounding rect (1x1 tile at entity position)
            entity_rect = (entity.x, entity.y, 1.0, 1.0)

            # Calculate overlap with interaction area
            overlap = self._calculate_rect_overlap(interact_rect, entity_rect)

            if overlap > best_overlap:
                best_entity = entity
                best_overlap = overlap

        if best_entity is None:
            return

        # Interact with the closest entity
        if best_entity.has_tag("npc"):
            self._interact_with_npc(best_entity)
        elif best_entity.has_tag("rune_stone"):
            self._interact_with_rune_stone(best_entity)
        elif best_entity.has_tag("door"):
            self._interact_with_door(best_entity)
        else:
            interaction = best_entity.get_component("InteractionComponent")
            if interaction and interaction.can_examine:
                self.dialogue_box.show(interaction.examine_text)

    def _interact_with_door(self, door):
        """Handle interaction with a door to transition areas."""
        transition_data = door.get_transition_data()
        target_area = transition_data.get("target_area", "")
        target_entry = transition_data.get("target_entry", "default")

        if not target_area:
            self.show_message("This door doesn't lead anywhere.")
            return

        self.transition_to_area(target_area, target_entry)

    def _interact_with_npc(self, npc):
        """Handle interaction with an NPC using dialogue box."""
        # Pause NPC movement during conversation
        npc.in_conversation = True
        self._conversation_npc = npc

        # Check if NPC has a dialogue tree
        if npc.dialogue_tree:
            self._start_dialogue_tree(npc, npc.dialogue_tree)
            return

        # Legacy dialogue handling
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

    def _start_dialogue_tree(self, npc, tree_data):
        """Start a branching dialogue tree conversation."""
        from ..ui.dialogue_box import DialogueTree

        # Create dialogue tree from data
        tree = DialogueTree(tree_data)
        node = tree.start("start")

        if not node:
            # Fallback to simple greeting
            self.dialogue_box.show(npc.get_greeting(self.player), npc.get_display_name())
            return

        # Store tree reference for continuation
        self._active_dialogue_tree = tree
        self._active_dialogue_npc = npc

        # Show first node
        self._show_dialogue_node(node, npc)

    def _show_dialogue_node(self, node, npc):
        """Display a single dialogue node."""
        if not node:
            # Dialogue complete, check for teaching
            self._finish_dialogue_with_npc(npc)
            return

        speaker = node.get("speaker", npc.get_display_name())
        text = node.get("text", "...")

        if "choices" in node:
            # Show choice dialogue
            choices = [{"label": c["label"], "value": i} for i, c in enumerate(node["choices"])]

            def on_choice(choice_index):
                next_node = self._active_dialogue_tree.advance(choice_index)
                self._show_dialogue_node(next_node, npc)

            self.dialogue_box.show_choice(text, choices, on_choice, speaker)
        else:
            # Show regular dialogue, then advance
            def after_text():
                next_node = self._active_dialogue_tree.advance()
                if next_node:
                    self._show_dialogue_node(next_node, npc)
                else:
                    self._finish_dialogue_with_npc(npc)

            # Queue text and set up continuation
            self.dialogue_box.show(text, speaker)
            self._pending_dialogue_continuation = after_text

    def _on_dialogue_closed(self):
        """Called when dialogue box closes - handle continuations and NPC state."""
        # Check for pending dialogue continuation
        if self._pending_dialogue_continuation:
            continuation = self._pending_dialogue_continuation
            self._pending_dialogue_continuation = None
            continuation()
            return  # Continuation may start new dialogue

        # Resume NPC movement if no continuation
        if self._conversation_npc:
            self._conversation_npc.in_conversation = False
            self._conversation_npc = None

    def _finish_dialogue_with_npc(self, npc):
        """Handle end of dialogue - teach symbols if applicable."""
        self._active_dialogue_tree = None
        self._active_dialogue_npc = None
        self._pending_dialogue_continuation = None
        self._conversation_npc = None

        # Resume NPC movement
        npc.in_conversation = False

        # Check if NPC can teach something
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
                    self.spell_notebook.learn_spell(symbol_id)
                    self.dialogue_box.show(
                        [f"Let me teach you the symbol of {symbol_id}...",
                         f"You have learned: {symbol_id}!"],
                        npc.get_display_name()
                    )

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
            "SPACE=Magic, WASD=Move, E=Interact, Click=Attack, "
            "R=Dismiss, I=Introspect, J=Journal, TAB=Menu, ESC=Pause"
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
            apply_save_data(save_data, self.player, self.world, self.notebook, self.spell_notebook)
            # Re-equip physical weapon from inventory if one was saved
            self._restore_equipped_physical_weapon()
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
            self.game_menu.close()
            self._go_to_title()
        elif action == "resume":
            # Clean slate - close menu and any other open UI (journal)
            self.game_menu.close()
            if self.spell_notebook.is_open:
                self.spell_notebook.close()
        elif action == "journal":
            self.spell_notebook.open()
        elif action == "customize_spells":
            self._open_radial_menu_editor()
        elif action == "settings":
            self.settings_menu.open()
        elif action == "inventory":
            if self.player:
                self.inventory_ui.open(self.player.inventory)

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

    def _apply_settings(self):
        """Apply current settings to game systems."""
        # Apply casting reset setting to radial menu
        casting_reset = self.settings_menu.get_setting("casting_reset")
        if casting_reset is not None:
            self.radial_menu.set_casting_reset(casting_reset)

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

        # Render weapon swing effect
        if self.weapon_swing_timer > 0 and self.weapon_swing_effect:
            self._render_weapon_swing()

        # Render arrow impact effects
        if self.arrow_impact_effects:
            self._render_arrow_impacts()

        # Render weapon HUD (what weapon is held)
        if self.player and self.player.hand_occupancy.is_holding_weapon():
            self._render_weapon_hud()

        # Render bow draw indicator
        if self.bow_drawing:
            self._render_bow_draw_indicator()

        # Render dialogue box
        if self.dialogue_box.is_active:
            self.dialogue_box.render(self.screen)

        # Render spell notebook/journal
        if self.spell_notebook.is_open:
            self.spell_notebook.render(self.screen)

        # Render inventory UI
        if self.inventory_ui.is_open:
            self.inventory_ui.render(self.screen)

        # Render game menu (on top of everything)
        if self.game_menu.is_open:
            self.game_menu.render(self.screen)

        # Render pause overlay
        if self.paused:
            self._render_pause_overlay()

        # Render radial menu editor (full-screen overlay)
        if self.radial_menu_editor.is_open:
            self.radial_menu_editor.render(self.screen)

        # Render settings menu (full-screen overlay)
        if self.settings_menu.is_open:
            self.settings_menu.render(self.screen)

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

    def _render_weapon_swing(self):
        """Render visual feedback for weapon swing (sub-grid aware, supports arc effect)."""
        if not self.weapon_swing_effect:
            return

        # Calculate alpha based on timer
        alpha = int((self.weapon_swing_timer / 0.15) * 180)

        # Check if using new multi-rect arc effect
        if "rects" in self.weapon_swing_effect:
            # Render all rectangles for arc effect
            for rect in self.weapon_swing_effect["rects"]:
                hb_x, hb_y, hb_w, hb_h = rect

                # Convert to screen coordinates
                screen_x, screen_y = self.camera.grid_to_screen(hb_x, hb_y)
                pixel_w = int(hb_w * Settings.TILE_SIZE)
                pixel_h = int(hb_h * Settings.TILE_SIZE)

                # Draw swing effect
                swing_surf = pygame.Surface((pixel_w, pixel_h), pygame.SRCALPHA)
                swing_surf.fill((255, 200, 100, alpha))
                self.screen.blit(swing_surf, (int(screen_x), int(screen_y)))
        elif "rect" in self.weapon_swing_effect:
            # Single rect-based rendering (backward compatibility)
            hb_x, hb_y, hb_w, hb_h = self.weapon_swing_effect["rect"]

            # Convert to screen coordinates
            screen_x, screen_y = self.camera.grid_to_screen(hb_x, hb_y)
            pixel_w = int(hb_w * Settings.TILE_SIZE)
            pixel_h = int(hb_h * Settings.TILE_SIZE)

            # Draw swing effect
            swing_surf = pygame.Surface((pixel_w, pixel_h), pygame.SRCALPHA)
            swing_surf.fill((255, 200, 100, alpha))
            self.screen.blit(swing_surf, (int(screen_x), int(screen_y)))
        else:
            # Legacy tile-based rendering (backward compatibility)
            tiles = self.weapon_swing_effect.get("tiles", [])
            for tile_x, tile_y in tiles:
                screen_x, screen_y = self.camera.grid_to_screen(tile_x, tile_y)
                swing_surf = pygame.Surface((Settings.TILE_SIZE, Settings.TILE_SIZE), pygame.SRCALPHA)
                swing_surf.fill((255, 200, 100, alpha))
                self.screen.blit(swing_surf, (int(screen_x), int(screen_y)))

    def _render_weapon_hud(self):
        """Render HUD showing currently held weapon."""
        weapon = self.player.hand_occupancy.get_weapon()
        if not weapon:
            return

        font = pygame.font.Font(None, 20)

        # Weapon name and info
        hands_text = "2H" if weapon.is_two_handed() else "1H"
        weapon_text = f"{weapon.name} [{hands_text}]"

        # Cooldown indicator
        if weapon.current_cooldown > 0:
            cooldown_pct = int((weapon.current_cooldown / weapon.swing_cooldown) * 100)
            weapon_text += f" (CD: {cooldown_pct}%)"
        else:
            weapon_text += " [Ready]"

        text_surf = font.render(weapon_text, True, weapon.color)

        # Position in bottom-left
        x = 10
        y = Settings.SCREEN_HEIGHT - 60

        # Background
        padding = 4
        bg_rect = pygame.Rect(x - padding, y - padding,
                              text_surf.get_width() + padding * 2,
                              text_surf.get_height() + padding * 2)
        pygame.draw.rect(self.screen, (30, 30, 40), bg_rect, border_radius=3)
        pygame.draw.rect(self.screen, weapon.color, bg_rect, 1, border_radius=3)

        self.screen.blit(text_surf, (x, y))

        # Instructions (different for ranged vs melee)
        if weapon.is_ranged():
            instruction = "R: Dismiss | Hold Click: Draw & Release to Fire"
        else:
            instruction = "R: Dismiss | Click: Attack"
        dismiss_text = font.render(instruction, True, (150, 150, 150))
        self.screen.blit(dismiss_text, (x, y + 18))

    def _render_arrow_impacts(self):
        """Render fading yellow squares at arrow impact locations."""
        sub_tile_px = Settings.TILE_SIZE // 8  # one sub-tile in pixels
        for effect in self.arrow_impact_effects:
            alpha = int((effect["timer"] / self.arrow_impact_duration) * 180)
            screen_x, screen_y = self.camera.grid_to_screen(effect["x"], effect["y"])
            # Center the sub-tile square on the impact point
            px = int(screen_x) - sub_tile_px // 2
            py = int(screen_y) - sub_tile_px // 2
            impact_surf = pygame.Surface((sub_tile_px, sub_tile_px), pygame.SRCALPHA)
            impact_surf.fill((255, 200, 100, alpha))
            self.screen.blit(impact_surf, (px, py))

    def _render_bow_draw_indicator(self):
        """Render a draw progress bar near the player when drawing a bow."""
        if not self.bow_drawing:
            return

        draw_pct = min(1.0, self.bow_draw_timer / self.bow_draw_time_required)

        # Position above the player
        player_screen_x, player_screen_y = self.camera.grid_to_screen(
            self.player.x, self.player.y
        )
        bar_width = Settings.TILE_SIZE
        bar_height = 6
        bar_x = int(player_screen_x)
        bar_y = int(player_screen_y) - 14

        # Background
        pygame.draw.rect(self.screen, (50, 50, 50),
                         (bar_x, bar_y, bar_width, bar_height))

        # Fill - green when ready, yellow when drawing
        fill_width = int(bar_width * draw_pct)
        if draw_pct >= 1.0:
            fill_color = (80, 220, 80)  # Green = ready to fire
        else:
            fill_color = (220, 180, 50)  # Yellow = still drawing
        if fill_width > 0:
            pygame.draw.rect(self.screen, fill_color,
                             (bar_x, bar_y, fill_width, bar_height))

        # Border
        pygame.draw.rect(self.screen, (150, 150, 150),
                         (bar_x, bar_y, bar_width, bar_height), 1)

    def _render_pause_overlay(self):
        """Render pause screen overlay."""
        # Semi-transparent dark overlay
        overlay = pygame.Surface((Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # Pause text
        font_large = pygame.font.Font(None, 72)
        font_small = pygame.font.Font(None, 28)

        pause_text = font_large.render("PAUSED", True, (255, 255, 255))
        resume_text = font_small.render("Press ESC to resume", True, (180, 180, 180))

        # Center the text
        pause_x = (Settings.SCREEN_WIDTH - pause_text.get_width()) // 2
        pause_y = Settings.SCREEN_HEIGHT // 2 - 50

        resume_x = (Settings.SCREEN_WIDTH - resume_text.get_width()) // 2
        resume_y = pause_y + 60

        self.screen.blit(pause_text, (pause_x, pause_y))
        self.screen.blit(resume_text, (resume_x, resume_y))
