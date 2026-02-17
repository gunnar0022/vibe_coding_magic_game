"""
Tiled map visual data — holds per-layer GID grids and a tileset sprite atlas.

Used alongside the collision tile grid (world.tiles) so that TMX maps render
with their actual pixel-art tilesets while JSON maps fall back to colored
rectangles.
"""
import os
import pygame


# Upper 3 bits of a Tiled GID encode flip flags.  Mask them off before lookup.
_GID_MASK = 0x1FFFFFFF


class TilesetAtlas:
    """
    Loads tileset PNG spritesheets, scales them 2x (16px -> 32px), and maps
    raw Tiled GIDs to individual 32x32 pygame.Surface tiles.
    """

    def __init__(self):
        # Each entry: (firstgid, lastgid, columns, scaled_surface)
        self._tilesets = []
        # GID -> Surface cache (populated on first access)
        self._cache = {}

    def add_tileset(self, firstgid, image_path, tile_w, tile_h, columns, tilecount):
        """
        Register a tileset.

        Args:
            firstgid: First global tile ID for this tileset.
            image_path: Absolute path to the tileset PNG.
            tile_w, tile_h: Original tile dimensions (expected 16x16).
            columns: Number of tile columns in the spritesheet.
            tilecount: Total number of tiles in the tileset.
        """
        if not os.path.exists(image_path):
            print(f"[TilesetAtlas] WARNING: tileset image not found: {image_path}")
            return

        raw_surface = pygame.image.load(image_path).convert_alpha()

        # Scale 2x with nearest-neighbor for crisp pixel art
        scaled_w = raw_surface.get_width() * 2
        scaled_h = raw_surface.get_height() * 2
        scaled_surface = pygame.transform.scale(raw_surface, (scaled_w, scaled_h))

        lastgid = firstgid + tilecount - 1

        self._tilesets.append((firstgid, lastgid, columns, tile_w * 2, tile_h * 2, scaled_surface))

        # Keep sorted by firstgid for binary-search-friendly lookups
        self._tilesets.sort(key=lambda t: t[0])

    def get_sprite(self, raw_gid):
        """
        Get the 32x32 sprite surface for a raw Tiled GID.

        Returns None for GID 0 (empty tile) or unknown GIDs.
        """
        gid = raw_gid & _GID_MASK
        if gid == 0:
            return None

        if gid in self._cache:
            return self._cache[gid]

        sprite = self._lookup_sprite(gid)
        self._cache[gid] = sprite
        return sprite

    def _lookup_sprite(self, gid):
        """Find the tileset containing this GID and extract the sprite."""
        for firstgid, lastgid, columns, tw, th, surface in self._tilesets:
            if firstgid <= gid <= lastgid:
                local_id = gid - firstgid
                col = local_id % columns
                row = local_id // columns
                x = col * tw
                y = row * th
                # Bounds check against scaled surface
                if x + tw <= surface.get_width() and y + th <= surface.get_height():
                    return surface.subsurface(pygame.Rect(x, y, tw, th))
                return None
        return None


class TiledLayerData:
    """One visual tile layer's raw GID grid with optional pixel offset."""

    def __init__(self, name, width, height, gids, offset_x=0.0, offset_y=0.0):
        """
        Args:
            name: Layer name from Tiled (e.g. "background", "paths", "Trees").
            width, height: Grid dimensions in tiles.
            gids: 2D list [y][x] of raw integer GIDs.
            offset_x, offset_y: Pixel offset (already scaled to game coords).
        """
        self.name = name
        self.width = width
        self.height = height
        self.gids = gids
        self.offset_x = offset_x
        self.offset_y = offset_y

    def get_gid(self, x, y):
        """Get the raw GID at tile position (x, y). Returns 0 if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.gids[y][x]
        return 0


class TiledMapData:
    """
    Top-level container for Tiled visual data.

    Holds a TilesetAtlas (GID -> sprite lookup) and an ordered list of
    TiledLayerData (bottom-to-top rendering order).
    """

    def __init__(self):
        self.atlas = TilesetAtlas()
        self.layers = []  # List[TiledLayerData], ordered bottom-to-top

    def get_sprite(self, raw_gid):
        """Convenience: delegate to atlas."""
        return self.atlas.get_sprite(raw_gid)
