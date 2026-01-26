"""
Status component for tracking conditions and effects.
"""
from .base import Component


class StatusEffect:
    """A single status effect with duration and properties."""

    def __init__(self, name, duration=-1, intensity=1.0, source=None):
        self.name = name
        self.duration = duration  # -1 = permanent until removed
        self.intensity = intensity
        self.source = source  # what caused this effect
        self.elapsed = 0.0

    def is_expired(self):
        return self.duration >= 0 and self.elapsed >= self.duration

    def update(self, dt):
        if self.duration >= 0:
            self.elapsed += dt

    def serialize(self):
        return {
            "name": self.name,
            "duration": self.duration,
            "intensity": self.intensity,
            "elapsed": self.elapsed
        }


class StatusComponent(Component):
    """Manages status effects and boolean flags."""

    def __init__(self):
        super().__init__()
        # Boolean status flags for quick checks
        self.flags = {
            "burning": False,
            "wet": False,
            "frozen": False,
            "poisoned": False,
            "stunned": False,
            "slowed": False,
            "hastened": False,
            "invisible": False,
            "invulnerable": False,
            "silenced": False,  # cannot cast magic
        }

        # Active status effects with durations
        self.effects = []

    def has_flag(self, flag_name):
        """Check if a status flag is set."""
        return self.flags.get(flag_name, False)

    def set_flag(self, flag_name, value=True):
        """Set a status flag."""
        self.flags[flag_name] = value

    def clear_flag(self, flag_name):
        """Clear a status flag."""
        self.flags[flag_name] = False

    def add_effect(self, name, duration=-1, intensity=1.0, source=None):
        """Add a new status effect."""
        # Check for conflicting effects and handle interactions
        self._handle_effect_interaction(name)

        effect = StatusEffect(name, duration, intensity, source)
        self.effects.append(effect)

        # Update corresponding flag
        if name in self.flags:
            self.flags[name] = True

        return effect

    def remove_effect(self, name):
        """Remove all effects with given name."""
        self.effects = [e for e in self.effects if e.name != name]
        if name in self.flags:
            self.flags[name] = False

    def has_effect(self, name):
        """Check if an effect is active."""
        return any(e.name == name for e in self.effects)

    def _handle_effect_interaction(self, new_effect):
        """Handle interactions between conflicting effects."""
        # Water removes burning
        if new_effect == "wet" and self.has_flag("burning"):
            self.remove_effect("burning")

        # Fire removes wet and frozen
        if new_effect == "burning":
            if self.has_flag("wet"):
                self.remove_effect("wet")
            if self.has_flag("frozen"):
                self.remove_effect("frozen")

        # Frozen removes burning
        if new_effect == "frozen" and self.has_flag("burning"):
            self.remove_effect("burning")

    def update(self, dt):
        """Update all effects and remove expired ones."""
        expired = []
        for effect in self.effects:
            effect.update(dt)
            if effect.is_expired():
                expired.append(effect)

        for effect in expired:
            self.remove_effect(effect.name)

    def serialize(self):
        return {
            "flags": self.flags.copy(),
            "effects": [e.serialize() for e in self.effects]
        }

    def deserialize(self, data):
        self.flags.update(data.get("flags", {}))
        self.effects = []
        for e_data in data.get("effects", []):
            effect = StatusEffect(
                e_data["name"],
                e_data.get("duration", -1),
                e_data.get("intensity", 1.0)
            )
            effect.elapsed = e_data.get("elapsed", 0.0)
            self.effects.append(effect)
