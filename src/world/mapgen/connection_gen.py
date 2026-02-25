"""ConnectionGenerator — zone transitions, entry points, and game objects.

v2: 12-slot anchor system, fixed-size transition zones with flanking
obstacles, consolidated edge collision (run-length encoded).

Handles all the game-logic objects that wire maps together:
zone transitions at edges, entry points for arrivals, player spawns,
NPCs, enemy spawners, rune stones, and ground items.
"""

from __future__ import annotations

from .map_canvas import MapCanvas


# ── 12-slot edge anchor definitions ──────────────────────────────────────
#
# Each slot maps to a fixed fractional position along its edge.
# Config connections reference slots by name:
#   {"anchor": "south_mid", "target": "home_village", ...}

ANCHOR_FRACTIONS: dict[str, tuple[str, float]] = {
    # (edge, fraction_along_edge)
    "north_left":  ("north", 0.25),
    "north_mid":   ("north", 0.50),
    "north_right": ("north", 0.75),
    "south_left":  ("south", 0.25),
    "south_mid":   ("south", 0.50),
    "south_right": ("south", 0.75),
    "west_top":    ("west",  0.25),
    "west_mid":    ("west",  0.50),
    "west_bottom": ("west",  0.75),
    "east_top":    ("east",  0.25),
    "east_mid":    ("east",  0.50),
    "east_bottom": ("east",  0.75),
}


def anchor_position(anchor_name: str, w: int, h: int) -> tuple[int, int]:
    """Compute the tile (x, y) for a named anchor slot."""
    edge, frac = ANCHOR_FRACTIONS[anchor_name]
    if edge in ("north", "south"):
        x = int(w * frac)
        y = 0 if edge == "north" else h - 1
    else:
        x = 0 if edge == "west" else w - 1
        y = int(h * frac)
    return x, y


def anchor_edge(anchor_name: str) -> str:
    """Return the edge name for a given anchor slot."""
    return ANCHOR_FRACTIONS[anchor_name][0]


