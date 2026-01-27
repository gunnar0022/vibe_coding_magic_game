"""
Environmental traits component for inanimate objects.
"""
from .base import Component


class EnvironmentalComponent(Component):
    """Defines environmental properties and reaction rules for world objects."""

    def __init__(self):
        super().__init__()
        # Material properties
        self.traits = {
            "flammable": False,
            "conductive": False,
            "porous": False,
            "brittle": False,
            "organic": False,
            "metallic": False,
            "liquid": False,
        }

        # Structural properties
        self.durability = 100
        self.max_durability = 100

        # Current state
        self.state = "intact"  # intact, damaged, burning, flooded, destroyed, etc.

        # What this object produces when destroyed or harvested
        self.drops = []  # List of (item_definition_id, quantity, chance)

        # Damage type immunities (completely ignores these)
        self.immunities = set()

        # Damage type vulnerabilities (extra damage)
        self.vulnerabilities = {}  # damage_type -> multiplier

    def has_trait(self, trait):
        """Check if object has a specific trait."""
        return self.traits.get(trait, False)

    def set_trait(self, trait, value=True):
        """Set an environmental trait."""
        self.traits[trait] = value

    def is_immune_to(self, damage_type):
        """Check if immune to a damage type."""
        return damage_type in self.immunities

    def get_vulnerability(self, damage_type):
        """Get damage multiplier for a damage type."""
        return self.vulnerabilities.get(damage_type, 1.0)

    def take_damage(self, amount, damage_type="physical"):
        """Apply damage considering immunities and vulnerabilities."""
        if self.is_immune_to(damage_type):
            return 0

        multiplier = self.get_vulnerability(damage_type)
        actual_damage = amount * multiplier
        self.durability = max(0, self.durability - actual_damage)

        # Update state based on durability
        # Note: Don't overwrite active states like "burning" with "damaged"
        if self.durability <= 0:
            self.state = "destroyed"
        elif self.durability < self.max_durability * 0.5:
            # Only set to damaged if not in an active state
            if self.state not in ("burning", "flooded", "destroyed"):
                self.state = "damaged"

        return actual_damage

    def set_state(self, new_state):
        """Change the object's state."""
        old_state = self.state
        self.state = new_state
        return old_state != new_state

    def is_destroyed(self):
        """Check if object is destroyed."""
        return self.state == "destroyed"

    def serialize(self):
        return {
            "traits": self.traits.copy(),
            "durability": self.durability,
            "max_durability": self.max_durability,
            "state": self.state,
            "drops": self.drops.copy(),
            "immunities": list(self.immunities),
            "vulnerabilities": self.vulnerabilities.copy()
        }

    def deserialize(self, data):
        self.traits.update(data.get("traits", {}))
        self.durability = data.get("durability", 100)
        self.max_durability = data.get("max_durability", 100)
        self.state = data.get("state", "intact")
        self.drops = data.get("drops", [])
        self.immunities = set(data.get("immunities", []))
        self.vulnerabilities = data.get("vulnerabilities", {})
