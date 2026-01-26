"""
World class - manages the game world, entities, and spatial queries.
"""
from .tile import Tile
from ..core.settings import Settings


class World:
    """
    The game world containing tiles, entities, and handling spatial queries.
    """

    def __init__(self, width=None, height=None):
        self.width = width or Settings.GRID_WIDTH
        self.height = height or Settings.GRID_HEIGHT

        # Tile grid
        self.tiles = [[Tile("ground") for _ in range(self.width)] for _ in range(self.height)]

        # All entities in the world
        self.entities = {}  # id -> entity

        # Spatial index for quick lookups
        self._entity_grid = {}  # (x, y) -> set of entity ids

        # Effect instances (tracked separately for updates)
        self.active_effects = []

        # Player reference
        self.player = None

    def add_entity(self, entity):
        """Add an entity to the world."""
        self.entities[entity.id] = entity
        self._add_to_grid(entity)

        if entity.has_tag("player"):
            self.player = entity

        return entity

    def remove_entity(self, entity_or_id):
        """Remove an entity from the world."""
        if isinstance(entity_or_id, int):
            entity_id = entity_or_id
        else:
            entity_id = entity_or_id.id

        if entity_id in self.entities:
            entity = self.entities[entity_id]
            self._remove_from_grid(entity)
            del self.entities[entity_id]

            if self.player and self.player.id == entity_id:
                self.player = None

    def _add_to_grid(self, entity):
        """Add entity to spatial grid."""
        key = (entity.x, entity.y)
        if key not in self._entity_grid:
            self._entity_grid[key] = set()
        self._entity_grid[key].add(entity.id)

    def _remove_from_grid(self, entity):
        """Remove entity from spatial grid."""
        key = (entity.x, entity.y)
        if key in self._entity_grid:
            self._entity_grid[key].discard(entity.id)

    def update_entity_position(self, entity, old_x, old_y):
        """Update entity position in spatial grid."""
        old_key = (old_x, old_y)
        if old_key in self._entity_grid:
            self._entity_grid[old_key].discard(entity.id)

        self._add_to_grid(entity)

    def get_tile(self, x, y):
        """Get tile at grid position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def set_tile(self, x, y, tile_type):
        """Set tile at grid position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = Tile(tile_type)

    def is_in_bounds(self, x, y):
        """Check if position is within world bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def is_walkable(self, x, y):
        """Check if a tile can be walked on."""
        if not self.is_in_bounds(x, y):
            return False
        tile = self.get_tile(x, y)
        return tile is not None and tile.walkable

    def is_blocked(self, x, y):
        """Check if movement to position is blocked (tile or solid entity)."""
        if not self.is_walkable(x, y):
            return True

        # Check for solid entities
        entities = self.get_entities_at(x, y)
        for entity in entities:
            if entity.solid:
                return True

        return False

    def get_entities_at(self, x, y):
        """Get all entities at a grid position."""
        key = (x, y)
        if key not in self._entity_grid:
            return []

        return [self.entities[eid] for eid in self._entity_grid[key]
                if eid in self.entities]

    def get_entities_in_radius(self, x, y, radius):
        """Get all entities within Manhattan distance."""
        results = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if abs(dx) + abs(dy) <= radius:
                    results.extend(self.get_entities_at(x + dx, y + dy))
        return results

    def get_entities_by_tag(self, tag):
        """Get all entities with a specific tag."""
        return [e for e in self.entities.values() if e.has_tag(tag)]

    def spawn_effect(self, effect):
        """Add an effect instance to the world."""
        self.add_entity(effect)
        self.active_effects.append(effect)
        return effect

    def try_push_entity(self, entity, dx, dy):
        """
        Attempt to push an entity one tile in the given direction.
        Returns True if push succeeded, False if blocked.
        Used for force spells pushing rocks.
        """
        new_x = entity.x + dx
        new_y = entity.y + dy

        # Check if destination is blocked
        if self.is_blocked(new_x, new_y):
            return False

        # Execute the push
        old_x, old_y = entity.x, entity.y
        entity.x = new_x
        entity.y = new_y
        self.update_entity_position(entity, old_x, old_y)
        return True

    def update(self, dt):
        """Update all entities and effects."""
        # Track entities to remove (destroyed by burning, etc.)
        entities_to_remove = []

        # Track position changes
        for entity in list(self.entities.values()):
            old_x, old_y = entity.x, entity.y
            entity.update(dt)

            # Update spatial grid if moved
            if entity.x != old_x or entity.y != old_y:
                self.update_entity_position(entity, old_x, old_y)

            # Check if entity should be removed (e.g., tree burned down)
            if hasattr(entity, 'should_be_removed') and entity.should_be_removed():
                entities_to_remove.append(entity)

        # Remove destroyed entities
        for entity in entities_to_remove:
            self.remove_entity(entity)

        # Update active effects
        expired_effects = []
        for effect in self.active_effects:
            if effect.should_tick():
                effect.tick(self)

            if effect.is_expired():
                expired_effects.append(effect)

        # Remove expired effects
        for effect in expired_effects:
            self.active_effects.remove(effect)
            self.remove_entity(effect)

    def serialize(self):
        """Serialize world state for saving."""
        return {
            "width": self.width,
            "height": self.height,
            "tiles": [[self.tiles[y][x].tile_type
                       for x in range(self.width)]
                      for y in range(self.height)],
            "entities": [e.serialize() for e in self.entities.values()
                         if not e.has_tag("effect")]  # Don't save temporary effects
        }

    def clear(self):
        """Remove all entities from the world."""
        self.entities.clear()
        self._entity_grid.clear()
        self.active_effects.clear()
        self.player = None
