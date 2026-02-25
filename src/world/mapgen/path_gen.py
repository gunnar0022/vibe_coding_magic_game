"""PathGenerator — draws smooth, variable-width roads with auto-tiled edges.

v2: Chaikin subdivision for smooth curves, variable width along each path
(wider at endpoints/intersections, narrower in between), and optional
noise displacement for organic flow.

All path drawing operations paint onto an internal boolean mask.
Call :meth:`finalize` after all paths are drawn so the AutoTiler can
resolve intersections and edges in a single pass.
"""

from __future__ import annotations

import math

from .map_canvas import MapCanvas
from .auto_tiler import AutoTiler
from .rng import SeededRNG


class PathGenerator:
    """Draws roads and paths with Chaikin-smoothed curves and variable width."""

    def __init__(self, canvas: MapCanvas, auto_tiler: AutoTiler, rng: SeededRNG):
        self._canvas = canvas
        self._auto = auto_tiler
        self._rng = rng
        self._mask: list[list[bool]] = [
            [False] * canvas.width for _ in range(canvas.height)
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def draw_curved_path(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        noise_field: list[list[float]] | None = None,
        width_start: float = 4.0,
        width_end: float = 4.0,
        width_mid: float = 2.5,
        noise_strength: float = 3.0,
        subdivisions: int = 3,
        n_control: int = 4,
    ):
        """Draw a smooth, variable-width path between two points.

        Parameters
        ----------
        start, end      : tile coordinates of the path endpoints.
        noise_field     : optional 2D noise grid for perpendicular displacement.
        width_start/end : path width at the endpoints (wider for anchors).
        width_mid       : path width at the midpoint (narrower between).
        noise_strength  : maximum tile displacement from noise (0 = straight).
        subdivisions    : Chaikin subdivision iterations (2-4 recommended).
        n_control       : number of intermediate control points to generate.
        """
        # Build control points along the line from start to end
        control_points = self._make_control_points(
            start, end, noise_field, noise_strength, n_control
        )

        # Smooth with Chaikin subdivision
        smooth = self._chaikin(control_points, subdivisions)

        # Rasterize with variable width
        self._rasterize_variable_width(smooth, width_start, width_end, width_mid)

    def draw_approach(
        self,
        door_pos: tuple[int, int],
        target_pos: tuple[int, int],
        width: int = 2,
    ):
        """Draw a short, straight approach path from a door to the nearest road.

        Uses Bresenham with fixed width — no curves needed for short connectors.
        """
        points = self._bresenham(door_pos, target_pos)
        self._paint_width(points, width)

    def draw_rect(self, x: int, y: int, w: int, h: int):
        """Paint a filled rectangle directly onto the mask (e.g. a plaza)."""
        for ty in range(max(0, y), min(self._canvas.height, y + h)):
            for tx in range(max(0, x), min(self._canvas.width, x + w)):
                self._mask[ty][tx] = True

    def get_mask(self) -> list[list[bool]]:
        """Return a copy of the current path mask (for avoidance zones)."""
        return [row[:] for row in self._mask]

    def finalize(self):
        """Auto-tile the entire path mask and write to the 'paths' layer.

        Must be called *after* all drawing operations so that
        intersections and adjacent paths resolve their edges correctly.
        """
        for y in range(self._canvas.height):
            for x in range(self._canvas.width):
                if self._mask[y][x]:
                    gid = self._auto.resolve(self._mask, x, y, "dirt_path")
                    if gid:
                        self._canvas.set_tile("paths", x, y, gid)

    def nearest_path_tile(self, x: int, y: int) -> tuple[int, int] | None:
        """Find the nearest True tile on the path mask to (x, y).

        Used by structure_gen to connect doors to roads.
        """
        best = None
        best_dist = float("inf")
        # Search in expanding squares — usually finds something within 15 tiles
        max_search = 20
        for radius in range(1, max_search):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius:
                        continue  # only check the perimeter of each square
                    tx, ty = x + dx, y + dy
                    if (0 <= tx < self._canvas.width and
                            0 <= ty < self._canvas.height and
                            self._mask[ty][tx]):
                        d = dx * dx + dy * dy
                        if d < best_dist:
                            best_dist = d
                            best = (tx, ty)
            if best is not None:
                return best
        return None

    # ------------------------------------------------------------------
    # Chaikin subdivision
    # ------------------------------------------------------------------

    @staticmethod
    def _chaikin(points: list[tuple[float, float]],
                 iterations: int = 3) -> list[tuple[float, float]]:
        """Smooth a polyline using Chaikin corner cutting.

        Each iteration replaces every segment (P_i, P_{i+1}) with two new
        points:  Q = 0.75*P_i + 0.25*P_{i+1}
                 R = 0.25*P_i + 0.75*P_{i+1}

        The first and last points are preserved to keep endpoints fixed.
        """
        if len(points) < 2:
            return list(points)

        for _ in range(iterations):
            new_pts: list[tuple[float, float]] = [points[0]]
            for i in range(len(points) - 1):
                p0 = points[i]
                p1 = points[i + 1]
                q = (0.75 * p0[0] + 0.25 * p1[0],
                     0.75 * p0[1] + 0.25 * p1[1])
                r = (0.25 * p0[0] + 0.75 * p1[0],
                     0.25 * p0[1] + 0.75 * p1[1])
                new_pts.append(q)
                new_pts.append(r)
            new_pts.append(points[-1])
            points = new_pts

        return points

    # ------------------------------------------------------------------
    # Control point generation with noise displacement
    # ------------------------------------------------------------------

    def _make_control_points(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        noise_field: list[list[float]] | None,
        noise_strength: float,
        n_control: int,
    ) -> list[tuple[float, float]]:
        """Generate control points between start and end.

        Intermediate points are offset perpendicular to the line by noise
        values sampled from the noise field, producing organically curved
        paths that follow the terrain.
        """
        sx, sy = float(start[0]), float(start[1])
        ex, ey = float(end[0]), float(end[1])

        # Direction vector and perpendicular
        dx = ex - sx
        dy = ey - sy
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1.0:
            return [(sx, sy), (ex, ey)]

        # Unit perpendicular (rotated 90 degrees)
        perp_x = -dy / length
        perp_y = dx / length

        points: list[tuple[float, float]] = [(sx, sy)]

        for i in range(1, n_control + 1):
            t = i / (n_control + 1)
            mx = sx + dx * t
            my = sy + dy * t

            # Sample noise at this position for perpendicular displacement
            offset = 0.0
            if noise_field is not None and noise_strength > 0:
                nx = int(max(0, min(len(noise_field[0]) - 1, mx)))
                ny = int(max(0, min(len(noise_field) - 1, my)))
                # Noise is 0-1, centre it around 0 and scale
                noise_val = noise_field[ny][nx]
                offset = (noise_val - 0.5) * 2.0 * noise_strength

            # Add a small random jitter for variety
            offset += self._rng.gauss(0, 0.5)

            px = mx + perp_x * offset
            py = my + perp_y * offset

            # Clamp inside map
            px = max(1.0, min(float(self._canvas.width - 2), px))
            py = max(1.0, min(float(self._canvas.height - 2), py))

            points.append((px, py))

        points.append((ex, ey))
        return points

    # ------------------------------------------------------------------
    # Variable-width rasterization
    # ------------------------------------------------------------------

    def _rasterize_variable_width(
        self,
        curve: list[tuple[float, float]],
        w_start: float,
        w_end: float,
        w_mid: float,
    ):
        """Walk along the curve, stamping circles with varying radius.

        Width interpolates: w_start -> w_mid -> w_end using a smooth
        bell curve, so endpoints are wide and the middle is narrow.
        """
        n = len(curve)
        if n < 2:
            return

        for i, (cx, cy) in enumerate(curve):
            t = i / max(1, n - 1)  # 0 at start, 1 at end

            # Smooth width interpolation:
            # At t=0: w_start, at t=0.5: w_mid, at t=1: w_end
            # Use a parabolic blend
            if t < 0.5:
                # Blend start -> mid
                u = t * 2.0  # 0 to 1
                width = w_start + (w_mid - w_start) * u
            else:
                # Blend mid -> end
                u = (t - 0.5) * 2.0  # 0 to 1
                width = w_mid + (w_end - w_mid) * u

            radius = max(1.0, width / 2.0)
            self._stamp_circle(int(round(cx)), int(round(cy)), radius)

    def _stamp_circle(self, cx: int, cy: int, radius: float):
        """Paint a filled circle on the mask."""
        r_int = int(math.ceil(radius))
        r_sq = radius * radius
        for dy in range(-r_int, r_int + 1):
            for dx in range(-r_int, r_int + 1):
                if dx * dx + dy * dy <= r_sq:
                    tx, ty = cx + dx, cy + dy
                    if (0 <= tx < self._canvas.width and
                            0 <= ty < self._canvas.height):
                        self._mask[ty][tx] = True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bresenham(p0, p1) -> list[tuple[int, int]]:
        """Integer grid line between two points."""
        points = []
        x0, y0 = p0
        x1, y1 = p1
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            points.append((x0, y0))
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

        return points

    def _paint_width(self, centerline, width: int):
        """Expand a centerline to the given width on the mask."""
        half = width // 2
        for cx, cy in centerline:
            for dy in range(-half, half + 1):
                for dx in range(-half, half + 1):
                    tx, ty = cx + dx, cy + dy
                    if 0 <= tx < self._canvas.width and 0 <= ty < self._canvas.height:
                        self._mask[ty][tx] = True
