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
