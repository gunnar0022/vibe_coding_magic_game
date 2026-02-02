"""
Animation manager — loads / caches sprite sheets and bridges them to entities.
"""
import os
import random
import pygame
from .sprite_sheet import SpriteSheet
from .animation_controller import (
    AnimationController,
    SLIME_ANIMATIONS,
    SKELETON_ANIMATIONS,
    GHOST_ANIMATIONS,
    GOLEM_ANIMATIONS,
    NPC_ANIMATIONS,
    NPC_HERBALIST_ANIMATIONS,
    PLAYER_ANIMATIONS,
)

# ---------------------------------------------------------------------------
# Registry: maps enemy_type → sprite config
# ---------------------------------------------------------------------------
_SPRITE_BASE = os.path.join("assets", "sprites", "entities", "enemies")

ANIMATED_ENEMY_REGISTRY = {
    "slime": {
        "variants": ["Slime1", "Slime2", "Slime3"],
        "path_template": os.path.join(_SPRITE_BASE, "slimes", "{variant}_{state}_with_shadow.png"),
        "frame_size": (64, 64),
        "states": ["Attack", "Death", "Hurt", "Idle", "Run", "Walk"],
        "animations": SLIME_ANIMATIONS,
    },
    "skeleton_archer": {
        "variants": ["Skeleton1", "Skeleton2", "Skeleton3"],
        "path_template": os.path.join(_SPRITE_BASE, "skeletons", "{variant}_{state}_with_shadow.png"),
        "frame_size": (64, 64),
        "states": ["Attack", "Death", "Hurt", "Idle", "Run", "Walk"],
        "animations": SKELETON_ANIMATIONS,
    },
    "ember_sprite": {
        "variants": ["Ghost1", "Ghost2", "Ghost3"],
        "path_template": os.path.join(_SPRITE_BASE, "ghosts", "{variant}_{state}_with_shadow.png"),
        "frame_size": (64, 64),
        "states": ["Attack", "Death", "Hurt", "Idle", "Run", "Walk"],
        "animations": GHOST_ANIMATIONS,
    },
    "stone_guardian": {
        "variants": ["Golem1", "Golem2", "Golem3"],
        "path_template": os.path.join(_SPRITE_BASE, "golems", "{variant}_{state}_with_shadow.png"),
        "frame_size": (128, 128),
        "states": ["Attack", "Death", "Hurt", "Idle", "Run", "Walk"],
        "animations": GOLEM_ANIMATIONS,
    },
}

# ---------------------------------------------------------------------------
# NPC sprite registry: maps npc_id → sprite config
# ---------------------------------------------------------------------------
_NPC_BASE = os.path.join("assets", "sprites", "entities", "npcs")

NPC_SPRITE_REGISTRY = {
    "village_elder": {
        "sprite_name": "Herbalist",
        "subdir": "herbalist",
        "states": {"idle": "Idle", "walk": "Walk"},
        "frame_size": (32, 32),
        "animations": NPC_HERBALIST_ANIMATIONS,
    },
    "finn_farmer": {
        "sprite_name": "Citizen1",
        "subdir": "guild-hall",
        "states": {"idle": "Idle", "walk": "Walk"},
        "frame_size": (32, 32),
        "animations": NPC_ANIMATIONS,
    },
    "young_sera": {
        "sprite_name": "Citizen2",
        "subdir": "guild-hall",
        "states": {"idle": "Idle", "walk": "Walk"},
        "frame_size": (32, 32),
        "animations": NPC_ANIMATIONS,
    },
    "wandering_mage": {
        "sprite_name": "Fighter2",
        "subdir": "guild-hall",
        "states": {"idle": "Idle", "walk": "Walk"},
        "frame_size": (32, 32),
        "animations": NPC_ANIMATIONS,
    },
    "hermit": {
        "sprite_name": "Fighter2",
        "subdir": "guild-hall",
        "states": {"idle": "Idle", "walk": "Walk"},
        "frame_size": (32, 32),
        "animations": NPC_ANIMATIONS,
    },
}

# ---------------------------------------------------------------------------
# Player sprite config
# ---------------------------------------------------------------------------
PLAYER_SPRITE_CONFIG = {
    "sprite_name": "Fighter2",
    "subdir": "guild-hall",
    "states": {"idle": "Idle", "walk": "Walk"},
    "frame_size": (32, 32),
    "animations": PLAYER_ANIMATIONS,
}


