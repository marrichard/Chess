# Visual Improvements Draft

Prioritized by impact. Each phase is independent and can be done in any order.

---

## Phase A: CSS Custom Properties + Color Consistency

**Problem:** 18+ hardcoded gray shades, 6+ inconsistent font sizes for equivalent elements, HP bar colors from a completely different design language. Overlay CSS duplicated across game.css and menu.css (~300 lines).

**Changes:**

### New file: `web/shared.css`
Extract into a shared stylesheet loaded by both pages:
- CSS custom properties for the full palette (backgrounds, accents, text hierarchy, team colors)
- All overlay/codex/settings panel styles (currently duplicated)
- Unified card interaction classes

```
:root {
  --bg-deep:    #0a0a14;
  --bg-surface: rgba(15, 15, 30, 0.98);
  --bg-card:    rgba(20, 20, 40, 0.85);
  --bg-panel:   rgba(20, 20, 40, 0.7);

  --accent:       #b48eff;
  --accent-dim:   rgba(180, 142, 255, 0.15);
  --accent-mid:   rgba(180, 142, 255, 0.3);
  --accent-bright: rgba(180, 142, 255, 0.6);

  --gold:    #ffd700;
  --player:  #5082ff;
  --enemy:   #ff4646;
  --success: #66ff88;
  --danger:  #ff6666;

  --text-primary:   #e0e0e0;
  --text-secondary: #aaa;
  --text-dim:       #888;
  --text-muted:     #666;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 12px;

  --card-padding: 12px;
  --card-gap: 6px;
}
```

Replace all hardcoded colors with variables. Consolidate to 4 text grays, 3 radii, 1 card padding value.

### HP bar colors
Replace Material-design greens/oranges/reds with theme-consistent:
- High: `#66ff88` (matches existing success green)
- Medium: `var(--gold)`
- Low: `var(--enemy)`

---

## Phase B: Board Visual Upgrade

**Problem:** The board is the centerpiece but has the least visual depth. Warm beige/olive cells clash with the cool purple UI. No shadow, no frame, no coordinate labels, flat cells.

**Changes:**

### Board frame
- Add `box-shadow: 0 0 30px rgba(180, 142, 255, 0.15), inset 0 0 1px rgba(255,255,255,0.05)` to `#board`
- Increase `border-radius` from `4px` to `6px` to reduce the jarring gap with `10px` cards

### Themed board colors
Replace warm beige/olive with cool-toned colors that match the UI:
- Light cells: `#8882a8` (muted lavender)
- Dark cells: `#504868` (deep purple-slate)

### Cell depth
Add subtle inner shadow to each cell:
```css
.cell { box-shadow: inset 0 1px 0 rgba(255,255,255,0.06), inset 0 -1px 0 rgba(0,0,0,0.15); }
```

### Coordinate labels
Add rank (1-8) and file (a-h) labels via CSS `::before`/`::after` on edge cells, or via small DOM elements generated in `renderBoard()`. Small, `0.5rem`, `var(--text-muted)`, positioned at cell edges.

### Blocked cell pattern
Replace flat `#333` with a diagonal stripe pattern:
```css
.cell.blocked {
  background: repeating-linear-gradient(45deg, #2a2a3a, #2a2a3a 4px, #222235 4px, #222235 8px) !important;
}
```

### Move indicator pulse
```css
.cell.highlight-move::after { animation: movePulse 1.5s ease-in-out infinite; }
@keyframes movePulse { 0%,100%{opacity:0.5} 50%{opacity:0.9} }
```

---

## Phase C: Overlay Animations + Depth

**Problem:** Overlays snap in/out with `display:none`/`display:flex`. No backdrop blur. No shadows on panels. No entrance drama.

**Changes:**

### Animated overlay toggle
Replace `overlay-hidden`/`overlay-visible` with animatable classes:
```css
.overlay-base {
  position: fixed; inset: 0; z-index: 150;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; pointer-events: none;
  transition: opacity 200ms ease;
}
.overlay-base.open {
  opacity: 1; pointer-events: auto;
}
```

Update JS to toggle `.open` class instead of swapping classNames.

### Backdrop blur
```css
.options-backdrop { backdrop-filter: blur(6px); }
```

### Panel shadow + entrance
```css
.options-panel, .chessticon-panel {
  box-shadow: 0 8px 40px rgba(0,0,0,0.5);
  transform: scale(0.95);
  transition: transform 200ms ease;
}
.overlay-base.open .options-panel,
.overlay-base.open .chessticon-panel {
  transform: scale(1);
}
```

### Panel close button
Add a small X button in the top-right of each overlay panel (purely a mouse affordance, ESC still works).

### Tooltip upgrade
Add shadow and entrance transform:
```css
#tooltip {
  box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  transform: translateY(4px);
  transition: opacity 150ms ease, transform 150ms ease;
}
#tooltip.visible { transform: translateY(0); }
```

---

## Phase D: Unified Card Interactions

**Problem:** 5+ card types with slightly different padding, radius, hover transforms, and selected shadows. No `:active` or `:focus-visible` on game-side buttons.

**Changes:**

### Shared interaction mixin
All interactive cards (`.shop-card`, `.draft-card`, `.elo-card`, `.codex-card`, `.roster-select-card`, `.tarot-select-card`) get:
```css
/* Consistent card base */
padding: var(--card-padding);
border-radius: var(--radius-md);
background: var(--bg-card);
border: 1px solid var(--accent-dim);

/* Unified interactions */
:hover { border-color: var(--accent-mid); box-shadow: 0 0 12px rgba(180,142,255,0.2); transform: translateY(-2px); }
.selected { border-color: var(--accent); box-shadow: 0 0 16px rgba(180,142,255,0.4); transform: translateY(-3px); }
:active { transform: scale(0.97); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
```

