"""
TMX (Tiled Map Editor) loader.

Parses .tmx XML files and converts them into the game's internal
tile grid + object list format, so that MapLoader._process_objects()
can handle entity creation identically to hand-crafted JSON maps.

Tile classification strategy (layer-based, not per-GID):
  - "background" layer  → all tiles become "grass"
  - "paths" layer        → non-zero tiles become "dirt" (walkable paths)
  - "Trees" layer        → non-zero tiles become "wall" (solid obstacles)
  - collision objects     → stamp "wall" over covered tiles
"""
import math
import os
import xml.etree.ElementTree as ET
from .tile import Tile
from .tiled_map_data import TiledMapData, TiledLayerData


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def load_from_tmx(filepath, world, area_config, area_state=None):
    """
    Load a Tiled .tmx map into the game world.

    Args:
        filepath: Path to the .tmx file.
        world: World instance to populate with tiles.
        area_config: Dict with metadata the TMX doesn't carry:
            area_id, name, mana_pool, entry_points, max_enemies
        area_state: Optional AreaState for persistent overrides.

    Returns:
        (objects, area_data) where objects is a list of game-format
        object dicts and area_data is the metadata dict.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    width = int(root.get("width"))
    height = int(root.get("height"))
    tile_size = int(root.get("tilewidth"))

    # --- Build tile grid ---
    tile_grid = _build_tile_grid(root, width, height)
    _apply_collision_rects(tile_grid, root, tile_size, width, height)

    # --- Apply to world ---
    if width != world.width or height != world.height:
        world.width = width
        world.height = height
        world.tiles = [[Tile("ground") for _ in range(width)] for _ in range(height)]

    for y in range(height):
        for x in range(width):
            world.tiles[y][x] = Tile(tile_grid[y][x])

    # --- Build visual tile data (sprites from tilesets) ---
    world.tiled_map_data = _build_tiled_map_data(root, filepath, width, height)

    # --- Build area_data (same shape as JSON loader produces) ---
    area_data = {
        "area_id": area_config.get("area_id", "unknown"),
        "name": area_config.get("name", "Unknown Area"),
        "entry_points": dict(area_config.get("entry_points", {})),
        "max_enemies": area_config.get("max_enemies", 10),
        "mana_pool": area_config.get("mana_pool", {}),
    }

    # --- Parse objects ---
    objects = _parse_objects(root, tile_size, width, height)

    # Determine default player spawn
    player_spawn = (width // 2, height // 2)
    if "default" in area_data["entry_points"]:
        ep = area_data["entry_points"]["default"]
        player_spawn = (ep["x"], ep["y"])

    # Let player_spawn object override
    for obj in objects:
        if obj["type"] == "player_spawn":
            player_spawn = (obj["x"], obj["y"])
            if "default" not in area_data["entry_points"]:
                area_data["entry_points"]["default"] = {
                    "x": obj["x"], "y": obj["y"]
                }
            break

    return player_spawn, objects, area_data


# ---------------------------------------------------------------------------
# Tile grid construction
# ---------------------------------------------------------------------------

def _build_tile_grid(root, width, height):
    """Build a 2D list of tile-type strings from TMX tile layers."""
    # Start with all grass
    grid = [["grass"] * width for _ in range(height)]

    for layer in root.findall("layer"):
        name = layer.get("name", "").lower()
        data_el = layer.find("data")
        if data_el is None or data_el.get("encoding") != "csv":
            continue

        gids = _parse_csv_data(data_el.text, width, height)

        if name == "paths":
            # Non-zero path tiles → dirt (walkable)
            for y in range(height):
                for x in range(width):
                    if gids[y][x] != 0:
                        grid[y][x] = "dirt"

        elif name == "trees":
            # Non-zero tree tiles → wall (solid)
            for y in range(height):
                for x in range(width):
                    if gids[y][x] != 0:
                        grid[y][x] = "wall"

        # "background" layer: everything stays grass (already default)

    return grid


def _parse_csv_data(csv_text, width, height):
    """Parse Tiled CSV tile data into a 2D list of integer GIDs."""
    # Strip whitespace and split by comma
    values = [int(v) for v in csv_text.replace("\n", "").replace("\r", "").split(",") if v.strip()]
    grid = []
    for y in range(height):
        row = values[y * width:(y + 1) * width]
        # Pad with 0 if row is short (shouldn't happen but safety)
        while len(row) < width:
            row.append(0)
        grid.append(row)
    return grid


# ---------------------------------------------------------------------------
# Visual layer data (sprite rendering)
# ---------------------------------------------------------------------------

def _build_tiled_map_data(root, tmx_filepath, width, height):
    """
    Build a TiledMapData object with the atlas of tileset sprites
    and per-layer GID grids, so the renderer can blit actual pixel art.

    Args:
        root: ElementTree root of the TMX file.
        tmx_filepath: Path to the .tmx file (for resolving relative paths).
        width, height: Map dimensions in tiles.

    Returns:
        TiledMapData instance.
    """
    tmd = TiledMapData()
    tmx_dir = os.path.dirname(os.path.abspath(tmx_filepath))

    # --- Register tilesets ---
    for ts_el in root.findall("tileset"):
        firstgid = int(ts_el.get("firstgid"))
        tsx_source = ts_el.get("source")

        if tsx_source:
            # External tileset (.tsx) — parse it for image info
            tsx_path = os.path.normpath(os.path.join(tmx_dir, tsx_source))
            tsx_dir = os.path.dirname(tsx_path)

            tsx_tree = ET.parse(tsx_path)
            tsx_root = tsx_tree.getroot()

            tile_w = int(tsx_root.get("tilewidth", 16))
            tile_h = int(tsx_root.get("tileheight", 16))
            columns = int(tsx_root.get("columns", 1))
            tilecount = int(tsx_root.get("tilecount", 0))

            img_el = tsx_root.find("image")
            if img_el is not None:
                img_source = img_el.get("source")
                img_path = os.path.normpath(os.path.join(tsx_dir, img_source))
                tmd.atlas.add_tileset(firstgid, img_path, tile_w, tile_h, columns, tilecount)
        else:
            # Embedded tileset (inline in TMX) — less common
            tile_w = int(ts_el.get("tilewidth", 16))
            tile_h = int(ts_el.get("tileheight", 16))
            columns = int(ts_el.get("columns", 1))
            tilecount = int(ts_el.get("tilecount", 0))

            img_el = ts_el.find("image")
            if img_el is not None:
                img_source = img_el.get("source")
                img_path = os.path.normpath(os.path.join(tmx_dir, img_source))
                tmd.atlas.add_tileset(firstgid, img_path, tile_w, tile_h, columns, tilecount)

    # --- Build per-layer GID grids ---
    for layer in root.findall("layer"):
        name = layer.get("name", "")
        data_el = layer.find("data")
        if data_el is None or data_el.get("encoding") != "csv":
            continue

        gids = _parse_csv_data(data_el.text, width, height)

        # Layer pixel offsets (in original 16px units) — scale to game coords (2x)
        offset_x = float(layer.get("offsetx", 0)) * 2.0
        offset_y = float(layer.get("offsety", 0)) * 2.0

        layer_data = TiledLayerData(name, width, height, gids, offset_x, offset_y)
        tmd.layers.append(layer_data)

    return tmd


def _apply_collision_rects(tile_grid, root, tile_size, width, height):
    """Stamp wall tiles for each collision rectangle in object layers."""
    for objgroup in root.findall("objectgroup"):
        for obj in objgroup.findall("object"):
            obj_type = (obj.get("type") or "").lower()
            if obj_type != "collision":
                continue

            # Pixel-based rectangle
            px = float(obj.get("x", 0))
            py = float(obj.get("y", 0))
            pw = float(obj.get("width", 0))
            ph = float(obj.get("height", 0))

            if pw <= 0 or ph <= 0:
                continue

            # Convert to tile range (inclusive)
            tx_start = max(0, int(math.floor(px / tile_size)))
            ty_start = max(0, int(math.floor(py / tile_size)))
            tx_end = min(width - 1, int(math.ceil((px + pw) / tile_size)) - 1)
            ty_end = min(height - 1, int(math.ceil((py + ph) / tile_size)) - 1)

            for ty in range(ty_start, ty_end + 1):
                for tx in range(tx_start, tx_end + 1):
                    tile_grid[ty][tx] = "wall"


# ---------------------------------------------------------------------------
# Object parsing
# ---------------------------------------------------------------------------

# Map TMX object types (case-insensitive) → game object types
_TYPE_MAP = {
    "player_spawn": "player_spawn",
    "npc_spawn": "npc",
    "enemy_spawn": "enemy_spawner",
    "zone_transition": "zone_transition",
    "door": "door",
    "wild_rune": "rune_stone",
}

# Default properties for object types that need them.
# These fill in values that the TMX doesn't specify but the game expects.
_OBJECT_DEFAULTS = {
    "npc": {
        "template": "village_elder",
    },
    "door": {
        "target_area": "elder_house",
        "target_entry": "default",
        "door_id": "elder_house_door",
    },
    "zone_transition": {
        "target_entry": "from_village",
        "zone_id": "zone",
    },
}


def _parse_objects(root, tile_size, map_width, map_height):
    """Parse TMX object layers into a list of game-format object dicts."""
    objects = []

    for objgroup in root.findall("objectgroup"):
        for obj in objgroup.findall("object"):
            raw_type = (obj.get("type") or "").strip()
            lower_type = raw_type.lower()

            # Skip collision rects (handled as tile stamps)
            if lower_type == "collision":
                continue

            game_type = _TYPE_MAP.get(lower_type)
            if game_type is None:
                # Unknown type — skip silently
                continue

            # Pixel → grid conversion
            px = float(obj.get("x", 0))
            py = float(obj.get("y", 0))
            grid_x = int(px / tile_size)
            grid_y = int(py / tile_size)

            # Clamp to map bounds
            grid_x = max(0, min(grid_x, map_width - 1))
            grid_y = max(0, min(grid_y, map_height - 1))

            # Read custom properties from TMX
            props = _read_properties(obj)

            # Build the game object dict
            game_obj = {"type": game_type, "x": grid_x, "y": grid_y}

            # Apply defaults first, then TMX properties override
            if game_type in _OBJECT_DEFAULTS:
                for key, val in _OBJECT_DEFAULTS[game_type].items():
                    game_obj[key] = val

            # Zone transitions: expand rectangles into multiple tiles
            obj_w = float(obj.get("width", 0))
            obj_h = float(obj.get("height", 0))

            if game_type == "zone_transition" and obj_w > 0 and obj_h > 0:
                _expand_zone_transition(objects, game_obj, props,
                                        px, py, obj_w, obj_h,
                                        tile_size, map_width, map_height)
                continue

            # Apply TMX properties to the game object
            _apply_properties(game_obj, game_type, props)

            objects.append(game_obj)

    return objects


def _expand_zone_transition(objects, base_obj, props, px, py, pw, ph,
                            tile_size, map_width, map_height):
    """Expand a rectangular zone_transition into one object per covered tile."""
    tx_start = max(0, int(math.floor(px / tile_size)))
    ty_start = max(0, int(math.floor(py / tile_size)))
    tx_end = min(map_width - 1, int(math.ceil((px + pw) / tile_size)) - 1)
    ty_end = min(map_height - 1, int(math.ceil((py + ph) / tile_size)) - 1)

    for ty in range(ty_start, ty_end + 1):
        for tx in range(tx_start, tx_end + 1):
            zone_obj = dict(base_obj)
            zone_obj["x"] = tx
            zone_obj["y"] = ty
            _apply_properties(zone_obj, "zone_transition", props)
            objects.append(zone_obj)


def _apply_properties(game_obj, game_type, props):
    """Apply TMX custom properties to a game object dict."""
    if game_type == "npc":
        game_obj["template"] = props.get("template", game_obj.get("template", "village_elder"))

    elif game_type == "enemy_spawner":
        enemy_type = props.get("enemy_type", "slime")
        chance_str = props.get("spawn_chances", props.get("spawn_chance", "100"))
        try:
            chance = float(chance_str) / 100.0 if float(chance_str) > 1.0 else float(chance_str)
        except (ValueError, TypeError):
            chance = 1.0

        game_obj["spawn_chance"] = chance
        game_obj["respawn_time"] = float(props.get("respawn_time", 90.0))
        game_obj["enemy_types"] = [{"type": enemy_type, "weight": 100}]

    elif game_type == "zone_transition":
        if "target_area" in props:
            game_obj["target_area"] = props["target_area"]
        if "target_entry" in props:
            game_obj["target_entry"] = props["target_entry"]

    elif game_type == "door":
        if "target_area" in props:
            game_obj["target_area"] = props["target_area"]
        if "target_entry" in props:
            game_obj["target_entry"] = props["target_entry"]
        if "door_id" in props:
            game_obj["door_id"] = props["door_id"]

    elif game_type == "rune_stone":
        game_obj["symbol"] = props.get("symbol", "earth")


def _read_properties(obj_element):
    """Read Tiled custom properties from an object element."""
    props = {}
    properties_el = obj_element.find("properties")
    if properties_el is not None:
        for prop in properties_el.findall("property"):
            name = prop.get("name")
            value = prop.get("value")
            prop_type = prop.get("type", "string")
            if prop_type == "bool":
                value = value.lower() == "true"
            elif prop_type == "int":
                value = int(value)
            elif prop_type == "float":
                value = float(value)
            props[name] = value
    return props
