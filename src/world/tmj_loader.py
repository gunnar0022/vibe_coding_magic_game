"""
TMJ (Tiled JSON) map loader.

Parses .tmj files exported from Tiled and converts them into the game's
internal tile grid + object list format.  MapLoader._process_objects()
handles entity creation identically to hand-crafted JSON maps.

Tile classification strategy (layered, highest priority wins):
  1. Per-tile collision    -> GIDs with collision=true in .tsx -> "wall"
  2. "structures" layer    -> non-zero tiles become "wall" (fallback)
  3. "trees" layer         -> non-zero tiles become "wall" (backward compat)
  4. "paths" layer         -> non-zero tiles become "dirt" (walkable paths)
  5. "foliage" layer       -> visual only (walkable, no collision)
  6. "canopy" layer        -> visual only, renders above entities
  7. collision objects      -> stamp "wall" over covered tiles
"""
import json
import math
import os
import xml.etree.ElementTree as ET

from .tile import Tile
from .tiled_map_data import TiledMapData, TiledLayerData


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def load_from_tmj(filepath, world, area_config, area_state=None):
    """
    Load a Tiled .tmj (JSON) map into the game world.

    Args:
        filepath: Path to the .tmj file.
        world: World instance to populate with tiles.
        area_config: Dict with metadata the TMJ doesn't carry:
            area_id, name, mana_pool, max_enemies
        area_state: Optional AreaState for persistent overrides.

    Returns:
        (player_spawn, objects, area_data)
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    width = data["width"]
    height = data["height"]
    tile_size = data["tilewidth"]

    # Separate layers by type
    tile_layers = []
    object_layers = []
    for layer in data.get("layers", []):
        if layer["type"] == "tilelayer":
            tile_layers.append(layer)
        elif layer["type"] == "objectgroup":
            object_layers.append(layer)

    # --- Parse per-tile collision from tilesets ---
    tmj_dir = os.path.dirname(os.path.abspath(filepath))
    collision_gids = _parse_all_tileset_collision(data, tmj_dir)

    # --- Build collision tile grid ---
    tile_grid = _build_tile_grid(tile_layers, width, height, collision_gids)
    _apply_collision_rects(tile_grid, object_layers, tile_size, width, height)

    # --- Apply to world ---
    if width != world.width or height != world.height:
        world.width = width
        world.height = height
        world.tiles = [[Tile("ground") for _ in range(width)] for _ in range(height)]

    for y in range(height):
        for x in range(width):
            world.tiles[y][x] = Tile(tile_grid[y][x])

    # --- Build visual tile data (sprites from tilesets) ---
    world.tiled_map_data = _build_tiled_map_data(
        data, filepath, tile_layers, width, height
    )

    # --- Build area_data ---
    area_data = {
        "area_id": area_config.get("area_id", "unknown"),
        "name": area_config.get("name", "Unknown Area"),
        "entry_points": dict(area_config.get("entry_points", {})),
        "max_enemies": area_config.get("max_enemies", 10),
        "mana_pool": area_config.get("mana_pool", {}),
    }

    # --- Parse objects ---
    objects = _parse_objects(object_layers, tile_size, width, height, area_data)

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
# Per-tile collision parsing from .tsx/.tsj tilesets
# ---------------------------------------------------------------------------

def _parse_all_tileset_collision(data, tmj_dir):
    """Parse collision=true properties from all referenced tilesets.

    Returns a set of global GIDs that should be treated as walls.
    Extensible: any tileset can mark tiles with collision=true.
    """
    collision_gids = set()

    for ts in data.get("tilesets", []):
        firstgid = ts["firstgid"]
        source = ts.get("source")
        if not source:
            continue

        ts_path = os.path.normpath(os.path.join(tmj_dir, source))
        if not os.path.exists(ts_path):
            continue

        if source.endswith(".tsj") or source.endswith(".json"):
            _parse_tsj_collision(ts_path, firstgid, collision_gids)
        else:
            _parse_tsx_collision(ts_path, firstgid, collision_gids)

    return collision_gids


def _parse_tsx_collision(ts_path, firstgid, collision_gids):
    """Parse collision properties from an XML .tsx tileset."""
    try:
        tree = ET.parse(ts_path)
        root = tree.getroot()
    except ET.ParseError:
        return

    for tile_el in root.findall("tile"):
        tile_id = int(tile_el.get("id", -1))
        if tile_id < 0:
            continue

        props_el = tile_el.find("properties")
        if props_el is None:
            continue

        for prop in props_el.findall("property"):
            if (prop.get("name") == "collision" and
                    prop.get("value", "").lower() == "true"):
                collision_gids.add(firstgid + tile_id)
                break


def _parse_tsj_collision(ts_path, firstgid, collision_gids):
    """Parse collision properties from a JSON .tsj tileset."""
    try:
        with open(ts_path, "r") as f:
            ts_data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    for tile_data in ts_data.get("tiles", []):
        tile_id = tile_data.get("id", -1)
        if tile_id < 0:
            continue

        for prop in tile_data.get("properties", []):
            if prop.get("name") == "collision":
                val = prop.get("value")
                if val is True or (isinstance(val, str) and val.lower() == "true"):
                    collision_gids.add(firstgid + tile_id)
                    break


# ---------------------------------------------------------------------------
# Tile grid construction
# ---------------------------------------------------------------------------

def _build_tile_grid(tile_layers, width, height, collision_gids=None):
    """Build a 2D list of tile-type strings from Tiled tile layers.

    Two-pass strategy:
    1. Layer-name fallback: "paths"->dirt, "trees"/"structures"->wall
    2. Per-tile collision: any GID in collision_gids -> wall (overrides)
    """
    collision_gids = collision_gids or set()
    grid = [["grass"] * width for _ in range(height)]

    for layer in tile_layers:
        name = layer.get("name", "").lower()
        raw_data = layer.get("data")
        if raw_data is None:
            continue

        gids = _flat_to_grid(raw_data, width, height)

        # Pass 1: layer-name-based classification (fallback)
        if name == "paths":
            for y in range(height):
                for x in range(width):
                    if gids[y][x] != 0:
                        grid[y][x] = "dirt"
        elif name in ("trees", "structures"):
            for y in range(height):
                for x in range(width):
                    if gids[y][x] != 0:
                        grid[y][x] = "wall"
        # "foliage" and "canopy" are visual-only — no collision from layer name

        # Pass 2: per-tile collision from tileset properties (overrides)
        if collision_gids:
            for y in range(height):
                for x in range(width):
                    raw_gid = gids[y][x]
                    if raw_gid != 0:
                        # Mask off flip flags before checking
                        masked = raw_gid & 0x1FFFFFFF
                        if masked in collision_gids:
                            grid[y][x] = "wall"

    return grid


def _flat_to_grid(flat_data, width, height):
    """Convert a flat list of GIDs into a 2D [y][x] grid."""
    grid = []
    for y in range(height):
        row = flat_data[y * width:(y + 1) * width]
        while len(row) < width:
            row.append(0)
        grid.append(row)
    return grid


def _apply_collision_rects(tile_grid, object_layers, tile_size, width, height):
    """Stamp wall tiles for each collision rectangle in object layers."""
    for layer in object_layers:
        for obj in layer.get("objects", []):
            obj_type = (obj.get("type") or "").lower()
            if obj_type != "collision":
                continue

            px = float(obj.get("x", 0))
            py = float(obj.get("y", 0))
            pw = float(obj.get("width", 0))
            ph = float(obj.get("height", 0))

            if pw <= 0 or ph <= 0:
                continue

            tx_start = max(0, int(math.floor(px / tile_size)))
            ty_start = max(0, int(math.floor(py / tile_size)))
            tx_end = min(width - 1, int(math.ceil((px + pw) / tile_size)) - 1)
            ty_end = min(height - 1, int(math.ceil((py + ph) / tile_size)) - 1)

            for ty in range(ty_start, ty_end + 1):
                for tx in range(tx_start, tx_end + 1):
                    tile_grid[ty][tx] = "wall"


# ---------------------------------------------------------------------------
# Visual layer data (sprite rendering)
# ---------------------------------------------------------------------------

def _build_tiled_map_data(data, tmj_filepath, tile_layers, width, height):
    """
    Build a TiledMapData with tileset atlas and per-layer GID grids.

    Tilesets in .tmj still reference external .tsx files for image paths,
    so we parse those via XML.
    """
    tmd = TiledMapData()
    tmj_dir = os.path.dirname(os.path.abspath(tmj_filepath))

    # --- Register tilesets ---
    for ts in data.get("tilesets", []):
        firstgid = ts["firstgid"]
        source = ts.get("source")

        if source:
            # External tileset (.tsx or .tsj) — parse for image info
            ts_path = os.path.normpath(os.path.join(tmj_dir, source))
            ts_dir = os.path.dirname(ts_path)

            if source.endswith(".tsj") or source.endswith(".json"):
                # JSON tileset
                with open(ts_path, "r") as f:
                    ts_data = json.load(f)
                tile_w = ts_data.get("tilewidth", 16)
                tile_h = ts_data.get("tileheight", 16)
                columns = ts_data.get("columns", 1)
                tilecount = ts_data.get("tilecount", 0)
                img_source = ts_data.get("image", "")
            else:
                # XML tileset (.tsx)
                tsx_tree = ET.parse(ts_path)
                tsx_root = tsx_tree.getroot()
                tile_w = int(tsx_root.get("tilewidth", 16))
                tile_h = int(tsx_root.get("tileheight", 16))
                columns = int(tsx_root.get("columns", 1))
                tilecount = int(tsx_root.get("tilecount", 0))
                img_el = tsx_root.find("image")
                img_source = img_el.get("source", "") if img_el is not None else ""

            if img_source:
                img_path = os.path.normpath(os.path.join(ts_dir, img_source))
                tmd.atlas.add_tileset(firstgid, img_path, tile_w, tile_h, columns, tilecount)

    # --- Build per-layer GID grids ---
    for layer in tile_layers:
        name = layer.get("name", "")
        raw_data = layer.get("data")
        if raw_data is None:
            continue

        gids = _flat_to_grid(raw_data, width, height)

        # Layer pixel offsets (in original 16px units) — scale to game coords (2x)
        offset_x = float(layer.get("offsetx", 0)) * 2.0
        offset_y = float(layer.get("offsety", 0)) * 2.0

        # Canopy layer renders above entities
        above = (name.lower() == "canopy")

        layer_data = TiledLayerData(name, width, height, gids, offset_x, offset_y,
                                    above_entities=above)
        tmd.layers.append(layer_data)

    return tmd


# ---------------------------------------------------------------------------
# Object parsing
# ---------------------------------------------------------------------------

# Tiled type names (lowercase) -> game object types
_TYPE_MAP = {
    "player_spawn": "player_spawn",
    "npc_spawn": "npc",
    "enemy_spawn": "enemy_spawner",
    "enemy_spawner": "enemy_spawner",      # alias
    "zone_transition": "zone_transition",
    "door": "door",
    "wild_rune": "rune_stone",
    "ground_item": "ground_item",
    "entry_point": "entry_point",
}


def _parse_objects(object_layers, tile_size, map_width, map_height, area_data):
    """Parse Tiled object layers into a list of game-format object dicts.

    entry_point objects are consumed here (populate area_data) and not
    returned in the objects list.
    """
    objects = []

    for layer in object_layers:
        for obj in layer.get("objects", []):
            raw_type = (obj.get("type") or "").strip()
            lower_type = raw_type.lower()

            if lower_type == "collision":
                continue

            game_type = _TYPE_MAP.get(lower_type)
            if game_type is None:
                continue

            # Pixel -> grid conversion
            px = float(obj.get("x", 0))
            py = float(obj.get("y", 0))
            grid_x = int(px / tile_size)
            grid_y = int(py / tile_size)
            grid_x = max(0, min(grid_x, map_width - 1))
            grid_y = max(0, min(grid_y, map_height - 1))

            # Read custom properties
            props = _read_properties(obj)

            # --- entry_point: populate area_data, don't create entity ---
            if game_type == "entry_point":
                entry_name = props.get("name", "default")
                area_data["entry_points"][entry_name] = {
                    "x": grid_x, "y": grid_y
                }
                continue

            # Build game object dict
            game_obj = {"type": game_type, "x": grid_x, "y": grid_y}

            # Zone transitions: expand rectangles into multiple tiles
            obj_w = float(obj.get("width", 0))
            obj_h = float(obj.get("height", 0))

            if game_type == "zone_transition" and obj_w > 0 and obj_h > 0:
                _expand_zone_transition(
                    objects, game_obj, props,
                    px, py, obj_w, obj_h,
                    tile_size, map_width, map_height
                )
                continue

            # Apply Tiled properties to the game object
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
    """Apply Tiled custom properties to a game object dict."""
    if game_type == "npc":
        game_obj["template"] = props.get("template", "village_elder")

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
        game_obj["target_area"] = props.get("target_area", "")
        game_obj["target_entry"] = props.get("target_entry", "default")
        game_obj["zone_id"] = props.get("zone_id", "zone")

    elif game_type == "door":
        game_obj["target_area"] = props.get("target_area", "")
        game_obj["target_entry"] = props.get("target_entry", "default")
        game_obj["door_id"] = props.get("door_id", "door")

    elif game_type == "rune_stone":
        game_obj["symbol"] = props.get("symbol", "earth")

    elif game_type == "ground_item":
        game_obj["item_id"] = props.get("item_id", "trinket")
        game_obj["quantity"] = int(props.get("quantity", 1))


def _read_properties(obj):
    """Read Tiled custom properties from a JSON object dict."""
    props = {}
    for prop in obj.get("properties", []):
        name = prop.get("name")
        value = prop.get("value")
        prop_type = prop.get("type", "string")
        # JSON already has typed values, but handle string-encoded numbers
        if prop_type == "bool" and isinstance(value, str):
            value = value.lower() == "true"
        elif prop_type == "int" and isinstance(value, str):
            value = int(value)
        elif prop_type == "float" and isinstance(value, str):
            value = float(value)
        props[name] = value
    return props
