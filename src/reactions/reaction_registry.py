"""
ReactionRegistry - central registry for all elemental reactions.
Provides lookup for element+element and element+attribute reactions.
"""
from .reaction_definition import ReactionDefinition


class ReactionRegistry:
    """
    Central registry for all element+element and element+attribute reactions.
    Uses class-level storage so reactions are globally accessible.
    """

    # Element + Element reactions: (elem1, elem2) -> ReactionDefinition
    # Keys are sorted tuples for order-independent lookup
    _element_reactions = {}

    # Element + Attribute reactions: (element, attribute) -> ReactionDefinition
    _attribute_reactions = {}

    # Registered status effects that participate in reactions
    _reactive_statuses = set()

    @classmethod
    def clear(cls):
        """Clear all registered reactions (useful for testing)."""
        cls._element_reactions.clear()
        cls._attribute_reactions.clear()
        cls._reactive_statuses.clear()

    @classmethod
    def register_element_reaction(cls, element1, element2, reaction_def):
        """
        Register a reaction between two elements.
        Order-independent: fire+water == water+fire

        Args:
            element1: First element
            element2: Second element
            reaction_def: ReactionDefinition or dict
        """
        if isinstance(reaction_def, dict):
            reaction_def = ReactionDefinition(reaction_def)

        # Normalize key to be order-independent
        key = tuple(sorted([element1, element2]))
        cls._element_reactions[key] = reaction_def

    @classmethod
    def register_attribute_reaction(cls, element, attribute, reaction_def):
        """
        Register a reaction between an element and an attribute.

        Args:
            element: The element being applied
            attribute: The attribute of the target
            reaction_def: ReactionDefinition or dict
        """
        if isinstance(reaction_def, dict):
            reaction_def = ReactionDefinition(reaction_def)

        cls._attribute_reactions[(element, attribute)] = reaction_def

    @classmethod
    def register_reactive_status(cls, status_name):
        """Register a status effect that can trigger element reactions."""
        cls._reactive_statuses.add(status_name)

    @classmethod
    def get_element_reaction(cls, element1, element2):
        """
        Look up reaction between two elements.

        Args:
            element1: First element
            element2: Second element

        Returns:
            ReactionDefinition or None
        """
        key = tuple(sorted([element1, element2]))
        return cls._element_reactions.get(key)

    @classmethod
    def get_attribute_reaction(cls, element, attribute):
        """
        Look up reaction between an element and an attribute.

        Args:
            element: The element being applied
            attribute: The attribute of the target

        Returns:
            ReactionDefinition or None
        """
        return cls._attribute_reactions.get((element, attribute))

    @classmethod
    def get_all_attribute_reactions(cls, element):
        """
        Get all attribute reactions for a given element.

        Args:
            element: The element to look up

        Returns:
            List of (attribute, ReactionDefinition) tuples
        """
        results = []
        for (elem, attr), reaction in cls._attribute_reactions.items():
            if elem == element:
                results.append((attr, reaction))
        return results

    @classmethod
    def is_reactive_status(cls, status_name):
        """Check if a status effect can trigger element reactions."""
        return status_name in cls._reactive_statuses

    @classmethod
    def get_reaction_count(cls):
        """Get count of registered reactions (for debugging)."""
        return {
            "element_reactions": len(cls._element_reactions),
            "attribute_reactions": len(cls._attribute_reactions),
        }
