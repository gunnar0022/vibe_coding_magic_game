"""Seeded random number generator for reproducible map generation."""

from __future__ import annotations

import math
import random as _random


class SeededRNG:
    """Thin wrapper around random.Random for reproducible generation.

    Every mapgen component uses the same SeededRNG instance so that
    a single seed reproduces the entire map deterministically.
    """

    def __init__(self, seed: int = None):
        self.seed = seed if seed is not None else _random.randint(0, 2**32 - 1)
        self._rng = _random.Random(self.seed)
        self._noise_grids: dict[int, list[list[float]]] = {}

    # --- delegation --------------------------------------------------------
    def choice(self, seq):
        return self._rng.choice(seq)

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def random(self) -> float:
        return self._rng.random()

    def shuffle(self, seq):
        self._rng.shuffle(seq)

    def gauss(self, mu: float, sigma: float) -> float:
        return self._rng.gauss(mu, sigma)

    def sample(self, population, k: int):
        return self._rng.sample(population, k)

    def uniform(self, a: float, b: float) -> float:
        return self._rng.uniform(a, b)

    # --- value noise -------------------------------------------------------

    def _get_noise_grid(self, grid_size: int, octave: int) -> list[list[float]]:
        """Build (or cache) a random grid for a specific octave."""
        key = hash((grid_size, octave))
        if key not in self._noise_grids:
            # Deterministic sub-RNG so noise is stable regardless of call order
            sub = _random.Random(self.seed ^ (octave * 7919 + grid_size * 104729))
            grid = []
            for _ in range(grid_size + 2):
                grid.append([sub.random() for _ in range(grid_size + 2)])
            self._noise_grids[key] = grid
        return self._noise_grids[key]

    def noise2d(self, x: float, y: float, scale: float = 12.0,
                octaves: int = 3) -> float:
        """Multi-octave value noise in the range 0.0 - 1.0.

        Parameters
        ----------
        x, y     : world coordinates (tile positions).
        scale    : base wavelength in tiles.  Larger = smoother.
        octaves  : layers of detail.  More = more variation.

        Algorithm: for each octave, build a low-res random grid seeded
        deterministically, bilinearly interpolate between grid points,
        then layer octaves at decreasing amplitude / increasing frequency.
        """
        total = 0.0
        amplitude = 1.0
        frequency = 1.0
        max_value = 0.0

        for octave in range(octaves):
            # Scale coordinates into grid space for this octave
            freq_scale = scale / frequency
            gx = x / freq_scale
            gy = y / freq_scale

            # Grid coordinates
            ix = int(math.floor(gx))
            iy = int(math.floor(gy))
            fx = gx - ix
            fy = gy - iy

            # Smoothstep for smoother interpolation
            fx = fx * fx * (3.0 - 2.0 * fx)
            fy = fy * fy * (3.0 - 2.0 * fy)

            # Grid size needs to cover the range of ix/iy values
            grid_size = max(4, int(math.ceil(max(abs(ix) + 4, abs(iy) + 4))))
            grid = self._get_noise_grid(grid_size, octave)

            # Wrap indices into grid range
            ix0 = ix % len(grid)
            iy0 = iy % len(grid)
            ix1 = (ix + 1) % len(grid)
            iy1 = (iy + 1) % len(grid)

            # Bilinear interpolation
            v00 = grid[iy0][ix0]
            v10 = grid[iy0][ix1]
            v01 = grid[iy1][ix0]
            v11 = grid[iy1][ix1]

            top = v00 + (v10 - v00) * fx
            bot = v01 + (v11 - v01) * fx
            val = top + (bot - top) * fy

            total += val * amplitude
            max_value += amplitude
            amplitude *= 0.5
            frequency *= 2.0

        return total / max_value if max_value > 0 else 0.5

    def noise_field(self, width: int, height: int,
                    scale: float = 12.0, octaves: int = 3) -> list[list[float]]:
        """Generate a 2D noise field for the entire map.

        Returns a height×width grid of floats in [0, 1].
        """
        return [
            [self.noise2d(x, y, scale, octaves)
             for x in range(width)]
            for y in range(height)
        ]
