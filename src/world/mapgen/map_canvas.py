"""MapCanvas — multi-layer writable tile grid with TMJ export.

The canvas accumulates tile data, collision info, and game objects,
then serialises everything as a Tiled-compatible ``.tmj`` JSON file
that the existing ``tmj_loader`` can consume directly.
"""

from __future__ import annotations

import json
from typing import Any

from .tileset_defs import TilesetRegistry


# Tiled property type inference
def _tiled_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "string"


class MapCanvas:
    """A writable map that exports to ``.tmj``."""

    def __init__(self, width: int, height: int, registry: TilesetRegistry):
        self.width = width
        self.height = height
        self._registry = registry

        # Tile layers: name → 2-D list[row][col] of GIDs (0 = empty)
        self._tile_layers: dict[str, list[list[int]]] = {}
        self._layer_order: list[str] = []
        self._layer_offsets: dict[str, tuple[float, float]] = {}

        # Object layer
        self._objects: list[dict] = []
        self._next_obj_id = 1

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------

    def add_tile_layer(self, name: str,
                       offset_x: float = 0.0,
                       offset_y: float = 0.0):
        """Create a new tile layer filled with 0 (empty)."""
        self._tile_layers[name] = [
            [0] * self.width for _ in range(self.height)
        ]
        self._layer_order.append(name)
        if offset_x or offset_y:
            self._layer_offsets[name] = (offset_x, offset_y)

    # ------------------------------------------------------------------
    # Tile painting
    # ------------------------------------------------------------------

    def set_tile(self, layer: str, x: int, y: int, gid: int):
        """Set a single tile GID on a layer."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._tile_layers[layer][y][x] = gid

    def get_tile(self, layer: str, x: int, y: int) -> int:
        """Read the GID at (x, y) on a layer.  Returns 0 if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._tile_layers[layer][y][x]
        return 0

    def fill_rect(self, layer: str, x: int, y: int, w: int, h: int, gid: int):
        """Fill a rectangular region with a single GID."""
        for ty in range(max(0, y), min(self.height, y + h)):
            for tx in range(max(0, x), min(self.width, x + w)):
                self._tile_layers[layer][ty][tx] = gid

    def fill_layer(self, layer: str, gid: int):
        """Fill an entire layer with a single GID."""
        self.fill_rect(layer, 0, 0, self.width, self.height, gid)

    def stamp(self, layer: str, grid: list[list[int]], x: int, y: int):
        """Stamp a 2-D GID grid onto a layer at *(x, y)*.

        GID 0 in the grid is treated as transparent (skipped).
        """
        for row_idx, row in enumerate(grid):
            for col_idx, gid in enumerate(row):
                if gid != 0:
                    self.set_tile(layer, x + col_idx, y + row_idx, gid)

    # ------------------------------------------------------------------
    # Objects
    # ------------------------------------------------------------------

    def add_object(self, obj_type: str, x: int, y: int, *,
                   name: str = "",
                   width: float = 0.0,
                   height: float = 0.0,
                   properties: dict | None = None) -> int:
        """Add a game object.  *x, y* are in **tile** coordinates.

        Returns the assigned object ID.
        """
        obj_id = self._next_obj_id
        self._next_obj_id += 1

        # Convert tile coords → pixel coords (native 16 px tiles)
        px = x * 16
        py = y * 16
        pw = width * 16
        ph = height * 16

        obj: dict[str, Any] = {
            "id": obj_id,
            "name": name,
            "type": obj_type,
            "x": px,
            "y": py,
            "width": pw,
            "height": ph,
            "rotation": 0,
            "visible": True,
        }

        if pw == 0 and ph == 0:
            obj["point"] = True

        if properties:
            obj["properties"] = [
                {"name": k, "type": _tiled_type(v), "value": v}
                for k, v in properties.items()
            ]

        self._objects.append(obj)
        return obj_id

    # ------------------------------------------------------------------
    # TMJ export
    # ------------------------------------------------------------------

    def export_tmj(self) -> dict:
        """Return a complete TMJ dict ready for ``json.dump``."""
        layers: list[dict] = []
        layer_id = 1

        # Tile layers (bottom → top)
        for name in self._layer_order:
            grid = self._tile_layers[name]
            flat: list[int] = []
            for row in grid:
                flat.extend(row)

            ld: dict[str, Any] = {
                "data": flat,
                "height": self.height,
                "id": layer_id,
                "name": name,
                "opacity": 1,
                "type": "tilelayer",
                "visible": True,
                "width": self.width,
                "x": 0,
                "y": 0,
            }

            if name in self._layer_offsets:
                ox, oy = self._layer_offsets[name]
                ld["offsetx"] = ox
                ld["offsety"] = oy

            layers.append(ld)
            layer_id += 1

        # Object layer
        if self._objects:
            layers.append({
                "draworder": "topdown",
                "id": layer_id,
                "name": "Object Layer 1",
                "objects": self._objects,
                "opacity": 1,
                "type": "objectgroup",
                "visible": True,
                "x": 0,
                "y": 0,
            })
            layer_id += 1

        return {
            "compressionlevel": -1,
            "height": self.height,
            "infinite": False,
            "layers": layers,
            "nextlayerid": layer_id,
            "nextobjectid": self._next_obj_id,
            "orientation": "orthogonal",
            "renderorder": "right-down",
            "tiledversion": "1.11.2",
            "tileheight": 16,
            "tilesets": self._registry.tmj_tilesets_array(),
            "tilewidth": 16,
            "type": "map",
            "version": "1.10",
            "width": self.width,
        }

    def save_tmj(self, filepath: str):
        """Export and write to a ``.tmj`` file."""
        with open(filepath, "w") as f:
            json.dump(self.export_tmj(), f, indent=1)
