"""
Environmental Mana Pool system.

Each area has a shared mana pool with a max capacity and slow regen rate.
All casters in an area (player + enemies) draw from the same pool.
When the pool is empty, casters can draw from their own health instead.
"""


class AreaManaPool:
    """A single area's environmental mana pool."""

    def __init__(self, max_capacity=100.0, regen_rate=1.0):
        self.max_capacity = max_capacity
        self.current = max_capacity  # Start full
        self.regen_rate = regen_rate  # Mana per second

    def update(self, dt):
        """Regenerate mana over time (called every frame for the active area)."""
        if self.current < self.max_capacity:
            self.current = min(self.max_capacity, self.current + self.regen_rate * dt)

    def try_cast(self, spell_cost):
        """
        Attempt to draw mana from the area pool for a spell.

        Returns:
            (mana_drawn, shortfall) - mana_drawn is how much came from the pool,
            shortfall is how much the caster must cover from health.
        """
        if self.current >= spell_cost:
            self.current -= spell_cost
            return spell_cost, 0.0
        else:
            mana_drawn = self.current
            shortfall = spell_cost - self.current
            self.current = 0.0
            return mana_drawn, shortfall

    def restore(self, amount):
        """Restore mana to the pool (e.g. from a mana potion)."""
        self.current = min(self.max_capacity, self.current + amount)

    def serialize(self):
        return {
            "max_capacity": self.max_capacity,
            "current": self.current,
            "regen_rate": self.regen_rate,
        }

    @staticmethod
    def deserialize(data):
        pool = AreaManaPool(
            max_capacity=data.get("max_capacity", 100.0),
            regen_rate=data.get("regen_rate", 1.0),
        )
        pool.current = data.get("current", pool.max_capacity)
        return pool


# Default mana pool configs per area.
# Maps can override these via their JSON "mana_pool" field.
AREA_MANA_DEFAULTS = {
    "forest": {"max_capacity": 150.0, "regen_rate": 2.0},
    "home_village": {"max_capacity": 80.0, "regen_rate": 1.5},
    "elder_house": {"max_capacity": 40.0, "regen_rate": 0.5},
    "test_map": {"max_capacity": 150.0, "regen_rate": 2.0},
}

# Fallback for areas not listed above and not specified in JSON
DEFAULT_POOL = {"max_capacity": 100.0, "regen_rate": 1.0}


class ManaPoolManager:
    """
    Global manager for all area mana pools.
    Tracks pools whether the player is present or not.
    Passive (off-screen) areas regenerate on a 30-second tick with a 1.25x bonus.
    """

    # Health-to-mana conversion: 1 HP buys this much mana worth of casting.
    # Intentionally generous so it *feels* like a good trade.
    HEALTH_TO_MANA_RATIO = 3.0  # 1 HP = 3 mana of casting power

    # Passive regen: areas you're NOT in get a 25% bonus and update every 30s
    PASSIVE_TICK_INTERVAL = 30.0  # seconds
    PASSIVE_REGEN_MULTIPLIER = 1.25

    def __init__(self):
        # {area_id: AreaManaPool}
        self._pools = {}
        self._current_area_id = None
        self._passive_timer = 0.0

    @property
    def current_pool(self):
        """The mana pool for the area the player is currently in."""
        if self._current_area_id and self._current_area_id in self._pools:
            return self._pools[self._current_area_id]
        return None

    def get_or_create_pool(self, area_id, max_capacity=None, regen_rate=None):
        """Get an existing pool or create one for the area."""
        if area_id not in self._pools:
            # Use explicit values, then area defaults, then global default
            defaults = AREA_MANA_DEFAULTS.get(area_id, DEFAULT_POOL)
            cap = max_capacity if max_capacity is not None else defaults["max_capacity"]
            rate = regen_rate if regen_rate is not None else defaults["regen_rate"]
            self._pools[area_id] = AreaManaPool(cap, rate)
        return self._pools[area_id]

    def set_current_area(self, area_id, max_capacity=None, regen_rate=None):
        """Called when the player enters a new area."""
        self._current_area_id = area_id
        self.get_or_create_pool(area_id, max_capacity, regen_rate)

    def update(self, dt):
        """
        Called every frame from the game loop.
        - Active area: regenerates every frame (normal rate).
        - Passive areas: regenerate on a 30-second tick with 1.25x bonus.
        """
        # Active area: frame-by-frame regen
        pool = self.current_pool
        if pool is not None:
            pool.update(dt)

        # Passive areas: batch regen every 30 seconds
        self._passive_timer += dt
        if self._passive_timer >= self.PASSIVE_TICK_INTERVAL:
            elapsed = self._passive_timer
            self._passive_timer = 0.0
            for area_id, p in self._pools.items():
                if area_id != self._current_area_id:
                    regen = p.regen_rate * self.PASSIVE_REGEN_MULTIPLIER * elapsed
                    p.current = min(p.max_capacity, p.current + regen)

    def cast_from_pool(self, spell_cost, caster_stats):
        """
        Central casting logic. Draws from the area pool first;
        any shortfall comes from the caster's health.

        Args:
            spell_cost: The mana cost of the spell.
            caster_stats: The caster's StatsComponent (for health deduction).

        Returns:
            True if the cast proceeds (always True; caster may die).
        """
        pool = self.current_pool
        if pool is not None and pool.current >= spell_cost:
            # Enough area mana — pure environmental cast
            pool.current -= spell_cost
            return True

        # Partial or no area mana — health covers the rest
        if pool is not None:
            mana_from_pool = pool.current
            pool.current = 0.0
        else:
            mana_from_pool = 0.0

        shortfall = spell_cost - mana_from_pool
        hp_cost = shortfall / self.HEALTH_TO_MANA_RATIO
        caster_stats.health = max(0, caster_stats.health - hp_cost)

        # Track corruption: the FULL shortfall in mana terms, not HP terms
        caster_stats.corruption_accumulator += shortfall

        return True

    def serialize(self):
        """Serialize all pools for saving."""
        return {
            area_id: pool.serialize()
            for area_id, pool in self._pools.items()
        }

    def deserialize(self, data):
        """Restore pools from saved data."""
        self._pools.clear()
        if data:
            for area_id, pool_data in data.items():
                self._pools[area_id] = AreaManaPool.deserialize(pool_data)
