"""
Map loading utilities.
"""
import json
import os
from .tile import Tile
from ..entities import WorldObject, Player, create_rune_stone, create_enemy, create_npc_from_template
from ..entities.world_object import Door
from ..entities.ground_item import GroundItem
from ..items.item_instance import ItemInstance


# Registry of area file paths
AREA_REGISTRY = {
    "test_map": "data/maps/test_map.json",
    "home_village": "data/maps/home_village.json",
    "elder_house": "data/maps/elder_house_interior.json",
}


class MapLoader:
    """Loads maps from JSON files and creates test maps."""

    # Character mappings for simple text-based maps
    CHAR_TO_TILE = {
        '.': 'ground',
        ',': 'grass',
        '#': 'wall',
        '~': 'water_shallow',
        'W': 'water_deep',
        'd': 'dirt',
        's': 'stone',
        ' ': 'void',
    }

    CHAR_TO_OBJECT = {
        'T': 'tree',
        'R': 'rock',
        'B': 'bush',
        '@': 'player_spawn',
        '*': 'rune_stone_earth',  # Earth rune stone
        '!': 'rune_stone_sword',  # Sword rune stone
        '%': 'rune_stone_axe',    # Axe rune stone
        '^': 'rune_stone_great',  # Great modifier rune stone
        '&': 'rune_stone_bow',    # Bow rune stone
        '1': 'rune_stone_dark',     # Darkness rune stone
        '2': 'rune_stone_electric', # Electric rune stone
        '3': 'rune_stone_thunder',  # Thunder rune stone
        '4': 'rune_stone_blaze',    # Blaze rune stone
        '5': 'rune_stone_cut',      # Cut rune stone
        '6': 'rune_stone_stone',    # Stone rune stone
        'F': 'fence',
        'C': 'crate',
        'w': 'well',
        't': 'table',
        'c': 'chair',
        's': 'sign',
    }

    # Enemy spawn markers
    CHAR_TO_ENEMY = {
        'S': 'stationary',        # Legacy stationary enemy (now slime)
        'P': 'patrolling',        # Legacy patrolling enemy (now slime patrol)
        'q': 'slime',             # Slime - slow melee chaser
        'A': 'skeleton_archer',   # Skeleton Archer - ranged kiter
        'E': 'ember_sprite',      # Ember Sprite - fire elemental
        'G': 'stone_guardian',    # Stone Guardian - heavy tank
    }

    # Item spawn markers
    CHAR_TO_ITEM = {
        'i': 'wooden_spear',
    }

    # Patrol route definitions (char -> list of relative patrol offsets)
    # P followed by direction indicates patrol direction
    PATROL_ROUTES = {
        'P': [(0, 0), (4, 0)],     # Default: patrol 4 tiles right
        'H': [(0, 0), (0, 4)],     # Horizontal: patrol 4 tiles down
    }

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

    @staticmethod
    def load_from_text(text_map, world):
        """
        Load a map from a simple text representation.
        Returns player spawn position.
        """
        lines = text_map.strip().split('\n')
        height = len(lines)
        width = max(len(line) for line in lines)

        # Resize world
        world.width = width
        world.height = height
        world.tiles = [[Tile("ground") for _ in range(width)] for _ in range(height)]

        player_spawn = (width // 2, height // 2)

        for y, line in enumerate(lines):
            for x, char in enumerate(line):
                # Check for tile
                if char in MapLoader.CHAR_TO_TILE:
                    world.tiles[y][x] = Tile(MapLoader.CHAR_TO_TILE[char])

                # Check for object
                elif char in MapLoader.CHAR_TO_OBJECT:
                    obj_type = MapLoader.CHAR_TO_OBJECT[char]
                    if obj_type == 'player_spawn':
                        player_spawn = (x, y)
                        world.tiles[y][x] = Tile('ground')
                    elif obj_type.startswith('rune_stone_'):
                        # Extract the symbol from the object type (e.g., rune_stone_earth -> earth_stone)
                        symbol = obj_type.split('_', 2)[2]  # Gets 'earth' from 'rune_stone_earth'
                        world.tiles[y][x] = Tile('ground')
                        rune = create_rune_stone(f"{symbol}_stone", x, y)
                        world.add_entity(rune)
                    else:
                        world.tiles[y][x] = Tile('ground')  # Object sits on ground
                        obj = WorldObject(x, y, obj_type)
                        world.add_entity(obj)

                # Check for enemy
                elif char in MapLoader.CHAR_TO_ENEMY:
                    enemy_type = MapLoader.CHAR_TO_ENEMY[char]
                    world.tiles[y][x] = Tile('ground')  # Enemy spawns on ground

                    if enemy_type == 'patrolling':
                        # Get patrol route from PATROL_ROUTES
                        route = MapLoader.PATROL_ROUTES.get(char, [(0, 0), (4, 0)])
                        # Convert relative route to absolute positions
                        patrol_points = [(x + dx, y + dy) for dx, dy in route]
                        enemy = create_enemy(enemy_type, x, y, patrol_points=patrol_points)
                    else:
                        enemy = create_enemy(enemy_type, x, y)

                    world.add_entity(enemy)

                # Check for ground item
                elif char in MapLoader.CHAR_TO_ITEM:
                    item_def_id = MapLoader.CHAR_TO_ITEM[char]
                    world.tiles[y][x] = Tile('ground')
                    item_inst = ItemInstance(item_def_id)
                    ground_item = GroundItem(x, y, item_inst)
                    world.add_entity(ground_item)


        return player_spawn

    @staticmethod
    def create_test_map(world):
        """Create a simple test map for development."""
        # Map legend:
        # @ = player spawn
        # T = tree, R = rock, B = bush
        # * = earth rune stone, ! = sword rune, % = axe rune, ^ = great rune
        # & = bow rune, 1 = dark, 2 = electric, 3 = thunder, 4 = blaze
        # 5 = cut, 6 = stone
        # S = legacy stationary, P = legacy patrolling
        # q = slime, A = skeleton archer, E = ember sprite, G = stone guardian
        # ~ = water
        test_map = """
##################################################
#................................................#
#.....T.........T.................................#
#...........R.....................................#
#.....T.............................T.............#
#.................................................#
#..........T......................................#
#.................................................#
#.............~~~~................................#
#............~~~~~.......R.....................*..#
#.......@..i.~~~~~...!............................#
#............~~~~~...%............................#
#.............~~~~...^..&.........................#
#.................................................#
#..........T......................................#
#.................................................#
#.....R.............q.............................#
#...........................T.....................#
#.............................A...................#
#.....T.....R..........T..........R...............#
#...................................q.............#
#............B.........B..........................#
#.................................................#
#..1..........2..........3.......R................#
#.....T...........E...............................#
#..4..........5..........6........................#
#.................................................#
#...........T...........G.........................#
#.................................................#
##################################################
"""
        return MapLoader.load_from_text(test_map, world)
