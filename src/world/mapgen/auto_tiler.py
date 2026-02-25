"""Auto-tiler — resolves logical terrain grids to specific tile GIDs.

Uses Wang corner lookup tables to select the visually correct tile for
every position based on its 8 neighbours.  Variant tiles are chosen
randomly via the seeded RNG for natural-looking terrain.
"""

from __future__ import annotations

from . import wang_tables
from .tileset_defs import TilesetRegistry
from .rng import SeededRNG


class AutoTiler:
    """Resolves terrain boundaries into specific tile GIDs."""

    # Map terrain-type string → (wang_table, tileset_name, base_gid_or_None)
    _TERRAIN_TABLES: dict[str, tuple[str, str]] = {
        "leafy":     ("LEAFY_AREA",  "ground_grass_forest"),
        "dirt_path": ("DIRT_PATH",   "ground_grass_forest"),
    }

    def __init__(self, registry: TilesetRegistry, rng: SeededRNG):
        self._registry = registry
        self._rng = rng

        # Pre-resolve table references
        self._tables: dict[str, tuple[dict, str]] = {}
        for terrain, (table_name, ts_name) in self._TERRAIN_TABLES.items():
            table = getattr(wang_tables, table_name)
            self._tables[terrain] = (table, ts_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, mask: list[list[bool]], x: int, y: int,
                terrain_type: str) -> int:
        """Compute the correct GID for position *(x, y)* in *mask*.

        Parameters
        ----------
        mask : 2-D bool grid — ``True`` where *terrain_type* is present.
        x, y : tile coordinates.
        terrain_type : one of the keys in ``_TERRAIN_TABLES``.

        Returns the global GID to paint, or **0** if the tile is base terrain.
        """
        if not mask[y][x]:
            return 0

        key = self._corner_key(mask, x, y)
        table, ts_name = self._tables[terrain_type]
        local_ids = table.get(key, [])

        if not local_ids:
            # Isolated single tile — use full-fill as fallback
            local_ids = table.get(15, [])
            if not local_ids:
                return 0

        local_id = self._rng.choice(local_ids)
        return self._registry.gid(ts_name, local_id)

    # ------------------------------------------------------------------
    # Corner key computation
    # ------------------------------------------------------------------

    @staticmethod
    def _corner_key(mask: list[list[bool]], x: int, y: int) -> int:
        """Compute the 4-bit Wang corner key for *(x, y)*.

        A corner is **1** when the tile itself, both orthogonal neighbours
        sharing that corner, *and* the diagonal neighbour are all True.
        This produces smooth transitions where terrain meets base.
        """
        h = len(mask)
        w = len(mask[0]) if h else 0

        def at(tx: int, ty: int) -> bool:
            if 0 <= tx < w and 0 <= ty < h:
                return mask[ty][tx]
            return False

        n  = at(x,     y - 1)
        s  = at(x,     y + 1)
        e  = at(x + 1, y)
        w_ = at(x - 1, y)
        nw = at(x - 1, y - 1)
        ne = at(x + 1, y - 1)
        se = at(x + 1, y + 1)
        sw = at(x - 1, y + 1)

        tl = 1 if (n and w_ and nw) else 0
        tr = 1 if (n and e  and ne) else 0
        br = 1 if (s and e  and se) else 0
        bl = 1 if (s and w_ and sw) else 0

        return (tl << 3) | (tr << 2) | (br << 1) | bl
