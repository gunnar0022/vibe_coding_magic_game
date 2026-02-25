"""TerrainGenerator — paints base terrain layers.

v2: Noise-driven foliage generation.  Instead of scattering random
rectangles, foliage is placed everywhere the noise field exceeds a
threshold, then carved where paths and buildings exist.  This produces
large, irregular, map-spanning foliage regions instead of isolated patches.

All painting uses the AutoTiler for proper Wang-corner edge resolution.
"""

from __future__ import annotations

from .map_canvas import MapCanvas
from .auto_tiler import AutoTiler
from .rng import SeededRNG
from .wang_tables import BASE_GRASS_GID


class TerrainGenerator:
    """Paints base terrain: grass fill, noise-driven foliage, clearings."""

    def __init__(self, canvas: MapCanvas, auto_tiler: AutoTiler, rng: SeededRNG):
        self._canvas = canvas
        self._auto = auto_tiler
        self._rng = rng

    # ------------------------------------------------------------------
    # Grass base
    # ------------------------------------------------------------------

    def fill_grass(self, gid: int = BASE_GRASS_GID):
        """Fill the entire background layer with a grass tile."""
        self._canvas.fill_layer("background", gid)

    # ------------------------------------------------------------------
    # Noise-driven foliage (v2)
    # ------------------------------------------------------------------

    def generate_foliage_from_noise(
        self,
        noise_field: list[list[float]],
        threshold: float = 0.45,
        path_mask: list[list[bool]] | None = None,
        building_zones: list[tuple[int, int, int, int]] | None = None,
        transition_zones: list[tuple[int, int, int, int]] | None = None,
        border_margin: int = 2,
    ):
        """Generate foliage from a continuous noise field.

        Every tile where noise > threshold gets foliage.  Paths, buildings,
        transition zones, and border margins are carved out.

        Parameters
        ----------
        noise_field      : 2D grid of floats [0, 1] (from rng.noise_field).
        threshold        : noise cutoff — lower = more foliage coverage.
        path_mask        : boolean grid of path tiles (carved out).
        building_zones   : list of (x, y, w, h) building footprints to carve.
        transition_zones : list of (x, y, w, h) transition zones to carve.
        border_margin    : tiles of border to keep clear of foliage.
        """
        building_zones = building_zones or []
        transition_zones = transition_zones or []
        w_map = self._canvas.width
        h_map = self._canvas.height

        # Build the foliage mask from noise
        mask = [[False] * w_map for _ in range(h_map)]

        for y in range(h_map):
            for x in range(w_map):
                # Border margin
                if (x < border_margin or x >= w_map - border_margin or
                        y < border_margin or y >= h_map - border_margin):
                    continue

                # Noise threshold
                if y < len(noise_field) and x < len(noise_field[0]):
                    if noise_field[y][x] < threshold:
                        continue
                else:
                    continue

                # Carve paths
                if path_mask and path_mask[y][x]:
                    continue

                # Carve buildings (with padding)
                in_building = False
                for bx, by, bw, bh in building_zones:
                    if bx <= x < bx + bw and by <= y < by + bh:
                        in_building = True
                        break
                if in_building:
                    continue

                # Carve transition zones (with padding)
                in_transition = False
                pad = 2
                for tx, ty, tw, th in transition_zones:
                    if (tx - pad <= x < tx + tw + pad and
                            ty - pad <= y < ty + th + pad):
                        in_transition = True
                        break
                if in_transition:
                    continue

                mask[y][x] = True

        # Auto-tile onto the foliage layer
        self.paint_leafy_regions(mask)

    # ------------------------------------------------------------------
    # Auto-tiling
    # ------------------------------------------------------------------

    def paint_leafy_regions(self, mask: list[list[bool]]):
        """Auto-tile a pre-built boolean mask onto the **foliage** layer.

        True positions get leafy tiles on the dedicated foliage overlay
        layer (rendered above paths so there are no gray gaps behind
        partially-transparent foliage sprites).
        """
        for y in range(self._canvas.height):
            for x in range(self._canvas.width):
                if mask[y][x]:
                    gid = self._auto.resolve(mask, x, y, "leafy")
                    if gid:
                        self._canvas.set_tile("foliage", x, y, gid)

    # ------------------------------------------------------------------
    # Clearings
    # ------------------------------------------------------------------

    def clear_rect(self, x: int, y: int, w: int, h: int):
        """Reset a rectangular region of the background to base grass.

        Useful for carving out building footprints or plazas.
        """
        self._canvas.fill_rect("background", x, y, w, h, BASE_GRASS_GID)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _rects_overlap(x1, y1, w1, h1, x2, y2, w2, h2) -> bool:
        return x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2
