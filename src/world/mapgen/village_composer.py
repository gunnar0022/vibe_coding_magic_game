"""VillageComposer — generates complete village maps (v2).

Landscape-first pipeline: generate noise-driven terrain, carve organic
paths through it, slot buildings along the paths, then flood-fill trees
everywhere else.  The village feels carved out of a forest rather than
stamped onto a grid.

Pipeline order
--------------
1. Noise field        -> continuous terrain variation across map
2. Anchor grid        -> 12 fixed edge slots, connections assigned to slots
3. Path network       -> Chaikin-smoothed curves between anchors, variable width
4. Buildings          -> placed along paths, doors facing path, approach walkways
5. Foliage            -> noise-driven, carved where paths/buildings exist
6. Tree fill          -> flood the map, remove where paths/buildings/connections are
7. Connections        -> fixed 3x2/2x3 transitions with flanking obstacles
8. Edge walls         -> consolidated rectangles (run-length encoded)
9. Game objects       -> NPCs, spawners, items from config

Usage
-----
>>> composer = VillageComposer(seed=42)
>>> composer.generate({
...     "width": 55, "height": 45,
...     "buildings": [
...         {"prefab": "house_small", "x": 18, "y": 15},
...     ],
...     "connections": [
...         {"anchor": "south_mid", "target": "home_village", "entry": "from_north"},
...     ],
... })
>>> composer.save("Tiled_Workspace/my_village.tmj")
"""

from __future__ import annotations

from typing import Any

from .rng import SeededRNG
from .tileset_defs import TilesetRegistry
from .auto_tiler import AutoTiler
from .map_canvas import MapCanvas
from .prefabs import PrefabLibrary
from .terrain_gen import TerrainGenerator
from .path_gen import PathGenerator
from .vegetation_gen import VegetationGenerator
from .structure_gen import StructureGenerator
from .connection_gen import (
    ConnectionGenerator, anchor_position, anchor_edge,
)


