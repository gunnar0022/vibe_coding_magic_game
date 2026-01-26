"""
Classic RPG-style dialogue box for NPC conversations.
Positioned at bottom of screen, advances via player input.
"""
import pygame


class DialogueBox:
    """
    A classic RPG-style text box for displaying dialogue.
    - Positioned at bottom of screen
    - Text advances via player input (E, Enter, or Space)
    - No portraits, voice, or branching
    """

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Box dimensions
        self.box_height = 120
        self.box_margin = 20
        self.padding = 15

        # Position (bottom of screen, above any UI bars)
        self.box_y = screen_height - self.box_height - 80  # Above stats bar

        # State
        self.is_active = False
        self.dialogue_queue = []  # List of text strings to display
        self.current_text = ""
        self.speaker_name = ""

        # Text display
        self.displayed_chars = 0
        self.char_delay = 0.03  # Seconds between characters
        self.char_timer = 0
        self.text_complete = False

        # Colors
        self.bg_color = (20, 25, 35)
        self.border_color = (80, 90, 110)
        self.text_color = (230, 230, 230)
        self.speaker_color = (150, 200, 255)
        self.continue_color = (150, 150, 160)

        # Font
        self.font = None
        self.name_font = None

    def _init_fonts(self):
        """Initialize fonts if not already done."""
        if self.font is None:
            pygame.font.init()
            self.font = pygame.font.Font(None, 26)
            self.name_font = pygame.font.Font(None, 22)

    def show(self, text, speaker_name=""):
        """
        Start showing dialogue.
        text can be a string or list of strings for multi-page dialogue.
        """
        self._init_fonts()
        self.is_active = True

        if isinstance(text, str):
            self.dialogue_queue = [text]
        else:
            self.dialogue_queue = list(text)

        self.speaker_name = speaker_name
        self._advance_to_next()

    def _advance_to_next(self):
        """Advance to next dialogue in queue."""
        if self.dialogue_queue:
            self.current_text = self.dialogue_queue.pop(0)
            self.displayed_chars = 0
            self.char_timer = 0
            self.text_complete = False
        else:
            self.close()

    def close(self):
        """Close the dialogue box."""
        self.is_active = False
        self.current_text = ""
        self.dialogue_queue = []
        self.speaker_name = ""

    def handle_input(self):
        """
        Handle player input to advance dialogue.
        Returns True if input was consumed.
        """
        if not self.is_active:
            return False

        if self.text_complete:
            # Advance to next page or close
            self._advance_to_next()
            return True
        else:
            # Skip to full text
            self.displayed_chars = len(self.current_text)
            self.text_complete = True
            return True

    def update(self, dt):
        """Update text reveal animation."""
        if not self.is_active or self.text_complete:
            return

        self.char_timer += dt
        if self.char_timer >= self.char_delay:
            self.char_timer = 0
            self.displayed_chars += 1
            if self.displayed_chars >= len(self.current_text):
                self.displayed_chars = len(self.current_text)
                self.text_complete = True

    def render(self, screen):
        """Render the dialogue box."""
        if not self.is_active:
            return

        self._init_fonts()

        # Box dimensions
        box_x = self.box_margin
        box_width = self.screen_width - self.box_margin * 2

        # Draw background
        box_rect = pygame.Rect(box_x, self.box_y, box_width, self.box_height)
        pygame.draw.rect(screen, self.bg_color, box_rect, border_radius=8)
        pygame.draw.rect(screen, self.border_color, box_rect, 3, border_radius=8)

        # Draw speaker name if present
        text_y = self.box_y + self.padding
        if self.speaker_name:
            name_surf = self.name_font.render(self.speaker_name, True, self.speaker_color)
            screen.blit(name_surf, (box_x + self.padding, text_y))
            text_y += 25

        # Draw current text (word-wrapped, revealed character by character)
        visible_text = self.current_text[:self.displayed_chars]
        self._render_wrapped_text(screen, visible_text,
                                  box_x + self.padding,
                                  text_y,
                                  box_width - self.padding * 2)

        # Draw continue indicator if text is complete
        if self.text_complete:
            if self.dialogue_queue:
                continue_text = "[Press E to continue]"
            else:
                continue_text = "[Press E to close]"

            continue_surf = self.name_font.render(continue_text, True, self.continue_color)
            continue_x = box_x + box_width - continue_surf.get_width() - self.padding
            continue_y = self.box_y + self.box_height - continue_surf.get_height() - 10
            screen.blit(continue_surf, (continue_x, continue_y))

    def _render_wrapped_text(self, screen, text, x, y, max_width):
        """Render text with word wrapping."""
        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + word + " "
            test_surf = self.font.render(test_line, True, self.text_color)

            if test_surf.get_width() <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.rstrip())
                current_line = word + " "

        if current_line:
            lines.append(current_line.rstrip())

        # Render each line
        line_height = self.font.get_linesize()
        for i, line in enumerate(lines):
            if y + i * line_height > self.box_y + self.box_height - 20:
                break  # Don't overflow the box
            line_surf = self.font.render(line, True, self.text_color)
            screen.blit(line_surf, (x, y + i * line_height))
