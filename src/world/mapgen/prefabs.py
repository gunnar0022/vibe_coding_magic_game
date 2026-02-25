"""Prefab definitions — reusable multi-tile structures.

Each prefab is a named 2-D GID grid with an associated collision
footprint and optional object attachment points (doors, signs, …).
Prefabs are stamped onto the MapCanvas by generators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .tileset_defs import TilesetRegistry, OBJECTS, HOUSE_DETAILS


@dataclass
class Prefab:
    """A reusable multi-tile structure."""
    name: str
    width: int                                     # tiles
    height: int                                    # tiles
    tiles: list[list[int]]                         # [row][col] GIDs for structures layer
    collision: list[list[str | None]]              # [row][col] "wall"/None
    objects: list[dict[str, Any]] = field(default_factory=list)
    layer: str = "structures"                      # target tile layer
    canopy_tiles: list[list[int]] = field(default_factory=list)  # [row][col] GIDs for canopy layer


class PrefabLibrary:
    """Collection of all reusable prefabs, built from tileset math."""

    def __init__(self, registry: TilesetRegistry):
        self._registry = registry
        self._prefabs: dict[str, Prefab] = {}
        self._build_all()

    def get(self, name: str) -> Prefab:
        return self._prefabs[name]

    def list_names(self) -> list[str]:
        return list(self._prefabs.keys())

    # ------------------------------------------------------------------
    # Prefab builders
    # ------------------------------------------------------------------

    def _build_all(self):
        self._build_trees()
        self._build_houses()

    # ── Trees ─────────────────────────────────────────────────────────

    def _build_trees(self):
        """Large tree: 4 wide × 5 tall from Objects tileset.

        Grid formula:  local_id = 19 + col + (row × 51)
        Objects has 51 columns; the tree sprite starts at local 19.
        Collision: only the trunk (rows 3-4, cols 1-2) — via .tsx properties.

        Layer split (canopy mask):
            xxxx  row 0: all -> canopy
            xxxx  row 1: all -> canopy
            x..x  row 2: cols 0,3 -> canopy; cols 1,2 -> structures
            ....  row 3: all -> structures (trunk)
            ....  row 4: all -> structures (trunk base)
        """
        r = self._registry

        # Compute all GIDs for the full tree
        all_gids: list[list[int]] = []
        for row in range(5):
            all_gids.append([
                r.gid("objects", 19 + col + row * OBJECTS.columns)
                for col in range(4)
            ])

        # Split into structures layer (trunk + inner canopy parts)
        struct_tiles: list[list[int]] = [
            [0, 0, 0, 0],                                # row 0: canopy
            [0, 0, 0, 0],                                # row 1: canopy
            [0, all_gids[2][1], all_gids[2][2], 0],      # row 2: inner cols on structures
            list(all_gids[3]),                            # row 3: trunk
            list(all_gids[4]),                            # row 4: trunk base
        ]

        # Split into canopy layer (treetop + outer edges)
        canopy: list[list[int]] = [
            list(all_gids[0]),                            # row 0: full canopy
            list(all_gids[1]),                            # row 1: full canopy
            [all_gids[2][0], 0, 0, all_gids[2][3]],      # row 2: outer cols on canopy
            [0, 0, 0, 0],                                # row 3: trunk (structures)
            [0, 0, 0, 0],                                # row 4: trunk base (structures)
        ]

        coll: list[list[str | None]] = [
            [None, None, None, None],       # canopy top
            [None, None, None, None],       # canopy
            [None, None, None, None],       # canopy/inner
            [None, "wall", "wall", None],   # trunk (collision from .tsx)
            [None, "wall", "wall", None],   # trunk base (collision from .tsx)
        ]

        self._prefabs["tree_large"] = Prefab(
            name="tree_large", width=4, height=5,
            tiles=struct_tiles, collision=coll, layer="structures",
            canopy_tiles=canopy,
        )

    # ── Houses ────────────────────────────────────────────────────────

    def _build_houses(self):
        """Small house: 5 wide × 5 tall from house_details tileset.

        The house sprite occupies a 5×5 block in the tileset starting
        from different local offsets.  GIDs are computed per row.
        Collision: the entire 5×5 footprint is wall.
        A door attachment point sits at the bottom-center.
        """
        r = self._registry
        cols = HOUSE_DETAILS.columns  # 10

        # --- house_small: starts at local row 1, col 1  (local_id = 11) ---
        # Each row in the tileset is `cols` wide.
        # We pick 5 contiguous columns starting at col 1.
        base_local = 11                        # row 1, col 1
        gids: list[list[int]] = []
        for row in range(5):
            row_start = base_local + row * cols
            gids.append([
                r.gid("house_details", row_start + col)
                for col in range(5)
            ])

        coll = [["wall"] * 5 for _ in range(5)]

        self._prefabs["house_small"] = Prefab(
            name="house_small", width=5, height=5,
            tiles=gids, collision=coll, layer="structures",
            objects=[
                # Door 1 tile below the house, centered (col 2)
                {"type": "door", "rx": 2, "ry": 5,
                 "props": {"door_id": "house_door"}},
            ],
        )

        # --- house_medium: wider variant, 7 wide × 5 tall ---
        # Starts at local row 1, col 0 and takes 7 cols
        base_local_m = 10                      # row 1, col 0
        gids_m: list[list[int]] = []
        for row in range(5):
            row_start = base_local_m + row * cols
            gids_m.append([
                r.gid("house_details", row_start + col)
                for col in range(7)
            ])

        coll_m = [["wall"] * 7 for _ in range(5)]

        self._prefabs["house_medium"] = Prefab(
            name="house_medium", width=7, height=5,
            tiles=gids_m, collision=coll_m, layer="structures",
            objects=[
                {"type": "door", "rx": 3, "ry": 5,
                 "props": {"door_id": "house_door"}},
            ],
        )
