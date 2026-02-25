"""
Map loading utilities.

Supports two source formats:
  - .json  — hand-crafted game JSON (tile type strings + object arrays)
  - .tmj   — Tiled Map Editor JSON (parsed via tmj_loader)
"""
import json
import os
from .tile import Tile
from .area_state_manager import AreaStateManager
from ..entities import WorldObject, Player, create_rune_stone, create_enemy, create_npc_from_template
from ..entities.world_object import Door, ZoneTransition
from ..entities.ground_item import GroundItem
from ..items.item_instance import ItemInstance


# Registry of area file paths (supports .json and .tmj)
AREA_REGISTRY = {
    "test_map": "data/maps/test_map.json",
    "forest": "data/maps/test_map.json",  # Alias for forest
    "home_village": "Tiled_Workspace/south_village_central.tmj",
    "south_village": "Tiled_Workspace/south_village_south.tmj",
    "north_village": "Tiled_Workspace/south_village_north.tmj",
    "elder_house": "data/maps/elder_house_interior.json",
}

# Metadata that Tiled map files don't carry (area_id, name, mana_pool, etc.).
# Entry points defined via entry_point objects in Tiled are auto-populated
# by the loader, but these serve as fallbacks / non-Tiled metadata.
TILED_AREA_CONFIGS = {
    "home_village": {
        "area_id": "home_village",
        "name": "South Village",
        "mana_pool": {"max_capacity": 80.0, "regen_rate": 1.5},
        "max_enemies": 4,
        "entry_points": {},
    },
    "south_village": {
        "area_id": "south_village",
        "name": "South Village — Outskirts",
        "mana_pool": {"max_capacity": 60.0, "regen_rate": 1.0},
        "max_enemies": 3,
        "entry_points": {},
    },
    "north_village": {
        "area_id": "north_village",
        "name": "South Village — North District",
        "mana_pool": {"max_capacity": 70.0, "regen_rate": 1.2},
        "max_enemies": 2,
        "entry_points": {},
    },
}


