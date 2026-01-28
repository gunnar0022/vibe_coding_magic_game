"""
Hand occupancy component for tracking what the player is holding.
Supports both summoned (magic) and physical (inventory) weapons.
"""
from .base import Component


class HandOccupancyComponent(Component):
    """
    Tracks hand occupancy for spellcasting and weapon usage.

    Players have two hands. Casting spells requires at least one free hand.
    Summoned and physical weapons occupy one or two hands depending on type.
    Only one weapon (of either kind) at a time.
    """

    def __init__(self):
        super().__init__()
        # What each hand is holding (None = free, "summoned", "physical")
        self.left_hand = None
        self.right_hand = None

        # Reference to currently summoned weapon (only one allowed)
        self.summoned_weapon = None

        # Reference to currently equipped physical weapon (PhysicalWeapon entity)
        self.physical_weapon = None

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
        """Check if player is currently holding any weapon."""
        return self.summoned_weapon is not None or self.physical_weapon is not None

    def get_weapon(self):
        """Get the currently held weapon (summoned or physical), if any."""
        return self.summoned_weapon or self.physical_weapon

    def equip_weapon(self, weapon):
        """
        Equip a summoned weapon, occupying the required hands.
        Dismisses any existing summoned weapon first.
        If a physical weapon is held, drops it and returns it
        (caller must spawn ground item).

        Returns:
            The dropped PhysicalWeapon, or None
        """
        dropped_physical = None

        # Drop physical weapon if held
        if self.physical_weapon is not None:
            dropped_physical = self.drop_physical_weapon()

        # Dismiss any existing summoned weapon
        if self.summoned_weapon is not None:
            self.dismiss_weapon()

        hands_needed = getattr(weapon, 'hands_required', 1)

        if hands_needed >= 2:
            self.left_hand = "summoned"
            self.right_hand = "summoned"
        else:
            self.right_hand = "summoned"

        self.summoned_weapon = weapon
        return dropped_physical

    def dismiss_weapon(self):
        """
        Dismiss the currently held summoned weapon, freeing hands.

        Returns:
            The dismissed weapon, or None if no summoned weapon was held
        """
        if self.summoned_weapon is None:
            return None

        weapon = self.summoned_weapon

        # Free hands that were holding the summoned weapon
        if self.left_hand == "summoned":
            self.left_hand = None
        if self.right_hand == "summoned":
            self.right_hand = None

        self.summoned_weapon = None
        return weapon

    def equip_physical_weapon(self, physical_weapon):
        """
        Equip a physical weapon (PhysicalWeapon entity).
        Dismisses summoned weapon if any.

        Args:
            physical_weapon: PhysicalWeapon entity to equip
        """
        # Dismiss summoned weapon first
        if self.summoned_weapon is not None:
            self.dismiss_weapon()

        # Drop existing physical weapon if any
        if self.physical_weapon is not None:
            self.drop_physical_weapon()

        hands_needed = getattr(physical_weapon, 'hands_required', 1)
        if hands_needed >= 2:
            self.left_hand = "physical"
            self.right_hand = "physical"
        else:
            self.right_hand = "physical"

        self.physical_weapon = physical_weapon

    def drop_physical_weapon(self):
        """
        Drop the currently held physical weapon, freeing hands.

        Returns:
            The dropped PhysicalWeapon, or None
        """
        if self.physical_weapon is None:
            return None

        pw = self.physical_weapon

        if self.left_hand == "physical":
            self.left_hand = None
        if self.right_hand == "physical":
            self.right_hand = None

        self.physical_weapon = None
        return pw

    def get_hands_used_by_weapon(self):
        """Get the number of hands used by the current weapon."""
        weapon = self.get_weapon()
        if weapon is None:
            return 0
        return getattr(weapon, 'hands_required', 1)

    def serialize(self):
        """Serialize hand occupancy state."""
        data = {
            "left_hand": self.left_hand,
            "right_hand": self.right_hand,
            # Summoned weapons don't persist between saves
        }
        # Physical weapon persists via inventory equipped_weapon slot
        return data

    def deserialize(self, data):
        """Deserialize hand occupancy state."""
        # On load, hands are free (summoned weapons don't persist)
        # Physical weapon is re-equipped from inventory.equipped_weapon in game.py
        self.left_hand = None
        self.right_hand = None
        self.summoned_weapon = None
        self.physical_weapon = None
