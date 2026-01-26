"""
Map loading utilities.
"""
import json
import os
from .tile import Tile
from ..entities import WorldObject, Player, create_rune_stone


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

        return player_spawn

    @staticmethod
    def create_test_map(world):
        """Create a simple test map for development."""
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
#.......@....~~~~~................................#
#............~~~~~................................#
#.............~~~~................................#
#.................................................#
#..........T......................................#
#.................................................#
#.....R...........................................#
#...........................T.....................#
#.................................................#
#.....T.....R..........T..........R...............#
#.................................................#
#............B.........B..........................#
#.................................................#
#..........................R......................#
#.....T...........................................#
#.................................................#
#.................................................#
#...........T.....................................#
#.................................................#
##################################################
"""
        return MapLoader.load_from_text(test_map, world)
