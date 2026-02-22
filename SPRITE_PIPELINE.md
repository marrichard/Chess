# Sprite Generation Pipeline — Current Task

## Goal
Generate **28x28 pixel art sprites** for all 42 piece types using Stable Diffusion, replacing the placeholder SVG icons.

## Desktop Setup Required
- NVIDIA 5060 Ti (16GB VRAM) on desktop PC
- Need to install ComfyUI + a pixel art SD model

## Steps

### 1. Install ComfyUI
Set up ComfyUI on the desktop (the modern node-based Stable Diffusion UI).

### 2. Download a Pixel Art Model
Get a Stable Diffusion checkpoint fine-tuned for pixel art / game icons.

### 3. Generate Sprites
- Generate at 512x512 with pixel art model
- Prompt template: "game icon, fantasy chess piece, [piece name], dark background, clean silhouette, pixel art, 2D sprite"
- Batch all 42 piece types
- Use img2img or IP-Adapter for style consistency across pieces

### 4. Post-Process
- Downscale 512x512 → 28x28 using **nearest-neighbor** interpolation (preserves hard pixel edges)
- Remove backgrounds → transparent PNG
- Generate two color variants per piece: **player** (blue) and **enemy** (red)
- Save as `web/sprites/{type}_{team}.png` (e.g. `web/sprites/pawn_player.png`)

### 5. Activate in Game
- In `web/pieceRenderer.js`, call `PieceRenderer.setMode('img')` to switch from SVG to sprite mode
- The renderer will load `web/sprites/{type}_{team}.png` automatically
- CSS `image-rendering: pixelated` ensures crispy upscaling on the board

## All 42 Piece Types

| Group | Pieces |
|-------|--------|
| **Classic (6)** | pawn, knight, bishop, rook, queen, king |
| **Undead (6)** | ghost, reaper, phantom, poltergeist, parasite, void |
| **Beast (5)** | wyvern, imp, king_rat, mimic, phoenix |
| **Warrior (6)** | berserker_piece, duelist, lancer, charger, assassin, sentinel |
| **Magic (7)** | witch, healer, bard, alchemist_piece, summoner, trickster, time_mage |
| **Mechanical (6)** | cannon, bomb, totem, decoy, wall, golem |
| **Special (6)** | gambler, anchor_piece, mirror_piece, shapeshifter, leech, torch |

## Style Notes
- 28x28 pixel art (Enter the Gungeon-like crunch)
- Two team colors: player (#5082ff blue) and enemy (#ff4646 red)
- Pixelation hides AI artifacts and gives cohesive retro aesthetic
- `web/sprite-preview.html` can be used to compare resolutions

## What's Already Built
- `web/pieceRenderer.js` — abstraction layer, SVG/IMG mode switching, fallback to Unicode
- `web/pieceSVGs.js` — placeholder SVG paths (will be replaced by sprites)
- `web/game.js` — all render functions use PieceRenderer, enhanced animations (attack lunge, spawn, death, particles, screen effects)
- `web/game.css` — animation keyframes for all effects
- `modes/autobattler.py` — `_last_actions` backend tracking for attack animations
