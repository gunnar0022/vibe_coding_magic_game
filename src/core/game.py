"""
Main game class - handles game loop and state management.
Updated with radial magic menu, dialogue box, introspection, and mana regen.
"""
import pygame
from .settings import Settings
from .camera import Camera
from ..world import World, MapLoader
from ..entities import Player, create_npc_from_template, EffectInstance, RuneStone, SummonedWeapon, WorldObject
from ..systems import InputHandler, Renderer, SaveSystem, create_save_data, apply_save_data, get_asset_manager
from ..ui import Notebook, RadialMagicMenu, DialogueBox, GameMenu, SpellNotebook, RadialMenuEditor, RadialMenuLayout, SettingsMenu
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
        self.settings_menu = SettingsMenu(Settings.SCREEN_WIDTH, Settings.SCREEN_HEIGHT)

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
        # Handle ESC as contextual back button / pause
        if self.input.toggle_pause:
            self._handle_escape_key()

        # Handle menu toggle (TAB) - works from anywhere except pause, editor, and settings
        # Menu can coexist with journal (side by side)
        if self.input.open_menu and not self.paused and not self.radial_menu_editor.is_open and not self.settings_menu.is_open:
            if self.game_menu.is_open:
                self.game_menu.close()
            else:
                self.game_menu.open()

        # If paused, don't update anything else
        if self.paused:
            return

        # Handle dialogue box (ESC/interact advances, world updates)
        if self.dialogue_box.is_active:
            self.dialogue_box.update(dt)
            if self.input.interact or self.input.space_just_pressed:
                self.dialogue_box.handle_input()
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

        # Handle weapon dismissal (R key)
        if self.input.dismiss_weapon:
            self._handle_weapon_dismiss()

        # Handle weapon attack (left click when holding weapon and menu not open)
        if self.input.mouse_clicked and not self.radial_menu.is_open:
            self._handle_weapon_attack()

        # Handle radial magic menu (only if player can open it)
        if self.player and self.player.can_open_spell_menu():
            self._handle_radial_menu()
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

        # Update weapon cooldown
        if self.player:
            weapon = self.player.hand_occupancy.get_weapon()
            if weapon:
                weapon.update(dt)

        # Update weapon swing visual timer
        if self.weapon_swing_timer > 0:
            self.weapon_swing_timer -= dt

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
            self.dialogue_box.handle_input()  # Advance/close dialogue
            return

        # Priority 4: Radial menu editor handles ESC internally (returns to menu)
        if self.radial_menu_editor.is_open:
            return  # Editor handles it

        # Priority 5: Close game menu first (if both menu and journal open)
        if self.game_menu.is_open:
            self.game_menu.close()
            return

        # Priority 6: Close spell notebook
        if self.spell_notebook.is_open:
            self.spell_notebook.close()
            return

        # Priority 7: Nothing open - toggle pause
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

        # Check for weapon summon spells (special handling)
        if spell_descriptor.get("category") == "weapon_summon":
            self._handle_weapon_summon(spell_descriptor)
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

    def _handle_weapon_summon(self, spell_descriptor):
        """
        Handle casting a weapon summon spell.
        Creates the weapon and equips it to the player.
        """
        weapon_type = spell_descriptor.get("weapon_type")
        if not weapon_type:
            return False

        # Create the weapon
        weapon = SummonedWeapon(weapon_type, owner=self.player)

        # Equip it (this also dismisses any existing weapon)
        self.player.hand_occupancy.equip_weapon(weapon)

        # Show message about the weapon
        hands_text = "two hands" if weapon.is_two_handed() else "one hand"
        self.show_message(f"Summoned {weapon.name}! ({hands_text})", 2.0)

        return True

    def _handle_weapon_dismiss(self):
        """Handle dismissing the currently held weapon (R key)."""
        if not self.player:
            return

        weapon = self.player.hand_occupancy.get_weapon()
        if weapon:
            self.player.hand_occupancy.dismiss_weapon()
            self.show_message(f"Dismissed {weapon.name}", 1.5)

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

    def _handle_weapon_attack(self):
        """Handle weapon attack (left-click when holding a weapon)."""
        if not self.player:
            return

        weapon = self.player.hand_occupancy.get_weapon()
        if not weapon:
            return

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

            # Handle actors (NPCs, enemies)
            elif hasattr(entity, 'stats'):
                # Apply slashing damage to actors
                damage = weapon.get_swing_damage()
                actual_damage = entity.stats.take_damage(damage, "slashing")
                if actual_damage > 0:
                    total_hits += 1
                    print(f"[Weapon] Hit {entity} for {actual_damage} damage")

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

    def _spawn_log_at(self, x, y):
        """Spawn a log at the given position."""
        log = WorldObject(x, y, object_type="log")
        self.world.add_entity(log)
        print(f"[World] Spawned log at ({x}, {y})")

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

        # Get interaction rect in mouse direction (1x1 tile / 8x8 fine grid)
        interact_rect = self._get_interaction_rect(interact_facing)

        # Get entities in the interaction area
        rx, ry, rw, rh = interact_rect
        entities = self.world.get_entities_in_rect(rx, ry, rw, rh)

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
        else:
            interaction = best_entity.get_component("InteractionComponent")
            if interaction and interaction.can_examine:
                self.dialogue_box.show(interaction.examine_text)

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

        # Render weapon HUD (what weapon is held)
        if self.player and self.player.hand_occupancy.is_holding_weapon():
            self._render_weapon_hud()

        # Render dialogue box
        if self.dialogue_box.is_active:
            self.dialogue_box.render(self.screen)

        # Render spell notebook/journal
        if self.spell_notebook.is_open:
            self.spell_notebook.render(self.screen)

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

        # Instructions
        dismiss_text = font.render("R: Dismiss | Click: Attack", True, (150, 150, 150))
        self.screen.blit(dismiss_text, (x, y + 18))

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
