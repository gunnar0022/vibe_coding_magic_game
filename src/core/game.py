"""
Main game class - handles game loop and state management.
Updated with radial magic menu, dialogue box, introspection, and mana regen.
"""
import pygame
from .settings import Settings
from .camera import Camera
from ..world import World, MapLoader, AreaStateManager
from ..world.mana_pool import ManaPoolManager
from ..entities import Player, create_npc_from_template, EffectInstance, RuneStone, SummonedWeapon, WorldObject, Projectile, Enemy, GroundItem, PhysicalWeapon, EnemySpawner, SpawnerManager
from ..items import ItemInstance
from ..combat import check_contact_damage
from ..systems import InputHandler, Renderer, SaveSystem, create_save_data, apply_save_data, get_asset_manager
from ..ui import Notebook, RadialMagicMenu, DialogueBox, GameMenu, SpellNotebook, RadialMenuEditor, RadialMenuLayout, SettingsMenu, InventoryUI, NodeMagicMenu, NodeMenuEditor, NodeMenuLayout
from ..ui.shop_ui import ShopUI
from ..ui.title_screen import TitleScreen
from ..ui.death_screen import DeathScreen
from ..magic import MagicSystem
from .combat_handler import CombatHandler
from .interaction_handler import InteractionHandler
from .spell_handler import SpellHandler
from ..cutscene import CutsceneManager


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
        self.area_state_manager = AreaStateManager()
        self.spawner_manager = SpawnerManager()

        # Environmental mana pool system (shared per-area)
        self.mana_pool_manager = ManaPoolManager()

        # Dialogue tree state
        self._active_dialogue_tree = None
        self._active_dialogue_npc = None
        self._pending_dialogue_continuation = None
        self._conversation_npc = None  # Track NPC in conversation for movement pause

        # Player systems
        self.notebook = Notebook()

        # UI systems — spell menus (dial and node modes)
        self._radial_magic_menu = RadialMagicMenu(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self._node_magic_menu = NodeMagicMenu(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.dialogue_box = DialogueBox(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.game_menu = GameMenu(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.spell_notebook = SpellNotebook(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.radial_menu_editor = RadialMenuEditor(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.node_menu_editor = NodeMenuEditor(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.settings_menu = SettingsMenu(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.inventory_ui = InventoryUI(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.shop_ui = ShopUI(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)

        # Title and death screens
        self.title_screen = TitleScreen(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)
        self.death_screen = DeathScreen(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)

        # Modular handlers
        self.combat_handler = CombatHandler(self)
        self.interaction_handler = InteractionHandler(self)
        self.spell_handler = SpellHandler(self)
        self.cutscene_manager = CutsceneManager(self)

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

        # Health snapshot for damage-interrupt (closes menus when hit)
        self._menu_health_snapshot = 0

        # Weapon swing visual feedback
        self.weapon_swing_effect = None
        self.weapon_swing_timer = 0

        # Projectile system
        self.active_projectiles = []

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

    @property
    def radial_menu(self):
        """Active spell menu (radial dial or node canvas, based on player mode).
        Named 'radial_menu' for backward compatibility with SpellHandler."""
        if self.player and getattr(self.player, 'active_spell_mode', 'dial') == 'node':
            return self._node_magic_menu
        return self._radial_magic_menu

    def _init_world(self):
        """Initialize the game world."""
        # Try to load home village, fall back to forest if it doesn't exist
        try:
            player_spawn = self.load_area("home_village")
        except (FileNotFoundError, ValueError):
            # Fall back to forest for development
            player_spawn = self.load_area("forest")

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

        self.show_message("Hold SPACE for magic. ESC for menu.")

    def load_area(self, area_id, entry_point="default"):
        """
        Load a new area, preserving the player.

        Args:
            area_id: The area ID to load from the registry
            entry_point: Named entry point for player spawn position

        Returns:
            Player spawn position tuple (x, y)
        """
        # Validate area exists before clearing anything
        from ..world.map_loader import AREA_REGISTRY
        if area_id not in AREA_REGISTRY:
            raise ValueError(f"Unknown area: {area_id}")

        # Save current area state before leaving
        if self.current_area_id:
            self._snapshot_current_area_state()

        # Clear world entities but remember player reference
        player_ref = self.player
        has_player = player_ref is not None

        # Clear all entities from world
        self.world.clear()

        # Get persistent state for the destination area
        area_state = self.area_state_manager.get_state(area_id)

        # Load the new area with persistent state applied
        player_spawn, area_data = MapLoader.load_area(area_id, self.world, area_state=area_state)

        # Update area tracking
        self.current_area_id = area_id
        self.current_area_data = area_data

        # Register / switch to this area's environmental mana pool
        mana_cfg = area_data.get("mana_pool", {})
        self.mana_pool_manager.set_current_area(
            area_id,
            max_capacity=mana_cfg.get("max_capacity"),
            regen_rate=mana_cfg.get("regen_rate"),
        )

        # Get spawn position from named entry point
        if entry_point in area_data.get("entry_points", {}):
            ep = area_data["entry_points"][entry_point]
            player_spawn = (ep["x"], ep["y"])

        # If we have a player, reposition them in the new area
        if has_player and player_ref:
            player_ref.x = float(player_spawn[0])
            player_ref.y = float(player_spawn[1])
            self.world.add_entity(player_ref)

        # Set up enemy spawners for this area
        self._setup_spawners(area_data, area_state)

        return player_spawn

    def _setup_spawners(self, area_data, area_state):
        """
        Create EnemySpawner entities from area data and initialize them.
        """
        self.spawner_manager.clear()
        self.spawner_manager.max_enemies = area_data.get("max_enemies", 10)

        spawner_defs = area_data.get("spawner_defs", [])
        for obj_data in spawner_defs:
            spawner_id = obj_data.get(
                "spawner_id",
                f"spawner_{obj_data['x']}_{obj_data['y']}"
            )
            spawner = EnemySpawner(
                x=obj_data['x'],
                y=obj_data['y'],
                spawner_id=spawner_id,
                spawn_chance=obj_data.get('spawn_chance', 1.0),
                enemy_types=obj_data.get('enemy_types', [{"type": "slime", "weight": 100}]),
                respawn_time=obj_data.get('respawn_time', 60.0),
            )
            self.world.add_entity(spawner)
            self.spawner_manager.register_spawner(spawner)

        # Set wave interval from area data
        self.spawner_manager.wave_interval = area_data.get("spawn_wave_interval", 120.0)

        # Initialize: restore saved states or do first-time spawns
        self.spawner_manager.initialize_spawners(self.world, area_state)

    def _snapshot_current_area_state(self):
        """
        Snapshot dynamic entity state from the current area into the
        AreaStateManager before transitioning away. This captures
        player-dropped items and spawner states so they persist.
        """
        if not self.current_area_id:
            return

        area_state = self.area_state_manager.get_state(self.current_area_id)

        # Rebuild dropped items list from current world ground items
        # (only items without a map_object_id, i.e., player-dropped)
        area_state.dropped_items.clear()
        for entity in list(self.world.entities.values()):
            if entity.has_tag("ground_item") and hasattr(entity, 'map_object_id'):
                if entity.map_object_id is None:
                    area_state.add_dropped_item(
                        entity.item_instance.item_def_id,
                        entity.item_instance.quantity,
                        entity.x,
                        entity.y,
                    )

        # Save spawner states
        self.spawner_manager.save_spawner_states(area_state)

    def transition_to_area(self, target_area, target_entry="default"):
        """
        Transition to a new area via a door or portal.
        Handles the full transition including fade effect later.
        """
        # End any active focused action before switching areas
        if self.spell_handler.is_focused:
            self.spell_handler.cancel_focused_action()

        try:
            self.load_area(target_area, target_entry)
            area_name = self.current_area_data.get("name", target_area)
            self.show_message(f"Entered {area_name}")
            self._check_area_cutscenes(target_area)
        except (FileNotFoundError, ValueError) as e:
            self.show_message(f"Cannot enter: {e}")

    def _check_zone_transitions(self):
        """Check if player has entered a zone transition area."""
        if not self.player:
            return

        # Get entities at player's position
        px, py = self.player.x, self.player.y
        entities = self.world.get_entities_in_rect(px, py, 1.0, 1.0)

        for entity in entities:
            if entity.has_tag("zone_transition"):
                # Player stepped on a zone transition - teleport them
                transition_data = entity.get_transition_data()
                target_area = transition_data.get("target_area", "")
                target_entry = transition_data.get("target_entry", "default")

                if target_area:
                    self.transition_to_area(target_area, target_entry)
                    return  # Only transition once

    def _check_area_cutscenes(self, area_id):
        """Trigger one-time cutscenes when entering an area."""
        if area_id == "forest":
            area_state = self.area_state_manager.get_state("forest")
            if not area_state.get_flag("forest_intro_played"):
                from ..cutscene.scripts.forest_intro import build_forest_intro
                self.cutscene_manager.start(build_forest_intro())

    def _init_player_radial_layout(self):
        """Initialize player's spell menu layouts if needed."""
        # Radial dial layout
        if self.player.radial_menu_layout is None:
            self.player.radial_menu_layout = RadialMenuLayout()
            self.player.radial_menu_layout.auto_populate_from_spells(
                self.player.get_known_symbols_ordered()
            )
        self._radial_magic_menu.set_layout(self.player.radial_menu_layout)

        # Node menu layout
        if self.player.node_menu_layout is None:
            self.player.node_menu_layout = NodeMenuLayout()
            self.player.node_menu_layout.auto_populate_from_spells(
                self.player.get_known_symbols_ordered()
            )
        self._node_magic_menu.set_layout(self.player.node_menu_layout)

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
        if self.node_menu_editor.is_open:
            self.node_menu_editor.close(save=False)
        if self.settings_menu.is_open:
            self.settings_menu.close(save=False)
        self._radial_magic_menu.cancel()
        self._node_magic_menu.cancel()

        # Reset persistent area state
        self.area_state_manager = AreaStateManager()
        self.spawner_manager.clear()
        self.cutscene_manager.reset()
        self.mana_pool_manager = ManaPoolManager()

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
        self.renderer.render_ui(self.player, self.game_state, self.mana_pool_manager.current_pool)
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
        # Snapshot health for damage-interrupt detection in menus
        self._snapshot_player_health()

        # Handle ESC as contextual back button / pause
        if self.input.toggle_pause:
            self._handle_escape_key()

        # Handle TAB key - universal back button when busy, menu toggle when free
        if self.input.open_menu:
            if self._is_player_busy():
                # Player is busy - TAB acts as back button
                self._handle_tab_back()
            else:
                # Player is free - TAB opens game menu
                self.game_menu.open()

        # If paused, don't update anything else
        if self.paused:
            return

        # Cutscene playback — blocks all player input, world still animates
        if self.cutscene_manager.active:
            self.cutscene_manager.update(dt)
            self._update_world_only(dt)
            return

        # Focused action — player can move but menus/interaction/casting/sprint blocked
        if self.spell_handler.is_focused:
            self.spell_handler.update_focused_action(dt)
            # Allow movement during focused actions (but not sprint)
            if self.player and self.player.is_alive():
                self.player.is_sprinting = False
                dx, dy = self.input.get_movement_direction()
                if dx != 0 or dy != 0:
                    old_x, old_y = self.player.x, self.player.y
                    if self.player.try_move(dx, dy, self.world, dt=dt):
                        self.world.update_entity_position(self.player, old_x, old_y)
                        self._check_zone_transitions()
            # World updates continue (mana regen intentionally skipped for channel drains)
            self._update_world_and_combat(dt)
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
                        self._check_damage_close_menus()
                        return
            # Advance/confirm on interact
            if self.input.interact or self.input.space_just_pressed:
                was_active = self.dialogue_box.is_active
                self.dialogue_box.handle_input(self.input)
                # Check for dialogue closing
                if was_active and not self.dialogue_box.is_active:
                    self.interaction_handler.on_dialogue_closed()
            self._update_world_only(dt)
            self._check_damage_close_menus()
            return

        # Handle radial menu editor (full-screen)
        if self.radial_menu_editor.is_open:
            result = self.radial_menu_editor.handle_input(self.input, self.current_events)
            if result == "back_to_menu":
                self._sync_radial_menu_layout()
                self.game_menu.open()
            elif result == "switch_to_node":
                self._sync_radial_menu_layout()
                self.player.active_spell_mode = "node"
                self._open_node_menu_editor()
            self._update_world_only(dt)
            if self._check_damage_close_menus():
                return
            return

        # Handle node menu editor (full-screen)
        if self.node_menu_editor.is_open:
            result = self.node_menu_editor.handle_input(self.input, self.current_events)
            if result == "back_to_menu":
                self._sync_node_menu_layout()
                self.game_menu.open()
            elif result == "switch_to_dial":
                self._sync_node_menu_layout()
                self.player.active_spell_mode = "dial"
                self._open_radial_menu_editor()
            self._update_world_only(dt)
            if self._check_damage_close_menus():
                return
            return

        # Handle settings menu (full-screen)
        if self.settings_menu.is_open:
            result = self.settings_menu.handle_input(self.input)
            if result == "save":
                self._apply_settings()
                self.game_menu.open()  # Return to game menu
            elif result == "cancel":
                self.game_menu.open()  # Return to game menu
            self._update_world_only(dt)
            if self._check_damage_close_menus():
                return
            return

        # Handle inventory UI (full-screen overlay)
        if self.inventory_ui.is_open:
            action = self.inventory_ui.handle_input(self.input)
            if action:
                self._handle_inventory_action(action)
            self._update_world_only(dt)
            self._check_damage_close_menus()
            return

        # Handle shop UI (full-screen overlay)
        if self.shop_ui.is_open:
            action = self.shop_ui.handle_input(self.input)
            if action:
                self._handle_shop_action(action)
            self._update_world_only(dt)
            self._check_damage_close_menus()
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
            self._check_damage_close_menus()
            return

        # Handle global input (J for journal)
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
            # Player tried to open menu but can't
            weapon = self.player.hand_occupancy.get_weapon()
            if self.player.is_sprinting:
                self.show_message("Cannot cast spells while sprinting!", 2.0)
            elif weapon and weapon.is_two_handed():
                self.show_message("Cannot cast spells with a two-handed weapon equipped!", 2.0)

        # Player can move even while radial menu is open
        if self.player and self.player.is_alive():
            # Sprint + movement
            dx, dy = self.input.get_movement_direction()
            is_moving = dx != 0 or dy != 0
            speed_override = None

            if self.input.shift_held and is_moving:
                self.player.is_sprinting = True
                speed_override = self.player.move_speed * 1.8
                # Drain stamina at 30/sec (health reserve covers shortfall)
                self.player.stats.use_stamina(30 * dt)
                if not self.player.is_alive():
                    self._trigger_death()
                    return
                # Cancel radial menu if sprint starts while open
                if self.radial_menu.is_open:
                    self.radial_menu.cancel()
                    self.show_message("Sprint cancelled spell menu", 1.0)
            else:
                self.player.is_sprinting = False

            self.player._is_moving = is_moving
            if is_moving:
                old_x, old_y = self.player.x, self.player.y
                if self.player.try_move(dx, dy, self.world, dt=dt, speed_override=speed_override):
                    self.world.update_entity_position(self.player, old_x, old_y)
                    # Check for zone transitions (auto-teleport areas)
                    self._check_zone_transitions()

            # Handle interaction (E key)
            if self.input.interact and not self.radial_menu.is_open:
                self.interaction_handler.handle_interaction()

            # Handle introspection (T key)
            if self.input.introspect and not self.in_combat:
                self.spell_handler.handle_introspection()

        # Update player stamina regen
        if self.player:
            self.player.stats.update(dt)

        # Update environmental mana pools (active + passive areas)
        self.mana_pool_manager.update(dt)

        # Update weapon cooldown
        if self.player:
            weapon = self.player.hand_occupancy.get_weapon()
            if weapon:
                weapon.update(dt)

        # Update weapon swing visual timer
        if self.weapon_swing_timer > 0:
            self.weapon_swing_timer -= dt

        # Update world, combat, camera, timers
        self._update_world_and_combat(dt)

    def _update_world_and_combat(self, dt):
        """Update world systems, enemy AI, projectiles, camera, and timers.
        Used by both the focused action gate and the normal update path."""
        self.world.update(dt)
        self.spawner_manager.update(dt, self.world, self.player)
        self.combat_handler.update_enemy_ai(dt)
        self.combat_handler.check_enemy_damage()
        self.combat_handler.update_projectiles(dt)
        if self.player and not self.player.is_alive():
            self._trigger_death()
            return
        self.camera.update()
        if self.message_timer > 0:
            self.message_timer -= dt
        if self.introspection_timer > 0:
            self.introspection_timer -= dt
        self.last_spell_time += dt
        self.game_state["fps"] = self.clock.get_fps()
        self.game_state["entity_count"] = len(self.world.entities)
        self.game_state["effect_count"] = len(self.world.active_effects)

    def _update_world_only(self, dt):
        """Update world systems without player input (used when menus are open).
        Includes full enemy simulation so the world stays alive."""
        # Update player stamina regen
        if self.player:
            self.player.stats.update(dt)

        # Update environmental mana pools (active + passive areas)
        self.mana_pool_manager.update(dt)

        # Update world (handles burning, entity removal, etc.)
        self.world.update(dt)

        # Update enemy spawners
        self.spawner_manager.update(dt, self.world, self.player)

        # Update enemy AI (needs player reference)
        self.combat_handler.update_enemy_ai(dt)

        # Check contact damage (enemies touching player)
        self.combat_handler.check_enemy_damage()

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

    def _check_damage_close_menus(self):
        """Check if the player took damage since last snapshot.
        If so, force-close all menus/sub-screens and return True.
        Also triggers death screen if the player died."""
        if not self.player:
            return False

        current_health = self.player.stats.health
        if current_health < self._menu_health_snapshot:
            self._force_close_all_menus()
            if not self.player.is_alive():
                self._trigger_death()
            else:
                self.show_message("Interrupted!", 1.5)
            return True

        return False

    def _snapshot_player_health(self):
        """Take a health snapshot for damage-interrupt detection."""
        if self.player:
            self._menu_health_snapshot = self.player.stats.health

    def _force_close_all_menus(self):
        """Immediately close every menu and sub-screen, returning to gameplay."""
        if self.game_menu.is_open:
            self.game_menu.close()
        if self.spell_notebook.is_open:
            self.spell_notebook.close()
        if self.radial_menu_editor.is_open:
            self.radial_menu_editor.close(save=False)
        if self.node_menu_editor.is_open:
            self.node_menu_editor.close(save=False)
        if self.settings_menu.is_open:
            self.settings_menu.close(save=False)
        if self.inventory_ui.is_open:
            self.inventory_ui.close()
        if self.shop_ui.is_open:
            self.shop_ui.close()
        if self.dialogue_box.is_active:
            self.dialogue_box.close()
            self.interaction_handler.on_dialogue_closed()

    def _handle_escape_key(self):
        """Handle ESC key as contextual back button or pause toggle."""
        # Priority 1: If paused, unpause
        if self.paused:
            self.paused = False
            self.message_timer = 0
            return

        # Priority 2: Cancel any focused action (channeling, bow draw, stowed spell)
        if self.spell_handler.is_focused:
            self.spell_handler.cancel_focused_action()
            return

        # Priority 3: Cancel radial magic menu if open
        if self.radial_menu.is_open:
            self.radial_menu.cancel()
            self.show_message("Spell cancelled", 1.0)
            return

        # Priority 4: Close dialogue
        if self.dialogue_box.is_active:
            self.dialogue_box.handle_input(self.input)  # Advance/close dialogue
            return

        # Priority 5: Editors handle ESC internally (returns to menu)
        if self.radial_menu_editor.is_open:
            return  # Editor handles it
        if self.node_menu_editor.is_open:
            return  # Editor handles it

        # Priority 6: Close game menu first (if both menu and journal open)
        if self.game_menu.is_open:
            self.game_menu.close()
            return

        # Priority 7: Inventory UI - handle back (may stay open if in confirmation)
        if self.inventory_ui.is_open:
            if not self.inventory_ui.handle_back():
                # Inventory wants to close
                self.inventory_ui.close()
                self.game_menu.open()
            return

        # Priority 8: Close spell notebook
        if self.spell_notebook.is_open:
            self.spell_notebook.close()
            return

        # Priority 9: Nothing open - toggle pause
        self.paused = True
        self.show_message("PAUSED - Press ESC to resume", 0)

    def _is_player_busy(self):
        """
        Check if the player is busy with any UI or activity.
        When busy, TAB acts as a back button instead of opening the menu.
        """
        # Check all UI states that make the player "busy"
        if self.spell_handler.is_focused:
            return True
        if self.cutscene_manager.active:
            return True
        if self.paused:
            return True
        if self.shop_ui.is_open:
            return True
        if self.dialogue_box.is_active:
            return True
        if self.radial_menu.is_open or self.radial_menu.is_stowed:
            return True
        if self.inventory_ui.is_open:
            return True
        if self.game_menu.is_open:
            return True
        if self.spell_notebook.is_open:
            return True
        if self.settings_menu.is_open:
            return True
        if self.radial_menu_editor.is_open:
            return True
        if self.node_menu_editor.is_open:
            return True
        return False

    def _handle_tab_back(self):
        """
        Handle TAB as a back button when player is busy.
        Routes to the appropriate back/close action for the current UI.
        """
        # Priority 1: If paused, unpause
        if self.paused:
            self.paused = False
            self.message_timer = 0
            return

        # Priority 2: Cancel any focused action (channeling, bow draw, stowed spell)
        if self.spell_handler.is_focused:
            self.spell_handler.cancel_focused_action()
            return

        # Priority 3: Shop UI handles Tab internally (back navigation)
        if self.shop_ui.is_open:
            # Shop UI already handles Tab in its handle_input
            return

        # Priority 4: Cancel radial magic menu if open
        if self.radial_menu.is_open:
            self.radial_menu.cancel()
            self.show_message("Spell cancelled", 1.0)
            return

        # Priority 5: Close/advance dialogue
        if self.dialogue_box.is_active:
            self.dialogue_box.handle_input(self.input)
            if not self.dialogue_box.is_active:
                self.interaction_handler.on_dialogue_closed()
            return

        # Priority 6: Settings menu - cancel and return to game menu
        if self.settings_menu.is_open:
            self.settings_menu.close(save=False)
            self.game_menu.open()
            return

        # Priority 7: Radial menu editor - close without saving and return to game menu
        if self.radial_menu_editor.is_open:
            self.radial_menu_editor.close(save=False)
            self.game_menu.open()
            return

        # Priority 7b: Node menu editor - close without saving and return to game menu
        if self.node_menu_editor.is_open:
            self.node_menu_editor.close(save=False)
            self.game_menu.open()
            return

        # Priority 8: Inventory UI - handle back (may stay open if in confirmation)
        if self.inventory_ui.is_open:
            if not self.inventory_ui.handle_back():
                # Inventory wants to close
                self.inventory_ui.close()
                self.game_menu.open()
            return

        # Priority 9: Spell notebook - close
        if self.spell_notebook.is_open:
            self.spell_notebook.close()
            return

        # Priority 10: Game menu - close
        if self.game_menu.is_open:
            self.game_menu.close()
            return

    def _handle_global_input(self):
        """Handle input that works regardless of game state."""
        # J key opens spell journal directly
        if self.input.was_key_pressed(pygame.K_j):
            if not self.spell_notebook.is_open and not self.game_menu.is_open:
                self.spell_notebook.open()
            return

    def _handle_inventory_action(self, action):
        """Handle an action from the inventory UI."""
        action_type = action.get("type")

        if action_type == "close":
            return

        item = action.get("item")
        is_equipped = action.get("equipped", False)
        backpack_index = action.get("backpack_index", -1)

        if action_type == "stow":
            # Stow equipped physical weapon into backpack
            if not item or not item.is_weapon or not is_equipped:
                return
            if self.player.inventory.has_stowed_weapon():
                self.show_message("Already have a weapon stowed!", 1.5)
                return
            if self.player.inventory.is_full():
                self.show_message("Inventory full!", 1.5)
                return
            pw = self.player.hand_occupancy.drop_physical_weapon()
            if pw:
                self.player.inventory.equipped_weapon = None
                self.player.inventory.add_item(pw.item_instance)
                self.show_message(f"Stowed {pw.name}", 1.5)

        elif action_type == "unstow":
            # Unstow weapon from backpack to hands (must have empty hands)
            if not item or not item.is_weapon:
                return
            if self.player.hand_occupancy.is_holding_weapon():
                self.show_message("Hands are full! Drop or dismiss your weapon first.", 2.0)
                return
            removed = self.player.inventory.remove_item_at(backpack_index)
            if removed:
                pw = PhysicalWeapon(removed, owner=self.player)
                self.player.hand_occupancy.equip_physical_weapon(pw)
                self.player.inventory.equipped_weapon = removed
                self.show_message(f"Equipped {removed.name}", 1.5)

        elif action_type == "equip":
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

        elif action_type == "use":
            if not item or not item.is_consumable:
                return
            if backpack_index < 0:
                return

            # Apply consumable effect
            effect = item.effect_type
            amount = item.effect_amount

            if effect == "heal_health":
                old_hp = self.player.stats.health
                self.player.stats.heal(amount)
                healed = self.player.stats.health - old_hp
                if healed > 0:
                    self.show_message(f"Restored {healed} health", 1.5)
                else:
                    self.show_message("Already at full health", 1.5)
                    return  # Don't consume if no effect
            elif effect == "heal_mana":
                pool = self.mana_pool_manager.current_pool
                if pool is None:
                    self.show_message("No mana pool here", 1.5)
                    return
                old_mp = pool.current
                pool.restore(amount)
                restored = pool.current - old_mp
                if restored > 0:
                    self.show_message(f"Restored {int(restored)} area mana", 1.5)
                else:
                    self.show_message("Area mana already full", 1.5)
                    return  # Don't consume if no effect
            else:
                self.show_message("This item has no effect", 1.5)
                return

            # Consume one from stack
            if item.quantity > 1:
                item.quantity -= 1
            else:
                self.player.inventory.remove_item_at(backpack_index)

    def _handle_shop_action(self, action):
        """Handle an action from the shop UI."""
        from ..items.item_instance import ItemInstance
        from ..items.item_defs import ITEM_DEFS

        action_type = action.get("type")

        if action_type == "close":
            return

        if action_type == "chat":
            # Show merchant's dialogue
            if self.shop_ui.merchant_npc:
                npc = self.shop_ui.merchant_npc
                self.shop_ui.close()
                if npc.dialogue_tree:
                    self.interaction_handler._start_dialogue_tree(npc, npc.dialogue_tree)
                else:
                    self.dialogue_box.show(npc.get_greeting(self.player), npc.get_display_name())
            return

        if action_type == "buy":
            item_id = action.get("item_id")
            quantity = action.get("quantity", 1)
            total_cost = action.get("total_cost", 0)

            if not item_id or quantity <= 0:
                return

            # Check player has enough gold
            if self.player.gold < total_cost:
                self.show_message("Not enough gold!", 1.5)
                return

            # Create item and add to inventory
            item_def = ITEM_DEFS.get(item_id, {})
            new_item = ItemInstance(item_id, quantity)

            if self.player.inventory.add_item(new_item):
                self.player.gold -= total_cost
                self.shop_ui.update_gold(self.player.gold)
                self.show_message(f"Bought {quantity}x {item_def.get('name', item_id)}", 1.5)
            else:
                self.show_message("Inventory full!", 1.5)

        elif action_type == "sell":
            backpack_index = action.get("backpack_index")
            quantity = action.get("quantity", 1)
            total_value = action.get("total_value", 0)

            if backpack_index is None or quantity <= 0:
                return

            # Get the item
            if backpack_index >= len(self.player.inventory.items):
                return
            item = self.player.inventory.items[backpack_index]

            if item.quantity < quantity:
                return

            # Remove items and give gold
            item_name = item.name
            if item.quantity > quantity:
                item.quantity -= quantity
            else:
                self.player.inventory.remove_item_at(backpack_index)

            self.player.gold += total_value
            self.shop_ui.update_gold(self.player.gold)
            self.show_message(f"Sold {quantity}x {item_name} for {total_value}g", 1.5)

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

    def _quick_save(self):
        """Quick save the game."""
        # Snapshot current area state before saving
        self._snapshot_current_area_state()

        save_data = create_save_data(
            self.player, self.world, self.notebook, self.spell_notebook,
            current_area_id=self.current_area_id,
            area_states=self.area_state_manager.serialize(),
            player_gold=getattr(self.player, 'gold', 0),
            mana_pools=self.mana_pool_manager.serialize(),
        )
        success, result = self.save_system.save_game("quicksave", save_data)
        if success:
            self.show_message("Game saved.")
        else:
            self.show_message(f"Save failed: {result}")

    def _quick_load(self):
        """Quick load the game."""
        save_data, error = self.save_system.load_game("quicksave")
        if save_data:
            # Restore player stats, inventory, magic knowledge, notebooks
            current_area_id, area_states_data, mana_pools_data = apply_save_data(
                save_data, self.player, self.world, self.notebook, self.spell_notebook
            )

            # Restore area state manager from saved data
            if area_states_data:
                self.area_state_manager.deserialize(area_states_data)
            else:
                self.area_state_manager = AreaStateManager()

            # Restore environmental mana pools
            if mana_pools_data:
                self.mana_pool_manager.deserialize(mana_pools_data)
            else:
                self.mana_pool_manager = ManaPoolManager()

            # Remember saved player position (load_area will overwrite with entry point)
            saved_x, saved_y = self.player.x, self.player.y
            saved_facing = self.player.facing

            # Reload the saved area with persistent state applied
            if current_area_id:
                self.current_area_id = None  # Clear so load_area doesn't snapshot stale state
                self.load_area(current_area_id)
            else:
                # Fallback: reload current area
                if self.current_area_id:
                    area_id = self.current_area_id
                    self.current_area_id = None
                    self.load_area(area_id)

            # Restore saved player position (not the entry point)
            self.player.x = saved_x
            self.player.y = saved_y
            self.player.facing = saved_facing
            if hasattr(self.player, 'transform'):
                self.player.transform.set_position(saved_x, saved_y)
                self.player.transform.facing = saved_facing

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
            self._open_spell_editor()
        elif action == "settings":
            self.settings_menu.open()
        elif action == "inventory":
            if self.player:
                self.inventory_ui.open(self.player.inventory)

    def _open_spell_editor(self):
        """Open the appropriate spell customization editor based on active mode."""
        if self.player.active_spell_mode == "node":
            self._open_node_menu_editor()
        else:
            self._open_radial_menu_editor()

    def _open_radial_menu_editor(self):
        """Open the radial menu customization editor."""
        if not hasattr(self.player, 'radial_menu_layout') or self.player.radial_menu_layout is None:
            self.player.radial_menu_layout = RadialMenuLayout()
            self.player.radial_menu_layout.auto_populate_from_spells(
                self.player.get_known_symbols_ordered()
            )
        self.radial_menu_editor.open(
            self.player.radial_menu_layout,
            self.player.get_known_symbols_ordered()
        )

    def _open_node_menu_editor(self):
        """Open the node menu customization editor."""
        if self.player.node_menu_layout is None:
            self.player.node_menu_layout = NodeMenuLayout()
            self.player.node_menu_layout.auto_populate_from_spells(
                self.player.get_known_symbols_ordered()
            )
        self.node_menu_editor.open(
            self.player.node_menu_layout,
            self.player.get_known_symbols_ordered()
        )

    def _sync_radial_menu_layout(self):
        """Sync the edited layout to the radial menu and player."""
        if self.radial_menu_editor.layout:
            self.player.radial_menu_layout = self.radial_menu_editor.layout
            self._radial_magic_menu.set_layout(self.player.radial_menu_layout)

    def _sync_node_menu_layout(self):
        """Sync the edited node layout to the node menu and player."""
        if self.node_menu_editor.layout:
            self.player.node_menu_layout = self.node_menu_editor.layout
            self._node_magic_menu.set_layout(self.player.node_menu_layout)

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
        self.renderer.render_ui(self.player, self.game_state, self.mana_pool_manager.current_pool)

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
        if self.spell_handler.bow_drawing:
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

        # Render shop UI
        if self.shop_ui.is_open:
            self.shop_ui.render(self.screen)

        # Render game menu (on top of everything)
        if self.game_menu.is_open:
            self.game_menu.render(self.screen)

        # Render pause overlay
        if self.paused:
            self._render_pause_overlay()

        # Render radial menu editor (full-screen overlay)
        if self.radial_menu_editor.is_open:
            self.radial_menu_editor.render(self.screen)

        # Render node menu editor (full-screen overlay)
        if self.node_menu_editor.is_open:
            self.node_menu_editor.render(self.screen)

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
        """Render HUD showing currently held weapon, positioned above the stats bar."""
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

        # Controls hint
        if weapon.is_ranged():
            hint = "R: Dismiss | Hold Click: Draw"
        else:
            hint = "R: Dismiss | Click: Attack"

        text_surf = font.render(weapon_text, True, weapon.color)
        hint_surf = font.render(hint, True, (150, 150, 150))

        # Position above the stats bar, left-aligned with health
        padding = 5
        box_w = max(text_surf.get_width(), hint_surf.get_width()) + padding * 2
        box_h = text_surf.get_height() + hint_surf.get_height() + 2 + padding * 2
        x = 10
        y = self.renderer.stats_bar_top_y - box_h - 4

        # Background
        bg_rect = pygame.Rect(x - padding, y, box_w, box_h)
        pygame.draw.rect(self.screen, (30, 30, 40), bg_rect, border_radius=3)
        pygame.draw.rect(self.screen, weapon.color, bg_rect, 1, border_radius=3)

        self.screen.blit(text_surf, (x, y + padding))
        self.screen.blit(hint_surf, (x, y + padding + text_surf.get_height() + 2))

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
        if not self.spell_handler.bow_drawing:
            return

        draw_pct = min(1.0, self.spell_handler.bow_draw_timer / self.spell_handler.bow_draw_time_required)

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
