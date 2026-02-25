"""mapgen — Modular map generation library.

Generates Tiled-compatible .tmj files from composable generators.
No pygame or runtime game dependencies required.

Quick start
-----------
>>> from src.world.mapgen import TilesetRegistry, MapCanvas, AutoTiler, SeededRNG
>>> from src.world.mapgen import PrefabLibrary
>>> from src.world.mapgen.wang_tables import BASE_GRASS_GID
>>>
>>> rng = SeededRNG(42)
>>> reg = TilesetRegistry()
>>> canvas = MapCanvas(50, 40, reg)
>>> canvas.add_tile_layer("background")
>>> canvas.fill_layer("background", BASE_GRASS_GID)
>>> canvas.save_tmj("Tiled_Workspace/test_gen.tmj")
"""

from .rng import SeededRNG
from .tileset_defs import TilesetRegistry, TilesetInfo
from .auto_tiler import AutoTiler
from .map_canvas import MapCanvas
from .prefabs import Prefab, PrefabLibrary
from .terrain_gen import TerrainGenerator
from .path_gen import PathGenerator
from .vegetation_gen import VegetationGenerator
from .structure_gen import StructureGenerator
from .connection_gen import ConnectionGenerator, anchor_position, anchor_edge, ANCHOR_FRACTIONS
from .village_composer import VillageComposer

__all__ = [
    # Core
    "SeededRNG",
    "TilesetRegistry",
    "TilesetInfo",
    "AutoTiler",
    "MapCanvas",
    "Prefab",
    "PrefabLibrary",
    # Generators
    "TerrainGenerator",
    "PathGenerator",
    "VegetationGenerator",
    "StructureGenerator",
    "ConnectionGenerator",
    "anchor_position",
    "anchor_edge",
    "ANCHOR_FRACTIONS",
    # Composers
    "VillageComposer",
]
