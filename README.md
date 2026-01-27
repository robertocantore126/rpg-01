# RPG-01: Undertale-like RPG Engine

A modular RPG engine built with **Python** and **Pygame**, heavily inspired by the mechanics and aesthetics of *Undertale*. This project focuses on high-precision "crispy" pixel art through internal resolution scaling and a unique bullet-hell battle system.

## 🚀 Features

### 🌍 Exploration Mode
- **Retro Visuals**: Internal rendering at 320x240 scaled to 640x480 for authentic pixel aesthetics.
- **Top-Down Movement**: Smooth 4-way movement with collision detection.
- **Dialogue System**: Scrollable typewriter effect with support for NPC interaction.
- **Dynamic Camera**: Smoothly follows the player through map boundaries.

### ⚔️ Battle Engine
- **State-Based Combat**: Toggle between Menu selection and Defense phases.
- **The Soul**: Control a heart restricted within a dynamic "Arena" box.
- **Bullet Patterns**: Spawning system for complex projectile patterns (currently featuring random side-spawning projectiles).
- **Collision Logic**: Real-time hit detection between the Soul and enemy bullets.

## 📁 Project Structure

```text
rpg-01/
├── assets/             # Game resources (sprites, fonts, sounds)
├── engine/             # Core engine package (ServiceContainer, Input, Camera)
├── src/
│   ├── entities/       # Game objects (Player, NPC, Soul, Bullet)
│   ├── scenes/         # Game states (WorldScene, BattleScene)
│   ├── ui/             # UI components (DialogueBox)
│   └── settings.py     # Global constants and config
├── main.py             # Entry point
└── README.md
```

## 🎮 Controls

### Exploration
- **WASD / Arrows**: Move Player
- **Z / Enter**: Interact / Advance Dialogue
- **B**: (Debug) Trigger Battle

### Battle
- **Arrows**: Navigate Menu / Move Soul
- **Z**: Select / Speed up text
- **X**: (Mockup) Return to menu from Defense

## 🛠️ Getting Started

### Prerequisites
- Python 3.x
- Pygame (`pip install pygame`)

### Running the Game
Simply run the main entry point:
```bash
python main.py
```

## 🗺️ Roadmap
- [ ] Implement HP system and damage numbers.
- [ ] Add Menu navigation (FIGHT, ACT, ITEM, MERCY sub-menus).
- [ ] Implement Tiled (.tmx) map loading.
- [ ] Add Sprite animations for characters.
- [ ] Expand Bullet pattern library.

---
*Created with ❤️ for Advanced RPG Development.*
