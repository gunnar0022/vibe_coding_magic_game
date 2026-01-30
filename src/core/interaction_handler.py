"""
Interaction handling module - manages player interactions with objects, NPCs, and doors.
Extracted from game.py for modularity.
"""
from ..magic import MagicSystem


class InteractionHandler:
    """Handles all interaction-related functionality."""

    def __init__(self, game):
        """
        Initialize with reference to game instance.

        Args:
            game: The main Game instance
        """
        self.game = game

    @property
    def player(self):
        return self.game.player

    @property
    def world(self):
        return self.game.world

    @property
    def input(self):
        return self.game.input

    @property
    def dialogue_box(self):
        return self.game.dialogue_box

    @property
    def notebook(self):
        return self.game.notebook

    @property
    def spell_notebook(self):
        return self.game.spell_notebook

    def handle_interaction(self):
        """
        Handle player interaction with nearby entities.
        Uses mouse direction and picks entity with most overlap in the interaction area.
        """
        # Get interaction direction from mouse position (8-directional)
        mouse_x, mouse_y = self.input.get_mouse_position()
        interact_facing = self.game._get_facing_from_mouse(mouse_x, mouse_y)

        # Snap player to face the interaction direction (4-directional)
        four_dir_facing = self.game._get_facing_from_mouse(mouse_x, mouse_y, eight_dir=False)
        self.player.facing = four_dir_facing
        self.player.transform.facing = four_dir_facing

        # Get interaction rect in mouse direction (1x1 tile / 8x8 fine grid)
        interact_rect = self._get_interaction_rect(interact_facing)

        # Get entities in the interaction area
        rx, ry, rw, rh = interact_rect
        entities = self.world.get_entities_in_rect(rx, ry, rw, rh)

        # Check for ground items first (pickup priority)
        for entity in entities:
            if entity.id == self.player.id:
                continue
            if entity.has_tag("ground_item"):
                overlap = self._calculate_rect_overlap(interact_rect, (entity.x, entity.y, 1.0, 1.0))
                if overlap > 0:
                    self.game.combat_handler.pickup_ground_item(entity)
                    return

        # Find interactable entity with most overlap in the interaction area
        best_entity = None
        best_overlap = 0.0

        for entity in entities:
            if entity.id == self.player.id:
                continue

            # Check if entity is interactable
            is_interactable = False
            if entity.has_tag("npc") or entity.has_tag("rune_stone"):
                is_interactable = True
            elif entity.has_tag("door"):
                is_interactable = True
            else:
                interaction = entity.get_component("InteractionComponent")
                if interaction and interaction.can_examine:
                    is_interactable = True

            if not is_interactable:
                continue

            # Calculate entity's bounding rect (1x1 tile at entity position)
            entity_rect = (entity.x, entity.y, 1.0, 1.0)

            # Calculate overlap with interaction area
            overlap = self._calculate_rect_overlap(interact_rect, entity_rect)

            if overlap > best_overlap:
                best_entity = entity
                best_overlap = overlap

        if best_entity is None:
            return

        # Interact with the closest entity
        if best_entity.has_tag("npc"):
            self._interact_with_npc(best_entity)
        elif best_entity.has_tag("rune_stone"):
            self._interact_with_rune_stone(best_entity)
        elif best_entity.has_tag("door"):
            self._interact_with_door(best_entity)
        else:
            interaction = best_entity.get_component("InteractionComponent")
            if interaction and interaction.can_examine:
                self.dialogue_box.show(interaction.examine_text)

    def _get_interaction_rect(self, facing):
        """
        Get the interaction hitbox rectangle based on player position and facing.
        Uses a smaller 1x1 tile (8x8 sub-grid) area for precise interaction.

        Returns (x, y, width, height) in float tile units.
        """
        px, py = self.player.x, self.player.y
        size = 1.0

        # Cardinal directions
        if facing == "right":
            return (px + 1.0, py, size, size)
        elif facing == "left":
            return (px - size, py, size, size)
        elif facing == "up":
            return (px, py - size, size, size)
        elif facing == "down":
            return (px, py + 1.0, size, size)

        # Diagonal directions
        if facing == "up_right":
            return (px + 1.0, py - size, size, size)
        elif facing == "up_left":
            return (px - size, py - size, size, size)
        elif facing == "down_right":
            return (px + 1.0, py + 1.0, size, size)
        elif facing == "down_left":
            return (px - size, py + 1.0, size, size)

        # Default
        return (px, py + 1.0, size, size)

    def _calculate_rect_overlap(self, rect1, rect2):
        """
        Calculate the overlap area between two rectangles.
        Returns the overlap area (0 if no overlap).
        """
        x1, y1, w1, h1 = rect1
        x2, y2, w2, h2 = rect2

        overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))

        return overlap_x * overlap_y

    def _interact_with_door(self, door):
        """Handle interaction with a door to transition areas."""
        transition_data = door.get_transition_data()
        target_area = transition_data.get("target_area", "")
        target_entry = transition_data.get("target_entry", "default")

        if not target_area:
            self.game.show_message("This door doesn't lead anywhere.")
            return

        self.game.transition_to_area(target_area, target_entry)

    def _interact_with_npc(self, npc):
        """Handle interaction with an NPC using dialogue box."""
        # Pause NPC movement during conversation
        npc.in_conversation = True
        self.game._conversation_npc = npc

        # Check if NPC is a merchant - open shop UI
        if getattr(npc, 'can_trade', False):
            self._open_shop(npc)
            return

        # Check if NPC has a dialogue tree
        if npc.dialogue_tree:
            self._start_dialogue_tree(npc, npc.dialogue_tree)
            return

        # Legacy dialogue handling
        dialogue_lines = []

        # Add greeting (pass player so NPC can customize based on taught status)
        dialogue_lines.append(npc.get_greeting(self.player))

        # Check if NPC can teach
        if npc.can_teach:
            teachable = npc.get_teachable_for_player(self.player)
            if teachable:
                symbol_id = teachable[0]
                success, message, data = npc.teach_symbol(symbol_id, self.player)
                if success:
                    # Record in notebook
                    symbol = MagicSystem.get_symbol(symbol_id)
                    symbol_data = symbol.to_dict() if symbol else {}
                    self.notebook.record_symbol_discovery(
                        symbol_id,
                        data.get("context", ""),
                        f"Location: {self.player.x}, {self.player.y}",
                        symbol_data
                    )
                    # Also add to spell notebook (journal)
                    self.spell_notebook.learn_spell(symbol_id)
                    dialogue_lines.append(f"Let me teach you the symbol of {symbol_id}...")
                    dialogue_lines.append(f"You have learned: {symbol_id}!")
            else:
                dialogue_lines.append("I have taught you all I know.")

        # Show dialogue
        self.dialogue_box.show(dialogue_lines, npc.get_display_name())

    def _start_dialogue_tree(self, npc, tree_data):
        """Start a branching dialogue tree conversation."""
        from ..ui.dialogue_box import DialogueTree

        # Create dialogue tree from data
        tree = DialogueTree(tree_data)
        node = tree.start("start")

        if not node:
            # Fallback to simple greeting
            self.dialogue_box.show(npc.get_greeting(self.player), npc.get_display_name())
            return

        # Store tree reference for continuation
        self.game._active_dialogue_tree = tree
        self.game._active_dialogue_npc = npc

        # Show first node
        self._show_dialogue_node(node, npc)

    def _show_dialogue_node(self, node, npc):
        """Display a single dialogue node."""
        if not node:
            # Dialogue complete, check for teaching
            self._finish_dialogue_with_npc(npc)
            return

        speaker = node.get("speaker", npc.get_display_name())
        text = node.get("text", "...")

        if "choices" in node:
            # Show choice dialogue
            choices = [{"label": c["label"], "value": i} for i, c in enumerate(node["choices"])]

            def on_choice(choice_index):
                next_node = self.game._active_dialogue_tree.advance(choice_index)
                self._show_dialogue_node(next_node, npc)

            self.dialogue_box.show_choice(text, choices, on_choice, speaker)
        else:
            # Show regular dialogue, then advance
            def after_text():
                next_node = self.game._active_dialogue_tree.advance()
                if next_node:
                    self._show_dialogue_node(next_node, npc)
                else:
                    self._finish_dialogue_with_npc(npc)

            # Queue text and set up continuation
            self.dialogue_box.show(text, speaker)
            self.game._pending_dialogue_continuation = after_text

    def _finish_dialogue_with_npc(self, npc):
        """Handle end of dialogue - teach symbols if applicable."""
        self.game._active_dialogue_tree = None
        self.game._active_dialogue_npc = None
        self.game._pending_dialogue_continuation = None
        self.game._conversation_npc = None

        # Resume NPC movement
        npc.in_conversation = False

        # Check if NPC can teach something
        if npc.can_teach:
            teachable = npc.get_teachable_for_player(self.player)
            if teachable:
                symbol_id = teachable[0]
                success, message, data = npc.teach_symbol(symbol_id, self.player)
                if success:
                    # Record in notebook
                    symbol = MagicSystem.get_symbol(symbol_id)
                    symbol_data = symbol.to_dict() if symbol else {}
                    self.notebook.record_symbol_discovery(
                        symbol_id,
                        data.get("context", ""),
                        f"Location: {self.player.x}, {self.player.y}",
                        symbol_data
                    )
                    self.spell_notebook.learn_spell(symbol_id)
                    self.dialogue_box.show(
                        [f"Let me teach you the symbol of {symbol_id}...",
                         f"You have learned: {symbol_id}!"],
                        npc.get_display_name()
                    )

    def on_dialogue_closed(self):
        """Called when dialogue box closes - handle continuations and NPC state."""
        # Check for pending dialogue continuation
        if self.game._pending_dialogue_continuation:
            continuation = self.game._pending_dialogue_continuation
            self.game._pending_dialogue_continuation = None
            continuation()
            return  # Continuation may start new dialogue

        # Resume NPC movement if no continuation
        if self.game._conversation_npc:
            self.game._conversation_npc.in_conversation = False
            self.game._conversation_npc = None

    def _interact_with_rune_stone(self, rune_stone):
        """Handle interaction with a rune stone."""
        dialogue_lines = []

        if rune_stone.can_teach(self.player):
            success, messages = rune_stone.teach(self.player)
            dialogue_lines.extend(messages)

            if success:
                # Record in notebook
                symbol = MagicSystem.get_symbol(rune_stone.symbol_id)
                symbol_data = symbol.to_dict() if symbol else {}
                self.notebook.record_symbol_discovery(
                    rune_stone.symbol_id,
                    rune_stone.teaching_context,
                    f"Location: {self.player.x}, {self.player.y}",
                    symbol_data
                )
                # Also add to spell notebook (journal)
                self.spell_notebook.learn_spell(rune_stone.symbol_id)

                # Persist rune stone activation in area state
                map_obj_id = getattr(rune_stone, 'map_object_id', None)
                if map_obj_id and self.game.current_area_id:
                    area_state = self.game.area_state_manager.get_state(
                        self.game.current_area_id
                    )
                    area_state.set_rune_stone_state(map_obj_id, True)
        else:
            # Stone is dormant or player already knows the symbol
            interaction = rune_stone.get_component("InteractionComponent")
            if interaction:
                dialogue_lines.append(interaction.examine_text)

        self.dialogue_box.show(dialogue_lines, "Rune Stone")

    def _open_shop(self, npc):
        """Open shop UI for a merchant NPC."""
        def on_shop_close():
            # Resume NPC movement when shop closes
            npc.in_conversation = False
            self.game._conversation_npc = None

        self.game.shop_ui.open(
            npc,
            self.player.inventory,
            self.player.gold,
            on_close=on_shop_close
        )
