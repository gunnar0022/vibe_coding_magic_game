"""
World object entity - inanimate objects like trees, rocks, water, walls.
"""
from .base import Entity
from ..components import EnvironmentalComponent, InteractionComponent


class WorldObject(Entity):
    """Inanimate world object with environmental properties."""

    def __init__(self, x=0, y=0, object_type="generic", tags=None):
        super().__init__(x, y, tags)
        self.add_tag("world_object")
        self.add_tag(object_type)

        self.object_type = object_type

        # Add components
        self.environmental = self.add_component(EnvironmentalComponent())
        self.interaction = self.add_component(InteractionComponent())

        # Apply type-specific defaults
        self._apply_type_defaults()

    def _apply_type_defaults(self):
        """Set default properties based on object type."""
        defaults = OBJECT_TYPE_DEFAULTS.get(self.object_type, {})

        self.solid = defaults.get("solid", True)
        self.color = defaults.get("color", (150, 150, 150))

        # Environmental traits
        for trait, value in defaults.get("traits", {}).items():
            self.environmental.set_trait(trait, value)

        # Durability
        if "durability" in defaults:
            self.environmental.durability = defaults["durability"]
            self.environmental.max_durability = defaults["durability"]

        # Immunities
        for immunity in defaults.get("immunities", []):
            self.environmental.immunities.add(immunity)

        # Vulnerabilities
        for vuln, mult in defaults.get("vulnerabilities", {}).items():
            self.environmental.vulnerabilities[vuln] = mult

        # Initial state
        if "state" in defaults:
            self.environmental.state = defaults["state"]

        # Examination text
        if "examine" in defaults:
            self.interaction.set_examine_text(defaults["examine"])

    def on_magic_applied(self, spell_descriptor, context=None):
        """Handle magic effects on this world object."""
        result = {"affected": False, "messages": [], "state_changed": False, "push_request": None}

        env = self.environmental

        # Handle fire effects on flammable objects
        # Fire applies burning status - does NOT deal direct damage
        if spell_descriptor.get("element") == "fire":
            if env.has_trait("flammable") and env.state != "burning":
                if not env.is_immune_to("fire"):
                    env.set_state("burning")
                    result["affected"] = True
                    result["state_changed"] = True
                    result["messages"].append(f"The {self.object_type} catches fire!")

        # Handle water effects (visual only per spec, extinguishes fire)
        if spell_descriptor.get("element") == "water":
            if env.state == "burning":
                env.set_state("intact")
                result["affected"] = True
                result["state_changed"] = True
                result["messages"].append(f"The fire on the {self.object_type} is extinguished.")

        # Handle force/physical spells - push rocks
        if spell_descriptor.get("element") == "physical" or "pressure" in spell_descriptor.get("traits", []):
            if self.object_type == "rock":
                # Request push in direction from caster
                # Context should contain cast_direction
                cast_dir = context.get("cast_direction", (0, 0)) if context else (0, 0)
                if cast_dir != (0, 0):
                    result["push_request"] = {
                        "dx": cast_dir[0],
                        "dy": cast_dir[1],
                    }
                    result["affected"] = True
                    result["messages"].append("The rock shifts from the force.")

        return result

    def update(self, dt):
        super().update(dt)

        # Handle burning state - damage over time until destruction
        if self.environmental.state == "burning":
            # Apply burning damage over time (10 damage per second)
            self.environmental.take_damage(10 * dt, "fire")

            # Check for destruction
            if self.environmental.is_destroyed():
                self.environmental.state = "destroyed"
                # Mark for removal from world
                # World.update() will check this and remove the entity
                self._pending_destroy = True

    def should_be_removed(self):
        """Check if this object should be removed from the world."""
        return getattr(self, '_pending_destroy', False)


# Default configurations for common object types
OBJECT_TYPE_DEFAULTS = {
    "tree": {
        "solid": True,
        "color": (50, 120, 50),
        "durability": 100,
        "traits": {
            "flammable": True,
            "organic": True,
        },
        "immunities": ["poison", "psychic"],
        "vulnerabilities": {"slashing": 1.5, "fire": 1.2},
        "examine": "A sturdy tree. Its bark is rough to the touch."
    },
    "rock": {
        "solid": True,
        "color": (100, 100, 110),
        "durability": 200,
        "traits": {
            "brittle": True,
        },
        "immunities": ["poison", "psychic", "fire"],
        "vulnerabilities": {"physical": 0.5},
        "examine": "A large rock. It looks quite heavy."
    },
    "water": {
        "solid": False,
        "color": (40, 80, 200),
        "durability": -1,  # Infinite
        "traits": {
            "liquid": True,
            "conductive": True,
        },
        "immunities": ["physical", "slashing", "fire", "poison"],
        "state": "flowing",
        "examine": "Clear water flows gently."
    },
    "wall": {
        "solid": True,
        "color": (80, 70, 60),
        "durability": 500,
        "traits": {},
        "immunities": ["poison", "psychic"],
        "vulnerabilities": {},
        "examine": "A solid wall. It won't move easily."
    },
    "grass": {
        "solid": False,
        "color": (35, 80, 35),
        "durability": 10,
        "traits": {
            "flammable": True,
            "organic": True,
        },
        "immunities": ["psychic"],
        "examine": "Soft grass covers the ground."
    },
    "bush": {
        "solid": False,
        "color": (40, 100, 40),
        "durability": 30,
        "traits": {
            "flammable": True,
            "organic": True,
        },
        "immunities": ["psychic"],
        "examine": "A leafy bush."
    }
}
