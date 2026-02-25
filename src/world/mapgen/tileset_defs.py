"""Tileset registry — single source of truth for all tileset metadata.

Every tileset used in generated maps is registered here with fixed GID
assignments that match the existing hand-built Tiled maps.  This ensures
generated .tmj files reference the same .tsx files and produce identical
GID ranges.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TilesetInfo:
    """Metadata for one tileset."""
    name: str
    tsx_source: str      # Relative path for TMJ tilesets array
    firstgid: int
    columns: int
    tilecount: int

    @property
    def lastgid(self) -> int:
        return self.firstgid + self.tilecount - 1

    def local_to_gid(self, local_id: int) -> int:
        """Convert a tileset-local tile ID to a global GID."""
        return self.firstgid + local_id

    def gid_to_local(self, gid: int) -> int:
        """Convert a global GID to a tileset-local tile ID."""
        return gid - self.firstgid

    def contains_gid(self, gid: int) -> bool:
        return self.firstgid <= gid <= self.lastgid


# ---------------------------------------------------------------------------
# Village biome tilesets (fixed GID assignments matching south_village_central)
# ---------------------------------------------------------------------------

GROUND_FOREST = TilesetInfo(
    name="ground_grass_forest",
    tsx_source="Ground_grass.tsx",
    firstgid=1,
    columns=19,
    tilecount=437,
)

OBJECTS = TilesetInfo(
    name="objects",
    tsx_source="Objects.tsx",
    firstgid=438,
    columns=51,
    tilecount=867,
)

SPOTS_LIANAS = TilesetInfo(
    name="spots_lianas",
    tsx_source="spots_lianas.tsx",
    firstgid=1305,
    columns=21,
    tilecount=714,
)

HOUSE_DETAILS = TilesetInfo(
    name="house_details",
    tsx_source="house_details.tsx",
    firstgid=2019,
    columns=10,
    tilecount=170,
)

GROUND_PATHS = TilesetInfo(
    name="ground_grass_paths",
    tsx_source="Ground_grass2.tsx",
    firstgid=2189,
    columns=17,
    tilecount=527,
)


class TilesetRegistry:
    """Registry of all tilesets used in a biome.

    Currently only the village biome is supported.  Adding a new biome
    means registering its tilesets with non-overlapping GID ranges.
    """

    def __init__(self):
        self._tilesets: dict[str, TilesetInfo] = {}
        self._load_village_biome()

    # --- public API --------------------------------------------------------

    def get(self, name: str) -> TilesetInfo:
        """Get a tileset by its short name."""
        return self._tilesets[name]

    def gid(self, tileset_name: str, local_id: int) -> int:
        """Shorthand: global GID for a local tile ID in a named tileset."""
        return self._tilesets[tileset_name].local_to_gid(local_id)

    def tmj_tilesets_array(self) -> list[dict]:
        """Return the ``tilesets`` array for TMJ export."""
        sorted_ts = sorted(self._tilesets.values(), key=lambda t: t.firstgid)
        return [{"firstgid": ts.firstgid, "source": ts.tsx_source}
                for ts in sorted_ts]

    # --- private -----------------------------------------------------------

    def _load_village_biome(self):
        for ts in (GROUND_FOREST, OBJECTS, SPOTS_LIANAS, HOUSE_DETAILS, GROUND_PATHS):
            self._tilesets[ts.name] = ts
