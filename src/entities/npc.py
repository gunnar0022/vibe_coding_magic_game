"""
NPC entity - non-player characters that can teach, trade, and interact.
Supports patrol behavior with waypoints.
"""
import math
import random
from .actor import Actor


class NPC(Actor):
    """
    A non-player character.
    NPCs can teach symbols, provide information, and offer services.
    Supports patrol behavior with waypoints.
    """

    # AI States
    STATE_IDLE = "idle"
    STATE_WALKING = "walking"
    STATE_WAITING = "waiting"

    def __init__(self, x=0, y=0, npc_id="generic_npc", data=None):
        super().__init__(x, y, tags=["npc"])
        data = data or {}

        self.npc_id = npc_id
        self.controller = "ai"

        # NPC properties
        self.name = data.get("name", "Stranger")
        self.title = data.get("title", "")  # e.g., "Village Elder", "Wandering Mage"
        self.color = data.get("color", (200, 150, 100))

        # Internal backstory (not shown to player, for developer reference)
        self.backstory = data.get("backstory", "")

        # Personality descriptor (affects dialogue tone)
        self.personality = data.get("personality", "neutral")

        # Dialogue
        self.dialogue_id = data.get("dialogue_id", None)
        self.dialogue_tree = data.get("dialogue_tree", None)  # Full dialogue tree dict
        self.interaction.set_dialogue(self.dialogue_id)
        self.interaction.can_talk = True
        self.interaction.can_examine = True

        # Examination text
        examine = data.get("examine_text", f"{self.name} stands here.")
        if self.title:
            examine = f"{self.name}, {self.title}. " + examine
        self.interaction.set_examine_text(examine)

        # Teaching capability
        self.can_teach = data.get("can_teach", False)
        self.teachable_symbols = data.get("teachable_symbols", [])
        self.taught_symbols = set()  # Symbols already taught to player

        # Trading capability
        self.can_trade = data.get("can_trade", False)
        self.trade_inventory = data.get("trade_inventory", [])

        # Movement behavior
        self.wanders = data.get("wanders", False)
        self.wander_radius = data.get("wander_radius", 3)
        self.home_x = x
        self.home_y = y

        # Patrol behavior
        self.patrol_points = data.get("patrol_points", [])  # List of (x, y) tuples
        self.patrol_index = 0
        self.patrol_wait_time = data.get("patrol_wait_time", 3.0)  # Seconds to wait at each point
        self.patrol_speed = data.get("patrol_speed", 2.0)  # Tiles per second

        # AI state
        self.ai_state = self.STATE_IDLE
        self.ai_timer = 0
        self.target_x = None
        self.target_y = None

        # Conversation state - pauses AI movement
        self.in_conversation = False

        # World reference for collision detection (set by game)
        self.world_ref = None

    def set_world(self, world):
        """Set world reference for collision detection during movement."""
        self.world_ref = world

    def get_display_name(self):
        """Get full display name with title."""
        if self.title:
            return f"{self.name}, {self.title}"
        return self.name

    def can_teach_symbol(self, symbol_id):
        """Check if NPC can teach a specific symbol."""
        return (self.can_teach and
                symbol_id in self.teachable_symbols and
                symbol_id not in self.taught_symbols)

    def teach_symbol(self, symbol_id, player):
        """
        Teach a symbol to the player.
        Returns (success, message, symbol_data).
        """
        if not self.can_teach_symbol(symbol_id):
            return False, "I have nothing more to teach you about that.", None

        if player.learn_symbol(symbol_id):
            self.taught_symbols.add(symbol_id)
            return True, f"Let me show you the symbol of {symbol_id}...", {
                "symbol_id": symbol_id,
                "teacher": self.name,
                "context": f"Taught by {self.get_display_name()}",
            }
        else:
            return False, "You already know this symbol.", None

    def get_teachable_for_player(self, player):
        """Get list of symbols this NPC can teach to this player."""
        return [s for s in self.teachable_symbols
                if s not in self.taught_symbols and s not in player.known_symbols]

    def update(self, dt):
        super().update(dt)
        self._update_ai(dt)

    def _update_ai(self, dt):
        """Update AI behavior based on current state."""
        # Don't move during conversations
        if self.in_conversation:
            return

        if self.ai_state == self.STATE_IDLE:
            self._update_idle(dt)
        elif self.ai_state == self.STATE_WALKING:
            self._update_walking(dt)
        elif self.ai_state == self.STATE_WAITING:
            self._update_waiting(dt)

    def _update_idle(self, dt):
        """Handle idle state - decide what to do next."""
        self.ai_timer -= dt
        if self.ai_timer <= 0:
            # Decide next action
            if self.patrol_points:
                # Start patrol
                self._start_walking_to_patrol_point()
            elif self.wanders:
                # Random wander
                self._start_random_wander()
            else:
                # Just stand around, maybe change facing
                if random.random() < 0.1:
                    self.facing = random.choice(["up", "down", "left", "right"])
                self.ai_timer = 2.0 + random.random() * 3.0

    def _update_walking(self, dt):
        """Handle walking state - move toward target."""
        if self.target_x is None or self.target_y is None:
            self.ai_state = self.STATE_IDLE
            return

        # Calculate direction to target
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # Check if we've reached the target
        if distance < 0.3:
            self.x = float(self.target_x)
            self.y = float(self.target_y)
            self._on_reached_destination()
            return

        # Normalize direction
        if distance > 0:
            dx /= distance
            dy /= distance

        # Update facing based on movement direction
        if abs(dx) > abs(dy):
            self.facing = "right" if dx > 0 else "left"
        else:
            self.facing = "down" if dy > 0 else "up"

        # Try to move
        if self.world_ref:
            move_speed = self.patrol_speed * dt
            self.try_move(dx * move_speed, dy * move_speed, self.world_ref, dt)
        else:
            # No world reference, just teleport slowly
            move_amount = self.patrol_speed * dt
            self.x += dx * move_amount
            self.y += dy * move_amount

    def _update_waiting(self, dt):
        """Handle waiting state - wait at current position."""
        self.ai_timer -= dt
        if self.ai_timer <= 0:
            self.ai_state = self.STATE_IDLE
            self.ai_timer = 0.5  # Short delay before next action

    def _start_walking_to_patrol_point(self):
        """Start walking to the current patrol point."""
        if not self.patrol_points:
            return

        # Get next patrol point
        target = self.patrol_points[self.patrol_index]
        self.target_x = target[0]
        self.target_y = target[1]
        self.ai_state = self.STATE_WALKING

    def _start_random_wander(self):
        """Start walking to a random nearby point."""
        # Pick a random point within wander radius
        angle = random.random() * 2 * math.pi
        dist = random.random() * self.wander_radius
        self.target_x = self.home_x + math.cos(angle) * dist
        self.target_y = self.home_y + math.sin(angle) * dist
        self.ai_state = self.STATE_WALKING

    def _on_reached_destination(self):
        """Called when NPC reaches their destination."""
        if self.patrol_points:
            # Move to next patrol point
            self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)

        # Wait at destination
        self.ai_state = self.STATE_WAITING
        self.ai_timer = self.patrol_wait_time + random.random() * 2.0
        self.target_x = None
        self.target_y = None

    def get_greeting(self, player=None):
        """Get a greeting message for interaction."""
        # Check if we've taught everything we can
        if player and self.can_teach:
            teachable = self.get_teachable_for_player(player)
            if not teachable and self.taught_symbols:
                # Already taught what we know
                return f"Welcome back, young one. Practice the symbol of {', '.join(self.taught_symbols)} well."

        greetings = [
            f"Hello, traveler. I am {self.name}.",
            f"Greetings. What brings you here?",
            f"Ah, a visitor. I am {self.get_display_name()}.",
        ]
        return random.choice(greetings)

    def serialize(self):
        data = super().serialize()
        data.update({
            "npc_id": self.npc_id,
            "name": self.name,
            "title": self.title,
            "taught_symbols": list(self.taught_symbols),
            "ai_state": self.ai_state,
            "patrol_index": self.patrol_index,
        })
        return data

    def deserialize(self, data):
        super().deserialize(data)
        self.taught_symbols = set(data.get("taught_symbols", []))
        self.ai_state = data.get("ai_state", self.STATE_IDLE)
        self.patrol_index = data.get("patrol_index", 0)


