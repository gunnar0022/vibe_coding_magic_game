"""
Base entity class - root of all world objects.
"""
import uuid
import math


class Entity:
    """Base class for everything that exists in the world."""

    _next_id = 1

    def __init__(self, x=0, y=0, tags=None):
        self.id = Entity._next_id
        Entity._next_id += 1

        # Position (float for sub-grid movement, in tile units)
        self.x = float(x)
        self.y = float(y)

        # Whether this entity uses sub-grid movement (player, enemies)
        # If False, positions snap to integer tiles (world objects)
        self.uses_sub_grid = False

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
        """Get grid distance to another entity (Manhattan distance)."""
        return abs(self.x - other.x) + abs(self.y - other.y)

    def euclidean_distance_to(self, other):
        """Get Euclidean distance to another entity."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    def get_tile_x(self):
        """Get the large tile X coordinate (integer)."""
        return int(math.floor(self.x))

    def get_tile_y(self):
        """Get the large tile Y coordinate (integer)."""
        return int(math.floor(self.y))

    def get_tile(self):
        """Get the large tile coordinates as (int, int)."""
        return (self.get_tile_x(), self.get_tile_y())

    def get_tiles_occupied(self, width=1.0, height=1.0):
        """
        Get all large tiles this entity occupies.

        Args:
            width, height: Entity dimensions in tile units

        Returns:
            List of (tile_x, tile_y) tuples
        """
        tiles = set()
        left = self.x
        right = self.x + width
        top = self.y
        bottom = self.y + height

        min_tile_x = int(math.floor(left))
        max_tile_x = int(math.floor(right - 0.001))
        min_tile_y = int(math.floor(top))
        max_tile_y = int(math.floor(bottom - 0.001))

        for ty in range(min_tile_y, max_tile_y + 1):
            for tx in range(min_tile_x, max_tile_y + 1):
                tiles.add((tx, ty))

        return list(tiles)

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
