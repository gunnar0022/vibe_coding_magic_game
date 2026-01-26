"""
Input handling system.
Updated to support hold-to-open magic menu behavior.
"""
import pygame


class InputHandler:
    """Handles keyboard and mouse input."""

    def __init__(self):
        # Movement keys
        self.move_up = False
        self.move_down = False
        self.move_left = False
        self.move_right = False

        # Action keys (single-frame triggers)
        self.interact = False
        self.open_notebook = False
        self.open_magic_menu = False
        self.cancel = False
        self.introspect = False  # I key for spell introspection

        # SPACE key state for magic menu (hold behavior)
        self.space_held = False
        self.space_just_pressed = False
        self.space_just_released = False

        # Mouse state
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_clicked = False
        self.mouse_right_clicked = False

        # Key events this frame
        self.key_just_pressed = set()
        self.key_just_released = set()

    def update(self, events):
        """Process input events for this frame."""
        # Reset single-frame states
        self.interact = False
        self.cancel = False
        self.introspect = False
        self.mouse_clicked = False
        self.mouse_right_clicked = False
        self.space_just_pressed = False
        self.space_just_released = False
        self.key_just_pressed.clear()
        self.key_just_released.clear()

        # Get continuous key states
        keys = pygame.key.get_pressed()
        self.move_up = keys[pygame.K_w] or keys[pygame.K_UP]
        self.move_down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        self.move_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        self.move_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]

        # Track space held state
        was_space_held = self.space_held
        self.space_held = keys[pygame.K_SPACE]

        # Process events
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.key_just_pressed.add(event.key)

                # Single-press actions
                if event.key == pygame.K_e or event.key == pygame.K_RETURN:
                    self.interact = True
                if event.key == pygame.K_n:
                    self.open_notebook = not self.open_notebook
                if event.key == pygame.K_m:
                    self.open_magic_menu = not self.open_magic_menu
                if event.key == pygame.K_ESCAPE:
                    self.cancel = True
                if event.key == pygame.K_i:
                    self.introspect = True
                if event.key == pygame.K_SPACE:
                    self.space_just_pressed = True

            elif event.type == pygame.KEYUP:
                self.key_just_released.add(event.key)

                if event.key == pygame.K_SPACE:
                    self.space_just_released = True

            elif event.type == pygame.MOUSEMOTION:
                self.mouse_x, self.mouse_y = event.pos

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.mouse_clicked = True
                elif event.button == 3:
                    self.mouse_right_clicked = True

    def get_movement_direction(self):
        """Get normalized movement direction."""
        dx = 0
        dy = 0

        if self.move_up:
            dy = -1
        elif self.move_down:
            dy = 1

        if self.move_left:
            dx = -1
        elif self.move_right:
            dx = 1

        return dx, dy

    def was_key_pressed(self, key):
        """Check if a key was just pressed this frame."""
        return key in self.key_just_pressed

    def was_key_released(self, key):
        """Check if a key was just released this frame."""
        return key in self.key_just_released

    def get_mouse_position(self):
        """Get current mouse position."""
        return self.mouse_x, self.mouse_y