class MapLoader:
    """Loads maps from JSON or Tiled JSON (.tmj) files."""

    @staticmethod
    def load_area(area_id, world, area_state=None):
        """
        Load an area by its ID from the area registry.
        Returns (player_spawn, area_data) tuple.
        area_data contains entry_points and other metadata.

        Args:
            area_id: Area identifier from AREA_REGISTRY
            world: World instance to populate
            area_state: Optional AreaState for persistent overrides
        """
        if area_id not in AREA_REGISTRY:
            raise ValueError(f"Unknown area: {area_id}")

        filepath = AREA_REGISTRY[area_id]

        if filepath.endswith(".tmj"):
            return MapLoader._load_tiled_area(area_id, filepath, world, area_state)
        else:
            return MapLoader.load_from_json(filepath, world, return_metadata=True, area_state=area_state)

    @staticmethod
    def _load_tiled_area(area_id, filepath, world, area_state=None):
        """Load a Tiled JSON map via tmj_loader, then process objects through shared pipeline."""
        from .tmj_loader import load_from_tmj

        area_config = TILED_AREA_CONFIGS.get(area_id, {"area_id": area_id, "name": area_id})
        player_spawn, objects, area_data = load_from_tmj(filepath, world, area_config, area_state)

        # Process objects through the shared pipeline (same as JSON maps)
        player_spawn = MapLoader._process_objects(objects, world, area_data, area_state, player_spawn)

        # Restore player-dropped items from persistent state
        MapLoader._restore_dropped_items(world, area_state)

        return player_spawn, area_data

    @staticmethod
    def load_from_json(filepath, world, return_metadata=False, area_state=None):
        """Load a map from a JSON file, applying persistent state overrides."""
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
            "max_enemies": data.get("max_enemies", 10),
            "mana_pool": data.get("mana_pool", {}),
        }

        # Default player spawn
        player_spawn = (width // 2, height // 2)

        # Check for default entry point
        if "default" in area_data["entry_points"]:
            ep = area_data["entry_points"]["default"]
            player_spawn = (ep["x"], ep["y"])

        # Process objects
        if 'objects' in data:
            player_spawn = MapLoader._process_objects(
                data['objects'], world, area_data, area_state, player_spawn
            )

        # Restore player-dropped items
        MapLoader._restore_dropped_items(world, area_state)

        if return_metadata:
            return player_spawn, area_data
        return player_spawn

    @staticmethod
    def _process_objects(objects, world, area_data, area_state, player_spawn):
        """
        Process a list of game-format object dicts, creating entities in the world.

        Shared by both JSON and TMX loading paths. Each object dict has at minimum
        a 'type', 'x', and 'y' field.

        Returns the (possibly updated) player_spawn tuple.
        """
        for obj_data in objects:
            obj_type = obj_data['type']

            if obj_type == 'player_spawn':
                player_spawn = (obj_data['x'], obj_data['y'])
                if "default" not in area_data["entry_points"]:
                    area_data["entry_points"]["default"] = {
                        "x": obj_data['x'],
                        "y": obj_data['y']
                    }

            elif obj_type == 'door':
                door = Door(
                    x=obj_data['x'],
                    y=obj_data['y'],
                    target_area=obj_data.get('target_area', ''),
                    target_entry=obj_data.get('target_entry', 'default'),
                    door_id=obj_data.get('door_id', 'door')
                )
                world.add_entity(door)

            elif obj_type == 'zone_transition':
                zone = ZoneTransition(
                    x=obj_data['x'],
                    y=obj_data['y'],
                    target_area=obj_data.get('target_area', ''),
                    target_entry=obj_data.get('target_entry', 'default'),
                    zone_id=obj_data.get('zone_id', 'zone')
                )
                world.add_entity(zone)

            elif obj_type == 'entry_point':
                entry_name = obj_data.get('name', 'default')
                area_data["entry_points"][entry_name] = {
                    "x": obj_data['x'],
                    "y": obj_data['y']
                }

            elif obj_type == 'npc':
                template_id = obj_data.get('template', 'generic_npc')
                npc = create_npc_from_template(
                    template_id,
                    obj_data['x'],
                    obj_data['y']
                )
                npc.set_world(world)
                world.add_entity(npc)

            elif obj_type == 'ground_item':
                item_id = obj_data.get('item_id', 'trinket')
                quantity = obj_data.get('quantity', 1)
                obj_x = obj_data['x']
                obj_y = obj_data['y']

                # Generate stable ID for this map-placed item
                map_obj_id = AreaStateManager.make_object_id('ground_item', obj_x, obj_y)

                # Skip if this item was picked up (persistent state)
                if area_state and area_state.is_item_removed(map_obj_id):
                    continue

                item_inst = ItemInstance(item_id, quantity)
                ground_item = GroundItem(obj_x, obj_y, item_inst, map_object_id=map_obj_id)
                world.add_entity(ground_item)

            elif obj_type == 'rune_stone':
                symbol = obj_data.get('symbol', 'earth')
                obj_x = obj_data['x']
                obj_y = obj_data['y']
                rune = create_rune_stone(f"{symbol}_stone", obj_x, obj_y)

                # Apply persistent activation state
                rune_obj_id = AreaStateManager.make_object_id('rune_stone', obj_x, obj_y)
                rune.map_object_id = rune_obj_id
                if area_state:
                    rune_state = area_state.get_rune_stone_state(rune_obj_id)
                    if rune_state and rune_state.get("is_activated"):
                        rune.is_activated = True
                        rune._update_examine_text()

                world.add_entity(rune)

            elif obj_type == 'enemy_spawner':
                # Handled separately after loading - store in area_data
                if "spawner_defs" not in area_data:
                    area_data["spawner_defs"] = []
                area_data["spawner_defs"].append(obj_data)

            elif obj_type == 'enemy':
                # Legacy static enemy placement (kept for backwards compatibility)
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

        return player_spawn

    @staticmethod
    def _restore_dropped_items(world, area_state):
        """Restore player-dropped items from persistent state."""
        if area_state:
            for drop_data in area_state.dropped_items:
                item_id = drop_data.get("item_id")
                quantity = drop_data.get("quantity", 1)
                dx = drop_data.get("x", 0)
                dy = drop_data.get("y", 0)
                if item_id:
                    item_inst = ItemInstance(item_id, quantity)
                    ground_item = GroundItem(dx, dy, item_inst, map_object_id=None)
                    world.add_entity(ground_item)
