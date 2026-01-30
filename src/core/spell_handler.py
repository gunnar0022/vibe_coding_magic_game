"""
Spell handling module - manages all spell casting and magic effects.
Extracted from game.py for modularity.
"""
from ..entities import EffectInstance, SummonedWeapon, WorldObject
from ..magic import MagicSystem
from .channeled_spell import ChanneledSpell


class SpellHandler:
    """Handles all spell casting and magic-related functionality."""

    def __init__(self, game):
        """
        Initialize with reference to game instance.

        Args:
            game: The main Game instance
        """
        self.game = game
        self.active_channel = None

        # Bow draw state (moved from game.py for unified focused action)
        self.bow_drawing = False
        self.bow_draw_timer = 0.0
        self.bow_draw_time_required = 1.0
        self.bow_weapon = None

        # Shared damage interrupt tracking for all focused actions
        self._focus_last_health = None

    @property
    def player(self):
        return self.game.player

    @property
    def world(self):
        return self.game.world

    @property
    def radial_menu(self):
        return self.game.radial_menu

    @property
    def input(self):
        return self.game.input

    @property
    def is_channeling(self):
        return self.active_channel is not None

    @property
    def is_focused(self):
        """True when any focused action is active (channeling, bow draw, or spell stowed)."""
        return self.is_channeling or self.bow_drawing or self.radial_menu.is_stowed

    def start_bow_draw(self, weapon):
        """Begin a bow draw focused action."""
        self.bow_drawing = True
        self.bow_draw_timer = 0.0
        self.bow_draw_time_required = weapon.get_draw_time()
        self.bow_weapon = weapon
        self._focus_last_health = self.player.stats.health

    def update_focused_action(self, dt):
        """Unified update for all focused actions (channeling, bow draw, spell stowed).
        Handles right-click cancel, damage interrupt, and delegates to sub-handler."""
        # Right-click cancels any focused action
        if self.input.mouse_right_clicked:
            self.cancel_focused_action()
            return

        # Damage interrupt: health dropped since focused action started
        if self._focus_last_health is not None:
            current_health = self.player.stats.health
            if current_health < self._focus_last_health:
                self._interrupt_focused_action()
                return
            self._focus_last_health = current_health

        # Delegate to specific sub-handler
        if self.is_channeling:
            finished = self.active_channel.update(dt)
            if finished:
                self.active_channel = None
                self._focus_last_health = None
        elif self.bow_drawing:
            self._update_bow_draw(dt)
        elif self.radial_menu.is_stowed:
            self._update_stowed_spell()

    def _update_bow_draw(self, dt):
        """Update bow draw sub-handler within focused action."""
        if self.input.mouse_held:
            self.bow_draw_timer += dt
            # Update player facing toward mouse while drawing
            mouse_x, mouse_y = self.input.get_mouse_position()
            facing = self.game._get_facing_from_mouse(mouse_x, mouse_y)
            self.player.facing = facing
            self.player.transform.facing = facing

        if self.input.mouse_released:
            if self.bow_draw_timer >= self.bow_draw_time_required:
                self.game.combat_handler._fire_ranged_weapon(self.bow_weapon)
            else:
                self.game.show_message("Draw cancelled - hold longer!", 1.0)
            self.bow_drawing = False
            self.bow_draw_timer = 0.0
            self.bow_weapon = None
            self._focus_last_health = None

    def _update_stowed_spell(self):
        """Update stowed spell sub-handler within focused action."""
        if self.input.space_just_released:
            mouse_x, mouse_y = self.input.get_mouse_position()
            self.cast_spell(mouse_x, mouse_y)
            self._focus_last_health = None

    def cancel_focused_action(self):
        """Cancel whichever focused action is active (right-click, ESC, TAB, zone transition)."""
        if self.is_channeling:
            self.active_channel.cancel()
            self.active_channel = None
        elif self.bow_drawing:
            self.game.show_message("Draw cancelled", 1.0)
            self.bow_drawing = False
            self.bow_draw_timer = 0.0
            self.bow_weapon = None
        elif self.radial_menu.is_stowed:
            self.radial_menu.cancel()
            self.game.show_message("Spell cancelled (mana lost)", 1.0)
        self._focus_last_health = None

    def _interrupt_focused_action(self):
        """Interrupt focused action due to damage."""
        if self.is_channeling:
            self.game.show_message("Channel interrupted!", 1.5)
            self.active_channel.cleanup()
            self.active_channel = None
        elif self.bow_drawing:
            self.game.show_message("Draw interrupted!", 1.5)
            self.bow_drawing = False
            self.bow_draw_timer = 0.0
            self.bow_weapon = None
        elif self.radial_menu.is_stowed:
            self.radial_menu.cancel()
            self.game.show_message("Spell interrupted! (mana lost)", 1.5)
        self._focus_last_health = None

    def handle_radial_menu(self):
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
                        self.game.show_message(f"Selected: {', '.join(symbols)}", 1.0)
                elif result == "stow":
                    # Mana is deducted when menu is stowed
                    self._deduct_mana_for_spell()
                    # Initialize damage interrupt tracking for stowed spell
                    self._focus_last_health = self.player.stats.health

            # Right click - cancel
            if self.input.mouse_right_clicked:
                self.radial_menu.cancel()
                self.game.show_message("Spell cancelled", 1.0)

        # SPACE released - launch spell if menu is still open
        if self.input.space_just_released:
            if self.radial_menu.is_open:
                # Still open means they released without clicking off
                # Stow and cast immediately if they have selection
                if self.radial_menu.has_selection():
                    self._deduct_mana_for_spell()
                    self.radial_menu.stow()
                    self.cast_spell(mouse_x, mouse_y)
                else:
                    self.radial_menu.close()
            # Note: stowed spell space-release is handled by update_focused_action()

    def _deduct_mana_for_spell(self):
        """Deduct mana cost when spell is stowed (locked in).
        Channeled spells skip upfront deduction — they drain per-tick instead."""
        symbols = self.radial_menu.get_selected_symbols()
        if not symbols:
            return False

        spell_descriptor = MagicSystem.resolve_spell(symbols)
        if spell_descriptor is None:
            return False

        # Channeled spells drain mana gradually — health reserve means
        # they can always start (player may die during channeling).
        if spell_descriptor.get("channel"):
            return True

        # Normal spells: use_mana always succeeds (health reserve covers shortfall)
        mana_cost = spell_descriptor.get("mana_cost", 10)
        self.player.stats.use_mana(mana_cost)
        if not self.player.is_alive():
            self.radial_menu.cancel()
            return False

        return True

    def cast_spell(self, mouse_x, mouse_y):
        """Cast the prepared spell in direction of mouse."""
        symbols = self.radial_menu.get_selected_symbols()
        if not symbols:
            self.radial_menu.close()
            return

        # Get spell descriptor
        spell_descriptor = MagicSystem.resolve_spell(symbols)
        if spell_descriptor is None:
            self.game.show_message("Invalid combination")
            self.radial_menu.close()
            return

        # Snap player to face the cast direction (4-directional)
        cast_facing = self.game._get_facing_from_mouse(mouse_x, mouse_y, eight_dir=False)
        self.player.facing = cast_facing
        self.player.transform.facing = cast_facing

        # Check for channeled spells (e.g. fire flamethrower)
        channel_config = spell_descriptor.get("channel")
        if channel_config:
            self.active_channel = ChanneledSpell(self.game, spell_descriptor, channel_config)
            self._focus_last_health = self.player.stats.health
            spell_name = spell_descriptor.get("name", "Unknown spell")
            self.game.show_message(f"Channeling: {spell_name}", channel_config["duration"])
            self._record_spell_cast(spell_descriptor, [])
            self.radial_menu.close()
            return

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
            self.game.show_message(f"Cast: {spell_name}", 1.5)
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
        self.game.show_message(f"Cast: {spell_name}", 1.5)

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
            self.game._spawn_ground_item(dropped_pw.item_instance, self.player.x, self.player.y)
            self.player.inventory.equipped_weapon = None

        # Show message about the weapon
        hands_text = "two hands" if weapon.is_two_handed() else "one hand"
        self.game.show_message(f"Summoned {weapon.name}! ({hands_text})", 2.0)

        return True

    def _handle_boulder_summon(self, spell_descriptor, target_x, target_y):
        """Handle Summon Boulder spell - spawn a rock WorldObject at target tile."""
        tx = int(target_x)
        ty = int(target_y)

        if self.world.is_blocked(tx, ty):
            self.game.show_message("No space for boulder!", 1.5)
            return []

        rock = WorldObject(tx, ty, object_type="rock")
        self.world.add_entity(rock)
        self.game.show_message("Summoned a boulder!", 1.5)
        return [{"affected": True, "messages": ["A boulder materializes from the earth."]}]

    def _handle_directional_spell(self, spell_descriptor, cast_dir):
        """Handle directional shape spells like Magma Burst (+ or X pattern)."""
        results = []
        shape = spell_descriptor.get("directional_shape", "cross")

        # Define patterns
        if shape == "cross":
            # + pattern: up, down, left, right
            offsets = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        else:
            # X pattern: diagonals
            offsets = [(-1, -1), (1, -1), (-1, 1), (1, 1)]

        # Create effect at each offset position
        for dx, dy in offsets:
            tx = self.player.x + dx
            ty = self.player.y + dy

            effect = EffectInstance(
                tx, ty,
                spell_descriptor,
                duration=spell_descriptor.get("duration", 0.5),
                radius=0
            )
            effect.caster = self.player
            self.world.spawn_effect(effect)

            context = {"cast_direction": cast_dir}
            result = self._apply_effect_with_context(effect, context)
            results.extend(result)

        return results

    def _handle_cone_spell(self, spell_descriptor, cast_dir, target_x, target_y):
        """Handle cone-shaped spells like Shadow Flame (3-tile cone)."""
        results = []

        # Determine cone tiles based on cast direction
        # Cone starts at target and spreads perpendicular to cast direction
        cone_tiles = []

        # Center tile (directly in front)
        cone_tiles.append((target_x, target_y))

        # Side tiles (perpendicular to cast direction)
        if cast_dir[0] != 0:  # Casting horizontally
            cone_tiles.append((target_x, target_y - 1))
            cone_tiles.append((target_x, target_y + 1))
        else:  # Casting vertically
            cone_tiles.append((target_x - 1, target_y))
            cone_tiles.append((target_x + 1, target_y))

        # Create effects at each cone tile
        for tx, ty in cone_tiles:
            effect = EffectInstance(
                tx, ty,
                spell_descriptor,
                duration=spell_descriptor.get("duration", 0.5),
                radius=0
            )
            effect.caster = self.player
            self.world.spawn_effect(effect)

            context = {"cast_direction": cast_dir}
            result = self._apply_effect_with_context(effect, context)
            results.extend(result)

        return results

    def _handle_path_spell(self, spell_descriptor, cast_dir):
        """Handle path effect spells like Blast (3-tile line with push)."""
        results = []
        path_length = spell_descriptor.get("path_length", 3)

        # Create effects along the path
        for i in range(1, path_length + 1):
            tx = self.player.x + cast_dir[0] * i
            ty = self.player.y + cast_dir[1] * i

            effect = EffectInstance(
                tx, ty,
                spell_descriptor,
                duration=spell_descriptor.get("duration", 0.3),
                radius=0
            )
            effect.caster = self.player
            self.world.spawn_effect(effect)

            context = {"cast_direction": cast_dir}
            result = self._apply_effect_with_context(effect, context)
            results.extend(result)

        return results

    def _handle_projectile_spell(self, spell_descriptor, mouse_x, mouse_y):
        """Handle projectile spells that fire toward the mouse position."""
        import math
        from ..entities import Projectile

        # Calculate direction from player to mouse (in world coordinates)
        player_screen_x = (self.player.x + 0.5) * 32 - self.game.camera.offset_x
        player_screen_y = (self.player.y + 0.5) * 32 - self.game.camera.offset_y

        dx = mouse_x - player_screen_x
        dy = mouse_y - player_screen_y

        # Normalize
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            dx /= dist
            dy /= dist

        # Calculate angle for projectile
        angle = math.atan2(dy, dx)

        # Create projectile
        speed = spell_descriptor.get("projectile_speed", 8.0)
        damage = spell_descriptor.get("damage", 10)
        element = spell_descriptor.get("element", "none")

        # Spawn at player center (owner is excluded from collision)
        spawn_x = self.player.x + 0.5
        spawn_y = self.player.y + 0.5

        projectile = Projectile(
            x=spawn_x,
            y=spawn_y,
            angle=angle,
            speed=speed,
            damage=damage,
            owner=self.player
        )

        # Set element and spell descriptor as attributes
        projectile.spell_descriptor = spell_descriptor

        # Set projectile color based on element
        element_colors = {
            "fire": (255, 100, 50),
            "ice": (100, 200, 255),
            "electric": (255, 255, 100),
            "dark": (100, 50, 150),
            "light": (255, 255, 200),
            "physical": (200, 200, 200),
        }
        projectile.color = element_colors.get(element, (200, 200, 200))

        self.world.add_entity(projectile)
        self.game.active_projectiles.append(projectile)

        return [{"affected": True, "messages": [f"Fired {spell_descriptor.get('name', 'projectile')}!"]}]

    def _apply_post_spell_effects(self, spell_descriptor, results, cast_dir):
        """Apply post-spell effects like knockback, cleanse, dispel."""
        # Apply knockback if spell has push_force
        push_force = spell_descriptor.get("push_force", 0)
        if push_force > 0:
            self._apply_knockback(results, push_force, cast_dir)

        # Apply cleanse if spell has cleanse trait
        if spell_descriptor.get("cleanse"):
            self._apply_cleanse(spell_descriptor, results)

        # Apply dispel if spell has dispel trait
        if spell_descriptor.get("dispel"):
            self._apply_dispel(spell_descriptor)

    def _apply_knockback(self, results, push_force, cast_dir):
        """Apply knockback to entities hit by spell."""
        for result in results:
            entity = result.get("entity")
            if entity and hasattr(entity, "apply_knockback"):
                # Calculate knockback velocity
                kb_x = cast_dir[0] * push_force
                kb_y = cast_dir[1] * push_force
                entity.apply_knockback(kb_x, kb_y)

    def _apply_cleanse(self, spell_descriptor, results):
        """Apply cleanse effect to remove negative status effects."""
        cleanse_targets = spell_descriptor.get("cleanse_targets", ["self"])

        if "self" in cleanse_targets:
            # Cleanse player
            if hasattr(self.player, 'status'):
                self.player.status.clear_negative_effects()
                self.game.show_message("Cleansed!", 1.0)

        if "allies" in cleanse_targets:
            # Cleanse nearby allies (NPCs)
            for entity in self.world.get_entities_in_radius(self.player.x, self.player.y, 3):
                if entity.has_tag("npc") and hasattr(entity, 'status'):
                    entity.status.clear_negative_effects()

    def _apply_dispel(self, spell_descriptor):
        """Apply dispel effect to remove magical effects from area."""
        dispel_radius = spell_descriptor.get("dispel_radius", 2)

        # Remove active effects in radius
        effects_to_remove = []
        for effect in self.world.active_effects:
            dx = effect.x - self.player.x
            dy = effect.y - self.player.y
            if dx * dx + dy * dy <= dispel_radius * dispel_radius:
                effects_to_remove.append(effect)

        for effect in effects_to_remove:
            self.world.active_effects.remove(effect)

        if effects_to_remove:
            self.game.show_message(f"Dispelled {len(effects_to_remove)} effect(s)!", 1.0)

    def _apply_effect_with_context(self, effect, context):
        """Apply an effect to entities at its location with context."""
        results = []

        # Get entities at effect location
        entities = self.world.get_entities_at(int(effect.x), int(effect.y))

        for entity in entities:
            if entity == self.player:
                continue  # Don't affect caster by default

            if hasattr(entity, 'on_magic_applied'):
                result = entity.on_magic_applied(effect.spell_descriptor, context)
                if result:
                    result["entity"] = entity
                    results.append(result)

        return results

    def _process_spell_results(self, results, cast_dir):
        """Process spell results - handle push requests, log messages."""
        for result in results:
            # Handle push requests (for rocks, logs, etc.)
            push_req = result.get("push_request")
            if push_req:
                entity = result.get("entity")
                if entity:
                    # Try to push the entity
                    new_x = entity.x + push_req["dx"]
                    new_y = entity.y + push_req["dy"]
                    if not self.world.is_blocked(int(new_x), int(new_y)):
                        entity.x = new_x
                        entity.y = new_y

            # Log messages
            for msg in result.get("messages", []):
                self.game.show_message(msg, 1.5)

    def _record_spell_cast(self, spell_descriptor, results):
        """Record spell cast for introspection system."""
        self.game.last_spell_cast = {
            "descriptor": spell_descriptor,
            "results": results,
            "time": 0
        }
        self.game.last_spell_time = 0

    def handle_introspection(self):
        """Handle introspection key press - show recent spell info."""
        if self.game.last_spell_cast and self.game.last_spell_time < self.game.introspection_decay:
            self.game.introspection_message = self._generate_introspection_text(
                self.game.last_spell_cast
            )
            self.game.introspection_timer = 3.0

    def _generate_introspection_text(self, spell_info):
        """Generate introspection text for a spell."""
        descriptor = spell_info.get("descriptor", {})

        name = descriptor.get("name", "Unknown")
        element = descriptor.get("element", "none")
        damage = descriptor.get("damage", 0)
        traits = descriptor.get("traits", [])

        lines = [f"Last Spell: {name}"]
        lines.append(f"Element: {element.title()}")

        if damage > 0:
            lines.append(f"Damage: {damage}")

        if traits:
            lines.append(f"Traits: {', '.join(traits)}")

        return " | ".join(lines)
