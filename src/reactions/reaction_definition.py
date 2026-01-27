"""
ReactionDefinition class - defines what happens when a reaction occurs.
"""


class ReactionDefinition:
    """
    Defines the outcome of an elemental reaction.

    Reactions can:
    - Remove existing status effects
    - Apply new status effects
    - Deal damage
    - Spread to nearby entities
    - Trigger chain reactions
    """

    def __init__(self, data):
        """
        Initialize a reaction definition from a data dictionary.

        Args:
            data: Dictionary containing reaction properties
        """
        # Identity
        self.name = data.get("name", "Unknown Reaction")
        self.priority = data.get("priority", 50)  # Higher = processed first

        # Status effect changes
        self.removes_statuses = data.get("removes_statuses", [])
        self.applies_statuses = data.get("applies_statuses", [])
        # Format for applies_statuses: [{"name": "burning", "duration": 5.0, "intensity": 1.0}]

        # Damage
        self.damage = data.get("damage", None)
        # Format: {"amount": 10, "type": "fire"}

        # Spread behavior
        self.spread_type = data.get("spread_type", None)  # "adjacent", "radius", "material"
        self.spread_range = data.get("spread_range", 1)
        self.spread_condition = data.get("spread_condition", None)  # Tag/trait required
        self.spread_element = data.get("spread_element", None)  # Element to spread (defaults to source)

        # Special flags
        self.cancels_source = data.get("cancels_source", False)  # Remove triggering element/status
        self.chain_reaction = data.get("chain_reaction", False)  # Can trigger further reactions
        self.produces_effect = data.get("produces_effect", None)  # Visual/audio effect to spawn

        # Intensity scaling
        self.intensity_multiplier = data.get("intensity_multiplier", 1.0)

    def __repr__(self):
        return f"ReactionDefinition({self.name}, priority={self.priority})"

    def to_dict(self):
        """Serialize to dictionary for debugging or saving."""
        return {
            "name": self.name,
            "priority": self.priority,
            "removes_statuses": self.removes_statuses,
            "applies_statuses": self.applies_statuses,
            "damage": self.damage,
            "spread_type": self.spread_type,
            "spread_range": self.spread_range,
            "spread_condition": self.spread_condition,
            "cancels_source": self.cancels_source,
            "chain_reaction": self.chain_reaction,
        }
