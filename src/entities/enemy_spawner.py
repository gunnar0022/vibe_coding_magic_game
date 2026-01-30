"""
EnemySpawner - invisible tile entity that manages enemy spawning.

Each spawner has:
- Spawn chance (probability of spawning when timer expires)
- Enemy type weights (weighted random selection)
- Active state (True = enemy alive, False = timer running)
- Respawn timer
"""
import math
import random
from .base import Entity
from .enemy import create_enemy


class EnemySpawner(Entity):
    """
    An invisible entity placed in the world that manages enemy spawning.
    Not rendered, not solid. Tracks whether its enemy is alive and manages
    respawn timing.
    """

    def __init__(self, x, y, spawner_id, spawn_chance=1.0, enemy_types=None,
                 respawn_time=60.0):
        """
        Args:
            x, y: Spawn position for the enemy
            spawner_id: Unique identifier for save/load persistence
            spawn_chance: Probability (0.0-1.0) of successfully spawning
            enemy_types: List of {"type": str, "weight": int} entries
            respawn_time: Seconds before respawn attempt after enemy dies
        """
        super().__init__(x=x, y=y, tags=["enemy_spawner"])
        self.solid = False
        self.spawner_id = spawner_id

        # Spawn configuration
        self.spawn_chance = max(0.0, min(1.0, spawn_chance))
        self.enemy_types = enemy_types or [{"type": "slime", "weight": 100}]
        self.respawn_time = respawn_time

        # State
        self.active = False  # True = enemy is alive
        self.current_enemy_id = None  # Entity ID of the spawned enemy
        self.respawn_timer = 0.0  # Countdown until next spawn attempt
        self.wants_to_spawn = False  # Set True when ready to attempt spawn

        # Whether this spawner has ever performed its initial spawn
        self.has_done_initial_spawn = False

    def initialize(self, world):
        """
        Perform initial spawn attempt when area is first loaded.
        Called by the spawner manager during area setup.
        """
        if self.has_done_initial_spawn:
            return
        self.has_done_initial_spawn = True
        self.wants_to_spawn = True

    def update_spawner(self, dt, world):
        """
        Update spawner state. Called each frame by the spawner manager.
        Checks if the linked enemy is still alive and manages the timer.
        """
        if self.active and self.current_enemy_id is not None:
            # Check if our enemy is still alive
            enemy = world.entities.get(self.current_enemy_id)
            if enemy is None or not enemy.is_alive():
                # Enemy died or was removed
                self.active = False
                self.current_enemy_id = None
                self.respawn_timer = self.respawn_time
        elif not self.active and not self.wants_to_spawn:
            # Timer is counting down
            if self.respawn_timer > 0:
                self.respawn_timer -= dt
            else:
                # Timer expired - ready to attempt spawn
                self.wants_to_spawn = True

    def attempt_spawn(self, world):
        """
        Attempt to spawn an enemy. Rolls the spawn chance, then picks
        a random enemy type if successful.

        Returns:
            The spawned Enemy entity, or None if spawn failed.
        """
        self.wants_to_spawn = False

        # Roll spawn chance
        if random.random() > self.spawn_chance:
            # Failed the spawn check - reset timer
            self.respawn_timer = self.respawn_time
            return None

        # Select enemy type using weighted random
        enemy_type = self._pick_enemy_type()

        # Create the enemy
        enemy = create_enemy(enemy_type, self.x, self.y)
        world.add_entity(enemy)

        # Link to this spawner
        self.active = True
        self.current_enemy_id = enemy.id

        return enemy

    def _pick_enemy_type(self):
        """Select an enemy type using weighted random selection."""
        total_weight = sum(e["weight"] for e in self.enemy_types)
        if total_weight <= 0:
            return "slime"

        roll = random.uniform(0, total_weight)
        cumulative = 0
        for entry in self.enemy_types:
            cumulative += entry["weight"]
            if roll <= cumulative:
                return entry["type"]

        return self.enemy_types[-1]["type"]

    def get_distance_to(self, x, y):
        """Euclidean distance from this spawner to a point."""
        dx = self.x - x
        dy = self.y - y
        return math.sqrt(dx * dx + dy * dy)

    def get_nearest_enemy_distance(self, world):
        """Get distance to the nearest living enemy in the world."""
        min_dist = float('inf')
        for entity in world.entities.values():
            if entity.has_tag("enemy") and entity.is_alive():
                dist = self.get_distance_to(entity.x, entity.y)
                if dist < min_dist:
                    min_dist = dist
        return min_dist

    def serialize_state(self):
        """Serialize spawner state for saving."""
        return {
            "active": self.active,
            "current_enemy_id": self.current_enemy_id,
            "respawn_timer": self.respawn_timer,
            "has_done_initial_spawn": self.has_done_initial_spawn,
            "wants_to_spawn": self.wants_to_spawn,
        }

    def restore_state(self, state_dict):
        """Restore spawner state from saved data."""
        self.active = state_dict.get("active", False)
        self.current_enemy_id = state_dict.get("current_enemy_id", None)
        self.respawn_timer = state_dict.get("respawn_timer", 0.0)
        self.has_done_initial_spawn = state_dict.get("has_done_initial_spawn", False)
        self.wants_to_spawn = state_dict.get("wants_to_spawn", False)


