"""
AIBrain - shared state machine for enemy AI behavior.
Each enemy type provides a config dict that tunes the same state machine.
"""
import math
import random
from .states import AIState


class AIBrain:
    """
    Data-driven AI state machine for enemies.

    Config keys:
        detection_range: float - distance to detect player
        chase_range: float - max distance to keep chasing
        attack_range: float - distance to start attacking
        flee_range: float - flee if player closer than this
        chase_speed: float - tiles per second while chasing
        patrol_speed: float - tiles per second while patrolling
        maintains_distance: float - ideal distance for ranged kiters (0 = disabled)
        erratic: bool - add random jitter to movement
        flee_health_pct: float - flee below this HP% (0.0-1.0)
        patrol_points: list - optional waypoint list [(x,y), ...]
    """

    def __init__(self, config, owner):
        self.config = config
        self.owner = owner
        self.state = AIState.IDLE

        # Patrol state
        self.patrol_index = 0
        self.patrol_points = config.get("patrol_points", [])

        # Attack state
        self.current_attack_slot = None

        # Erratic jitter timer
        self.jitter_timer = 0.0
        self.jitter_dx = 0.0
        self.jitter_dy = 0.0

    def update(self, dt, world, player, mana_pool_manager=None):
        """Run one tick of the AI state machine."""
        self._mana_pool_manager = mana_pool_manager
        if not player or not player.is_alive():
            self.state = AIState.IDLE
            return

        # Stunned/frozen override all states
        if self.owner.status.has_flag("stunned") or self.owner.status.has_flag("frozen"):
            self.state = AIState.STUNNED
            return

        # If in windup or recovery, stay there (managed by attack slot)
        if self.state == AIState.WINDUP:
            self._do_windup(dt, world, player)
            return
        if self.state == AIState.RECOVERY:
            self._do_recovery(dt)
            return

        # Evaluate state transitions
        dist = self.owner.euclidean_distance_to(player)
        health_pct = self.owner.stats.health / max(1, self.owner.stats.max_health)

        flee_range = self.config.get("flee_range", 0)
        flee_health_pct = self.config.get("flee_health_pct", 0)
        attack_range = self.config.get("attack_range", 1.5)
        detection_range = self.config.get("detection_range", 8.0)
        chase_range = self.config.get("chase_range", 12.0)

        # Priority: Stunned > Flee > Attack > Chase > Patrol/Idle
        if (flee_range > 0 and dist < flee_range) or (flee_health_pct > 0 and health_pct < flee_health_pct):
            self.state = AIState.FLEE
            self._do_flee(dt, world, player)
        elif dist <= attack_range and self._has_ready_attack():
            self.state = AIState.ATTACK
            self._do_attack(dt, world, player)
        elif dist <= detection_range:
            self.state = AIState.CHASE
            self._do_chase(dt, world, player)
        elif self.patrol_points:
            self.state = AIState.PATROL
            self._do_patrol(dt, world)
        else:
            self.state = AIState.IDLE

    def _has_ready_attack(self):
        """Check if any attack slot is ready."""
        if not hasattr(self.owner, 'attack_slots'):
            return False
        for slot in self.owner.attack_slots:
            if slot.is_ready():
                return True
        return False

    def _get_ready_attack(self):
        """Get the first ready attack slot."""
        if not hasattr(self.owner, 'attack_slots'):
            return None
        for slot in self.owner.attack_slots:
            if slot.is_ready():
                return slot
        return None

    def _get_contact_attack(self):
        """Get a ready contact-type attack slot."""
        if not hasattr(self.owner, 'attack_slots'):
            return None
        for slot in self.owner.attack_slots:
            if slot.is_ready() and slot.attack_def.get("type") == "contact":
                return slot
        return None

    def _do_chase(self, dt, world, player):
        """Move toward player, with optional distance maintenance for ranged."""
        maintains_distance = self.config.get("maintains_distance", 0)
        dist = self.owner.euclidean_distance_to(player)

        dx = player.x - self.owner.x
        dy = player.y - self.owner.y
        length = math.sqrt(dx * dx + dy * dy)
        if length < 0.01:
            return

        dx /= length
        dy /= length

        # Ranged enemies maintain distance - move away if too close
        if maintains_distance > 0 and dist < maintains_distance:
            dx = -dx
            dy = -dy

        # Add erratic jitter
        if self.config.get("erratic", False):
            self.jitter_timer -= dt
            if self.jitter_timer <= 0:
                self.jitter_timer = random.uniform(0.1, 0.3)
                self.jitter_dx = random.uniform(-0.5, 0.5)
                self.jitter_dy = random.uniform(-0.5, 0.5)
            dx += self.jitter_dx
            dy += self.jitter_dy
            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                dx /= length
                dy /= length

        self._move_toward(dx, dy, dt, world, self.config.get("chase_speed", 2.0))

    def _do_flee(self, dt, world, player):
        """Move away from player."""
        dx = self.owner.x - player.x
        dy = self.owner.y - player.y
        length = math.sqrt(dx * dx + dy * dy)
        if length < 0.01:
            dx, dy = 1.0, 0.0
        else:
            dx /= length
            dy /= length

        self._move_toward(dx, dy, dt, world, self.config.get("chase_speed", 2.0))

    def _do_patrol(self, dt, world):
        """Move between patrol waypoints."""
        if not self.patrol_points:
            return

        target = self.patrol_points[self.patrol_index]
        dx = target[0] - self.owner.x
        dy = target[1] - self.owner.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 0.15:
            self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
            return

        dx /= dist
        dy /= dist
        self._move_toward(dx, dy, dt, world, self.config.get("patrol_speed", 1.0))

    def _do_attack(self, dt, world, player):
        """Start an attack - find a ready slot and begin windup."""
        slot = self._get_ready_attack()
        if slot is None:
            self.state = AIState.CHASE
            return

        slot.start_windup()
        self.current_attack_slot = slot
        self.state = AIState.WINDUP

    def _do_windup(self, dt, world, player):
        """Wait for windup to complete, then execute the attack."""
        if self.current_attack_slot is None:
            self.state = AIState.IDLE
            return

        self.current_attack_slot.update_windup(dt)
        if self.current_attack_slot.is_windup_done():
            self._execute_attack(world, player)
            self.current_attack_slot.start_recovery()
            self.state = AIState.RECOVERY

    def _do_recovery(self, dt):
        """Wait for recovery to complete."""
        if self.current_attack_slot is None:
            self.state = AIState.IDLE
            return

        self.current_attack_slot.update_recovery(dt)
        if self.current_attack_slot.is_recovery_done():
            self.current_attack_slot.start_cooldown()
            self.current_attack_slot = None
            self.state = AIState.IDLE

    def _execute_attack(self, world, player):
        """Execute the current attack based on its type.
        If the attack has a mana_cost, deduct from the area mana pool first."""
        if self.current_attack_slot is None:
            return

        attack_def = self.current_attack_slot.attack_def

        # Deduct mana cost from area pool if the attack requires it
        mana_cost = attack_def.get("mana_cost", 0)
        if mana_cost > 0 and self._mana_pool_manager is not None:
            pool = self._mana_pool_manager.current_pool
            if pool is not None:
                pool.current = max(0.0, pool.current - mana_cost)

        attack_type = attack_def.get("type", "contact")

        if attack_type == "contact":
            self._execute_contact_attack(attack_def, player)
        elif attack_type == "melee":
            self._execute_melee_attack(attack_def, world, player)
        elif attack_type == "projectile":
            self._execute_projectile_attack(attack_def, world, player)
        elif attack_type == "aoe":
            self._execute_aoe_attack(attack_def, world, player)

    def _execute_contact_attack(self, attack_def, player):
        """Execute a contact damage attack on the player."""
        dist = self.owner.euclidean_distance_to(player)
        attack_range = attack_def.get("range", 1.5)
        if dist > attack_range:
            return

        dx = player.x - self.owner.x
        dy = player.y - self.owner.y
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            kb_dir = (dx / length, dy / length)
        else:
            kb_dir = (0, 1)

        player.take_hit(
            damage=attack_def.get("damage", 5),
            damage_type=attack_def.get("damage_type", "physical"),
            knockback_dir=kb_dir,
            knockback_multiplier=attack_def.get("knockback_multiplier", 0.5),
            status_effects=attack_def.get("status_effects", [])
        )

    def _execute_melee_attack(self, attack_def, world, player):
        """Execute a melee attack - check range then hit."""
        dist = self.owner.euclidean_distance_to(player)
        attack_range = attack_def.get("range", 2.0)
        if dist > attack_range:
            return

        dx = player.x - self.owner.x
        dy = player.y - self.owner.y
        length = math.sqrt(dx * dx + dy * dy)
        if length > 0:
            kb_dir = (dx / length, dy / length)
        else:
            kb_dir = (0, 1)

        player.take_hit(
            damage=attack_def.get("damage", 10),
            damage_type=attack_def.get("damage_type", "physical"),
            knockback_dir=kb_dir,
            knockback_multiplier=attack_def.get("knockback_multiplier", 1.0),
            status_effects=attack_def.get("status_effects", [])
        )

    def _execute_projectile_attack(self, attack_def, world, player):
        """Execute a projectile attack - create projectile aimed at player."""
        # Store pending projectile info on owner for game.py to pick up
        dx = player.x - self.owner.x
        dy = player.y - self.owner.y
        angle = math.atan2(dy, dx)

        self.owner.pending_projectile = {
            "angle": angle,
            "speed": attack_def.get("projectile_speed", 6.0),
            "damage": attack_def.get("damage", 10),
            "damage_type": attack_def.get("damage_type", "physical"),
            "knockback_multiplier": attack_def.get("knockback_multiplier", 0.5),
            "status_effects": attack_def.get("status_effects", []),
            "element": attack_def.get("element", "physical"),
            "max_range": attack_def.get("range", 10.0),
        }

    def _execute_aoe_attack(self, attack_def, world, player):
        """Execute an AoE attack centered on the enemy."""
        aoe_radius = attack_def.get("aoe_radius", 2.0)
        dist = self.owner.euclidean_distance_to(player)

        if dist <= aoe_radius:
            dx = player.x - self.owner.x
            dy = player.y - self.owner.y
            length = math.sqrt(dx * dx + dy * dy)
            if length > 0:
                kb_dir = (dx / length, dy / length)
            else:
                kb_dir = (0, 1)

            player.take_hit(
                damage=attack_def.get("damage", 15),
                damage_type=attack_def.get("damage_type", "earth"),
                knockback_dir=kb_dir,
                knockback_multiplier=attack_def.get("knockback_multiplier", 1.5),
                status_effects=attack_def.get("status_effects", [])
            )

        # Store pending AoE visual for game.py to pick up
        self.owner.pending_aoe = {
            "x": self.owner.x,
            "y": self.owner.y,
            "radius": aoe_radius,
            "element": attack_def.get("element", "earth"),
            "telegraph_color": attack_def.get("telegraph_color", (160, 140, 100)),
        }

    def _move_toward(self, dx, dy, dt, world, speed):
        """
        Move the owner in a direction using velocity-based try_move.
        If blocked, attempts perpendicular steering to navigate around obstacles.
        """
        if dx == 0 and dy == 0:
            return

        old_x, old_y = self.owner.x, self.owner.y
        if self.owner.try_move(dx, dy, world, dt=dt, speed_override=speed):
            world.update_entity_position(self.owner, old_x, old_y)
            self._stuck_timer = 0.0
            return

        # Straight-line move failed - try steering around the obstacle.
        # Use the two perpendicular directions to the desired movement.
        # Prefer whichever perpendicular is more aligned with the target.
        perp1_dx, perp1_dy = -dy, dx   # rotate 90 CCW
        perp2_dx, perp2_dy = dy, -dx   # rotate 90 CW

        # Try both perpendiculars; pick one semi-randomly based on a timer
        # to avoid oscillating back and forth on symmetric obstacles.
        stuck = getattr(self, '_stuck_timer', 0.0)
        self._stuck_timer = stuck + dt

        # Alternate which perpendicular we try first every 0.3s
        if int(self._stuck_timer / 0.3) % 2 == 0:
            candidates = [(perp1_dx, perp1_dy), (perp2_dx, perp2_dy)]
        else:
            candidates = [(perp2_dx, perp2_dy), (perp1_dx, perp1_dy)]

        for cdx, cdy in candidates:
            old_x, old_y = self.owner.x, self.owner.y
            if self.owner.try_move(cdx, cdy, world, dt=dt, speed_override=speed):
                world.update_entity_position(self.owner, old_x, old_y)
                return
