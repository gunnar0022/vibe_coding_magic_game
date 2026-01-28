"""
Stats component for living entities.
"""
from .base import Component


class StatsComponent(Component):
    """Manages health, stamina, mana, and resistances for actors."""

    def __init__(self, health=100, max_health=100, stamina=100, max_stamina=100, mana=100, max_mana=100):
        super().__init__()
        self.health = health
        self.max_health = max_health
        self.stamina = stamina
        self.max_stamina = max_stamina
        self.mana = mana
        self.max_mana = max_mana

        # Mana regeneration settings
        # Base rate: mana per second
        self.mana_regen_base = 2.0
        # Multiplier for modifiers (environmental, status, etc.)
        # Default 1.0, can be modified by future systems
        self.mana_regen_multiplier = 1.0

        # Resistances (0.0 = no resistance, 1.0 = immune, negative = weakness)
        self.resistances = {
            "fire": 0.0,
            "water": 0.0,
            "earth": 0.0,
            "wind": 0.0,
            "physical": 0.0,
            "poison": 0.0,
            "psychic": 0.0
        }

    def is_alive(self):
        return self.health > 0

    def take_damage(self, amount, damage_type="physical"):
        """Apply damage after resistance calculation."""
        resistance = self.resistances.get(damage_type, 0.0)
        actual_damage = amount * (1.0 - resistance)
        self.health = max(0, self.health - actual_damage)
        return actual_damage

    def heal(self, amount):
        """Heal health up to max."""
        self.health = min(self.max_health, self.health + amount)
        return amount

    def use_mana(self, amount):
        """Consume mana, returns True if successful."""
        if self.mana >= amount:
            self.mana -= amount
            return True
        return False

    def restore_mana(self, amount):
        """Restore mana up to max."""
        self.mana = min(self.max_mana, self.mana + amount)

    def use_stamina(self, amount):
        """Consume stamina, returns True if successful."""
        if self.stamina >= amount:
            self.stamina -= amount
            return True
        return False

    def restore_stamina(self, amount):
        """Restore stamina up to max."""
        self.stamina = min(self.max_stamina, self.stamina + amount)

    def update(self, dt):
        """
        Update stats over time.
        Handles continuous mana regeneration.
        """
        # Mana regeneration
        if self.mana < self.max_mana:
            regen_amount = self.mana_regen_base * self.mana_regen_multiplier * dt
            self.mana = min(self.max_mana, self.mana + regen_amount)

    def get_effective_mana_regen(self):
        """Get current effective mana regeneration rate per second."""
        return self.mana_regen_base * self.mana_regen_multiplier

    def serialize(self):
        return {
            "health": self.health,
            "max_health": self.max_health,
            "stamina": self.stamina,
            "max_stamina": self.max_stamina,
            "mana": self.mana,
            "max_mana": self.max_mana,
            "mana_regen_base": self.mana_regen_base,
            "mana_regen_multiplier": self.mana_regen_multiplier,
            "resistances": self.resistances.copy()
        }

    def deserialize(self, data):
        self.health = data.get("health", 100)
        self.max_health = data.get("max_health", 100)
        self.stamina = data.get("stamina", 100)
        self.max_stamina = data.get("max_stamina", 100)
        self.mana = data.get("mana", 100)
        self.max_mana = data.get("max_mana", 100)
        self.mana_regen_base = data.get("mana_regen_base", 2.0)
        self.mana_regen_multiplier = data.get("mana_regen_multiplier", 1.0)
        self.resistances.update(data.get("resistances", {}))