class SpawnerManager:
    """
    Manages all enemy spawners in the current area.
    Handles the max enemy cap and conflict resolution for simultaneous spawns.
    """

    def __init__(self, max_enemies=10):
        self.spawners = []  # List of EnemySpawner entities
        self.max_enemies = max_enemies

    def register_spawner(self, spawner):
        """Add a spawner to the manager."""
        self.spawners.append(spawner)

    def clear(self):
        """Clear all spawners (on area transition)."""
        self.spawners.clear()

    def initialize_spawners(self, world, area_state=None):
        """
        Run initial spawn for all spawners.
        If area_state has saved spawner states, restore them instead.
        """
        for spawner in self.spawners:
            # Restore persistent state if available
            if area_state:
                saved = area_state.get_spawner_state(spawner.spawner_id)
                if saved:
                    spawner.restore_state(saved)
                    # If enemy was active, we need to re-spawn it
                    # (the enemy entity doesn't persist, so recreate it)
                    if spawner.active:
                        enemy = spawner.attempt_spawn(world)
                        if not enemy:
                            # Force spawn for a restored active enemy
                            spawner.wants_to_spawn = False
                            enemy_type = spawner._pick_enemy_type()
                            enemy = create_enemy(enemy_type, spawner.x, spawner.y)
                            world.add_entity(enemy)
                            spawner.active = True
                            spawner.current_enemy_id = enemy.id
                    continue

            # First visit - do initial spawn
            spawner.initialize(world)

        # Process any initial spawns
        self._resolve_pending_spawns(world, None)

    def update(self, dt, world, player):
        """
        Update all spawners and resolve any pending spawns.
        Called from the game update loop.
        """
        for spawner in self.spawners:
            spawner.update_spawner(dt, world)

        self._resolve_pending_spawns(world, player)

    def _resolve_pending_spawns(self, world, player):
        """
        Collect all spawners that want to spawn and resolve conflicts
        if the area enemy cap would be exceeded.
        """
        # Gather pending spawners
        pending = [s for s in self.spawners if s.wants_to_spawn]
        if not pending:
            return

        # Count current living enemies
        current_count = self._count_living_enemies(world)
        available_slots = self.max_enemies - current_count

        if available_slots <= 0:
            # No room - all pending spawns fail, reset their timers
            for spawner in pending:
                spawner.wants_to_spawn = False
                spawner.respawn_timer = spawner.respawn_time
            return

        if len(pending) <= available_slots:
            # All can spawn - no conflict
            for spawner in pending:
                spawner.attempt_spawn(world)
            return

        # Conflict: more spawners want to spawn than slots available.
        # Priority system:
        #   1. Furthest from player
        #   2. Furthest from nearest monster
        #   3. Spawner ID hash (deterministic tiebreak)
        self._resolve_conflicts(pending, available_slots, world, player)

    def _resolve_conflicts(self, pending, available_slots, world, player):
        """
        Resolve simultaneous spawn conflicts using a combined priority score.
        Score = player_dist + enemy_dist (equally weighted).
        Higher score (far from player and isolated from other enemies) wins.
        Ties are broken arbitrarily via random shuffle.
        """
        scored = []
        for spawner in pending:
            player_dist = spawner.get_distance_to(player.x, player.y) if player else 0.0

            enemy_dist = spawner.get_nearest_enemy_distance(world)
            if enemy_dist == float('inf'):
                enemy_dist = 9999.0

            score = player_dist + enemy_dist
            scored.append((spawner, score))

        # Shuffle first so equal scores are resolved arbitrarily
        random.shuffle(scored)
        scored.sort(key=lambda s: s[1], reverse=True)

        # Let the top N spawn, reject the rest
        for i, (spawner, _) in enumerate(scored):
            if i < available_slots:
                spawner.attempt_spawn(world)
            else:
                spawner.wants_to_spawn = False
                spawner.respawn_timer = spawner.respawn_time

    def _count_living_enemies(self, world):
        """Count living enemies currently in the world."""
        count = 0
        for entity in world.entities.values():
            if entity.has_tag("enemy") and entity.is_alive():
                count += 1
        return count

    def save_spawner_states(self, area_state):
        """Save all spawner states to area state for persistence."""
        for spawner in self.spawners:
            area_state.set_spawner_state(
                spawner.spawner_id,
                spawner.serialize_state()
            )

    def get_spawner_count(self):
        """Get number of registered spawners."""
        return len(self.spawners)