class VillageComposer:
    """High-level composer that generates a complete village map (v2)."""

    def __init__(self, seed: int | None = None):
        self._rng = SeededRNG(seed)
        self._registry = TilesetRegistry()
        self._canvas: MapCanvas | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, config: dict[str, Any]) -> dict:
        """Generate a village map from a configuration dict.

        Returns the TMJ dict (also accessible via :meth:`save`).

        Config keys
        -----------
        width, height      : map dimensions in tiles (default 55x45).
        noise_scale        : terrain noise wavelength (default 12.0).
        noise_octaves      : terrain noise octaves (default 3).
        foliage_threshold  : noise cutoff for foliage 0-1 (default 0.45).
        buildings          : list of building dicts.
        connections        : list of connection dicts with "anchor" key.
        npcs               : list of NPC dicts.
        enemy_spawners     : list of enemy spawner dicts.
        rune_stones        : list of rune stone dicts.
        ground_items       : list of ground item dicts.
        spawn              : {"x": int, "y": int} player spawn (default center).

        Building dict: {"prefab", "x", "y", "door_target"?, "door_entry"?, "id"?}
        Connection dict: {"anchor", "target", "entry"?}
        NPC dict: {"x", "y", "template", "wander"?}
        Enemy dict: {"x", "y", "type"?, "spawn_chance"?, "respawn_time"?}
        Rune dict: {"x", "y", "symbol"}
        Item dict: {"x", "y", "item_id", "quantity"?}
        """
        width = config.get("width", 55)
        height = config.get("height", 45)
        noise_scale = config.get("noise_scale", 12.0)
        noise_octaves = config.get("noise_octaves", 3)
        foliage_threshold = config.get("foliage_threshold", 0.45)

        # ── Initialise core components ────────────────────────────────
        canvas = MapCanvas(width, height, self._registry)
        auto = AutoTiler(self._registry, self._rng)
        prefabs = PrefabLibrary(self._registry)

        canvas.add_tile_layer("background")
        canvas.add_tile_layer("paths", offset_x=2.18182, offset_y=0.96970)
        canvas.add_tile_layer("foliage")
        canvas.add_tile_layer("structures")
        canvas.add_tile_layer("canopy")

        # ── Phase 1: Noise field ─────────────────────────────────────
        noise = self._rng.noise_field(width, height, noise_scale, noise_octaves)

        # ── Phase 2: Base terrain ────────────────────────────────────
        terrain = TerrainGenerator(canvas, auto, self._rng)
        terrain.fill_grass()

        # ── Phase 3: Path network ────────────────────────────────────
        path_gen = PathGenerator(canvas, auto, self._rng)

        # Collect anchor positions for active connections
        connections = config.get("connections", [])
        anchor_positions: dict[str, tuple[int, int]] = {}
        for conn in connections:
            anchor_name = conn["anchor"]
            ax, ay = anchor_position(anchor_name, width, height)
            anchor_positions[anchor_name] = (ax, ay)

        # Build the path network: connect anchors through the map center
        cx, cy = width // 2, height // 2
        self._build_path_network(
            path_gen, anchor_positions, cx, cy, width, height, noise
        )

        # ── Phase 4: Place buildings ─────────────────────────────────
        struct = StructureGenerator(canvas, prefabs, self._rng)
        for bldg in config.get("buildings", []):
            struct.place_building(
                bldg["prefab"], bldg["x"], bldg["y"],
                door_target_area=bldg.get("door_target", ""),
                door_target_entry=bldg.get("door_entry", "default"),
                building_id=bldg.get("id", ""),
            )

        # Connect doors to nearest path
        struct.connect_doors_to_paths(path_gen)

        # Flatten paths horizontally in front of buildings
        self._flatten_paths_at_buildings(path_gen, struct)

        # Finalize path auto-tiling (after approach paths are drawn)
        path_gen.finalize()

        # ── Phase 5: Foliage ─────────────────────────────────────────
        path_mask = path_gen.get_mask()
        building_zones = struct.get_footprints(padding=3)

        # Pre-compute transition zones (connections haven't been placed yet,
        # but we know where they'll go from anchor positions)
        transition_zones = self._precompute_transition_zones(
            connections, width, height
        )

        terrain.generate_foliage_from_noise(
            noise,
            threshold=foliage_threshold,
            path_mask=path_mask,
            building_zones=building_zones,
            transition_zones=transition_zones,
            border_margin=1,
        )

        # ── Phase 6: Tree fill ───────────────────────────────────────
        veg = VegetationGenerator(canvas, prefabs, self._rng)
        veg.fill_trees(
            path_mask=path_mask,
            building_zones=building_zones,
            transition_zones=transition_zones,
            noise_field=noise,
            path_padding=2,
            building_padding=2,
            transition_padding=3,
            density_threshold=0.3,
        )

        # ── Phase 7: Connections ─────────────────────────────────────
        conn_gen = ConnectionGenerator(canvas)

        for conn in connections:
            conn_gen.add_anchor_connection(
                anchor=conn["anchor"],
                target_area=conn["target"],
                target_entry=conn.get("entry", "default"),
            )

        # ── Phase 8: Edge walls ──────────────────────────────────────
        conn_gen.add_edge_walls(wall_depth=1)

        # ── Phase 9: Game objects ────────────────────────────────────
        # Player spawn
        spawn = config.get("spawn", {})
        sx = spawn.get("x", width // 2)
        sy = spawn.get("y", height // 2)
        conn_gen.add_player_spawn(sx, sy)

        for npc in config.get("npcs", []):
            conn_gen.add_npc(
                npc["x"], npc["y"],
                npc["template"],
                npc.get("wander", False),
            )

        for es in config.get("enemy_spawners", []):
            conn_gen.add_enemy_spawner(
                es["x"], es["y"],
                es.get("type", "slime"),
                es.get("spawn_chance", 100),
                es.get("respawn_time", 90.0),
            )

        for rs in config.get("rune_stones", []):
            conn_gen.add_rune_stone(rs["x"], rs["y"], rs.get("symbol", "earth"))

        for gi in config.get("ground_items", []):
            conn_gen.add_ground_item(
                gi["x"], gi["y"],
                gi["item_id"],
                gi.get("quantity", 1),
            )

        self._canvas = canvas
        return canvas.export_tmj()

    def save(self, filepath: str):
        """Write the last generated map to a ``.tmj`` file."""
        if self._canvas is None:
            raise RuntimeError("Call generate() before save()")
        self._canvas.save_tmj(filepath)

    # ------------------------------------------------------------------
    # Path network generation
    # ------------------------------------------------------------------

    def _build_path_network(
        self,
        path_gen: PathGenerator,
        anchors: dict[str, tuple[int, int]],
        cx: int, cy: int,
        width: int, height: int,
        noise: list[list[float]],
    ):
        """Build the main road network from anchors through the center.

        Strategy:
        1. Each anchor gets a curved path inward to the map center.
        2. If multiple anchors exist, they connect through the center,
           creating a natural intersection.
        3. Noise displacement gives paths organic curves.
        """
        if not anchors:
            # No connections — just draw a cross through center
            path_gen.draw_curved_path(
                (cx, 2), (cx, height - 3), noise,
                width_start=4.0, width_end=4.0, width_mid=2.5,
            )
            path_gen.draw_curved_path(
                (4, cy), (width - 5, cy), noise,
                width_start=4.0, width_end=4.0, width_mid=2.5,
            )
            return

        # Draw a path from each anchor to the center
        for anchor_name, (ax, ay) in anchors.items():
            edge = anchor_edge(anchor_name)

            # Offset the anchor start point slightly inside the map
            if edge == "north":
                start = (ax, 2)
            elif edge == "south":
                start = (ax, height - 3)
            elif edge == "west":
                start = (3, ay)
            elif edge == "east":
                start = (width - 4, ay)
            else:
                start = (ax, ay)

            path_gen.draw_curved_path(
                start, (cx, cy), noise,
                width_start=4.5, width_end=3.0, width_mid=2.5,
                noise_strength=3.0,
                subdivisions=3,
                n_control=4,
            )

        # If we have 2+ anchors on opposite sides, the center becomes a
        # natural intersection.  Draw a small plaza there for breathing room.
        if len(anchors) >= 2:
            path_gen.draw_rect(cx - 2, cy - 2, 5, 5)

    # ------------------------------------------------------------------
    # Path flattening at buildings
    # ------------------------------------------------------------------

    @staticmethod
    def _flatten_paths_at_buildings(
        path_gen: PathGenerator,
        struct: StructureGenerator,
    ):
        """Draw horizontal path strips in front of each building's door.

        This prevents paths from curving diagonally through building
        footprints.  A flat horizontal band at the door row gives a
        natural-looking approach area.
        """
        for name, x, y, w, h in struct._placed:
            prefab = struct._prefabs.get(name)
            for obj_def in prefab.objects:
                if obj_def["type"] == "door":
                    door_y = y + obj_def["ry"]
                    # Horizontal strip spanning building width ± 1 tile
                    strip_x = max(0, x - 1)
                    strip_w = w + 2
                    path_gen.draw_rect(strip_x, door_y, strip_w, 2)

    # ------------------------------------------------------------------
    # Transition zone pre-computation
    # ------------------------------------------------------------------

    @staticmethod
    def _precompute_transition_zones(
        connections: list[dict],
        width: int, height: int,
    ) -> list[tuple[int, int, int, int]]:
        """Pre-compute transition zone rectangles before ConnectionGenerator runs.

        This lets foliage and tree placement know where transitions will be.
        """
        zones = []
        for conn in connections:
            anchor_name = conn["anchor"]
            ax, ay = anchor_position(anchor_name, width, height)
            edge = anchor_edge(anchor_name)

            if edge in ("north", "south"):
                tw = ConnectionGenerator.TRANSITION_H_WIDTH
                td = ConnectionGenerator.TRANSITION_H_DEPTH
                zone_x = max(0, ax - tw // 2)
                zone_x = min(zone_x, width - tw)
                zone_y = 0 if edge == "north" else height - td
                zones.append((zone_x, zone_y, tw, td))
            else:
                tw = ConnectionGenerator.TRANSITION_V_WIDTH
                td = ConnectionGenerator.TRANSITION_V_DEPTH
                zone_y = max(0, ay - td // 2)
                zone_y = min(zone_y, height - td)
                zone_x = 0 if edge == "west" else width - tw
                zones.append((zone_x, zone_y, tw, td))

        return zones
