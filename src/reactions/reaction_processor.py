"""
ReactionProcessor - the core engine for processing elemental reactions.
Handles the queue system, reaction execution, and spread logic.
"""
from .elements import Element, Attribute, STATUS_TO_ELEMENT, ELEMENT_TO_STATUS, ELEMENT_PRIORITY
from .reaction_registry import ReactionRegistry


class ReactionProcessor:
    """
    Processes elemental reactions when magic or environmental effects are applied.
    Uses a priority queue for handling simultaneous reactions.
    """

    def __init__(self, world=None):
        """
        Initialize the processor.

        Args:
            world: Reference to the game world (for spatial queries)
        """
        self.world = world
        self.reaction_queue = []
        self.processed_this_frame = set()  # Prevent infinite loops

    def process_element_applied(self, entity, element, context=None, intensity=1.0):
        """
        Main entry point when an element is applied to an entity.
        Checks for reactions and queues them for processing.

        Args:
            entity: The entity receiving the element
            element: The element being applied (Element constant)
            context: Optional context dict (world, caster, etc.)
            intensity: Strength of the element application

        Returns:
            List of reaction results
        """
        if context is None:
            context = {}

        # Store world reference if provided
        if "world" in context and self.world is None:
            self.world = context["world"]

        # Reset per-frame tracking
        self.reaction_queue = []
        self.processed_this_frame = set()

        # Check for element + current status reactions
        self._check_status_reactions(entity, element, context, intensity)

        # Check for element + attribute reactions
        self._check_attribute_reactions(entity, element, context, intensity)

        # Process the queue
        return self._process_queue(context)

    def _check_status_reactions(self, entity, incoming_element, context, intensity):
        """Check for reactions between incoming element and entity's current statuses."""
        status = entity.get_component("StatusComponent")
        if not status:
            return

        # Check each active status flag
        for flag_name, is_active in status.flags.items():
            if not is_active:
                continue

            # Map status to element
            status_element = STATUS_TO_ELEMENT.get(flag_name)
            if not status_element:
                continue

            # Skip if same element (no self-reaction)
            if status_element == incoming_element:
                continue

            # Look up reaction
            reaction = ReactionRegistry.get_element_reaction(incoming_element, status_element)
            if reaction:
                self._queue_reaction(
                    entity=entity,
                    reaction=reaction,
                    source_element=incoming_element,
                    target_element=status_element,
                    context=context,
                    intensity=intensity,
                    reaction_type="element_element"
                )

    def _check_attribute_reactions(self, entity, element, context, intensity):
        """Check for reactions between element and entity's attributes."""
        attributes = self._get_entity_attributes(entity)

        for attribute in attributes:
            reaction = ReactionRegistry.get_attribute_reaction(element, attribute)
            if reaction:
                self._queue_reaction(
                    entity=entity,
                    reaction=reaction,
                    source_element=element,
                    target_element=attribute,
                    context=context,
                    intensity=intensity,
                    reaction_type="element_attribute"
                )

    def _get_entity_attributes(self, entity):
        """
        Get all attributes for an entity from tags and components.

        Args:
            entity: The entity to check

        Returns:
            List of attribute strings
        """
        attributes = []

        # Check entity tags
        for attr in Attribute.ALL:
            if entity.has_tag(attr):
                attributes.append(attr)

        # Check environmental component traits for backward compatibility
        env = entity.get_component("EnvironmentalComponent")
        if env:
            trait_to_attr = {
                "organic": Attribute.ORGANIC,
                "metallic": Attribute.METAL,
                "liquid": Attribute.LIQUID,
                "flammable": Attribute.PLANT,  # flammable often implies plant
            }
            for trait, attr in trait_to_attr.items():
                if env.has_trait(trait) and attr not in attributes:
                    attributes.append(attr)

        return attributes

    def _queue_reaction(self, entity, reaction, source_element, target_element,
                        context, intensity, reaction_type):
        """Add a reaction to the priority queue."""
        # Create unique key to prevent duplicate reactions
        reaction_key = (id(entity), reaction.name, source_element, target_element)
        if reaction_key in self.processed_this_frame:
            return

        self.reaction_queue.append({
            "entity": entity,
            "reaction": reaction,
            "source_element": source_element,
            "target_element": target_element,
            "context": context,
            "intensity": intensity,
            "reaction_type": reaction_type,
            "priority": reaction.priority,
        })

        # Sort by priority (higher first)
        self.reaction_queue.sort(key=lambda x: -x["priority"])

    def _process_queue(self, context):
        """Process all queued reactions in priority order."""
        results = []

        while self.reaction_queue:
            item = self.reaction_queue.pop(0)

            # Mark as processed to prevent loops
            reaction_key = (
                id(item["entity"]),
                item["reaction"].name,
                item["source_element"],
                item["target_element"]
            )
            if reaction_key in self.processed_this_frame:
                continue
            self.processed_this_frame.add(reaction_key)

            # Execute the reaction
            result = self._execute_reaction(item)
            results.append(result)

            # Handle chain reactions and spread
            if item["reaction"].chain_reaction:
                self._handle_chain_reaction(item, result, context)

            if item["reaction"].spread_type:
                self._handle_spread(item, context)

        return results

    def _execute_reaction(self, item):
        """
        Execute a single reaction.

        Args:
            item: Queue item dict

        Returns:
            Result dict with effects applied
        """
        entity = item["entity"]
        reaction = item["reaction"]
        intensity = item["intensity"] * reaction.intensity_multiplier

        result = {
            "entity": entity,
            "reaction_name": reaction.name,
            "reaction_type": item["reaction_type"],
            "effects": [],
            "affected": False,
        }

        # Get status component if available
        status = entity.get_component("StatusComponent")

        # Remove statuses
        for status_name in reaction.removes_statuses:
            if status and status.has_effect(status_name):
                status.remove_effect(status_name)
                result["effects"].append(f"removed:{status_name}")
                result["affected"] = True

        # Apply new statuses
        for effect_data in reaction.applies_statuses:
            if status:
                effect_name = effect_data["name"]
                duration = effect_data.get("duration", -1)
                effect_intensity = effect_data.get("intensity", 1.0) * intensity

                status.add_effect(effect_name, duration, effect_intensity)
                result["effects"].append(f"applied:{effect_name}")
                result["affected"] = True

        # Apply damage
        if reaction.damage:
            stats = entity.get_component("StatsComponent")
            if stats:
                damage_amount = reaction.damage["amount"] * intensity
                damage_type = reaction.damage.get("type", "physical")
                actual_damage = stats.take_damage(damage_amount, damage_type)
                result["effects"].append(f"damage:{actual_damage}:{damage_type}")
                result["affected"] = True

        # Handle source cancellation (e.g., fire extinguished by water)
        if reaction.cancels_source and status:
            source_status = self._element_to_status(item["source_element"])
            if source_status and status.has_effect(source_status):
                status.remove_effect(source_status)
                result["effects"].append(f"cancelled:{source_status}")

        return result

    def _element_to_status(self, element):
        """Map element to its primary status effect."""
        return ELEMENT_TO_STATUS.get(element)

    def _handle_chain_reaction(self, item, result, context):
        """Handle chain reactions that trigger further reactions."""
        # Chain reactions could trigger additional element applications
        # For now, this is handled by the spread system
        pass

    def _handle_spread(self, item, context):
        """
        Handle reaction spread to nearby entities.

        Args:
            item: Queue item containing spread configuration
            context: Context dict with world reference
        """
        reaction = item["reaction"]
        entity = item["entity"]

        if not self.world:
            return

        spread_element = reaction.spread_element or item["source_element"]
        neighbors = []

        if reaction.spread_type == "adjacent":
            neighbors = self._get_adjacent_entities(entity, reaction.spread_range)
        elif reaction.spread_type == "radius":
            neighbors = self._get_entities_in_radius(entity, reaction.spread_range)
        elif reaction.spread_type == "material":
            neighbors = self._get_connected_by_attribute(
                entity, reaction.spread_condition
            )

        # Queue spread effects for matching entities
        for neighbor in neighbors:
            if neighbor.id == entity.id:
                continue

            # Check if neighbor meets spread condition
            if reaction.spread_condition:
                if not self._meets_spread_condition(neighbor, reaction.spread_condition):
                    continue

            # Reduced intensity for spread
            spread_intensity = item["intensity"] * 0.8

            # Check for reactions on the neighbor
            self._check_attribute_reactions(
                neighbor, spread_element, context, spread_intensity
            )

    def _get_adjacent_entities(self, entity, distance=1):
        """Get entities in adjacent tiles."""
        if not self.world:
            return []

        neighbors = []
        ex, ey = int(entity.x), int(entity.y)

        for dx in range(-distance, distance + 1):
            for dy in range(-distance, distance + 1):
                if dx == 0 and dy == 0:
                    continue
                # Manhattan distance check for "adjacent" (not diagonal at distance 1)
                if abs(dx) + abs(dy) > distance:
                    continue

                tile_entities = self.world.get_entities_at(ex + dx, ey + dy)
                neighbors.extend(tile_entities)

        return neighbors

    def _get_entities_in_radius(self, entity, radius):
        """Get all entities within radius tiles."""
        if not self.world:
            return []

        ex, ey = entity.x, entity.y
        return self.world.get_entities_in_rect(
            ex - radius, ey - radius,
            radius * 2 + 1, radius * 2 + 1
        )

    def _get_connected_by_attribute(self, entity, attribute):
        """
        Get entities connected by a shared attribute (flood fill).
        Used for material-based spreading (e.g., electricity through water).
        """
        if not self.world or not attribute:
            return []

        visited = set()
        to_visit = [entity]
        connected = []

        while to_visit:
            current = to_visit.pop(0)
            if current.id in visited:
                continue
            visited.add(current.id)

            # Check if current has the attribute
            if self._meets_spread_condition(current, attribute):
                connected.append(current)

                # Add adjacent entities to visit
                adjacent = self._get_adjacent_entities(current, distance=1)
                for adj in adjacent:
                    if adj.id not in visited:
                        to_visit.append(adj)

        return connected

    def _meets_spread_condition(self, entity, condition):
        """
        Check if entity meets a spread condition.

        Args:
            entity: Entity to check
            condition: Attribute, tag, or trait name

        Returns:
            True if condition is met
        """
        # Check as tag
        if entity.has_tag(condition):
            return True

        # Check as attribute
        if condition in Attribute.ALL:
            return entity.has_tag(condition)

        # Check environmental traits
        env = entity.get_component("EnvironmentalComponent")
        if env and env.has_trait(condition):
            return True

        # Check status flags (for "wet" spreading electricity)
        status = entity.get_component("StatusComponent")
        if status and status.has_flag(condition):
            return True

        return False


# Singleton instance for convenience
_default_processor = None


def get_reaction_processor(world=None):
    """Get or create the default reaction processor."""
    global _default_processor
    if _default_processor is None:
        _default_processor = ReactionProcessor(world)
    elif world is not None:
        _default_processor.world = world
    return _default_processor
