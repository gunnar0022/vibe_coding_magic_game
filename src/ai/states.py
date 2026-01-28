"""
AI state constants for the enemy brain system.
"""


class AIState:
    """Constants for AI state machine states."""
    IDLE = "idle"
    PATROL = "patrol"
    CHASE = "chase"
    ATTACK = "attack"
    FLEE = "flee"
    STUNNED = "stunned"
    WINDUP = "windup"
    RECOVERY = "recovery"
