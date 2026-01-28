"""
Damage system - contact damage checks and player damage pipeline.
"""
import math


def check_contact_damage(world):
    """
    Check all enemies for AABB overlap with the player.
    If an enemy has a ready contact attack and overlaps, apply damage.

    Args:
        world: The game world with entities

    Returns:
        List of (enemy, attack_def) tuples for attacks that landed
    """
    player = world.player
    if not player or not player.is_alive():
        return []

    # Player is in iframes - skip
    if getattr(player, 'iframe_timer', 0) > 0:
        return []

    hits = []
    enemies = world.get_entities_by_tag("enemy")

    for enemy in enemies:
        if not enemy.active or not enemy.is_alive():
            continue

        # AABB overlap check (both occupy ~1x1 tile)
        if not _entities_overlap(player, enemy):
            continue

        # Check for ready contact attack
        if not hasattr(enemy, 'attack_slots'):
            continue

        for slot in enemy.attack_slots:
            if slot.is_ready() and slot.attack_def.get("type") == "contact":
                # Calculate knockback direction
                dx = player.x - enemy.x
                dy = player.y - enemy.y
                length = math.sqrt(dx * dx + dy * dy)
                if length > 0:
                    kb_dir = (dx / length, dy / length)
                else:
                    kb_dir = (0, 1)

                attack_def = slot.attack_def
                player.take_hit(
                    damage=attack_def.get("damage", 5),
                    damage_type=attack_def.get("damage_type", "physical"),
                    knockback_dir=kb_dir,
                    knockback_multiplier=attack_def.get("knockback_multiplier", 0.5),
                    status_effects=attack_def.get("status_effects", [])
                )

                # Start the cooldown on the contact attack
                slot.start_windup()
                slot._in_windup = False
                slot.start_recovery()
                slot._in_recovery = False
                slot.start_cooldown()

                hits.append((enemy, attack_def))
                break  # One hit per enemy per frame

    return hits


def _entities_overlap(a, b, size=0.8):
    """Check if two entities' bounding boxes overlap."""
    half = size / 2.0
    ax, ay = a.x + 0.5, a.y + 0.5
    bx, by = b.x + 0.5, b.y + 0.5
    return (abs(ax - bx) < size and abs(ay - by) < size)
