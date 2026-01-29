"""
Classic RPG-style dialogue box for NPC conversations.
Positioned at bottom of screen, advances via player input.
Supports branching dialogue with YES/NO choices.
"""
import pygame


class DialogueBox:
    """
    A classic RPG-style text box for displaying dialogue.
    - Positioned at bottom of screen
    - Text advances via player input (E, Enter, or Space)
    - Supports branching dialogue with choices
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
        self.dialogue_queue = []  # List of dialogue nodes to display
        self.current_text = ""
        self.speaker_name = ""

        # Text display
        self.displayed_chars = 0
        self.char_delay = 0.03  # Seconds between characters
        self.char_timer = 0
        self.text_complete = False

        # Choice state
        self.is_choice_mode = False
        self.choices = []  # List of {"label": str, "value": any}
        self.selected_choice = 0
        self.choice_callback = None  # Function to call with selected value
        self.choice_rects = []  # Store rects for mouse click detection

        # Colors
        self.bg_color = (20, 25, 35)
        self.border_color = (80, 90, 110)
        self.text_color = (230, 230, 230)
        self.speaker_color = (150, 200, 255)
        self.continue_color = (150, 150, 160)
        self.choice_color = (200, 200, 200)
        self.choice_selected_color = (255, 220, 100)
        self.choice_bg_color = (40, 45, 55)
        self.choice_selected_bg_color = (60, 70, 90)

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
        self.is_choice_mode = False
        self.choices = []
        self.choice_callback = None

        if isinstance(text, str):
            self.dialogue_queue = [text]
        else:
            self.dialogue_queue = list(text)

        self.speaker_name = speaker_name
        self._advance_to_next()

    def show_choice(self, prompt, choices, callback, speaker_name=""):
        """
        Show a dialogue with choices.

        Args:
            prompt: The question or prompt text
            choices: List of choice dicts with "label" and "value" keys
                     e.g., [{"label": "Yes", "value": True}, {"label": "No", "value": False}]
            callback: Function to call with the selected choice's value
            speaker_name: Optional speaker name
        """
        self._init_fonts()
        self.is_active = True
        self.is_choice_mode = False  # Start in text mode, switch to choice after text complete
        self.dialogue_queue = []
        self.current_text = prompt
        self.speaker_name = speaker_name
        self.displayed_chars = 0
        self.char_timer = 0
        self.text_complete = False

        # Store choices for after text is revealed
        self.choices = choices
        self.selected_choice = 0
        self.choice_callback = callback

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
        self.is_choice_mode = False
        self.choices = []
        self.choice_callback = None
        self.choice_rects = []

    def handle_input(self, input_handler=None):
        """
        Handle player input to advance dialogue or select choices.
        Returns True if input was consumed.

        Args:
            input_handler: Optional InputHandler (navigation handled externally in game.py)
        """
        if not self.is_active:
            return False

        # Choice mode input handling
        if self.is_choice_mode and self.choices:
            # E/Enter/Space confirms choice
            if self.choice_callback:
                selected_value = self.choices[self.selected_choice].get("value", self.selected_choice)
                callback = self.choice_callback
                self.close()
                callback(selected_value)
                return True

        # Normal text mode
        if self.text_complete:
            # If we have choices waiting, switch to choice mode
            if self.choices and not self.is_choice_mode:
                self.is_choice_mode = True
                return True
            # Otherwise advance to next page or close
            self._advance_to_next()
            return True
        else:
            # Skip to full text
            self.displayed_chars = len(self.current_text)
            self.text_complete = True
            return True

    def handle_mouse_click(self, mouse_x, mouse_y):
        """
        Handle mouse click on dialogue choices.
        Returns True if a choice was clicked and selected.
        """
        if not self.is_active or not self.is_choice_mode or not self.choices:
            return False

        # Check if click is on any choice rect
        for i, rect in enumerate(self.choice_rects):
            if rect.collidepoint(mouse_x, mouse_y):
                # Select and confirm this choice
                self.selected_choice = i
                if self.choice_callback:
                    selected_value = self.choices[self.selected_choice].get("value", self.selected_choice)
                    callback = self.choice_callback
                    self.close()
                    callback(selected_value)
                    return True
        return False

    def handle_navigation(self, direction):
        """
        Handle up/down navigation in choice mode.
        direction: -1 for up, 1 for down
        """
        if self.is_choice_mode and self.choices:
            self.selected_choice = (self.selected_choice + direction) % len(self.choices)

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

        # Draw choices or continue indicator
        if self.is_choice_mode and self.choices:
            self._render_choices(screen, box_x, box_width)
        elif self.text_complete:
            if self.choices:
                continue_text = "[Press E to see options]"
            elif self.dialogue_queue:
                continue_text = "[Press E to continue]"
            else:
                continue_text = "[Press E to close]"

            continue_surf = self.name_font.render(continue_text, True, self.continue_color)
            continue_x = box_x + box_width - continue_surf.get_width() - self.padding
            continue_y = self.box_y + self.box_height - continue_surf.get_height() - 10
            screen.blit(continue_surf, (continue_x, continue_y))

    def _render_choices(self, screen, box_x, box_width):
        """Render the choice options."""
        choice_y = self.box_y + self.box_height - 10

        # Calculate total height needed
        choice_height = 28
        total_height = len(self.choices) * choice_height + 10
        choice_y = self.box_y + self.box_height - total_height

        # Clear and rebuild choice rects for click detection
        self.choice_rects = []

        for i, choice in enumerate(self.choices):
            is_selected = (i == self.selected_choice)

            # Background for choice
            choice_rect = pygame.Rect(
                box_x + self.padding,
                choice_y + i * choice_height,
                box_width - self.padding * 2,
                choice_height - 4
            )

            # Store rect for click detection
            self.choice_rects.append(choice_rect)

            bg_color = self.choice_selected_bg_color if is_selected else self.choice_bg_color
            pygame.draw.rect(screen, bg_color, choice_rect, border_radius=4)

            # Selection indicator
            if is_selected:
                indicator = "> "
                text_color = self.choice_selected_color
            else:
                indicator = "  "
                text_color = self.choice_color

            # Choice text
            choice_text = indicator + choice.get("label", f"Option {i + 1}")
            choice_surf = self.font.render(choice_text, True, text_color)
            screen.blit(choice_surf, (box_x + self.padding + 8, choice_y + i * choice_height + 4))

        # Navigation hint
        hint_text = "[W/S or Click to select, E to confirm]"
        hint_surf = self.name_font.render(hint_text, True, self.continue_color)
        hint_x = box_x + box_width - hint_surf.get_width() - self.padding
        hint_y = choice_y - 20
        screen.blit(hint_surf, (hint_x, hint_y))

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
        max_lines = 2 if (self.is_choice_mode or self.choices) else 3
        for i, line in enumerate(lines[:max_lines]):
            if y + i * line_height > self.box_y + self.box_height - 20:
                break  # Don't overflow the box
            line_surf = self.font.render(line, True, self.text_color)
            screen.blit(line_surf, (x, y + i * line_height))


class DialogueTree:
    """
    Manages a tree of dialogue nodes for branching conversations.
    """

    def __init__(self, nodes=None):
        """
        Initialize with a dictionary of nodes.

        nodes format:
        {
            "start": {
                "text": "Hello, traveler.",
                "speaker": "Elder Mira",
                "next": "question"  # or None to end
            },
            "question": {
                "text": "Are you ready to leave the village?",
                "speaker": "Elder Mira",
                "choices": [
                    {"label": "Yes", "next": "yes_response"},
                    {"label": "No", "next": "no_response"}
                ]
            },
            "yes_response": {
                "text": "Be careful out there.",
                "speaker": "Elder Mira",
                "next": None
            },
            "no_response": {
                "text": "Take your time. There's no rush.",
                "speaker": "Elder Mira",
                "next": None
            }
        }
        """
        self.nodes = nodes or {}
        self.current_node_id = None

    def start(self, start_node="start"):
        """Start the dialogue from a specific node."""
        self.current_node_id = start_node
        return self.get_current_node()

    def get_current_node(self):
        """Get the current dialogue node."""
        if self.current_node_id is None:
            return None
        return self.nodes.get(self.current_node_id)

    def advance(self, choice_index=None):
        """
        Advance to the next node.

        Args:
            choice_index: If current node has choices, the index of the selected choice

        Returns:
            The next node, or None if dialogue is complete
        """
        node = self.get_current_node()
        if node is None:
            return None

        # Determine next node
        if "choices" in node and choice_index is not None:
            choices = node["choices"]
            if 0 <= choice_index < len(choices):
                self.current_node_id = choices[choice_index].get("next")
        else:
            self.current_node_id = node.get("next")

        return self.get_current_node()

    def is_complete(self):
        """Check if dialogue is complete."""
        return self.current_node_id is None or self.get_current_node() is None
