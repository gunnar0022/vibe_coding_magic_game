"""
Stats component for living entities.

Mana is now environmental (shared per-area pools managed by ManaPoolManager).
Personal mana fields are removed. Corruption accumulator tracks health-casting.
"""
from .base import Component


class StatsComponent(Component):
    """Manages health, stamina, and resistances for actors.
    Mana is environmental — see world.mana_pool.ManaPoolManager."""

    def __init__(self, health=100, max_health=100, stamina=100, max_stamina=100):
        super().__init__()
        self.health = health
        self.max_health = max_health
        self.stamina = stamina
        self.max_stamina = max_stamina

        # Stamina regeneration settings
        self.stamina_regen_base = 8.0    # per second
        self.stamina_regen_multiplier = 1.0

        # Hidden corruption stat — tracks mana spent from self (health-casting).
        # Drives hollowing. The player never sees this directly.
        self.corruption_accumulator = 0.0

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

    def use_stamina(self, amount):
        """Consume stamina. Shortfall draws from health at 1 HP = 4 stamina.
        Always returns True (action proceeds; player may die)."""
        if self.stamina >= amount:
            self.stamina -= amount
        else:
            shortfall = amount - self.stamina
            self.stamina = 0
            hp_cost = shortfall / 4.0
            self.health = max(0, self.health - hp_cost)
        return True

    def restore_stamina(self, amount):
        """Restore stamina up to max."""
        self.stamina = min(self.max_stamina, self.stamina + amount)

    def update(self, dt):
        """Update stats over time. Handles stamina regeneration.
        Mana regen is handled by ManaPoolManager at the area level."""
        # Stamina regeneration
        if self.stamina < self.max_stamina:
            stam_regen = self.stamina_regen_base * self.stamina_regen_multiplier * dt
            self.stamina = min(self.max_stamina, self.stamina + stam_regen)

    def serialize(self):
        return {
            "health": self.health,
            "max_health": self.max_health,
            "stamina": self.stamina,
            "max_stamina": self.max_stamina,
            "stamina_regen_base": self.stamina_regen_base,
            "stamina_regen_multiplier": self.stamina_regen_multiplier,
            "corruption_accumulator": self.corruption_accumulator,
            "resistances": self.resistances.copy()
        }

    def deserialize(self, data):
        self.health = data.get("health", 100)
        self.max_health = data.get("max_health", 100)
        self.stamina = data.get("stamina", 100)
        self.max_stamina = data.get("max_stamina", 100)
        self.stamina_regen_base = data.get("stamina_regen_base", 8.0)
        self.stamina_regen_multiplier = data.get("stamina_regen_multiplier", 1.0)
        self.corruption_accumulator = data.get("corruption_accumulator", 0.0)
        self.resistances.update(data.get("resistances", {}))
