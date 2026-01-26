"""
Interaction component for entities that can be interacted with.
"""
from .base import Component


class InteractionComponent(Component):
    """Handles interaction capabilities - dialogue, examination, reactions."""

    def __init__(self):
        super().__init__()
        # What interactions are available
        self.can_talk = False
        self.can_examine = True
        self.can_attack = False

        # Dialogue ID if NPC
        self.dialogue_id = None

        # Examination text
        self.examine_text = "You see nothing special."

        # Interaction range (in tiles)
        self.interaction_range = 1

        # Callback names for custom interactions
        self.on_interact = None
        self.on_examine = None

    def set_dialogue(self, dialogue_id):
        """Set dialogue tree for this entity."""
        self.dialogue_id = dialogue_id
        self.can_talk = dialogue_id is not None

    def set_examine_text(self, text):
        """Set the examination description."""
        self.examine_text = text

    def get_available_actions(self):
        """Get list of available interaction types."""
        actions = []
        if self.can_examine:
            actions.append("examine")
        if self.can_talk:
            actions.append("talk")
        if self.can_attack:
            actions.append("attack")
        return actions

    def serialize(self):
        return {
            "can_talk": self.can_talk,
            "can_examine": self.can_examine,
            "can_attack": self.can_attack,
            "dialogue_id": self.dialogue_id,
            "examine_text": self.examine_text,
            "interaction_range": self.interaction_range
        }

    def deserialize(self, data):
        self.can_talk = data.get("can_talk", False)
        self.can_examine = data.get("can_examine", True)
        self.can_attack = data.get("can_attack", False)
        self.dialogue_id = data.get("dialogue_id")
        self.examine_text = data.get("examine_text", "You see nothing special.")
        self.interaction_range = data.get("interaction_range", 1)
