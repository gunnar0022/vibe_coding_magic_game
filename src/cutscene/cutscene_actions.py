"""
Cutscene action classes — each action has start(), update(dt)->bool, cleanup().
update() returns True when the action is finished.
"""
import math
from ..core.settings import Settings


class CutsceneAction:
    """Base class for cutscene actions."""

    def start(self, ctx):
        pass

    def update(self, ctx, dt):
        """Tick the action. Return True when done."""
        return True

    def cleanup(self, ctx):
        pass


class WaitAction(CutsceneAction):
    """Pause for a fixed duration."""

    def __init__(self, duration):
        self.duration = duration
        self._elapsed = 0.0

    def start(self, ctx):
        self._elapsed = 0.0

    def update(self, ctx, dt):
        self._elapsed += dt
        return self._elapsed >= self.duration


class PanCameraTo(CutsceneAction):
    """Smoothly pan the camera to a world grid position."""

    def __init__(self, grid_x, grid_y, speed=4.0):
        self.target_gx = grid_x
        self.target_gy = grid_y
        self.speed = speed  # tiles per second

    def start(self, ctx):
        # Detach camera from player so we can drive it manually
        ctx["game"].camera.target = None

    def update(self, ctx, dt):
        camera = ctx["game"].camera
        # Target pixel offset (same formula Camera.update uses to center on a tile)
        target_px = self.target_gx * Settings.TILE_SIZE - Settings.SCREEN_WIDTH // 2 + Settings.TILE_SIZE // 2
        target_py = self.target_gy * Settings.TILE_SIZE - Settings.SCREEN_HEIGHT // 2 + Settings.TILE_SIZE // 2

        dx = target_px - camera.offset_x
        dy = target_py - camera.offset_y
        dist = math.sqrt(dx * dx + dy * dy)

        step = self.speed * Settings.TILE_SIZE * dt  # pixels per frame

        if dist <= max(step, 2.0):
            camera.offset_x = target_px
            camera.offset_y = target_py
            return True

        camera.offset_x += (dx / dist) * step
        camera.offset_y += (dy / dist) * step
        return False


class SpawnEntity(CutsceneAction):
    """Create an entity via a factory and store it in ctx['entities'][key]."""

    def __init__(self, key, entity_factory):
        self.key = key
        self.entity_factory = entity_factory

    def start(self, ctx):
        entity = self.entity_factory()
        ctx["entities"][self.key] = entity
        ctx["game"].world.add_entity(entity)

    def update(self, ctx, dt):
        return True


class MoveEntityTo(CutsceneAction):
    """Move a cutscene entity toward a target grid position."""

    def __init__(self, key, target_x, target_y, speed=1.5):
        self.key = key
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        self.speed = speed

    def update(self, ctx, dt):
        entity = ctx["entities"].get(self.key)
        if not entity:
            return True

        dx = self.target_x - entity.x
        dy = self.target_y - entity.y
        dist = math.sqrt(dx * dx + dy * dy)

        step = self.speed * dt
        if dist <= max(step, 0.05):
            entity.x = self.target_x
            entity.y = self.target_y
            return True

        entity.x += (dx / dist) * step
        entity.y += (dy / dist) * step

        # Update facing
        if abs(dx) > abs(dy):
            entity.facing = "right" if dx > 0 else "left"
        else:
            entity.facing = "down" if dy > 0 else "up"

        return False


class EntityAttack(CutsceneAction):
    """
    Make attacker hit target using its first attack_def.
    Bypasses AI — directly calls take_hit with computed knockback.
    """

    def __init__(self, attacker_key, target_key):
        self.attacker_key = attacker_key
        self.target_key = target_key

    def start(self, ctx):
        attacker = ctx["entities"].get(self.attacker_key)
        target = ctx["entities"].get(self.target_key)
        if not attacker or not target:
            return

        # Use first attack slot definition
        if not attacker.attack_slots:
            return
        attack_def = attacker.attack_slots[0].attack_def

        damage = attack_def.get("damage", 10)
        damage_type = attack_def.get("damage_type", "physical")
        kb_mult = attack_def.get("knockback_multiplier", 1.0)
        status_effects = attack_def.get("status_effects", [])

        # Compute knockback direction from attacker to target
        dx = target.x - attacker.x
        dy = target.y - attacker.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            kb_dir = (dx / dist, dy / dist)
        else:
            kb_dir = (1.0, 0.0)

        target.take_hit(
            damage=damage,
            damage_type=damage_type,
            knockback_dir=kb_dir,
            knockback_multiplier=kb_mult,
            status_effects=status_effects,
            attacker=attacker,
        )

    def update(self, ctx, dt):
        return True


class WaitUntilDead(CutsceneAction):
    """Wait until the named entity's HP <= 0."""

    def __init__(self, key):
        self.key = key

    def update(self, ctx, dt):
        entity = ctx["entities"].get(self.key)
        if not entity:
            return True
        return not entity.is_alive()


class ShowDialogue(CutsceneAction):
    """Show a dialogue box; finishes when the player dismisses it.

    During cutscene playback the normal dialogue input handling in
    game.update() is skipped (the cutscene early-returns), so this
    action drives dialogue update and input itself.
    """

    def __init__(self, text, speaker=None):
        self.text = text
        self.speaker = speaker
        self._shown = False

    def start(self, ctx):
        ctx["game"].dialogue_box.show(self.text, self.speaker)
        self._shown = True

    def update(self, ctx, dt):
        if not self._shown:
            return True

        game = ctx["game"]
        dialogue = game.dialogue_box

        if not dialogue.is_active:
            return True

        # Tick the dialogue box animation / typewriter
        dialogue.update(dt)

        # Check for advance/dismiss input (E or Space)
        if game.input.interact or game.input.space_just_pressed:
            dialogue.handle_input(game.input)

        return not dialogue.is_active


class ReturnCameraToPlayer(CutsceneAction):
    """Pan camera back to the player, then re-attach."""

    def __init__(self, speed=4.0):
        self.speed = speed

    def update(self, ctx, dt):
        game = ctx["game"]
        player = game.player
        if not player:
            return True

        camera = game.camera
        target_px = player.x * Settings.TILE_SIZE - Settings.SCREEN_WIDTH // 2 + Settings.TILE_SIZE // 2
        target_py = player.y * Settings.TILE_SIZE - Settings.SCREEN_HEIGHT // 2 + Settings.TILE_SIZE // 2

        dx = target_px - camera.offset_x
        dy = target_py - camera.offset_y
        dist = math.sqrt(dx * dx + dy * dy)

        step = self.speed * Settings.TILE_SIZE * dt

        if dist <= max(step, 2.0):
            camera.offset_x = target_px
            camera.offset_y = target_py
            # Re-attach camera to player
            camera.set_target(player)
            return True

        camera.offset_x += (dx / dist) * step
        camera.offset_y += (dy / dist) * step
        return False


class RemoveEntity(CutsceneAction):
    """Remove a cutscene entity from the world."""

    def __init__(self, key):
        self.key = key

    def start(self, ctx):
        entity = ctx["entities"].get(self.key)
        if entity:
            entity.active = False

    def update(self, ctx, dt):
        return True


class SetEventFlag(CutsceneAction):
    """Set a flag on an area state so the cutscene won't replay."""

    def __init__(self, area_id, flag_name):
        self.area_id = area_id
        self.flag_name = flag_name

    def start(self, ctx):
        area_state = ctx["game"].area_state_manager.get_state(self.area_id)
        area_state.set_flag(self.flag_name)

    def update(self, ctx, dt):
        return True
