"""
Spell descriptor - the resolved output of symbol combinations.
"""


class SpellDescriptor:
    """
    Describes the abstract properties of a spell.
    This is what gets passed to world objects to determine their reactions.

    Spells do NOT know their targets.
    Objects decide how they respond to spell descriptors.
    """

    def __init__(self, data=None):
        data = data or {}

        # Identity
        self.name = data.get("name", "Unknown Spell")
        self.source_symbols = data.get("source_symbols", [])

        # High-level category
        # destructive, environmental, social, utility, defensive, etc.
        self.category = data.get("category", "none")

        # Element / physical type
        # fire, water, earth, wind, lightning, ice, nature, light, dark, physical, none
        self.element = data.get("element", "none")

        # Interaction traits
        # pressure, slashing, piercing, erosion, burning, freezing, influence, etc.
        self.traits = set(data.get("traits", []))

        # Intensity/magnitude (1.0 = normal)
        self.intensity = data.get("intensity", 1.0)

        # Effect properties
        self.duration = data.get("duration", 0.5)  # How long the effect persists
        self.radius = data.get("radius", 0)  # Area of effect (0 = single tile)

        # Damage if applicable
        self.damage = data.get("damage", None)  # {"amount": X, "type": "fire"}

        # Status effects to apply
        self.status_effects = data.get("status_effects", [])

        # Mana cost
        self.mana_cost = data.get("mana_cost", 10)

        # Whether this affects the caster too
        self.affects_caster = data.get("affects_caster", False)

        # Special flags
        self.is_dud = data.get("is_dud", False)  # No effect combination

    def has_trait(self, trait):
        """Check if spell has a specific interaction trait."""
        return trait in self.traits

    def to_dict(self):
        """Convert to dictionary for passing to objects."""
        return {
            "name": self.name,
            "source_symbols": self.source_symbols,
            "category": self.category,
            "element": self.element,
            "traits": list(self.traits),
            "intensity": self.intensity,
            "duration": self.duration,
            "radius": self.radius,
            "damage": self.damage,
            "status_effects": self.status_effects,
            "mana_cost": self.mana_cost,
            "affects_caster": self.affects_caster,
            "is_dud": self.is_dud,
        }

    @staticmethod
    def from_dict(data):
        """Create SpellDescriptor from dictionary."""
        return SpellDescriptor(data)

    def __repr__(self):
        return f"SpellDescriptor({self.name}, {self.element}, traits={self.traits})"
