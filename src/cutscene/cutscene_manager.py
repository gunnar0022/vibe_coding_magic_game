"""
CutsceneManager — state machine that drives sequential cutscene playback.
"""


class CutsceneManager:
    """Drives a list of CutsceneAction objects sequentially."""

    def __init__(self, game):
        self.game = game
        self.active = False
        self.actions = []
        self.current_index = 0
        self.ctx = {}

    def start(self, action_list):
        """Begin a cutscene with the given action list."""
        if self.active:
            return  # Don't interrupt a running cutscene

        self.actions = action_list
        self.current_index = 0
        self.ctx = {
            "game": self.game,
            "entities": {},
        }
        self.active = True

        # Detach camera from player so actions can drive it
        self.game.camera.target = None

        # Start the first action
        if self.actions:
            self.actions[0].start(self.ctx)

    def update(self, dt):
        """Tick the current action; advance when done."""
        if not self.active:
            return

        if self.current_index >= len(self.actions):
            self._finish()
            return

        action = self.actions[self.current_index]
        done = action.update(self.ctx, dt)

        if done:
            action.cleanup(self.ctx)
            self.current_index += 1
            if self.current_index < len(self.actions):
                self.actions[self.current_index].start(self.ctx)
            else:
                self._finish()

    def _finish(self):
        """End the cutscene and restore normal gameplay."""
        self.active = False
        self.actions = []
        self.current_index = 0

        # Re-attach camera to player if not already
        player = self.game.player
        if player and self.game.camera.target is None:
            self.game.camera.set_target(player)

    def reset(self):
        """Hard-reset the cutscene manager (e.g., on world reset)."""
        self.active = False
        self.actions = []
        self.current_index = 0
        self.ctx = {}
