"""
Map loading utilities.
"""
import json
import os
from .tile import Tile
from ..entities import WorldObject, Player, create_rune_stone, create_enemy
from ..entities.ground_item import GroundItem
from ..items.item_instance import ItemInstance


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
    def load_from_json(filepath, world):
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

        # Load objects
        player_spawn = (width // 2, height // 2)
        if 'objects' in data:
            for obj_data in data['objects']:
                if obj_data['type'] == 'player_spawn':
                    player_spawn = (obj_data['x'], obj_data['y'])
                else:
                    obj = WorldObject(
                        obj_data['x'],
                        obj_data['y'],
                        obj_data['type']
                    )
                    world.add_entity(obj)

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
