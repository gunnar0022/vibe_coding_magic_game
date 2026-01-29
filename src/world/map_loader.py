"""
Map loading utilities.
"""
import json
import os
from .tile import Tile
from ..entities import WorldObject, Player, create_rune_stone, create_enemy, create_npc_from_template
from ..entities.world_object import Door, ZoneTransition
from ..entities.ground_item import GroundItem
from ..items.item_instance import ItemInstance


# Registry of area file paths
AREA_REGISTRY = {
    "test_map": "data/maps/test_map.json",
    "forest": "data/maps/test_map.json",  # Alias for forest
    "home_village": "data/maps/home_village.json",
    "elder_house": "data/maps/elder_house_interior.json",
}


class MapLoader:
    """Loads maps from JSON files."""

    @staticmethod
    def load_area(area_id, world):
        """
        Load an area by its ID from the area registry.
        Returns (player_spawn, area_data) tuple.
        area_data contains entry_points and other metadata.
        """
        if area_id not in AREA_REGISTRY:
            raise ValueError(f"Unknown area: {area_id}")

        filepath = AREA_REGISTRY[area_id]
        return MapLoader.load_from_json(filepath, world, return_metadata=True)

    @staticmethod
    def load_from_json(filepath, world, return_metadata=False):
        """Load a map from a JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        width = data.get('width', world.width)
        height = data.get('height', world.height)

        # Resize world if needed
        if width != world.width or height != world.height:
            world.width = width
            world.height = height
            world.tiles = [[Tile("ground") for _ in range(width)] for _ in range(height)]

        # Load tiles
        if 'tiles' in data:
            for y, row in enumerate(data['tiles']):
                for x, tile_type in enumerate(row):
                    if x < width and y < height:
                        world.tiles[y][x] = Tile(tile_type)

        # Extract metadata
        area_data = {
            "area_id": data.get("area_id", "unknown"),
            "name": data.get("name", "Unknown Area"),
            "entry_points": data.get("entry_points", {}),
        }

        # Default player spawn
        player_spawn = (width // 2, height // 2)

        # Check for default entry point
        if "default" in area_data["entry_points"]:
            ep = area_data["entry_points"]["default"]
            player_spawn = (ep["x"], ep["y"])

        # Load objects
        if 'objects' in data:
            for obj_data in data['objects']:
                obj_type = obj_data['type']

                if obj_type == 'player_spawn':
                    player_spawn = (obj_data['x'], obj_data['y'])
                    # Also register as default entry point if not already set
                    if "default" not in area_data["entry_points"]:
                        area_data["entry_points"]["default"] = {
                            "x": obj_data['x'],
                            "y": obj_data['y']
                        }

                elif obj_type == 'door':
                    # Create door with transition data
                    door = Door(
                        x=obj_data['x'],
                        y=obj_data['y'],
                        target_area=obj_data.get('target_area', ''),
                        target_entry=obj_data.get('target_entry', 'default'),
                        door_id=obj_data.get('door_id', 'door')
                    )
                    world.add_entity(door)

                elif obj_type == 'zone_transition':
                    # Create auto-transition zone (triggers when player enters)
                    zone = ZoneTransition(
                        x=obj_data['x'],
                        y=obj_data['y'],
                        target_area=obj_data.get('target_area', ''),
                        target_entry=obj_data.get('target_entry', 'default'),
                        zone_id=obj_data.get('zone_id', 'zone')
                    )
                    world.add_entity(zone)

                elif obj_type == 'entry_point':
                    # Register named entry point (not an object in the world)
                    entry_name = obj_data.get('name', 'default')
                    area_data["entry_points"][entry_name] = {
                        "x": obj_data['x'],
                        "y": obj_data['y']
                    }

                elif obj_type == 'npc':
                    # Create NPC from template
                    template_id = obj_data.get('template', 'generic_npc')
                    npc = create_npc_from_template(
                        template_id,
                        obj_data['x'],
                        obj_data['y']
                    )
                    # Set world reference for movement
                    npc.set_world(world)
                    world.add_entity(npc)

                elif obj_type == 'ground_item':
                    # Create a ground item from item definition
                    item_id = obj_data.get('item_id', 'trinket')
                    quantity = obj_data.get('quantity', 1)
                    item_inst = ItemInstance(item_id, quantity)
                    ground_item = GroundItem(obj_data['x'], obj_data['y'], item_inst)
                    world.add_entity(ground_item)

                elif obj_type == 'rune_stone':
                    # Create a rune stone that teaches a symbol
                    symbol = obj_data.get('symbol', 'earth')
                    rune = create_rune_stone(f"{symbol}_stone", obj_data['x'], obj_data['y'])
                    world.add_entity(rune)

                elif obj_type == 'enemy':
                    # Create an enemy
                    enemy_type = obj_data.get('enemy_type', 'slime')
                    patrol_points = obj_data.get('patrol_points', None)
                    if patrol_points:
                        enemy = create_enemy(enemy_type, obj_data['x'], obj_data['y'], patrol_points=patrol_points)
                    else:
                        enemy = create_enemy(enemy_type, obj_data['x'], obj_data['y'])
                    world.add_entity(enemy)

                else:
                    obj = WorldObject(
                        obj_data['x'],
                        obj_data['y'],
                        obj_type
                    )
                    world.add_entity(obj)

        if return_metadata:
            return player_spawn, area_data
        return player_spawn