class AnimationManager:
    """Singleton that loads and caches sprite sheets for animated enemies."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._sheets = {}   # (variant, state) → SpriteSheet
            cls._instance._scale_cache = {}  # (surface_id, w, h) → Surface
        return cls._instance

    # ------------------------------------------------------------------
    # Sheet loading
    # ------------------------------------------------------------------
    def _get_sheet(self, variant, state, config):
        """Return (and cache) the SpriteSheet for a variant + state."""
        key = (variant, state)
        if key not in self._sheets:
            path = config["path_template"].format(variant=variant, state=state)
            if not os.path.isfile(path):
                self._sheets[key] = None
            else:
                fw, fh = config["frame_size"]
                try:
                    self._sheets[key] = SpriteSheet(path, fw, fh)
                except Exception:
                    self._sheets[key] = None
        return self._sheets[key]

    def _get_npc_sheet(self, sprite_name, subdir, state_suffix, frame_size):
        """Return (and cache) a SpriteSheet for an NPC sprite."""
        key = ("npc", sprite_name, state_suffix)
        if key not in self._sheets:
            path = os.path.join(_NPC_BASE, subdir, f"{sprite_name}_{state_suffix}.png")
            if not os.path.isfile(path):
                # Try with _with_shadow suffix
                path = os.path.join(_NPC_BASE, subdir, f"{sprite_name}_{state_suffix}_with_shadow.png")
            if not os.path.isfile(path):
                self._sheets[key] = None
            else:
                fw, fh = frame_size
                try:
                    self._sheets[key] = SpriteSheet(path, fw, fh)
                except Exception:
                    self._sheets[key] = None
        return self._sheets[key]

    def _get_player_sheet(self, state_suffix):
        """Return (and cache) a SpriteSheet for the player sprite."""
        cfg = PLAYER_SPRITE_CONFIG
        return self._get_npc_sheet(
            cfg["sprite_name"], cfg["subdir"],
            state_suffix, cfg["frame_size"],
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def get_current_frame(self, entity):
        """Return the correct Surface for an entity's current animation, or None."""
        ac = getattr(entity, "animation_controller", None)
        variant = getattr(entity, "sprite_variant", None)
        enemy_type = getattr(entity, "enemy_type", None)
        if ac is None or variant is None or enemy_type is None:
            return None

        config = ANIMATED_ENEMY_REGISTRY.get(enemy_type)
        if config is None:
            return None

        # Map animation name → sprite-sheet state name (capitalised)
        state_name = ac.current_animation.capitalize()
        sheet = self._get_sheet(variant, state_name, config)
        if sheet is None:
            return None

        return sheet.get_frame(ac.row, ac.col)

    def get_npc_frame(self, npc):
        """Return the correct Surface for an NPC's current animation, or None."""
        ac = getattr(npc, "animation_controller", None)
        npc_id = getattr(npc, "npc_id", None)
        if ac is None or npc_id is None:
            return None

        config = NPC_SPRITE_REGISTRY.get(npc_id)
        if config is None:
            return None

        anim_name = ac.current_animation  # "idle" or "walk"
        state_suffix = config["states"].get(anim_name, "Idle")
        sheet = self._get_npc_sheet(
            config["sprite_name"], config["subdir"],
            state_suffix, config["frame_size"],
        )
        if sheet is None:
            return None

        return sheet.get_frame(ac.row, ac.col)

    def get_player_frame(self, player):
        """Return the correct Surface for the player's current animation, or None."""
        ac = getattr(player, "animation_controller", None)
        if ac is None:
            return None

        anim_name = ac.current_animation
        state_suffix = PLAYER_SPRITE_CONFIG["states"].get(anim_name, "Idle")
        sheet = self._get_player_sheet(state_suffix)
        if sheet is None:
            return None

        return sheet.get_frame(ac.row, ac.col)

    def get_scaled_frame(self, surface, size):
        """Return a scaled copy of *surface*, cached by (id, w, h)."""
        key = (id(surface), size[0], size[1])
        if key not in self._scale_cache:
            self._scale_cache[key] = pygame.transform.scale(surface, size)
        return self._scale_cache[key]


# Convenience accessor
def get_animation_manager():
    return AnimationManager()


# ---------------------------------------------------------------------------
# Free function: map game state → animation name
# ---------------------------------------------------------------------------
def resolve_animation_state(entity):
    """Inspect *entity* and set the correct animation + facing on its controller."""
    ac = getattr(entity, "animation_controller", None)
    if ac is None:
        return

    # Facing
    facing = getattr(entity, "facing", "down")
    ac.set_facing(facing)

    # --- one-shot guard: don't interrupt attack / hurt / death while playing ---
    if not ac.finished and ac.current_animation in ("attack", "death"):
        return

    # Dead?
    if not entity.is_alive():
        ac.set_animation("death")
        return

    # Hurt (iframe)?
    if getattr(entity, "iframe_timer", 0) > 0:
        ac.set_animation("hurt")
        return

    # AI state mapping
    ai_state = getattr(entity, "ai_state", "idle")
    state_map = {
        "idle": "idle",
        "patrol": "walk",
        "chase": "run",
        "attack": "attack",
        "windup": "attack",
        "flee": "run",
        "recovery": "idle",
        "stunned": "idle",
    }
    ac.set_animation(state_map.get(ai_state, "idle"))


def pick_random_variant(enemy_type):
    """Return a random variant name for the given enemy type, or None."""
    config = ANIMATED_ENEMY_REGISTRY.get(enemy_type)
    if config is None:
        return None
    return random.choice(config["variants"])
