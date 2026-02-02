"""
Animation controller — tracks current animation state, frame index, timing.
"""

# Per-state animation metadata for slimes.
# fps: playback speed, frame_count: frames in the row, loop: whether it repeats
SLIME_ANIMATIONS = {
    "idle":   {"fps": 8,  "frame_count": 6,  "loop": True},
    "walk":   {"fps": 10, "frame_count": 8,  "loop": True},
    "run":    {"fps": 12, "frame_count": 8,  "loop": True},
    "hurt":   {"fps": 10, "frame_count": 5,  "loop": False},
    "death":  {"fps": 10, "frame_count": 10, "loop": False},
    "attack": {"fps": 12, "frame_count": 10, "loop": False},
}

# Skeleton: 4-row, 64x64 frames
SKELETON_ANIMATIONS = {
    "idle":   {"fps": 8,  "frame_count": 4,  "loop": True},
    "walk":   {"fps": 10, "frame_count": 6,  "loop": True},
    "run":    {"fps": 12, "frame_count": 8,  "loop": True},
    "hurt":   {"fps": 10, "frame_count": 4,  "loop": False},
    "death":  {"fps": 10, "frame_count": 6,  "loop": False},
    "attack": {"fps": 12, "frame_count": 9,  "loop": False},
}

# Ghost: 4-row, 64x64 frames
GHOST_ANIMATIONS = {
    "idle":   {"fps": 8,  "frame_count": 4,  "loop": True},
    "walk":   {"fps": 10, "frame_count": 6,  "loop": True},
    "run":    {"fps": 12, "frame_count": 6,  "loop": True},
    "hurt":   {"fps": 10, "frame_count": 4,  "loop": False},
    "death":  {"fps": 10, "frame_count": 9,  "loop": False},
    "attack": {"fps": 12, "frame_count": 12, "loop": False},
}

# Golem: 4-row, 128x128 frames
GOLEM_ANIMATIONS = {
    "idle":   {"fps": 8,  "frame_count": 4,  "loop": True},
    "walk":   {"fps": 10, "frame_count": 8,  "loop": True},
    "run":    {"fps": 12, "frame_count": 8,  "loop": True},
    "hurt":   {"fps": 10, "frame_count": 4,  "loop": False},
    "death":  {"fps": 10, "frame_count": 8,  "loop": False},
    "attack": {"fps": 12, "frame_count": 9,  "loop": False},
}

# NPC animations: 4-row, 32x32 frame sprites (idle + walk only)
# Citizen idle sheets: 384x128 = 12 cols x 4 rows @32
# Citizen walk sheets: 192x128 = 6 cols x 4 rows @32
NPC_ANIMATIONS = {
    "idle": {"fps": 6, "frame_count": 12, "loop": True},
    "walk": {"fps": 8, "frame_count": 6, "loop": True},
}

# Herbalist NPC: 4-row, 32x32 frames
# Herbalist sheets: 192x128 = 6 cols x 4 rows @32
NPC_HERBALIST_ANIMATIONS = {
    "idle": {"fps": 6, "frame_count": 6, "loop": True},
    "walk": {"fps": 8, "frame_count": 6, "loop": True},
}

# Player animations: 4-row, 32x32 Fighter2 sprite (idle/walk)
# Fighter2_Idle: 384x128 = 12 cols x 4 rows @32
# Fighter2_Walk: 192x128 = 6 cols x 4 rows @32
PLAYER_ANIMATIONS = {
    "idle": {"fps": 6, "frame_count": 12, "loop": True},
    "walk": {"fps": 8, "frame_count": 6, "loop": True},
}

# Direction string → sprite-sheet row mapping (down/up/right/left layout)
# Used by enemy sprites (64x64 frames)
DIRECTION_ROW = {
    "down": 0,
    "up": 1,
    "right": 2,
    "left": 3,
}

# 32x32 NPC/player sprites use down/left/right/up row order
NPC_DIRECTION_ROW = {
    "down": 0,
    "left": 1,
    "right": 2,
    "up": 3,
}

class AnimationController:
    """Drives frame-by-frame animation for a single entity."""

    def __init__(self, animations=None, direction_map=None):
        self.animations = animations or SLIME_ANIMATIONS
        self.direction_map = direction_map or DIRECTION_ROW
        self.current_animation = "idle"
        self.frame_index = 0
        self.elapsed = 0.0
        self.direction_row = 0  # default: facing down
        self.finished = False

    # ------------------------------------------------------------------
    def set_animation(self, name):
        """Switch to a new animation state. Idempotent if already active."""
        if name == self.current_animation:
            return
        if name not in self.animations:
            return
        self.current_animation = name
        self.frame_index = 0
        self.elapsed = 0.0
        self.finished = False

    def set_facing(self, direction):
        """Map a direction string to the correct sprite-sheet row."""
        self.direction_row = self.direction_map.get(direction, 0)

    # ------------------------------------------------------------------
    def update(self, dt):
        """Advance the animation timer and frame index."""
        if self.finished:
            return

        anim = self.animations.get(self.current_animation)
        if anim is None:
            return

        fps = anim["fps"]
        frame_count = anim["frame_count"]
        loop = anim["loop"]

        self.elapsed += dt
        frame_duration = 1.0 / fps

        while self.elapsed >= frame_duration:
            self.elapsed -= frame_duration
            self.frame_index += 1

            if self.frame_index >= frame_count:
                if loop:
                    self.frame_index = 0
                else:
                    self.frame_index = frame_count - 1
                    self.finished = True
                    break

    # ------------------------------------------------------------------
    @property
    def row(self):
        return self.direction_row

    @property
    def col(self):
        return self.frame_index