# Predefined NPC templates
NPC_TEMPLATES = {
    "village_elder": {
        "name": "Elder Mira",
        "title": "Village Elder",
        "color": (180, 160, 140),
        "can_teach": True,
        "teachable_symbols": ["force"],
        "examine_text": "An elderly woman with kind eyes and weathered hands. She has seen much.",
        "personality": "cautious, protective",
        "backstory": "Survived the collapse as a young woman. Lost her husband to the chaos. Raised the village's children.",
        "wanders": False,
        "dialogue_tree": {
            "start": {
                "text": "Ah, you're awake. I was wondering when you'd find your way here.",
                "speaker": "Elder Mira",
                "next": "question"
            },
            "question": {
                "text": "The world beyond the village is dangerous. Are you certain you wish to venture out?",
                "speaker": "Elder Mira",
                "choices": [
                    {"label": "Yes, I'm ready", "value": "yes", "next": "yes_response"},
                    {"label": "Not yet", "value": "no", "next": "no_response"}
                ]
            },
            "yes_response": {
                "text": "Then be careful. Trust your instincts, but do not trust them blindly. The magic... it changes things. Sometimes in ways we cannot see.",
                "speaker": "Elder Mira",
                "next": None
            },
            "no_response": {
                "text": "There is no shame in caution. This village has survived because we learned when to act and when to wait. Take your time.",
                "speaker": "Elder Mira",
                "next": None
            }
        }
    },
    "wandering_mage": {
        "name": "Kael",
        "title": "Wandering Scholar",
        "color": (100, 120, 180),
        "can_teach": True,
        "teachable_symbols": ["wind", "earth", "light"],
        "examine_text": "A traveler in worn robes, carrying a staff covered in strange markings.",
        "personality": "curious, detached",
        "backstory": "Travels between settlements collecting knowledge. Doesn't stay long anywhere.",
        "wanders": True,
        "wander_radius": 5,
    },
    "hermit": {
        "name": "The Hermit",
        "title": "",
        "color": (120, 100, 80),
        "can_teach": True,
        "teachable_symbols": ["life"],
        "examine_text": "A mysterious figure who rarely speaks. Their eyes hold ancient knowledge.",
        "personality": "withdrawn, knowing",
        "backstory": "Was among the first to receive visions. The experience changed them.",
        "wanders": False,
    },
    "merchant": {
        "name": "Bram",
        "title": "Traveling Merchant",
        "color": (160, 140, 100),
        "can_teach": False,
        "can_trade": True,
        "examine_text": "A jovial merchant with a cart full of curious goods.",
        "personality": "friendly, opportunistic",
        "backstory": "One of the few who travels between villages. Knows more than he lets on.",
        "wanders": False,
    },
    # New village NPCs
    "finn_farmer": {
        "name": "Finn",
        "title": "Farmer",
        "color": (140, 120, 90),
        "can_teach": False,
        "examine_text": "A weathered man with calloused hands. He tends the village garden with quiet dedication.",
        "personality": "practical, grounded, suspicious of magic",
        "backstory": "Lost his family during the collapse. Found purpose in growing food for the community.",
        "wanders": False,
        "patrol_points": [(31, 13), (31, 15), (32, 14)],
        "patrol_wait_time": 4.0,
        "patrol_speed": 1.5,
        "dialogue_tree": {
            "start": {
                "text": "Hmm? What do you want?",
                "speaker": "Finn",
                "next": "talk"
            },
            "talk": {
                "text": "I tend the garden. Plants grow faster now than before, they say. Stranger too. Some grow toward you when you're not looking. I don't trust it.",
                "speaker": "Finn",
                "next": "magic_question"
            },
            "magic_question": {
                "text": "You use that magic, don't you? The symbols?",
                "speaker": "Finn",
                "choices": [
                    {"label": "Yes, I do", "value": "yes", "next": "magic_yes"},
                    {"label": "Not much", "value": "no", "next": "magic_no"}
                ]
            },
            "magic_yes": {
                "text": "...Just be careful with it. I've seen what happens when people get too comfortable with power they don't understand.",
                "speaker": "Finn",
                "next": None
            },
            "magic_no": {
                "text": "Smart. Tools we can understand are better than forces we cannot. But I suppose we all have to adapt.",
                "speaker": "Finn",
                "next": None
            }
        }
    },
    "young_sera": {
        "name": "Sera",
        "title": "",
        "color": (180, 140, 160),
        "can_teach": False,
        "examine_text": "A young woman with curious eyes. She watches everything with intense interest.",
        "personality": "curious, hopeful, asks questions",
        "backstory": "Born after the collapse. Knows only this world. Fascinated by magic and stories of before.",
        "wanders": True,
        "wander_radius": 6,
        "patrol_speed": 2.5,
        "dialogue_tree": {
            "start": {
                "text": "Oh! Hi! You're the one who can do magic, right? Real magic?",
                "speaker": "Sera",
                "next": "question"
            },
            "question": {
                "text": "Can I ask you something? Have you seen the lights in the forest at night?",
                "speaker": "Sera",
                "choices": [
                    {"label": "Yes, I have", "value": "yes", "next": "lights_yes"},
                    {"label": "No, what lights?", "value": "no", "next": "lights_no"}
                ]
            },
            "lights_yes": {
                "text": "I knew it! The elders say it's nothing, but I've seen them too. Blue and green, dancing between the trees. I think... I think there's something out there. Something waiting.",
                "speaker": "Sera",
                "next": "excitement"
            },
            "lights_no": {
                "text": "Oh... maybe you haven't been out at night yet. Sometimes, if you watch the treeline, you can see them. Floating lights. The elders won't talk about it.",
                "speaker": "Sera",
                "next": "excitement"
            },
            "excitement": {
                "text": "When you go out there, will you tell me what you find? I want to know everything about the world outside.",
                "speaker": "Sera",
                "next": None
            }
        }
    },
    "old_bram_storyteller": {
        "name": "Old Bram",
        "title": "Storyteller",
        "color": (150, 130, 110),
        "can_teach": False,
        "examine_text": "An old man who sits by the fire. His eyes are distant, lost in memory.",
        "personality": "nostalgic, talkative, sometimes confused",
        "backstory": "Was a child when the collapse happened. Remembers fragments of the old world.",
        "wanders": False,
        "dialogue_tree": {
            "start": {
                "text": "Ah, a visitor. Sit, sit. Let me tell you something...",
                "speaker": "Old Bram",
                "next": "story"
            },
            "story": {
                "text": "I was just a boy when the lights went out. Not these lights - the old ones. The ones that came from wires and boxes. One moment they were there, and then... gone. Forever.",
                "speaker": "Old Bram",
                "next": "memory"
            },
            "memory": {
                "text": "People didn't believe it at first. They thought the lights would come back. They always came back before. But not this time. This time, something else came instead.",
                "speaker": "Old Bram",
                "next": "ending"
            },
            "ending": {
                "text": "Magic, they call it now. As if giving it a name makes it less strange. But I remember when the world made sense. Sometimes I miss that.",
                "speaker": "Old Bram",
                "next": None
            }
        }
    },
}


def create_npc_from_template(template_id, x, y):
    """Create an NPC from a predefined template."""
    if template_id not in NPC_TEMPLATES:
        return NPC(x, y, template_id)

    template = NPC_TEMPLATES[template_id].copy()
    return NPC(x, y, template_id, template)
