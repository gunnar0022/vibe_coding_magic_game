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

        # Slashing threshold (minimum slashing power to damage this object)
        self.slashing_threshold = 0

        # Track how this object was destroyed (for spawn logic)
        self.destruction_cause = None

        # What to spawn when destroyed (object_type or None)
        self.spawn_on_destroy = None

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

        # Attribute tags (for elemental reactions)
        for attribute in defaults.get("attributes", []):
            self.add_tag(attribute)

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

        # Slashing threshold
        if "slashing_threshold" in defaults:
            self.slashing_threshold = defaults["slashing_threshold"]

        # What to spawn on destruction
        if "spawn_on_destroy" in defaults:
            self.spawn_on_destroy = defaults["spawn_on_destroy"]

    def on_magic_applied(self, spell_descriptor, context=None):
        """Handle magic effects on this world object."""
        result = {"affected": False, "messages": [], "state_changed": False, "push_request": None}
        env = self.environmental

        # Get element from spell
        element = spell_descriptor.get("element", "none")

        # Use ReactionProcessor for elemental reactions (deferred import to avoid circular)
        try:
            from ..reactions import get_reaction_processor
            processor = get_reaction_processor(context.get("world") if context else None)
            reaction_results = processor.process_element_applied(self, element, context)

            if reaction_results:
                result["affected"] = True
                for r in reaction_results:
                    for effect in r.get("effects", []):
                        result["messages"].append(effect)
        except ImportError:
            pass  # Reactions module not available yet

        # Handle fire effects on flammable objects (legacy behavior + reaction system)
        if element == "fire":
            if env.has_trait("flammable") and env.state != "burning":
                if not env.is_immune_to("fire"):
                    env.set_state("burning")
                    result["affected"] = True
                    result["state_changed"] = True
                    result["messages"].append(f"The {self.object_type} catches fire!")

        # Handle water effects (extinguishes fire)
        if element == "water":
            if env.state == "burning":
                env.set_state("intact")
                result["affected"] = True
                result["state_changed"] = True
                result["messages"].append(f"The fire on the {self.object_type} is extinguished.")

        # Handle ice effects (extinguishes fire, freezes objects)
        if element == "ice":
            if env.state == "burning":
                env.set_state("intact")
                result["affected"] = True
                result["state_changed"] = True
                result["messages"].append(f"The fire on the {self.object_type} is frozen out!")
            if env.state != "frozen" and not env.is_immune_to("ice"):
                env.set_state("frozen")
                result["affected"] = True
                result["state_changed"] = True
                result["messages"].append(f"The {self.object_type} is encased in ice!")

        # Handle force/physical spells - push rocks and logs
        if element == "physical" or "pressure" in spell_descriptor.get("traits", []):
            if self.object_type in ("rock", "log"):
                cast_dir = context.get("cast_direction", (0, 0)) if context else (0, 0)
                if cast_dir != (0, 0):
                    result["push_request"] = {
                        "dx": cast_dir[0],
                        "dy": cast_dir[1],
                    }
                    result["affected"] = True
                    result["messages"].append(f"The {self.object_type} shifts from the force.")

        return result

    def on_slashing_attack(self, slashing_power, damage, context=None):
        """
        Handle a slashing attack from a weapon.

        Args:
            slashing_power: The weapon's slashing power tier
            damage: The raw damage amount
            context: Additional context (attacker, direction, etc.)

        Returns:
            Dict with affected, messages, and whether object was destroyed
        """
        result = {"affected": False, "messages": [], "destroyed": False}

        # Check if slashing power meets threshold
        if self.slashing_threshold > 0 and slashing_power < self.slashing_threshold:
            result["messages"].append(f"The {self.object_type} is too tough to cut.")
            return result

        # Apply slashing damage
        actual_damage = self.environmental.take_damage(damage, "slashing")

        if actual_damage > 0:
            result["affected"] = True
            result["messages"].append(f"The {self.object_type} takes slashing damage!")

            # Check for destruction
            if self.environmental.is_destroyed():
                self.destruction_cause = "slashing"
                self._pending_destroy = True
                result["destroyed"] = True
                result["messages"].append(f"The {self.object_type} is cut down!")

        return result

    def update(self, dt):
        super().update(dt)

        # Handle burning state - damage over time until destruction
        if self.environmental.state == "burning":
            # Apply burning damage over time (10 damage per second)
            self.environmental.take_damage(10 * dt, "fire")

            # Check for destruction (check durability directly for reliability)
            if self.environmental.durability <= 0 or self.environmental.is_destroyed():
                self.environmental.state = "destroyed"
                self.destruction_cause = "burning"
                # Mark for removal from world
                # World.update() will check this and remove the entity
                self._pending_destroy = True

    def should_be_removed(self):
        """Check if this object should be removed from the world."""
        return getattr(self, '_pending_destroy', False)


# Default configurations for common object types
# Note: attributes use string values matching Attribute constants ("organic", "plant", etc.)
OBJECT_TYPE_DEFAULTS = {
    "tree": {
        "solid": True,
        "color": (50, 120, 50),
        "durability": 100,
        "traits": {
            "flammable": True,
            "organic": True,
        },
        "attributes": ["plant", "organic"],
        "immunities": ["poison", "psychic"],
        "vulnerabilities": {"slashing": 1.5, "fire": 1.2},
        "slashing_threshold": 2,  # Requires axe or better to cut
        "spawn_on_destroy": "log",  # Only spawns log when slashed, not burned
        "examine": "A sturdy tree. Its bark is rough to the touch."
    },
    "rock": {
        "solid": True,
        "color": (100, 100, 110),
        "durability": 200,
        "traits": {
            "brittle": True,
        },
        "attributes": ["stone"],
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
        "attributes": ["liquid"],
        "immunities": ["physical", "slashing", "fire", "poison"],
        "state": "flowing",
        "examine": "Clear water flows gently."
    },
    "wall": {
        "solid": True,
        "color": (80, 70, 60),
        "durability": 500,
        "traits": {},
        "attributes": ["stone"],
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
        "attributes": ["plant"],
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
        "attributes": ["plant"],
        "immunities": ["psychic"],
        "examine": "A leafy bush."
    },
    "log": {
        "solid": True,
        "color": (139, 90, 43),  # Brown
        "durability": 150,
        "traits": {
            "flammable": True,
            "organic": True,
        },
        "attributes": ["organic"],  # Log is organic but not plant (dead wood)
        "immunities": ["poison", "psychic"],
        "vulnerabilities": {},
        "examine": "A heavy fallen log. Too heavy to lift with bare hands."
    }
}
