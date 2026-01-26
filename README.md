# Symbolic Magic RPG (Working Title)

This repository contains an experimental 2D RPG prototype built around a symbolic, knowledge-driven magic system.  
The project emphasizes *systems, discovery, and player understanding* over content volume or traditional stat-driven progression.

This is a **vibe coding project**: design-first, exploratory, iterative, and intentionally open-ended.  
The goal is not to rush toward a finished product, but to build a coherent, extensible foundation where ideas can be tested honestly.

---

## Project Philosophy

This game is built on a few core beliefs:

• Player knowledge can be a meaningful progression system  
• Complex behavior should emerge from simple, consistent rules  
• Static worlds can feel alive through dynamic systems  
• Mystery should persist, not disappear after onboarding  
• Development should stay flexible and reflective, not rigid  

The project intentionally avoids overproduction, premature optimization, and content bloat.  
Systems come first. Content follows once systems prove interesting.

---

## High-Level Concept

The game takes place in a post-collapse world where magic has recently emerged as a real, pervasive force.  
Civilization survived, but was fundamentally reshaped.

Magic manifests through symbol-like characters resembling Chinese or Japanese writing.  
These symbols are not a language in the traditional sense, but fragments of meaning encoded into the world itself.

The player does not receive explicit tutorials or spell explanations.  
Instead, they must learn through experimentation, observation, memory, and personal note-taking.

The world is not meant to feel “solved.”  
Knowledge is fragmented, localized, and often contradictory.

---

## Core Gameplay Pillars

### Symbol-Based Magic

Magic is represented as discrete symbols (e.g. 火 水 動 力).  
Symbols can be cast alone or combined in pairs.

• Order does not matter (X + Y = Y + X)  
• All combinations are hand-authored, including failures  
• Some combinations do nothing or have harmful side effects  

Spells resolve into abstract traits rather than direct effects.  
World objects decide how they react.

Spells do not know what they affect.  
Objects know how they respond.

---

### Knowledge as Progression

The player maintains an in-game notebook.

• Symbols are automatically recorded when discovered  
• Contextual notes may be sparse or incomplete  
• The player may add their own notes freely  
• Notes can be wrong, speculative, or incomplete  

The notebook does not gate gameplay.  
It reflects the player’s understanding, not the character’s stats.

A player who ignores the notebook can still play — but may struggle.  
A player who uses it thoughtfully gains clarity and confidence.

---

### Static World, Dynamic Systems

The world map is largely static and hand-authored.

Dynamic behavior emerges from:

• Environmental reactions to magic traits  
• Object state changes over time  
• Resource growth and decay  
• NPC discovery and progression  

The world can change offscreen.  
The player is not the sole driver of discovery.

---

## Technical Direction

• Python + Pygame  
• Lightweight 2D architecture  
• Data-driven spell definitions (JSON)  
• Modular systems designed for expansion  
• Deterministic logic with emergent outcomes  

This project intentionally avoids heavy engines or opaque tooling.  
The code is meant to be readable, hackable, and inspectable.

---

## Current State

The project is currently a **playable prototype**.

Implemented features include:

• 2D movement and camera system  
• Static test map with terrain and objects  
• Symbol-based magic system  
• Pairwise spell combinations  
• Object-driven spell reactions  
• Status effects (burning, wet, etc.)  
• NPC teachers that unlock symbols  
• Player notebook with discovery tracking  
• Save and load functionality  

Many systems are intentionally minimal and designed to evolve.

---

## AI-Assisted Development

This project makes active use of **Claude Code** as an agentic assistant.

The AI is used to:

• Implement well-defined systems  
• Refactor for clarity and modularity  
• Generate boilerplate and scaffolding  
• Execute on clearly specified tasks  

The human developer retains control over:

• Worldbuilding and lore  
• Design intent and constraints  
• Ethical and cultural considerations  
• High-level architecture decisions  

Uncertainties, ambiguities, and design questions are intentionally documented rather than guessed.

---

## Repository Structure (High-Level)

src/  
  core/           Core systems and state management  
  magic/          Symbol logic and spell resolution  
  world/          Map, tiles, and object behavior  
  ui/             Notebook, magic menus, dialogue  
  entities/       Player, NPCs, creatures  

data/  
  spells/         JSON spell definitions  
  world/          Static world data  

docs/  
  World overview and lore  
  Mechanics and systems  
  Structural planning  
  Open questions and TODOs  

---

## Development Style

This is not a content sprint.  
This is a slow-build systems project.

Expect:

• Iteration over polish  
• Experiments that may be reverted  
• Systems evolving before content  
• Design decisions being revisited  

Git is used as a safety net, not a scoreboard.

---

## What This Project Is NOT

• Not a finished commercial product  
• Not a tutorial-driven RPG  
• Not a stat-heavy or grind-focused game  
• Not a traditional fantasy magic system  

---

## Status

Active development.  
Design and systems exploration phase.

Expect frequent changes.

---

## License

License not yet finalized.

This repository is currently shared for development, experimentation, and documentation purposes.