### Unaffordable state
```css
.unaffordable { opacity: 0.5; cursor: not-allowed; filter: saturate(0.5); }
```

### Card entrance animation
Add staggered entrance to shop, draft, ELO shop, and codex cards via JS:
```js
card.style.animationDelay = (i * 50) + 'ms';
card.classList.add('card-enter');
```
```css
.card-enter {
  opacity: 0; transform: translateY(12px);
  animation: cardEnter 300ms ease forwards;
}
```

---

## Phase E: Particle System Enrichment

**Problem:** Only 12 particles per capture, circles only, no glow, no ambient particles, no non-capture events.

**Changes:**

### Glow composite
```js
particleCtx.globalCompositeOperation = 'lighter';
```
Restoring to `'source-over'` after the particle pass. This makes overlapping particles glow brighter.

### More + varied particles
- Increase to 20 particles per capture burst
- Add 4 "spark" particles: small (1-2px), faster (150-200 speed), shorter life (0.3s), white/gold color
- Slight random wobble: `p.vx += (Math.random() - 0.5) * 40 * dt;`

### Ambient motes (always-on)
Spawn 1 ambient particle every 2 seconds, slowly rising, very low alpha (0.15), purple tint, no gravity (slight upward drift). Creates subtle atmospheric movement.

### Additional triggers
- **Victory:** Gold confetti burst (30 particles, upward, gold + white)
- **Defeat:** Red embers (10 particles, slow, downward)
- **Purchase:** Small green/gold sparkle at the card position
- **Boss intro:** Red particle ring expanding outward from the boss icon

---

## Phase F: Battle Feedback

**Problem:** No damage numbers, no gold-change animation, no turn indicator, HP transitions don't fire due to board rebuild.

**Changes:**

### Floating damage numbers
After `detectAnimations()` compares old/new states, for any piece whose HP decreased, create a floating `<div>` at the board position:
```css
.damage-popup {
  position: absolute; color: var(--enemy); font-weight: bold; font-size: 0.9rem;
  pointer-events: none; z-index: 10;
  animation: damageFloat 800ms ease forwards;
}
@keyframes damageFloat { 0%{opacity:1;transform:translateY(0)} 100%{opacity:0;transform:translateY(-30px)} }
```

Show the delta: e.g. "-3". Positive heals show in green "+2".

### Gold/ELO flash
When `#stat-gold` or `#elo-balance` text changes, briefly pulse the element:
```css
.value-flash { animation: valueFlash 400ms ease; }
@keyframes valueFlash { 0%{color:#fff;transform:scale(1.2)} 100%{color:inherit;transform:scale(1)} }
```

### Turn indicator
In battle phase, add a pulsing border glow on the board:
- Player turn: soft blue pulse on board border
- Enemy turn: soft red pulse

```css
#board.player-turn { animation: playerTurnPulse 1.5s ease-in-out infinite alternate; }
@keyframes playerTurnPulse { from{box-shadow:0 0 20px rgba(80,130,255,0.2)} to{box-shadow:0 0 30px rgba(80,130,255,0.4)} }
```

### Cell hover highlight
```css
.cell:hover { filter: brightness(1.15); }
```

---

## Phase G: Dramatic Moments

**Problem:** Boss intro, victory, defeat all lack visual weight.

**Changes:**

### Boss intro
- Boss icon scales up from 0 to 1 with a bounce: `animation: bossAppear 600ms cubic-bezier(0.34, 1.56, 0.64, 1)`
- Red vignette on the backdrop: `box-shadow: inset 0 0 80px rgba(255,0,0,0.15)` on the overlay
- Brief screen shake on appear

### Victory overlay
- Green/gold border glow: `border-color: #66ff88; box-shadow: 0 0 30px rgba(102,255,136,0.3)`
- Gold confetti particles behind the card
- Title bounces in

### Defeat overlay
- Red vignette: dim red glow on the card border
- Slower fade-in (400ms vs 200ms) for weight
- Desaturate the game behind the overlay slightly

### Wave announcement
Between waves, briefly flash "WAVE X" as a large centered text that fades out:
```css
.wave-announce {
  position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 3rem; color: var(--accent); z-index: 50;
  animation: waveAnnounce 1.2s ease forwards; pointer-events: none;
}
@keyframes waveAnnounce { 0%{opacity:0;transform:scale(0.8)} 20%{opacity:1;transform:scale(1)} 80%{opacity:1} 100%{opacity:0;transform:scale(1.05)} }
```

---

## Phase H: Background Animation in Game

**Problem:** The menu has a slow-shifting radial gradient background. The game page has the same gradient but completely static.

**Changes:**

Add the `bgShift` animation to game.css `#bg-effects` (copy from menu.css, same `20s ease-in-out infinite alternate`). Subtle ambient movement that prevents the game feeling frozen during setup.

---

## Summary Table

| Phase | Effort | Impact | Files |
|-------|--------|--------|-------|
| A: CSS Variables + Shared | Medium | Foundation | +shared.css, game.css, menu.css, both .html |
| B: Board Upgrade | Small | High | game.css, game.js (coords) |
| C: Overlay Animations | Small | Medium | game.css, menu.css, game.js, menu.js |
| D: Unified Cards | Medium | Medium | game.css, menu.css |
| E: Particles | Medium | High | game.js |
| F: Battle Feedback | Medium | High | game.js, game.css |
| G: Dramatic Moments | Medium | High | game.js, game.css |
| H: Game Background Anim | Tiny | Low | game.css |

Recommended order: **H -> B -> C -> A -> D -> E -> F -> G** (quick wins first, foundation next, then richness).
