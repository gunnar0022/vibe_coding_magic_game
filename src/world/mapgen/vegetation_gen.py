"""VegetationGenerator — fill-and-carve tree placement with trunk collision.

v2: Instead of scattering trees or filling borders separately, the entire
map is flooded with a dense grid of tree positions.  Trees that overlap
paths, buildings, transition zones, or border margins are removed.  What
remains IS the forest — the village clearing is defined by the absence
of trees.

Each placed tree emits a collision object for its trunk (2x2 tiles at
rows 3-4, cols 1-2 of the tree_large prefab).
"""

from __future__ import annotations

from .map_canvas import MapCanvas
from .prefabs import Prefab, PrefabLibrary
from .rng import SeededRNG


class VegetationGenerator:
    """Flood-fills trees across the map, carving exclusions for roads/buildings."""

    def __init__(self, canvas: MapCanvas, prefab_lib: PrefabLibrary, rng: SeededRNG):
        self._canvas = canvas
        self._prefabs = prefab_lib
        self._rng = rng
        self._placed: list[tuple[int, int, int, int]] = []  # x, y, w, h

    # ------------------------------------------------------------------
    # Fill-and-carve (v2 main entry point)
    # ------------------------------------------------------------------

    def fill_trees(
        self,
        path_mask: list[list[bool]] | None = None,
        building_zones: list[tuple[int, int, int, int]] | None = None,
        transition_zones: list[tuple[int, int, int, int]] | None = None,
        noise_field: list[list[float]] | None = None,
        path_padding: int = 2,
        building_padding: int = 2,
        transition_padding: int = 2,
        density_threshold: float = 0.3,
        edge_margin: int = 0,
    ):
        """Flood the map with trees, removing any that overlap exclusions.

        Parameters
        ----------
        path_mask         : boolean grid of path tiles.
        building_zones    : (x, y, w, h) rectangles for buildings.
        transition_zones  : (x, y, w, h) rectangles for zone transitions.
        noise_field       : optional density modulator (low noise = sparser).
        path_padding      : extra tiles around paths to keep clear.
        building_padding  : extra tiles around buildings.
        transition_padding: extra tiles around transition zones.
        density_threshold : noise value below which trees are thinned.
        edge_margin       : tiles inset from map edge where trees aren't placed.
        """
        path_mask = path_mask or []
        building_zones = building_zones or []
        transition_zones = transition_zones or []

        tree = self._prefabs.get("tree_large")
        tw, th = tree.width, tree.height   # 4×5

        w_map = self._canvas.width
        h_map = self._canvas.height

        # Generate candidate positions on a grid
        candidates: list[tuple[int, int]] = []
        for y in range(edge_margin, h_map - th - edge_margin, th):
            for x in range(edge_margin, w_map - tw - edge_margin, tw):
                # Small random offset so the grid isn't perfectly aligned
                ox = self._rng.randint(-1, 1)
                oy = self._rng.randint(-1, 1)
                cx = max(edge_margin, min(w_map - tw - edge_margin, x + ox))
                cy = max(edge_margin, min(h_map - th - edge_margin, y + oy))
                candidates.append((cx, cy))

        # Also add half-offset rows for denser, more natural coverage
        for y in range(edge_margin + th // 2, h_map - th - edge_margin, th):
            for x in range(edge_margin + tw // 2, w_map - tw - edge_margin, tw):
                ox = self._rng.randint(-1, 1)
                oy = self._rng.randint(-1, 1)
                cx = max(edge_margin, min(w_map - tw - edge_margin, x + ox))
                cy = max(edge_margin, min(h_map - th - edge_margin, y + oy))
                candidates.append((cx, cy))

        # Shuffle for non-deterministic overlap resolution
        self._rng.shuffle(candidates)

        for cx, cy in candidates:
            # --- Noise-based density filter ---
            if noise_field is not None:
                # Sample noise at tree center
                nx = min(len(noise_field[0]) - 1, cx + tw // 2)
                ny = min(len(noise_field) - 1, cy + th // 2)
                noise_val = noise_field[ny][nx]
                # Low noise = sparser trees (skip some)
                if noise_val < density_threshold and self._rng.random() > 0.3:
                    continue

            # --- Path exclusion (with padding) ---
            if path_mask and self._overlaps_mask(
                    cx, cy, tw, th, path_mask, path_padding):
                continue

            # --- Building exclusion (with padding) ---
            if self._overlaps_rects(cx, cy, tw, th,
                                     building_zones, building_padding):
                continue

            # --- Transition zone exclusion (with padding) ---
            if self._overlaps_rects(cx, cy, tw, th,
                                     transition_zones, transition_padding):
                continue

            # --- Overlap with already-placed trees ---
            if self._overlaps_placed(cx, cy, tw, th):
                continue

            # Place the tree
            self._stamp_tree(tree, cx, cy)

    # ------------------------------------------------------------------
    # Stamping (collision comes from .tsx tile properties)
    # ------------------------------------------------------------------

    def _stamp_tree(self, prefab: Prefab, x: int, y: int):
        """Stamp prefab tiles on structures + canopy layers.

        Collision is handled automatically by tmj_loader reading
        collision=true properties from the tileset .tsx files.
        No separate collision objects needed.
        """
        self._canvas.stamp(prefab.layer, prefab.tiles, x, y)
        if prefab.canopy_tiles:
            self._canvas.stamp("canopy", prefab.canopy_tiles, x, y)
        self._placed.append((x, y, prefab.width, prefab.height))

    # ------------------------------------------------------------------
    # Overlap checks
    # ------------------------------------------------------------------

    @staticmethod
    def _overlaps_mask(x: int, y: int, w: int, h: int,
                       mask: list[list[bool]], padding: int) -> bool:
        """Check if a rectangle (with padding) overlaps any True cell in mask."""
        h_mask = len(mask)
        w_mask = len(mask[0]) if h_mask else 0
        for ty in range(max(0, y - padding), min(h_mask, y + h + padding)):
            for tx in range(max(0, x - padding), min(w_mask, x + w + padding)):
                if mask[ty][tx]:
                    return True
        return False

    @staticmethod
    def _overlaps_rects(x: int, y: int, w: int, h: int,
                        rects: list[tuple[int, int, int, int]],
                        padding: int) -> bool:
        """Check if a rectangle overlaps any of the padded exclusion rects."""
        for rx, ry, rw, rh in rects:
            if (x < rx + rw + padding and x + w > rx - padding and
                    y < ry + rh + padding and y + h > ry - padding):
                return True
        return False

    def _overlaps_placed(self, x: int, y: int, w: int, h: int) -> bool:
        """Check against previously placed tree positions."""
        for px, py, pw, ph in self._placed:
            if x < px + pw and x + w > px and y < py + ph and y + h > py:
                return True
        return False
