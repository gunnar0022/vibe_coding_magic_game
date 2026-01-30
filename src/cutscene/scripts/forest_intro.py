"""
Forest intro cutscene — plays the first time the player enters the forest.
Camera pans right to show a Stone Guardian killing a Slime, then pans back.
"""
from ..cutscene_actions import (
    WaitAction,
    PanCameraTo,
    SpawnEntity,
    MoveEntityTo,
    EntityAttack,
    WaitUntilDead,
    ShowDialogue,
    ReturnCameraToPlayer,
    RemoveEntity,
    SetEventFlag,
)
from ...entities.enemy import Enemy


def build_forest_intro():
    """Return the action list for the forest intro cutscene."""
    return [
        # Spawn combatants immediately (off-screen to the right)
        SpawnEntity("golem", lambda: Enemy(35, 17, enemy_type="stone_guardian")),
        SpawnEntity("slime", lambda: Enemy(30, 17, enemy_type="slime")),

        # Brief pause before camera starts moving
        WaitAction(0.5),

        # Pan camera to the fight area
        PanCameraTo(32, 17, speed=4.0),

        # Let the player observe both enemies
        WaitAction(1.0),

        # Golem walks toward the slime
        MoveEntityTo("golem", 31, 17, speed=1.5),

        # Beat before strike
        WaitAction(0.3),

        # Hit 1 (25 * (1 - 0.3) = 17.5 effective damage)
        EntityAttack("golem", "slime"),
        WaitAction(1.5),

        # Hit 2 (kills the slime — 35 total effective > 30 HP)
        EntityAttack("golem", "slime"),
        WaitUntilDead("slime"),

        # Dramatic pause
        WaitAction(1.0),

        # Pan camera back to the player
        ReturnCameraToPlayer(speed=4.0),

        # Clean up cutscene entities after camera is back
        RemoveEntity("golem"),
        RemoveEntity("slime"),

        # Warning dialogue
        ShowDialogue("There seem to be dangerous monsters in this area..."),

        # Mark the cutscene as played so it won't trigger again
        SetEventFlag("forest", "forest_intro_played"),
    ]
