"""
Channeled spell system - handles sustained spells like the fire flamethrower.
"""
import math
from ..entities import EffectInstance


class ChanneledSpell:
    """
    A channeled spell that continuously repositions an effect area
    toward the mouse over a fixed duration.

    While active, the player cannot move, open menus, or cast other spells.
    The world continues to animate (enemies move, effects tick, etc.).

    The channel ends early if:
    - The player takes damage (health drops)
    - The player right-clicks to cancel
    - The player runs out of mana
    - A zone transition occurs (caller invokes cancel())
    """

    def __init__(self, game, spell_descriptor, channel_config):
        self.game = game
        self.spell_descriptor = spell_descriptor
        self.channel_config = channel_config

        # Timing
        self.duration = channel_config["duration"]
        self.tick_interval = channel_config["tick_interval"]
        self.rotation_speed = channel_config["rotation_speed"]
        self.range = channel_config["range"]

        self.elapsed = 0.0
        self.tick_timer = 0.0

        # Rotation state - start aiming toward the mouse
        self.current_angle = self._get_target_angle()

        # Active effect in the world (only one at a time)
        self.active_effect = None

        # Damage interrupt: snapshot health so we can detect hits
        self.last_health = self.game.player.stats.health

        # Mana drain: compute per-tick cost from total mana_cost spread
        # across all ticks in the channel duration
        total_cost = spell_descriptor.get("mana_cost", 10)
        total_ticks = max(1, int(self.duration / self.tick_interval))
        self.mana_per_tick = total_cost / total_ticks

        # Fire the first tick immediately (also deducts first mana chunk)
        self._fire_tick()

    def _get_target_angle(self):
        """Compute angle from player center to current mouse position."""
        mouse_x, mouse_y = self.game.input.get_mouse_position()

        player_screen_x = (self.game.player.x + 0.5) * 32 - self.game.camera.offset_x
        player_screen_y = (self.game.player.y + 0.5) * 32 - self.game.camera.offset_y

        dx = mouse_x - player_screen_x
        dy = mouse_y - player_screen_y

        if dx == 0 and dy == 0:
            return 0.0

        return math.atan2(dy, dx)

    def _normalize_angle(self, angle):
        """Normalize angle to [-pi, pi]."""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle

    def update(self, dt):
        """
        Update the channeled spell. Returns True when finished.
        """
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.cleanup()
            return True

        # Check for damage interrupt: health dropped since last frame
        current_health = self.game.player.stats.health
        if current_health < self.last_health:
            self.game.show_message("Channel interrupted!", 1.5)
            self.cleanup()
            return True
        self.last_health = current_health

        # Rotate current_angle toward target
        target_angle = self._get_target_angle()
        diff = self._normalize_angle(target_angle - self.current_angle)

        # If the angular difference is near +/-pi, force counter-clockwise
        # (decreasing angle in screen coords)
        if abs(abs(diff) - math.pi) < 0.15:
            direction = -1  # CCW on screen = decreasing angle
        else:
            direction = 1 if diff > 0 else -1

        max_step = self.rotation_speed * dt
        if abs(diff) <= max_step:
            self.current_angle = target_angle
        else:
            self.current_angle += direction * max_step

        # Normalize to keep in [-pi, pi]
        self.current_angle = self._normalize_angle(self.current_angle)

        # Check if it's time for a new tick
        self.tick_timer += dt
        if self.tick_timer >= self.tick_interval:
            self.tick_timer -= self.tick_interval
            if not self._fire_tick():
                # Mana ran out
                return True

        return False

    def cancel(self):
        """Cancel the channel early (right-click, zone transition, etc.)."""
        self.game.show_message("Channel cancelled", 1.0)
        self.cleanup()

    def _fire_tick(self):
        """
        Remove old effect, place new one at current angle, apply damage,
        and deduct mana for this tick.

        Returns False if mana is insufficient (channel should end).
        """
        # Deduct mana for this tick (health reserve covers shortfall)
        self.game.player.stats.use_mana(self.mana_per_tick)
        if not self.game.player.is_alive():
            self.cleanup()
            return False

        # Remove old effect
        if self.active_effect is not None:
            self._remove_effect(self.active_effect)
            self.active_effect = None

        # Calculate target position (center of aim point)
        player_cx = self.game.player.x + 0.5
        player_cy = self.game.player.y + 0.5
        aim_x = player_cx + math.cos(self.current_angle) * self.range
        aim_y = player_cy + math.sin(self.current_angle) * self.range

        # Offset by -0.5 so the effect tile is centered on the aim point
        # (EffectInstance x,y is the top-left corner of the tile)
        effect_x = aim_x - 0.5
        effect_y = aim_y - 0.5

        # Create new effect
        effect = EffectInstance(
            effect_x, effect_y,
            self.spell_descriptor,
            duration=self.tick_interval + 0.1,  # Slightly longer than tick to avoid gaps
            radius=self.spell_descriptor.get("radius", 0),
        )
        effect.caster = self.game.player

        self.game.world.spawn_effect(effect)
        self.active_effect = effect

        # Apply immediate damage using the effect's sub-grid hitbox
        hit_rect = effect.get_affected_rect()
        entities = self.game.world.get_entities_in_rect(*hit_rect)
        for entity in entities:
            if entity == self.game.player:
                continue
            if hasattr(entity, "on_magic_applied"):
                entity.on_magic_applied(self.spell_descriptor, {"cast_direction": (0, 0)})

        return True

    def _remove_effect(self, effect):
        """Remove an effect from the world."""
        if effect in self.game.world.active_effects:
            self.game.world.active_effects.remove(effect)
        self.game.world.remove_entity(effect)

    def cleanup(self):
        """Remove any remaining active effect."""
        if self.active_effect is not None:
            self._remove_effect(self.active_effect)
            self.active_effect = None
