"""
Hand occupancy component for tracking what the player is holding.
"""
from .base import Component


class HandOccupancyComponent(Component):
    """
    Tracks hand occupancy for spellcasting and weapon usage.

    Players have two hands. Casting spells requires at least one free hand.
    Summoned weapons occupy one or two hands depending on type.
    """

    def __init__(self):
        super().__init__()
        # What each hand is holding (None = free)
        self.left_hand = None
        self.right_hand = None

        # Reference to currently summoned weapon (only one allowed)
        self.summoned_weapon = None

    def get_free_hand_count(self):
        """Get the number of free hands."""
        count = 0
        if self.left_hand is None:
            count += 1
        if self.right_hand is None:
            count += 1
        return count

    def has_free_hand(self):
        """Check if at least one hand is free."""
        return self.get_free_hand_count() > 0

    def can_cast(self):
        """Check if player can cast spells (needs at least one free hand)."""
        return self.has_free_hand()

    def is_holding_weapon(self):
        """Check if player is currently holding a summoned weapon."""
        return self.summoned_weapon is not None

    def get_weapon(self):
        """Get the currently held weapon, if any."""
        return self.summoned_weapon

    def equip_weapon(self, weapon):
        """
        Equip a summoned weapon, occupying the required hands.
        Dismisses any existing weapon first.

        Args:
            weapon: The weapon to equip (must have hands_required attribute)

        Returns:
            True if weapon was equipped successfully
        """
        # Dismiss any existing weapon first
        if self.summoned_weapon is not None:
            self.dismiss_weapon()

        hands_needed = getattr(weapon, 'hands_required', 1)

        if hands_needed >= 2:
            # Two-handed weapon - occupy both hands
            self.left_hand = "weapon"
            self.right_hand = "weapon"
        else:
            # One-handed weapon - occupy primary hand (right)
            self.right_hand = "weapon"

        self.summoned_weapon = weapon
        return True

    def dismiss_weapon(self):
        """
        Dismiss the currently held weapon, freeing hands.

        Returns:
            The dismissed weapon, or None if no weapon was held
        """
        if self.summoned_weapon is None:
            return None

        weapon = self.summoned_weapon

        # Free hands that were holding the weapon
        if self.left_hand == "weapon":
            self.left_hand = None
        if self.right_hand == "weapon":
            self.right_hand = None

        self.summoned_weapon = None
        return weapon

    def get_hands_used_by_weapon(self):
        """Get the number of hands used by the current weapon."""
        if self.summoned_weapon is None:
            return 0
        return getattr(self.summoned_weapon, 'hands_required', 1)

    def serialize(self):
        """Serialize hand occupancy state."""
        return {
            "left_hand": self.left_hand,
            "right_hand": self.right_hand,
            # Note: summoned_weapon is not serialized - weapons despawn on save/load
        }

    def deserialize(self, data):
        """Deserialize hand occupancy state."""
        # On load, hands are free (weapons don't persist)
        self.left_hand = None
        self.right_hand = None
        self.summoned_weapon = None
