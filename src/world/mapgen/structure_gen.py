"""StructureGenerator — places buildings from prefabs.

v2: Added approach walkway generation — automatically connects every
building's door to the nearest path tile with a short 2-tile-wide road.

Handles visual tiles, collision footprints, and attached objects
(doors, signs, etc.).  Tracks all placed buildings so vegetation
generators can exclude those areas.
"""

from __future__ import annotations

from .map_canvas import MapCanvas
from .prefabs import PrefabLibrary
from .rng import SeededRNG


class StructureGenerator:
    """Places buildings and structures from prefabs."""

    def __init__(self, canvas: MapCanvas, prefab_lib: PrefabLibrary,
                 rng: SeededRNG):
        self._canvas = canvas
        self._prefabs = prefab_lib
        self._rng = rng
        self._placed: list[tuple[str, int, int, int, int]] = []  # name,x,y,w,h

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def place_building(self, prefab_name: str, x: int, y: int,
                       door_target_area: str = "",
                       door_target_entry: str = "default",
                       building_id: str = ""):
        """Stamp a building prefab and wire up its objects.

        Parameters
        ----------
        prefab_name : name registered in PrefabLibrary.
        x, y        : top-left tile position.
        door_target_area : area_id the door leads to (empty = no door).
        door_target_entry : entry point name in the target area.
        building_id : unique id for the building (used in door_id).
        """
        prefab = self._prefabs.get(prefab_name)

        # Stamp visual tiles on structures layer
        self._canvas.stamp(prefab.layer, prefab.tiles, x, y)

        # Stamp canopy tiles if the prefab has them
        if prefab.canopy_tiles:
            self._canvas.stamp("canopy", prefab.canopy_tiles, x, y)

        # Record placement
        self._placed.append((prefab_name, x, y, prefab.width, prefab.height))

        # Wire up attached objects
        for obj_def in prefab.objects:
            obj_type = obj_def["type"]
            ox = x + obj_def["rx"]
            oy = y + obj_def["ry"]

            if obj_type == "door":
                door_id = building_id or f"{prefab_name}_{x}_{y}"
                props = {
                    "door_id": door_id,
                    "target_area": door_target_area,
                    "target_entry": door_target_entry,
                }
                self._canvas.add_object("door", ox, oy, properties=props,
                                         name=door_id)

        # Collision comes from .tsx per-tile properties — no explicit
        # collision rect needed.  tmj_loader reads collision=true from
        # the tileset and marks those tiles as walls automatically.

    # ------------------------------------------------------------------
    # Approach walkways (v2)
    # ------------------------------------------------------------------

    def connect_doors_to_paths(self, path_gen):
        """Draw short approach paths from every door to the nearest road tile.

        Parameters
        ----------
        path_gen : PathGenerator instance (must already have drawn main roads).
        """
        for name, x, y, w, h in self._placed:
            prefab = self._prefabs.get(name)
            for obj_def in prefab.objects:
                if obj_def["type"] == "door":
                    door_x = x + obj_def["rx"]
                    door_y = y + obj_def["ry"]

                    # Find nearest path tile
                    nearest = path_gen.nearest_path_tile(door_x, door_y)
                    if nearest is not None:
                        path_gen.draw_approach(
                            (door_x, door_y), nearest, width=2
                        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_footprints(self, padding: int = 2) -> list[tuple[int, int, int, int]]:
        """Return padded bounding boxes of all placed buildings.

        Useful for passing to vegetation/terrain exclusion zones.
        """
        return [
            (x - padding, y - padding, w + 2 * padding, h + 2 * padding)
            for _, x, y, w, h in self._placed
        ]

    def get_raw_footprints(self) -> list[tuple[int, int, int, int]]:
        """Return un-padded bounding boxes of all placed buildings."""
        return [(x, y, w, h) for _, x, y, w, h in self._placed]

    def get_door_positions(self) -> list[tuple[int, int]]:
        """Return tile positions of all placed doors (for path targets)."""
        positions = []
        for name, x, y, w, h in self._placed:
            prefab = self._prefabs.get(name)
            for obj_def in prefab.objects:
                if obj_def["type"] == "door":
                    positions.append((x + obj_def["rx"], y + obj_def["ry"]))
        return positions
