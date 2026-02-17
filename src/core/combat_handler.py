"""
Combat handling module - manages weapon attacks, projectiles, and enemy AI.
Extracted from game.py for modularity.
"""
import math
from ..entities import Projectile, EffectInstance, WorldObject, PhysicalWeapon, GroundItem


class CombatHandler:
    """Handles all combat-related functionality."""

    def __init__(self, game):
        """
        Initialize with reference to game instance.

        Args:
            game: The main Game instance
        """
        self.game = game

    @property
    def player(self):
        return self.game.player

    @property
    def world(self):
        return self.game.world

    @property
    def input(self):
        return self.game.input

    @property
    def camera(self):
        return self.game.camera

    def handle_weapon_input(self):
        """Handle weapon input, branching between melee and ranged."""
        if not self.player:
            return

        weapon = self.player.hand_occupancy.get_weapon()
        if not weapon:
            return

        if weapon.is_ranged():
            if not self.player.is_sprinting:
                self._handle_ranged_input(weapon)
        elif self.input.mouse_clicked:
            self._handle_melee_attack(weapon)

    def _handle_ranged_input(self, weapon):
        """
        Handle ranged weapon input - click to start drawing.
        Draw-in-progress logic is handled by SpellHandler's focused action system.
        """
        if self.input.mouse_clicked and not self.game.spell_handler.bow_drawing:
            if not weapon.can_swing():
                return
            self.game.spell_handler.start_bow_draw(weapon)

    def _fire_ranged_weapon(self, weapon):
        """Fire a projectile from a ranged weapon."""
        # Deduct stamina (health reserve covers shortfall)
        self.player.stats.use_stamina(weapon.get_stamina_cost())
        # Deduct mana from area pool (shortfall from health with corruption)
        mana_cost = weapon.get_mana_per_shot()
        if mana_cost > 0:
            self.game.mana_pool_manager.cast_from_pool(mana_cost, self.player.stats)
        if not self.player.is_alive():
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
        self.game.active_projectiles.append(projectile)

        # Update player facing
        facing = self.game._get_facing_from_mouse(mouse_x, mouse_y)
        self.player.facing = facing
        self.player.transform.facing = facing

    def _handle_melee_attack(self, weapon):
        """Handle melee weapon attack (left-click when holding a melee weapon)."""
        # Check if weapon can swing (cooldown ready)
        if not weapon.can_swing():
            return

        # Start the swing
        weapon.start_swing()

        # Deduct stamina for melee swing (health reserve covers shortfall)
        self.player.stats.use_stamina(weapon.get_stamina_cost())
        if not self.player.is_alive():
            return

        # Get attack direction from mouse position
        mouse_x, mouse_y = self.input.get_mouse_position()
        attack_facing = self.game._get_facing_from_mouse(mouse_x, mouse_y)

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

        # Enchantment is always active for enchanted weapons (health reserve covers cost)
        enchant_active = weapon.is_enchanted()

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

        # Deduct enchantment mana from area pool if any hits landed
        if enchant_active and total_hits > 0:
            mana_per_hit = weapon.get_mana_per_hit()
            if mana_per_hit > 0:
                self.game.mana_pool_manager.cast_from_pool(mana_per_hit, self.player.stats)
            # Cleanse caster if weapon has that property
            if weapon.cleanses_caster():
                self._cleanse_player_negative_status()

        # Spawn logs for destroyed trees
        for tree in destroyed_trees:
            if tree.spawn_on_destroy and tree.destruction_cause == "slashing":
                self._spawn_log_at(tree.x, tree.y)

        # Visual feedback
        if total_hits > 0:
            self.game.show_message(f"{weapon.name} strikes!", 0.5)
        else:
            self.game.show_message(f"{weapon.name} swings!", 0.3)

        # Store swing info for rendering (all rects for arc visual)
        self.game.weapon_swing_effect = {
            "rects": hitbox_rects,
            "timer": 0.15
        }
        self.game.weapon_swing_timer = 0.15

    def _apply_enchantment_on_hit(self, weapon, entity):
        """Apply enchanted weapon effects to a hit entity."""
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

    def _spawn_log_at(self, x, y):
        """Spawn a log at the given position."""
        log = WorldObject(x, y, object_type="log")
        self.world.add_entity(log)
        print(f"[World] Spawned log at ({x}, {y})")

    def handle_weapon_dismiss(self):
        """Handle dismissing/dropping the currently held weapon (R key)."""
        if not self.player:
            return

        # Physical weapon: drop on ground (not vanish)
        if self.player.hand_occupancy.physical_weapon is not None:
            pw = self.player.hand_occupancy.drop_physical_weapon()
            if pw:
                self._spawn_ground_item(pw.item_instance, self.player.x, self.player.y)
                self.player.inventory.equipped_weapon = None
                self.game.show_message(f"Dropped {pw.name}", 1.5)
            return

        # Summoned weapon: dismiss (vanish)
        if self.player.hand_occupancy.summoned_weapon is not None:
            weapon = self.player.hand_occupancy.dismiss_weapon()
            if weapon:
                self.game.show_message(f"Dismissed {weapon.name}", 1.5)

    def _spawn_ground_item(self, item_instance, x, y):
        """Create a GroundItem entity at the given position and add to world."""
        gi = GroundItem(x, y, item_instance)
        self.world.add_entity(gi)

    def pickup_ground_item(self, ground_entity):
        """Pick up a ground item entity."""
        item_instance = ground_entity.item_instance

        # Weapons require empty hands to pick up
        if item_instance.is_weapon:
            if self.player.hand_occupancy.is_holding_weapon():
                self.game.show_message("Hands are full! Stow or drop your weapon first.", 2.0)
                return
            pw = PhysicalWeapon(item_instance, owner=self.player)
            self.player.hand_occupancy.equip_physical_weapon(pw)
            self.player.inventory.equipped_weapon = item_instance
            self.world.remove_entity(ground_entity)
            self._mark_ground_item_picked_up(ground_entity)
            self.game.show_message(f"Equipped {item_instance.name}", 2.0)
        else:
            # Add non-weapon to backpack
            if self.player.inventory.add_item(item_instance):
                self.world.remove_entity(ground_entity)
                self._mark_ground_item_picked_up(ground_entity)
                self.game.show_message(f"Picked up {item_instance.name}", 1.5)
            else:
                self.game.show_message("Inventory full!", 1.5)

    def _mark_ground_item_picked_up(self, ground_entity):
        """Update area state when a ground item is picked up."""
        if not self.game.current_area_id:
            return
        # Only map-placed items need to be marked as removed
        map_obj_id = getattr(ground_entity, 'map_object_id', None)
        if map_obj_id:
            area_state = self.game.area_state_manager.get_state(self.game.current_area_id)
            area_state.mark_item_removed(map_obj_id)

    def update_enemy_ai(self, dt):
        """Update AI for all enemies and process pending enemy actions."""
        enemies = self.world.get_entities_by_tag("enemy")
        for enemy in enemies:
            if not enemy.active or not enemy.is_alive():
                continue
            if hasattr(enemy, 'update_ai'):
                enemy.update_ai(dt, self.world, self.player, self.game.mana_pool_manager)

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
        self.game.active_projectiles.append(projectile)

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

    def check_enemy_damage(self):
        """Check for contact damage between enemies and player."""
        from ..combat import check_contact_damage
        hits = check_contact_damage(self.world)
        for enemy, attack_def in hits:
            name = attack_def.get("name", "Attack")
            damage = attack_def.get("damage", 0)
            self.game.show_message(f"{name}! (-{damage})", 1.0)

    def update_projectiles(self, dt):
        """Update all active projectiles - movement, collision, cleanup."""
        to_remove = []

        for projectile in self.game.active_projectiles:
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
            if projectile in self.game.active_projectiles:
                self.game.active_projectiles.remove(projectile)
            if projectile.id in self.world.entities:
                self.world.remove_entity(projectile)

        # Update arrow impact effects
        remaining = []
        for effect in self.game.arrow_impact_effects:
            effect["timer"] -= dt
            if effect["timer"] > 0:
                remaining.append(effect)
        self.game.arrow_impact_effects = remaining

    def _handle_enemy_projectile_hit(self, projectile, player):
        """Handle an enemy projectile hitting the player."""
        dx = player.x - projectile.x
        dy = player.y - projectile.y
        length = math.sqrt(dx * dx + dy * dy)
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
        self.game.show_message(f"Hit by projectile! (-{projectile.damage})", 1.0)

    def _spawn_arrow_impact(self, x, y):
        """Spawn a small visual impact effect at the arrow's hit location."""
        self.game.arrow_impact_effects.append({
            "x": x,
            "y": y,
            "timer": self.game.arrow_impact_duration,
        })

    def _is_elemental_projectile(self, projectile):
        """Check if a projectile carries elemental effects (spell or enchanted arrow)."""
        return (getattr(projectile, 'spell_descriptor', None) is not None
                or getattr(projectile, 'enchantment', None) is not None)

    def _handle_projectile_impact(self, projectile, hit_entity=None):
        """Spawn an elemental AoE at the projectile's impact point."""
        spell_desc = getattr(projectile, 'spell_descriptor', None)
        enchant = getattr(projectile, 'enchantment', None)

        if spell_desc:
            # Spell projectile - use full spell descriptor
            impact_desc = spell_desc
            aoe_size = spell_desc.get("impact_radius", 0.5)
        elif enchant:
            # Enchanted arrow - construct descriptor from enchantment
            aoe_size = 0.5
            impact_desc = {
                "element": enchant,
                "damage": {"amount": projectile.damage, "type": projectile.damage_type},
                "status_effects": getattr(projectile, 'arrow_status_effects', []),
            }
        else:
            return

        # Calculate impact point
        if hit_entity is not None:
            if getattr(hit_entity, 'uses_sub_grid', False):
                ex, ey = hit_entity.x + 0.5, hit_entity.y + 0.5
            else:
                ex = int(hit_entity.x) + 0.5
                ey = int(hit_entity.y) + 0.5
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
