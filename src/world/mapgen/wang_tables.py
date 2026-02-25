"""Compiled Wang corner auto-tile lookup tables.

Derived directly from Ground_grass.tsx wangset data.  Each table maps
a 4-bit corner key to a list of tileset-local tile IDs (multiple entries
= visual variants chosen randomly for natural-looking terrain).

Corner key encoding
-------------------
    key = (TL << 3) | (TR << 2) | (BR << 1) | BL

    TL = top-left corner is terrain (1) or base (0)
    TR = top-right
    BR = bottom-right
    BL = bottom-left

Wang corner semantics
---------------------
A corner is 1 ("terrain") when the tile AND both orthogonal neighbours
AND the diagonal neighbour at that corner are all terrain.  Otherwise 0.

All local IDs reference the ``ground_grass_forest`` tileset (firstgid=1).
"""

# ── "Grassy Leafy Area" wangset ──────────────────────────────────────────
# Terrain-1 = leafy grass   |   Base = plain grass
# Two visual variant sets (tiles 0-46 and 114-156) for richness.

LEAFY_AREA: dict[int, list[int]] = {
    0:  [],                             # 0000  all grass  → use base fill GID
    1:  [2, 116],                       # 0001  BL
    2:  [0, 114],                       # 0010  BR
    3:  [1, 26, 27, 115, 140, 141],     # 0011  BR+BL  (bottom edge)
    4:  [38, 152],                      # 0100  TR
    5:  [20, 134],                      # 0101  TR+BL  (diagonal — fallback full)
    6:  [19, 117, 133],                 # 0110  TR+BR  (right edge)
    7:  [42, 156],                      # 0111  TR+BR+BL  (inner corner TL)
    8:  [40, 154],                      # 1000  TL
    9:  [21, 135],                      # 1001  TL+BL  (left edge)
    10: [20, 134],                      # 1010  TL+BR  (diagonal — fallback full)
    11: [41, 155],                      # 1011  TL+BR+BL  (inner corner TR)
    12: [39, 45, 46, 153],              # 1100  TL+TR  (top edge)
    13: [22, 136],                      # 1101  TL+TR+BL  (inner corner BR)
    14: [23, 137],                      # 1110  TL+TR+BR  (inner corner BL)
    15: [20, 134],                      # 1111  all leafy  (full fill)
}


# ── "Dirt Path" wangset ──────────────────────────────────────────────────
# Terrain-1 = dirt path   |   Base = plain grass

DIRT_PATH: dict[int, list[int]] = {
    0:  [],                             # 0000  all grass  → use base fill GID
    1:  [59],                           # 0001  BL
    2:  [57],                           # 0010  BR
    3:  [58, 83, 84],                   # 0011  BR+BL  (bottom edge)
    4:  [95],                           # 0100  TR
    5:  [77],                           # 0101  TR+BL  (diagonal — fallback full)
    6:  [60, 76],                       # 0110  TR+BR  (right edge)
    7:  [99],                           # 0111  TR+BR+BL  (inner corner TL)
    8:  [97],                           # 1000  TL
    9:  [78],                           # 1001  TL+BL  (left edge)
    10: [77],                           # 1010  TL+BR  (diagonal — fallback full)
    11: [98],                           # 1011  TL+BR+BL  (inner corner TR)
    12: [96, 102, 103],                 # 1100  TL+TR  (top edge)
    13: [79],                           # 1101  TL+TR+BL  (inner corner BR)
    14: [80],                           # 1110  TL+TR+BR  (inner corner BL)
    15: [77],                           # 1111  all dirt  (full fill)
}


# ── "Cliff" wangset (2-colour) ──────────────────────────────────────────
# Terrain-1 = red cliff    |   Terrain-2 = green ground
# Currently only full-fill entries exist.  Kept for future expansion.

CLIFF_RED_FILL: list[int] = [36, 37, 55, 56, 74, 75]
CLIFF_GREEN_FILL: list[int] = [9, 10, 17, 18, 28, 29, 47, 48]


# ── Convenience: base grass fill GID ─────────────────────────────────────
# Local tile 267 in ground_grass_forest → global GID 268
BASE_GRASS_LOCAL = 267
BASE_GRASS_GID = 268
