"""
AttackSlot - runtime wrapper for an enemy attack definition.
Manages cooldown, windup, and recovery timers.
"""


class AttackSlot:
    """
    Wraps an attack definition dict with runtime timer state.

    Attack definition keys:
        name: str
        type: str - "contact", "melee", "projectile", "aoe"
        damage: int
        damage_type: str
        range: float
        cooldown: float - seconds between attacks
        windup: float - seconds of telegraph before attack executes
        recovery: float - seconds of vulnerability after attack
        knockback_multiplier: float - 0.0 to 3.0
        status_effects: list of dicts
        projectile_speed: float (for projectile type)
        aoe_radius: float (for aoe type)
        telegraph_color: tuple (RGB)
        element: str
    """

    def __init__(self, attack_def):
        self.attack_def = attack_def
        self.cooldown_timer = 0.0
        self.windup_timer = 0.0
        self.recovery_timer = 0.0
        self._in_windup = False
        self._in_recovery = False

    def update(self, dt):
        """Tick cooldown timer."""
        if self.cooldown_timer > 0:
            self.cooldown_timer -= dt

    def is_ready(self):
        """Check if this attack can be used."""
        return (self.cooldown_timer <= 0
                and not self._in_windup
                and not self._in_recovery)

    def start_windup(self):
        """Begin the windup phase."""
        self._in_windup = True
        self.windup_timer = self.attack_def.get("windup", 0.0)

    def update_windup(self, dt):
        """Tick the windup timer."""
        if self._in_windup:
            self.windup_timer -= dt

    def is_windup_done(self):
        """Check if windup has completed."""
        return self._in_windup and self.windup_timer <= 0

    def start_recovery(self):
        """Begin the recovery phase after attack execution."""
        self._in_windup = False
        self._in_recovery = True
        self.recovery_timer = self.attack_def.get("recovery", 0.0)

    def update_recovery(self, dt):
        """Tick the recovery timer."""
        if self._in_recovery:
            self.recovery_timer -= dt

    def is_recovery_done(self):
        """Check if recovery has completed."""
        return self._in_recovery and self.recovery_timer <= 0

    def start_cooldown(self):
        """Start the cooldown after recovery completes."""
        self._in_recovery = False
        self.cooldown_timer = self.attack_def.get("cooldown", 1.0)

    @property
    def is_winding_up(self):
        return self._in_windup

    @property
    def is_recovering(self):
        return self._in_recovery
