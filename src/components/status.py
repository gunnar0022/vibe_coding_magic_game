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
            # Core elemental statuses
            "burning": False,
            "wet": False,
            "frozen": False,
            "electrified": False,
            "chilled": False,      # Slowed by cold, precursor to frozen
            "heated": False,       # Hot to touch, precursor to burning

            # Condition statuses
            "poisoned": False,
            "stunned": False,
            "slowed": False,
            "hastened": False,
            "muddy": False,        # Slowed by mud
            "obscured": False,     # Vision impaired (fog overlay)

            # Special statuses
            "invisible": False,
            "invulnerable": False,
            "silenced": False,     # Cannot cast magic

            # Dark/Spirit statuses
            "feared": False,       # From dark + spirit
            "cursed": False,       # Dark affliction
            "withered": False,     # Dark damage to organic
            "decaying": False,     # Dark damage to plants
            "weakened": False,     # Reduced effectiveness (dark + metal)
            "tainted": False,      # Corrupted (dark + liquid)

            # Light/Growth statuses
            "blessed": False,      # Light protection
            "growing": False,      # Plant growth from water
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
        # Water/wet removes burning and heated
        if new_effect == "wet":
            if self.has_flag("burning"):
                self.remove_effect("burning")
            if self.has_flag("heated"):
                self.remove_effect("heated")

        # Fire/burning removes wet, frozen, and chilled
        if new_effect == "burning":
            if self.has_flag("wet"):
                self.remove_effect("wet")
            if self.has_flag("frozen"):
                self.remove_effect("frozen")
            if self.has_flag("chilled"):
                self.remove_effect("chilled")

        # Heated removes chilled and frozen
        if new_effect == "heated":
            if self.has_flag("chilled"):
                self.remove_effect("chilled")
            if self.has_flag("frozen"):
                self.remove_effect("frozen")

        # Frozen removes burning and heated
        if new_effect == "frozen":
            if self.has_flag("burning"):
                self.remove_effect("burning")
            if self.has_flag("heated"):
                self.remove_effect("heated")

        # Chilled stacks toward frozen, removes heated
        if new_effect == "chilled":
            if self.has_flag("heated"):
                self.remove_effect("heated")

        # Blessed removes dark-based statuses
        if new_effect == "blessed":
            for dark_status in ["feared", "cursed", "withered", "decaying", "tainted"]:
                if self.has_flag(dark_status):
                    self.remove_effect(dark_status)

        # Growing removes withered and decaying
        if new_effect == "growing":
            if self.has_flag("withered"):
                self.remove_effect("withered")
            if self.has_flag("decaying"):
                self.remove_effect("decaying")

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