class ConnectionGenerator:
    """Adds zone transitions, entry points, and game objects to a map.

    v2 features:
    - 12-slot anchor system for standardised edge connections
    - Fixed 3x2 (top/bottom) and 2x3 (left/right) transition zones
    - Flanking collision objects beside each transition
    - Consolidated edge walls (one collision rect per contiguous run)
    """

    # Fixed transition zone dimensions
    TRANSITION_H_WIDTH = 3   # tiles wide for north/south edges
    TRANSITION_H_DEPTH = 2   # tiles deep for north/south edges
    TRANSITION_V_WIDTH = 2   # tiles wide for east/west edges
    TRANSITION_V_DEPTH = 3   # tiles deep for east/west edges

    def __init__(self, canvas: MapCanvas):
        self._canvas = canvas
        self._transition_zones: list[tuple[int, int, int, int]] = []  # x,y,w,h

    # ------------------------------------------------------------------
    # Anchor-based connections
    # ------------------------------------------------------------------

    def add_anchor_connection(
        self,
        anchor: str,
        target_area: str,
        target_entry: str = "default",
    ):
        """Add a zone transition at a named anchor slot.

        Creates a fixed-size transition zone and an entry point just
        inside the map edge.  Also records the zone for edge-wall gaps.

        Parameters
        ----------
        anchor       : one of the 12 anchor slot names.
        target_area  : area_id to transition to.
        target_entry : entry point name in the target area.
        """
        w = self._canvas.width
        h = self._canvas.height
        edge = anchor_edge(anchor)
        ax, ay = anchor_position(anchor, w, h)

        if edge in ("north", "south"):
            tw = self.TRANSITION_H_WIDTH
            td = self.TRANSITION_H_DEPTH
            # Center the zone on the anchor x
            zone_x = max(0, ax - tw // 2)
            zone_x = min(zone_x, w - tw)  # clamp to map

            if edge == "north":
                zone_y = 0
                entry_y = td + 1  # a few tiles inside
            else:
                zone_y = h - td
                entry_y = h - td - 2

            self._canvas.add_object(
                "zone_transition", zone_x, zone_y,
                width=float(tw), height=float(td),
                name=f"to_{target_area}",
                properties={
                    "target_area": target_area,
                    "target_entry": target_entry,
                    "zone_id": f"to_{target_area}",
                },
            )
            self._canvas.add_object(
                "entry_point", ax, entry_y,
                name="",
                properties={"name": f"from_{target_area}"},
            )

            # Record transition zone for edge wall gaps
            self._transition_zones.append((zone_x, zone_y, tw, td))

            # Flanking collision objects (1 tile wide, td tiles deep)
            flank_left_x = zone_x - 1
            flank_right_x = zone_x + tw
            if flank_left_x >= 0:
                self._canvas.add_object(
                    "collision", flank_left_x, zone_y,
                    width=1.0, height=float(td),
                    name=f"flank_L_{anchor}",
                )
            if flank_right_x < w:
                self._canvas.add_object(
                    "collision", flank_right_x, zone_y,
                    width=1.0, height=float(td),
                    name=f"flank_R_{anchor}",
                )

        else:  # east / west
            tw = self.TRANSITION_V_WIDTH
            td = self.TRANSITION_V_DEPTH
            zone_y = max(0, ay - td // 2)
            zone_y = min(zone_y, h - td)

            if edge == "west":
                zone_x = 0
                entry_x = tw + 1
            else:
                zone_x = w - tw
                entry_x = w - tw - 2

            self._canvas.add_object(
                "zone_transition", zone_x, zone_y,
                width=float(tw), height=float(td),
                name=f"to_{target_area}",
                properties={
                    "target_area": target_area,
                    "target_entry": target_entry,
                    "zone_id": f"to_{target_area}",
                },
            )
            self._canvas.add_object(
                "entry_point", entry_x, ay,
                name="",
                properties={"name": f"from_{target_area}"},
            )

            self._transition_zones.append((zone_x, zone_y, tw, td))

            # Flanking collision (tw tiles wide, 1 tile tall)
            flank_top_y = zone_y - 1
            flank_bot_y = zone_y + td
            if flank_top_y >= 0:
                self._canvas.add_object(
                    "collision", zone_x, flank_top_y,
                    width=float(tw), height=1.0,
                    name=f"flank_T_{anchor}",
                )
            if flank_bot_y < h:
                self._canvas.add_object(
                    "collision", zone_x, flank_bot_y,
                    width=float(tw), height=1.0,
                    name=f"flank_B_{anchor}",
                )

    def get_transition_zones(self) -> list[tuple[int, int, int, int]]:
        """Return all transition zone rectangles (x, y, w, h) in tiles."""
        return list(self._transition_zones)

    # ------------------------------------------------------------------
    # Consolidated edge collision walls
    # ------------------------------------------------------------------

    def add_edge_walls(self, wall_depth: int = 1):
        """Add consolidated collision rectangles around the map perimeter.

        Scans each edge for contiguous runs of non-transition tiles and
        emits one collision rect per run.  A 55-tile edge with one 3-tile
        transition becomes 2 collision objects instead of 52.

        Parameters
        ----------
        wall_depth : thickness of the wall in tiles (default 1).
        """
        w = self._canvas.width
        h = self._canvas.height

        # Build open-tile sets for each edge from transition zones
        open_north: set[int] = set()
        open_south: set[int] = set()
        open_west: set[int] = set()
        open_east: set[int] = set()

        for zx, zy, zw, zh in self._transition_zones:
            # North edge transitions (y=0)
            if zy == 0:
                for tx in range(zx, zx + zw):
                    open_north.add(tx)
            # South edge transitions (y touches bottom)
            if zy + zh >= h:
                for tx in range(zx, zx + zw):
                    open_south.add(tx)
            # West edge transitions (x=0)
            if zx == 0:
                for ty in range(zy, zy + zh):
                    open_west.add(ty)
            # East edge transitions (x touches right)
            if zx + zw >= w:
                for ty in range(zy, zy + zh):
                    open_east.add(ty)

        def _emit_runs(length: int, open_set: set[int],
                       is_horizontal: bool, edge_name: str):
            """Scan an edge and emit consolidated collision rects."""
            run_start = None
            for i in range(length):
                if i in open_set:
                    # Close current run if one is active
                    if run_start is not None:
                        run_len = i - run_start
                        self._emit_wall(edge_name, run_start, run_len,
                                        wall_depth, is_horizontal)
                        run_start = None
                else:
                    if run_start is None:
                        run_start = i
            # Close final run
            if run_start is not None:
                run_len = length - run_start
                self._emit_wall(edge_name, run_start, run_len,
                                wall_depth, is_horizontal)

        _emit_runs(w, open_north, True, "north")
        _emit_runs(w, open_south, True, "south")
        _emit_runs(h, open_west, False, "west")
        _emit_runs(h, open_east, False, "east")

    def _emit_wall(self, edge: str, start: int, length: int,
                   depth: int, is_horizontal: bool):
        """Emit a single consolidated collision rectangle for an edge run."""
        w = self._canvas.width
        h = self._canvas.height

        if edge == "north":
            self._canvas.add_object(
                "collision", start, 0,
                width=float(length), height=float(depth),
                name=f"wall_{edge}_{start}",
            )
        elif edge == "south":
            self._canvas.add_object(
                "collision", start, h - depth,
                width=float(length), height=float(depth),
                name=f"wall_{edge}_{start}",
            )
        elif edge == "west":
            self._canvas.add_object(
                "collision", 0, start,
                width=float(depth), height=float(length),
                name=f"wall_{edge}_{start}",
            )
        elif edge == "east":
            self._canvas.add_object(
                "collision", w - depth, start,
                width=float(depth), height=float(length),
                name=f"wall_{edge}_{start}",
            )

    # ------------------------------------------------------------------
    # Game objects
    # ------------------------------------------------------------------

    def add_player_spawn(self, x: int, y: int):
        self._canvas.add_object("player_spawn", x, y, name="player_spawn")

    def add_npc(self, x: int, y: int, template: str, wander: bool = False):
        self._canvas.add_object(
            "npc_spawn", x, y, name=template,
            properties={"template": template, "wander": wander},
        )

    def add_enemy_spawner(self, x: int, y: int, enemy_type: str = "slime",
                          spawn_chance: int = 100, respawn_time: float = 90.0):
        self._canvas.add_object(
            "enemy_spawn", x, y, name=f"spawner_{enemy_type}",
            properties={
                "enemy_type": enemy_type,
                "spawn_chances": str(spawn_chance),
                "respawn_time": str(respawn_time),
            },
        )

    def add_rune_stone(self, x: int, y: int, symbol: str = "earth"):
        self._canvas.add_object(
            "wild_rune", x, y, name=f"{symbol}_stone",
            properties={"symbol": symbol},
        )

    def add_ground_item(self, x: int, y: int, item_id: str, quantity: int = 1):
        self._canvas.add_object(
            "ground_item", x, y, name=item_id,
            properties={"item_id": item_id, "quantity": quantity},
        )
