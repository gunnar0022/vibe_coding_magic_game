"""
Base entity class - root of all world objects.
"""
import uuid


class Entity:
    """Base class for everything that exists in the world."""

    _next_id = 1

    def __init__(self, x=0, y=0, tags=None):
        self.id = Entity._next_id
        Entity._next_id += 1

        # Position (grid coordinates)
        self.x = x
        self.y = y

        # Tags for identification and filtering
        self.tags = set(tags) if tags else set()

        # Component storage
        self.components = {}

        # Whether entity blocks movement
        self.solid = False

        # Whether entity is active in the world
        self.active = True

        # Visual properties (placeholder)
        self.color = (255, 255, 255)
        self.sprite = None

    def add_component(self, component):
        """Add a component to this entity."""
        component_type = type(component).__name__
        self.components[component_type] = component
        component.attach(self)
        return component

    def get_component(self, component_type):
        """Get a component by class name or class."""
        if isinstance(component_type, str):
            return self.components.get(component_type)
        return self.components.get(component_type.__name__)

    def has_component(self, component_type):
        """Check if entity has a component."""
        if isinstance(component_type, str):
            return component_type in self.components
        return component_type.__name__ in self.components

    def remove_component(self, component_type):
        """Remove a component from entity."""
        if isinstance(component_type, str):
            name = component_type
        else:
            name = component_type.__name__

        if name in self.components:
            self.components[name].detach()
            del self.components[name]

    def has_tag(self, tag):
        """Check if entity has a specific tag."""
        return tag in self.tags

    def add_tag(self, tag):
        """Add a tag to entity."""
        self.tags.add(tag)

    def remove_tag(self, tag):
        """Remove a tag from entity."""
        self.tags.discard(tag)

    def update(self, dt):
        """Update entity and all components."""
        for component in self.components.values():
            component.update(dt)

    def on_magic_applied(self, spell_descriptor, context=None):
        """
        Called when magic is cast on this entity.
        Override in subclasses to define reactions.
        Returns dict describing what happened.
        """
        return {"affected": False, "message": "No effect."}

    def distance_to(self, other):
        """Get grid distance to another entity."""
        return abs(self.x - other.x) + abs(self.y - other.y)

    def serialize(self):
        """Serialize entity state for saving."""
        data = {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "tags": list(self.tags),
            "solid": self.solid,
            "active": self.active,
            "components": {}
        }
        for name, comp in self.components.items():
            data["components"][name] = comp.serialize()
        return data

    def deserialize(self, data):
        """Load entity state from saved data."""
        self.x = data.get("x", 0)
        self.y = data.get("y", 0)
        self.tags = set(data.get("tags", []))
        self.solid = data.get("solid", False)
        self.active = data.get("active", True)
        for name, comp_data in data.get("components", {}).items():
            if name in self.components:
                self.components[name].deserialize(comp_data)

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, x={self.x}, y={self.y})"
