# Game Assets

This folder contains all game assets. The game uses an AssetManager that provides
placeholder graphics when real assets aren't available.

## Folder Structure

```
assets/
├── sprites/           # Entity and object sprites
│   ├── player/        # Player character sprites
│   ├── entities/      # NPCs, enemies, etc.
│   ├── objects/       # Trees, rocks, logs, etc.
│   ├── effects/       # Spell effects, particles
│   └── weapons/       # Weapon sprites and swing effects
├── tiles/             # Tile sprites for the world
├── ui/                # UI elements (buttons, frames, icons)
├── fonts/             # Custom fonts
└── audio/             # Sound effects and music
    ├── sfx/           # Sound effects
    └── music/         # Background music
```

## Sprite Specifications

- **Tile Size**: 32x32 pixels (configurable in Settings)
- **Format**: PNG with transparency recommended
- **Naming Convention**: `entity_state.png` (e.g., `player_idle.png`, `tree_burning.png`)

## Placeholder System

The AssetManager will automatically use procedural placeholder graphics for any
missing assets. To add a real asset, simply place it in the correct folder with
the expected filename - the game will automatically use it.

## Asset Types Needed

### Sprites (32x32 unless noted)
- `player/player_idle.png` - Player standing
- `player/player_walk_*.png` - Player walking animation (up/down/left/right)
- `objects/tree.png` - Normal tree
- `objects/tree_burning.png` - Tree on fire
- `objects/rock.png` - Rock/boulder
- `objects/log.png` - Fallen log
- `objects/bush.png` - Bush
- `entities/npc_*.png` - NPC sprites
- `entities/rune_stone.png` - Rune stone (active)
- `entities/rune_stone_dormant.png` - Rune stone (used)
- `weapons/sword.png` - Sword icon
- `weapons/axe.png` - Axe icon
- `weapons/great_sword.png` - Great sword icon
- `weapons/great_axe.png` - Great axe icon
- `weapons/swing_effect.png` - Weapon swing arc (64x64)
- `effects/fire.png` - Fire particle
- `effects/water.png` - Water splash
- `effects/force.png` - Force push effect

### Tiles (32x32)
- `tiles/ground.png`
- `tiles/grass.png`
- `tiles/water.png`
- `tiles/wall.png`
- `tiles/dirt.png`
- `tiles/stone.png`

### UI Elements
- `ui/health_bar.png`
- `ui/mana_bar.png`
- `ui/menu_frame.png`
- `ui/button.png`
- `ui/radial_menu_bg.png`

### Audio
- `audio/sfx/sword_swing.wav`
- `audio/sfx/axe_swing.wav`
- `audio/sfx/tree_fall.wav`
- `audio/sfx/spell_cast.wav`
- `audio/sfx/fire_burning.wav`
- `audio/sfx/water_splash.wav`
- `audio/music/exploration.ogg`
