/* ================================================================
   game.js — Core game frontend for Chess Roguelike
   State management, input dispatch, render dispatch, animations
   ================================================================ */

// Unicode chess pieces
const PIECE_CHARS = {
  'king-player':   '\u2654', 'queen-player':  '\u2655', 'rook-player':   '\u2656',
  'bishop-player': '\u2657', 'knight-player': '\u2658', 'pawn-player':   '\u2659',
  'king-enemy':    '\u265A', 'queen-enemy':   '\u265B', 'rook-enemy':    '\u265C',
  'bishop-enemy':  '\u265D', 'knight-enemy':  '\u265E', 'pawn-enemy':    '\u265F',
  // New abstract pieces (same char for player/enemy, team color differentiates)
  'bomb-player': '\u2738',      'bomb-enemy': '\u2738',
  'mimic-player': '?',          'mimic-enemy': '?',
  'leech-player': '\u2687',     'leech-enemy': '\u2687',
  'summoner-player': '\u2726',  'summoner-enemy': '\u2726',
  'ghost-player': '\u2601',     'ghost-enemy': '\u2601',
  'gambler-player': '\u2660',   'gambler-enemy': '\u2660',
  'anchor_piece-player': '\u2693', 'anchor_piece-enemy': '\u2693',
  'parasite-player': '\u2623',  'parasite-enemy': '\u2623',
  'mirror_piece-player': '\u25C8', 'mirror_piece-enemy': '\u25C8',
  'void-player': '\u25C9',     'void-enemy': '\u25C9',
  'phoenix-player': '\u2600',  'phoenix-enemy': '\u2600',
  'king_rat-player': '\u2689', 'king_rat-enemy': '\u2689',
};

function pieceChar(type, team) {
  return PIECE_CHARS[type + '-' + team] || '?';
}

// State tracking
let currentState = null;
let oldState = null;
let autoBattleTimer = null;
let particleCtx = null;
let particles = [];

// Overlay state
let optionsOpen = false;
let chessiconOpen = false;
let battleSpeedMs = 400;
let particlesEnabled = true;
const SPEED_STEPS = [200, 300, 400, 600, 800, 1000];

// ================================================================
// INITIALIZATION
// ================================================================

window.addEventListener('pywebviewready', async () => {
  // Set up particle canvas
  const canvas = document.getElementById('particles');
  if (canvas) {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    particleCtx = canvas.getContext('2d');
    requestAnimationFrame(updateParticles);
  }

  // Load settings
  try {
    const settings = await pywebview.api.get_settings();
    battleSpeedMs = settings.battle_speed || 400;
    particlesEnabled = settings.particles_enabled !== false;
  } catch (e) {
    console.error('Failed to load settings:', e);
  }

  // Wire up overlay buttons
  setupOverlayControls();

  // Fetch initial state
  try {
    const state = await pywebview.api.get_game_state();
    handleStateUpdate(state);
  } catch (e) {
    console.error('Failed to get initial state:', e);
  }
});

window.addEventListener('resize', () => {
  const canvas = document.getElementById('particles');
  if (canvas) {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
});

// ================================================================
// INPUT HANDLING
// ================================================================

const KEY_MAP = {
  'ArrowUp': 'UP', 'ArrowDown': 'DOWN', 'ArrowLeft': 'LEFT', 'ArrowRight': 'RIGHT',
  'w': 'UP', 'a': 'LEFT', 's': 'DOWN', 'd': 'RIGHT',
  'Enter': 'CONFIRM',
  'Escape': 'CANCEL',
  ' ': 'SPACE',
  'Tab': 'TAB',
  '1': 'NUM_1', '2': 'NUM_2', '3': 'NUM_3', '4': 'NUM_4', '5': 'NUM_5',
  '6': 'NUM_6', '7': 'NUM_7', '8': 'NUM_8', '9': 'NUM_9',
};

document.addEventListener('keydown', async (e) => {
  const action = KEY_MAP[e.key];
  if (!action) return;
  e.preventDefault();

  // Intercept ESC for overlay handling
  if (action === 'CANCEL') {
    if (chessiconOpen) {
      closeChessiconOverlay();
      return;
    }
    if (optionsOpen) {
      closeOptionsOverlay();
      return;
    }
    // In gameplay phases, open options instead of sending CANCEL
    if (currentState) {
      const phase = currentState.phase;
      const gameplayPhases = ['setup', 'battle', 'result', 'shop', 'draft'];
      if (gameplayPhases.includes(phase)) {
        openOptionsOverlay();
        return;
      }
    }
    // Other phases (place_cell, place_border, elo_shop, etc.): pass through
  }

  // Block all other input when overlays are open
  if (optionsOpen || chessiconOpen) return;

  try {
    const result = await pywebview.api.send_action(action, -1, -1);
    handleStateUpdate(result);
  } catch (err) {
    console.error('send_action error:', err);
  }
});

// Board cell click handler (delegated)
function onBoardCellClick(boardId, x, y, eventType) {
  const action = eventType === 'mouseup' ? 'MOUSE_UP' : 'MOUSE_CLICK';
  pywebview.api.send_action(action, x, y).then(handleStateUpdate).catch(console.error);
}

let lastMoveX = -1, lastMoveY = -1;
function onBoardCellMove(boardId, x, y) {
  // Deduplicate: only send if cell actually changed
  if (x === lastMoveX && y === lastMoveY) return;
  lastMoveX = x;
  lastMoveY = y;
  // Update cursor position (lightweight — just updates cursor, no heavy processing)
  pywebview.api.send_action('MOUSE_MOVE', x, y).then(result => {
    // Only update cursor position locally, don't do full re-render for hover
    if (result && result.cursor && currentState) {
      currentState.cursor = result.cursor;
      // Update cursor visuals without full re-render
      updateCursorOnly(boardId, result.cursor);
    }
  }).catch(console.error);
}

function updateCursorOnly(boardId, cursor) {
  const boardEl = document.getElementById(boardId);
  if (!boardEl) return;
  boardEl.querySelectorAll('.cell.cursor-active').forEach(c => c.classList.remove('cursor-active'));
  const idx = cursor[1] * 8 + cursor[0];
  const cell = boardEl.children[idx];
  if (cell) cell.classList.add('cursor-active');
}

// ================================================================
// STATE UPDATE HANDLER
// ================================================================

function handleStateUpdate(state) {
  if (!state) return;

  // Navigation commands
  if (state.navigate === 'menu') {
    clearAutoBattle();
    pywebview.api.return_to_menu();
    return;
  }
  if (state.navigate === 'play_again') {
    clearAutoBattle();
    pywebview.api.play_again(state.tournament, state.difficulty || 'basic').then(() => {
      return pywebview.api.get_game_state();
    }).then(handleStateUpdate).catch(console.error);
    return;
  }

  oldState = currentState;
  currentState = state;

  // Detect animations
  detectAnimations(oldState, state);

  // Render the current phase
  render(state);

  // Auto-battle stepping
  handleAutoBattle(state);
}

// ================================================================
// AUTO-BATTLE STEPPING
// ================================================================

function clearAutoBattle() {
  if (autoBattleTimer) {
    clearTimeout(autoBattleTimer);
    autoBattleTimer = null;
  }
}

function handleAutoBattle(state) {
  clearAutoBattle();

  // In battle phase, auto-step when not manual mode or on enemy turn
  if (state.phase === 'battle') {
    if (!state.manualMode) {
      // Full auto: step at configured speed
      autoBattleTimer = setTimeout(async () => {
        try {
          const result = await pywebview.api.send_action('CONFIRM', -1, -1);
          handleStateUpdate(result);
        } catch (e) { console.error(e); }
      }, battleSpeedMs);
    } else if (!state.playerTurn) {
      // Manual mode but enemy turn: auto-step enemy
      autoBattleTimer = setTimeout(async () => {
        try {
          const result = await pywebview.api.send_action('CONFIRM', -1, -1);
          handleStateUpdate(result);
        } catch (e) { console.error(e); }
      }, battleSpeedMs);
    }
  }
}

// ================================================================
// ANIMATION DETECTION
// ================================================================

// pendingSlides: map of "toX,toY" → {fromX, fromY} for the next renderBoard call
let pendingSlides = {};

function detectAnimations(oldSt, newSt) {
  pendingSlides = {};
  if (!oldSt || !newSt) return;
  if (!oldSt.board || !newSt.board) return;

  // Phase changed — skip movement diffing (pieces reset between phases)
  if (oldSt.phase !== newSt.phase) return;

  // Build maps: type+team+mods → list of positions for old and new boards
  const oldPieces = []; // {type, team, x, y, key}
  const newPieces = [];

  for (let y = 0; y < 8; y++) {
    for (let x = 0; x < 8; x++) {
      const oc = oldSt.board[y] && oldSt.board[y][x];
      const nc = newSt.board[y] && newSt.board[y][x];
      if (oc && oc.piece) {
        const modKey = (oc.piece.modifiers || []).map(m => m.effect).sort().join(',');
        oldPieces.push({ type: oc.piece.type, team: oc.piece.team, x, y, key: oc.piece.type + '|' + oc.piece.team + '|' + modKey });
      }
      if (nc && nc.piece) {
        const modKey = (nc.piece.modifiers || []).map(m => m.effect).sort().join(',');
        newPieces.push({ type: nc.piece.type, team: nc.piece.team, x, y, key: nc.piece.type + '|' + nc.piece.team + '|' + modKey });
      }
    }
  }

  // Match pieces: for each new piece, find the closest old piece with same key
  // that isn't already at the same position
  const usedOld = new Set();

  for (const np of newPieces) {
    // Check if a piece already existed here with same key — no move
    const stayIdx = oldPieces.findIndex((op, i) => !usedOld.has(i) && op.x === np.x && op.y === np.y && op.key === np.key);
    if (stayIdx >= 0) {
      usedOld.add(stayIdx);
      continue;
    }

    // Find the closest old piece with the same key that moved
    let bestIdx = -1;
    let bestDist = Infinity;
    for (let i = 0; i < oldPieces.length; i++) {
      if (usedOld.has(i)) continue;
      const op = oldPieces[i];
      if (op.key !== np.key) continue;
      // Skip if this old piece still exists at its old position in the new state
      const stillThere = newPieces.some(p => p.x === op.x && p.y === op.y && p.key === op.key && p !== np);
      if (stillThere) continue;
      const dist = Math.abs(op.x - np.x) + Math.abs(op.y - np.y);
      if (dist < bestDist && dist > 0) {
        bestDist = dist;
        bestIdx = i;
      }
    }

    if (bestIdx >= 0) {
      usedOld.add(bestIdx);
      const op = oldPieces[bestIdx];
      pendingSlides[np.x + ',' + np.y] = { fromX: op.x, fromY: op.y };
    }
  }

  // Detect captures and HP changes
  for (let y = 0; y < 8; y++) {
    for (let x = 0; x < 8; x++) {
      const oldCell = oldSt.board[y] && oldSt.board[y][x];
      const newCell = newSt.board[y] && newSt.board[y][x];
      if (oldCell && oldCell.piece) {
        // Piece disappeared entirely
        if (!newCell || !newCell.piece) {
          spawnCaptureBurst(x, y, oldCell.piece.team === 'player' ? '#5082ff' : '#ff4646');
        }
        // Piece replaced by different team (capture at destination)
        else if (newCell.piece.team !== oldCell.piece.team) {
          spawnCaptureBurst(x, y, oldCell.piece.team === 'player' ? '#5082ff' : '#ff4646');
          triggerShake();
        }
        // Same piece still here — check HP delta
        else if (newCell.piece.type === oldCell.piece.type && newCell.piece.team === oldCell.piece.team) {
          const hpDelta = newCell.piece.hp - oldCell.piece.hp;
          if (hpDelta !== 0) {
            spawnDamagePopup(x, y, hpDelta);
          }
        }
      }
    }
  }

  // Detect gold change
  if (oldSt.gold !== undefined && newSt.gold !== undefined && oldSt.gold !== newSt.gold) {
    flashValue('stat-gold');
  }

  // Detect ELO change
  if (oldSt.elo !== undefined && newSt.elo !== undefined && oldSt.elo !== newSt.elo) {
    flashValue('elo-balance');
  }

  // Wave announcement
  if (oldSt.wave !== undefined && newSt.wave !== undefined && newSt.wave > oldSt.wave && newSt.phase === 'setup') {
    showWaveAnnouncement(newSt.wave);
  }
}

function spawnDamagePopup(boardX, boardY, delta) {
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;

  const popup = document.createElement('div');
  popup.className = 'damage-popup ' + (delta < 0 ? 'damage' : 'heal');
  popup.textContent = delta < 0 ? delta.toString() : '+' + delta;
  popup.style.left = pos.x + 'px';
  popup.style.top = pos.y + 'px';
  document.body.appendChild(popup);
  setTimeout(() => popup.remove(), 850);
}

function flashValue(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.classList.remove('value-flash');
  void el.offsetWidth;
  el.classList.add('value-flash');
  setTimeout(() => el.classList.remove('value-flash'), 450);
}

function showWaveAnnouncement(wave) {
  const existing = document.querySelector('.wave-announce');
  if (existing) existing.remove();

  const el = document.createElement('div');
  el.className = 'wave-announce';
  el.textContent = 'WAVE ' + wave;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1300);
}

function triggerShake() {
  const board = document.getElementById('board');
  if (!board) return;
  board.classList.remove('shaking');
  void board.offsetWidth; // force reflow
  board.classList.add('shaking');
  setTimeout(() => board.classList.remove('shaking'), 300);
}

// ================================================================
// PARTICLE SYSTEM
// ================================================================

function boardToScreen(boardX, boardY) {
  const boardEl = document.getElementById('board');
  if (!boardEl) return null;
  const rect = boardEl.getBoundingClientRect();
  const cellSize = rect.width / 8;
  return { x: rect.left + boardX * cellSize + cellSize / 2, y: rect.top + boardY * cellSize + cellSize / 2 };
}

function spawnCaptureBurst(boardX, boardY, color) {
  if (!particlesEnabled) return;
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;

  // 20 main burst particles
  for (let i = 0; i < 20; i++) {
    const angle = (Math.PI * 2 / 20) * i + Math.random() * 0.3;
    const speed = 80 + Math.random() * 60;
    const life = 0.6 + Math.random() * 0.3;
    particles.push({
      x: pos.x, y: pos.y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: life, maxLife: life,
      color: color,
      size: 3 + Math.random() * 3,
    });
  }
  // 4 fast sparks
  for (let i = 0; i < 4; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 150 + Math.random() * 50;
    particles.push({
      x: pos.x, y: pos.y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: 0.3, maxLife: 0.3,
      color: i % 2 === 0 ? '#ffffff' : '#ffd700',
      size: 1 + Math.random(),
    });
  }
}

function spawnVictoryBurst() {
  if (!particlesEnabled) return;
  const cx = window.innerWidth / 2;
  const cy = window.innerHeight / 2;
  for (let i = 0; i < 30; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 100 + Math.random() * 150;
    const life = 1.0 + Math.random() * 0.5;
    particles.push({
      x: cx + (Math.random() - 0.5) * 100, y: cy,
      vx: Math.cos(angle) * speed,
      vy: -Math.abs(Math.sin(angle) * speed) - 50,
      life: life, maxLife: life,
      color: i % 3 === 0 ? '#ffffff' : '#ffd700',
      size: 2 + Math.random() * 3,
      noGravity: true,
    });
  }
}

function spawnDefeatEmbers() {
  if (!particlesEnabled) return;
  const cx = window.innerWidth / 2;
  const cy = window.innerHeight / 2;
  for (let i = 0; i < 10; i++) {
    const life = 1.5 + Math.random() * 0.5;
    particles.push({
      x: cx + (Math.random() - 0.5) * 200, y: cy + (Math.random() - 0.5) * 100,
      vx: (Math.random() - 0.5) * 30,
      vy: 20 + Math.random() * 30,
      life: life, maxLife: life,
      color: '#ff4646',
      size: 2 + Math.random() * 2,
      noGravity: true,
    });
  }
}

function spawnBossRing(boardX, boardY) {
  if (!particlesEnabled) return;
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;
  for (let i = 0; i < 20; i++) {
    const angle = (Math.PI * 2 / 20) * i;
    const speed = 60 + Math.random() * 40;
    const life = 0.8 + Math.random() * 0.3;
    particles.push({
      x: pos.x, y: pos.y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: life, maxLife: life,
      color: '#ff4646',
      size: 2 + Math.random() * 2,
      noGravity: true,
    });
  }
}

let lastParticleTime = 0;
let ambientTimer = 0;

function updateParticles(time) {
  requestAnimationFrame(updateParticles);
  if (!particleCtx) return;

  const dt = lastParticleTime ? (time - lastParticleTime) / 1000 : 0.016;
  lastParticleTime = time;

  // Ambient motes — spawn 1 every 2 seconds
  if (particlesEnabled) {
    ambientTimer += dt;
    if (ambientTimer >= 2.0) {
      ambientTimer -= 2.0;
      const life = 4.0 + Math.random() * 2;
      particles.push({
        x: Math.random() * particleCtx.canvas.width,
        y: particleCtx.canvas.height + 10,
        vx: (Math.random() - 0.5) * 10,
        vy: -(15 + Math.random() * 10),
        life: life, maxLife: life,
        color: '#b48eff',
        size: 1.5 + Math.random(),
        noGravity: true,
        ambient: true,
      });
    }
  }

  particleCtx.clearRect(0, 0, particleCtx.canvas.width, particleCtx.canvas.height);
  particleCtx.globalCompositeOperation = 'lighter';

  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.life -= dt;
    if (p.life <= 0) { particles.splice(i, 1); continue; }

    // Wobble
    p.vx += (Math.random() - 0.5) * 40 * dt;

    p.x += p.vx * dt;
    p.y += p.vy * dt;
    if (!p.noGravity) p.vy += 120 * dt; // gravity

    const alpha = p.ambient ? 0.15 : Math.max(0, p.life / p.maxLife);
    particleCtx.globalAlpha = alpha;
    particleCtx.fillStyle = p.color;
    particleCtx.beginPath();
    particleCtx.arc(p.x, p.y, p.size * (p.ambient ? 1 : alpha), 0, Math.PI * 2);
    particleCtx.fill();
  }
  particleCtx.globalCompositeOperation = 'source-over';
  particleCtx.globalAlpha = 1;
}

// ================================================================
// MAIN RENDER DISPATCHER
// ================================================================

let lastRenderedPhase = null;

function render(state) {
  // Hide all phases
  document.querySelectorAll('.phase').forEach(p => p.classList.remove('active'));

  const phase = state.phase;
  const isNewPhase = (phase !== lastRenderedPhase);
  lastRenderedPhase = phase;

  // Reset build flags when leaving phases
  if (phase !== 'elo_shop') eloShopBuilt = false;
  if (phase !== 'shop') shopBuilt = false;
  if (phase !== 'draft') draftBuilt = false;

  if (phase === 'setup' || phase === 'battle') {
    document.getElementById('board-view').classList.add('active');
    renderBoardView(state);
  } else if (phase === 'result') {
    document.getElementById('result-view').classList.add('active');
    renderResult(state, isNewPhase);
  } else if (phase === 'shop') {
    document.getElementById('shop-view').classList.add('active');
    renderShop(state, isNewPhase);
  } else if (phase === 'draft') {
    document.getElementById('draft-view').classList.add('active');
    renderDraft(state, isNewPhase);
  } else if (phase === 'place_cell' || phase === 'place_border') {
    document.getElementById('placement-view').classList.add('active');
    renderPlacement(state);
  } else if (phase === 'place_piece_mod') {
    document.getElementById('piece-mod-view').classList.add('active');
    renderPieceMod(state);
  } else if (phase === 'swap_tarot') {
    document.getElementById('swap-tarot-view').classList.add('active');
    renderSwapTarot(state);
  } else if (phase === 'boss_intro') {
    document.getElementById('boss-intro-view').classList.add('active');
    renderBossIntro(state, isNewPhase);
  } else if (phase === 'tournament_end') {
    document.getElementById('tournament-end-view').classList.add('active');
    renderTournamentEnd(state);
  } else if (phase === 'game_over') {
    document.getElementById('game-over-view').classList.add('active');
    renderGameOver(state);
  } else if (phase === 'elo_shop') {
    document.getElementById('elo-shop-view').classList.add('active');
    renderEloShop(state);
  }
}

// ================================================================
// BOARD VIEW RENDERER (setup + battle)
// ================================================================

function renderBoardView(state) {
  // Top bar
  document.getElementById('stat-wave').textContent = 'Wave ' + state.wave;
  document.getElementById('stat-record').textContent = state.wins + 'W / ' + state.losses + 'L';
  document.getElementById('stat-lives').textContent = 'Lives: ' + state.lives;
  document.getElementById('stat-gold').textContent = state.gold + 'g';

  const modeText = state.tournament ? 'Tournament' : 'Free Play';
  document.getElementById('stat-mode').textContent = modeText;
  document.getElementById('stat-difficulty').textContent = state.tournament ? '(' + state.difficulty + ')' : '';

  // Board
  renderBoard('board', state);

  // Left panel — tarots, artifacts & synergies
  renderTarots(state);
  renderArtifacts(state);
  renderSynergies(state);

  // Right panel — battle log & controls
  renderBattleLog(state);
  renderControls(state);

  // Roster bar
  renderRoster(state);

  // Message bar
  document.getElementById('message-bar').textContent = state.message || '';
}

function renderBoard(boardId, state) {
  const boardEl = document.getElementById(boardId);
  if (!boardEl) return;

  const grid = state.board;
  const highlights = state.highlights || {};
  const cursor = state.cursor || [-1, -1];

  // Turn indicator glow
  boardEl.classList.remove('player-turn', 'enemy-turn');
  if (state.phase === 'battle') {
    boardEl.classList.add(state.playerTurn ? 'player-turn' : 'enemy-turn');
  }

  // Rebuild board cells
  boardEl.innerHTML = '';
  const slidingPieces = [];

  for (let y = 0; y < state.boardHeight; y++) {
    for (let x = 0; x < state.boardWidth; x++) {
      const cell = grid[y][x];
      const div = document.createElement('div');
      const isLight = (x + y) % 2 === 0;
      div.className = 'cell ' + (isLight ? 'light' : 'dark');

      // Highlights
      const hlKey = x + ',' + y;
      if (highlights[hlKey]) {
        div.classList.add('highlight-' + highlights[hlKey]);
      }

      // Cursor
      if (x === cursor[0] && y === cursor[1]) {
        div.classList.add('cursor-active');
      }

      // Blocked
      if (cell.blocked) {
        div.classList.add('blocked');
      }

      // Cell modifier overlay
      if (cell.cellMod) {
        const overlay = document.createElement('div');
        overlay.className = 'cell-mod-overlay';
        overlay.style.backgroundColor = 'rgb(' + cell.cellMod.color.join(',') + ')';
        overlay.title = cell.cellMod.name;
        div.appendChild(overlay);
      }

      // Border modifier
      if (cell.borderMod) {
        div.classList.add('has-border-mod');
        div.style.setProperty('--border-mod-color', 'rgb(' + cell.borderMod.color.join(',') + ')');
        div.title = (div.title ? div.title + ' | ' : '') + cell.borderMod.name;
      }

      // Piece
      if (cell.piece) {
        const pieceEl = document.createElement('span');
        pieceEl.className = 'piece ' + cell.piece.team;

        // Modifier glow classes
        if (cell.piece.modifiers) {
          for (const mod of cell.piece.modifiers) {
            pieceEl.classList.add('mod-' + mod.effect);
          }
        }

        pieceEl.textContent = pieceChar(cell.piece.type, cell.piece.team);

        // HP bar
        if (cell.piece.maxHp && cell.piece.maxHp > 0) {
          const hpPct = Math.max(0, Math.min(100, (cell.piece.hp / cell.piece.maxHp) * 100));
          const hpBar = document.createElement('div');
          hpBar.className = 'hp-bar';
          const hpFill = document.createElement('div');
          hpFill.className = 'hp-fill';
          if (hpPct > 60) hpFill.classList.add('hp-high');
          else if (hpPct > 30) hpFill.classList.add('hp-medium');
          else hpFill.classList.add('hp-low');
          hpFill.style.width = hpPct + '%';
          hpBar.appendChild(hpFill);
          div.appendChild(hpBar);

          // HP text
          const hpText = document.createElement('span');
          hpText.className = 'hp-text';
          hpText.textContent = cell.piece.hp;
          div.appendChild(hpText);
        }

        // Apply slide animation if this piece just moved here
        const slideKey = x + ',' + y;
        const slide = pendingSlides[slideKey];
        if (slide) {
          // Start at the old position (offset back), then transition to (0,0)
          const dx = (slide.fromX - x) * 100; // percentage of cell width
          const dy = (slide.fromY - y) * 100;
          pieceEl.style.transform = 'translate(' + dx + '%, ' + dy + '%)';
          pieceEl.classList.add('sliding');
          // Force layout, then remove transform to trigger transition
          slidingPieces.push(pieceEl);
        }

        div.appendChild(pieceEl);
      }

      // Click handlers
      div.addEventListener('mousedown', () => onBoardCellClick(boardId, x, y, 'mousedown'));
      div.addEventListener('mouseup', () => onBoardCellClick(boardId, x, y, 'mouseup'));
      div.addEventListener('mouseenter', () => {
        onBoardCellMove(boardId, x, y);
        const ttHtml = buildCellTooltip(cell);
        if (ttHtml) showTooltip(ttHtml, div);
      });
      div.addEventListener('mouseleave', hideTooltip);

      boardEl.appendChild(div);
    }
  }

  // Flush slide animations: force layout read, then clear transforms
  if (slidingPieces.length > 0) {
    // Force browser to compute the initial transform position
    void boardEl.offsetHeight;
    requestAnimationFrame(() => {
      for (const el of slidingPieces) {
        el.style.transform = 'translate(0, 0)';
      }
      // Clean up after transition finishes
      setTimeout(() => {
        for (const el of slidingPieces) {
          el.style.transform = '';
          el.classList.remove('sliding');
        }
      }, 220); // slightly longer than the 200ms transition
    });
  }

  // Clear pending slides after rendering
  pendingSlides = {};
}

function renderTarots(state) {
  const container = document.getElementById('tarot-items');
  if (!container) return;
  container.innerHTML = '';

  if (!state.tarotCards || state.tarotCards.length === 0) {
    container.innerHTML = '<span style="color:#555;font-size:0.65rem">None</span>';
    return;
  }

  for (const t of state.tarotCards) {
    const badge = document.createElement('div');
    badge.className = 'item-badge';
    badge.style.borderLeft = '3px solid rgb(' + (t.color || [180,142,255]).join(',') + ')';
    badge.innerHTML = '<span class="item-icon">' + (t.icon || '\u2605') + '</span>'
                    + '<span class="item-name">' + esc(t.name) + '</span>';
    if (t.description) {
      attachTooltip(badge, '<div class="tt-title">' + esc(t.name) + '</div><div class="tt-desc">' + esc(t.description) + '</div>');
    }
    container.appendChild(badge);
  }
}

function renderArtifacts(state) {
  const container = document.getElementById('artifact-items');
  if (!container) return;
  container.innerHTML = '';

  if (!state.artifacts || state.artifacts.length === 0) {
    container.innerHTML = '<span style="color:#555;font-size:0.65rem">None</span>';
    return;
  }

  for (const a of state.artifacts) {
    const badge = document.createElement('div');
    badge.className = 'item-badge';
    badge.style.borderLeft = '3px solid rgb(' + (a.color || [200,200,200]).join(',') + ')';
    badge.innerHTML = '<span class="item-icon">' + (a.icon || '\u2726') + '</span>'
                    + '<span class="item-name">' + esc(a.name) + '</span>';
    if (a.description) {
      attachTooltip(badge, '<div class="tt-title">' + esc(a.name) + '</div><div class="tt-desc">' + esc(a.description) + '</div>');
    }
    container.appendChild(badge);
  }
}

function renderSynergies(state) {
  const container = document.getElementById('synergy-items');
  if (!container) return;
  container.innerHTML = '';

  if (!state.activeSynergies || state.activeSynergies.length === 0) {
    container.innerHTML = '<span style="color:#555;font-size:0.65rem">None</span>';
    return;
  }

  for (const s of state.activeSynergies) {
    const badge = document.createElement('div');
    badge.className = 'synergy-badge';
    if (s.color) badge.style.borderLeft = '3px solid rgb(' + s.color.join(',') + ')';
    badge.innerHTML = '<span class="item-icon">' + (s.icon || '\u2726') + '</span>'
                    + '<span class="item-name">' + esc(s.name) + '</span>';
    if (s.description) {
      attachTooltip(badge, '<div class="tt-title">' + esc(s.name) + '</div><div class="tt-desc">' + esc(s.description) + '</div>');
    }
    container.appendChild(badge);
  }
}

function renderBattleLog(state) {
  const log = document.getElementById('battle-log');
  if (!log) return;
  log.innerHTML = '';

  const entries = state.battleLog || [];
  for (const entry of entries) {
    const div = document.createElement('div');
    div.className = 'log-entry';
    if (entry.includes('captures')) div.classList.add('capture');
    if (entry.includes('VICTORY')) div.classList.add('victory');
    if (entry.includes('DEFEAT')) div.classList.add('defeat');
    div.textContent = entry;
    log.appendChild(div);
  }
  log.scrollTop = log.scrollHeight;
}

function renderControls(state) {
  const el = document.getElementById('controls-text');
  if (!el) return;

  let lines = [];
  if (state.phase === 'setup') {
    lines = [
      'Arrows: Move cursor',
      'Enter: Place/pick up piece',
      '1-9: Select roster piece',
      'Space: Start battle',
      'Esc: Return to menu',
    ];
  } else if (state.phase === 'battle') {
    if (state.manualMode && state.playerTurn) {
      lines = [
        'Click piece to select',
        'Click destination to move',
        'Tab: Toggle auto mode',
        'Esc: Skip to end',
      ];
    } else {
      lines = [
        'Auto-battling...',
        'Tab: Toggle manual mode',
        'Esc: Skip to end',
      ];
    }
  }
  el.innerHTML = lines.map(l => esc(l)).join('<br>');
}

function renderRoster(state) {
  const container = document.getElementById('roster-items');
  if (!container) return;
  container.innerHTML = '';

  if (!state.roster) return;

  for (let i = 0; i < state.roster.length; i++) {
    const r = state.roster[i];
    const div = document.createElement('div');
    div.className = 'roster-piece';
    if (r.placed) div.classList.add('placed');
    if (i === state.rosterSelection && !r.placed) div.classList.add('selected');

    const icon = document.createElement('span');
    icon.className = 'piece-icon player-color';
    icon.textContent = pieceChar(r.type, 'player');
    div.appendChild(icon);

    const label = document.createElement('span');
    label.className = 'piece-label';
    let labelText = r.type;
    if (r.modifiers && r.modifiers.length > 0) {
      labelText += ' [' + r.modifiers.map(m => m.effect[0].toUpperCase()).join('') + ']';
    }
    if (r.hp != null && r.maxHp != null) {
      labelText += ' ' + r.hp + '/' + r.maxHp;
    }
    label.textContent = labelText;
    div.appendChild(label);

    // Click to select
    div.addEventListener('click', () => {
      if (!r.placed) {
        pywebview.api.send_action('NUM_' + (i + 1), -1, -1).then(handleStateUpdate).catch(console.error);
      }
    });

    // Tooltip
    let rosterTt = '<div class="tt-title">' + esc(r.type) + '</div>';
    if (r.hp != null && r.maxHp != null) {
      rosterTt += '<div class="tt-desc">HP: ' + r.hp + '/' + r.maxHp + ' | ATK: ' + (r.attack || 0) + '</div>';
    }
    if (r.modifiers && r.modifiers.length > 0) {
      for (const m of r.modifiers) {
        rosterTt += '<div class="tt-mod">' + esc(m.name);
        if (m.description) rosterTt += ': ' + esc(m.description);
        rosterTt += '</div>';
      }
    }
    attachTooltip(div, rosterTt);

    container.appendChild(div);
  }
}

// ================================================================
// RESULT RENDERER
// ================================================================

function renderResult(state, animate) {
  const title = document.getElementById('result-title');
  const body = document.getElementById('result-body');

  const won = state.wins > (oldState ? oldState.wins : 0);
  const lost = state.losses > (oldState ? oldState.losses : 0);
  title.textContent = won ? 'Victory!' : (lost ? 'Defeat' : 'Draw');
  title.style.color = won ? '#66ff88' : '#ff6666';

  let html = '<div style="margin: 12px 0;">';
  html += '<div>Wave ' + state.wave + ' complete</div>';
  html += '<div>Record: ' + state.wins + 'W / ' + state.losses + 'L</div>';
  html += '<div style="color:#ffd700;">Gold: ' + state.gold + 'g</div>';
  html += '</div>';

  body.innerHTML = html;

  const overlayCard = document.querySelector('#result-view .overlay-card');
  if (overlayCard) {
    overlayCard.classList.remove('victory', 'defeat');
    if (won) {
      overlayCard.classList.add('victory');
      if (animate) spawnVictoryBurst();
    } else if (lost) {
      overlayCard.classList.add('defeat');
      if (animate) spawnDefeatEmbers();
    }

    overlayCard.onclick = () => {
      pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
    };
  }
}

// ================================================================
// SHOP RENDERER
// ================================================================

let shopBuilt = false;

function renderShop(state, animate) {
  document.getElementById('shop-gold').textContent = state.gold + 'g';

  const container = document.getElementById('shop-rows');
  const rows = state.shopRows || [];

  // Build DOM only on first render; update classes on subsequent renders
  if (!shopBuilt || animate) {
    shopBuilt = true;
    container.innerHTML = '';

    for (let ri = 0; ri < rows.length; ri++) {
      const row = rows[ri];
      const rowDiv = document.createElement('div');

      const label = document.createElement('div');
      label.className = 'shop-row-label';
      label.style.color = 'rgb(' + row.color.join(',') + ')';
      label.textContent = row.label;
      rowDiv.appendChild(label);

      const itemsDiv = document.createElement('div');
      itemsDiv.className = 'shop-row-items';

      for (let ci = 0; ci < row.items.length; ci++) {
        const item = row.items[ci];
        const card = document.createElement('div');
        card.className = 'shop-card' + (animate ? ' card-enter' : '');
        if (animate) card.style.animationDelay = ((ri * row.items.length + ci) * 50) + 'ms';
        card.dataset.shopRi = ri;
        card.dataset.shopCi = ci;

        card.innerHTML =
          '<span class="shop-card-icon" style="color:rgb(' + item.color.join(',') + ')">' + esc(item.icon) + '</span>' +
          '<span class="shop-card-name">' + esc(item.name) + '</span>' +
          '<span class="shop-card-desc">' + esc(item.description) + '</span>' +
          '<span class="shop-card-cost">' + item.cost + 'g</span>';

        // Tooltip
        if (item.description) {
          attachTooltip(card, '<div class="tt-title">' + esc(item.name) + '</div><div class="tt-desc">' + esc(item.description) + '</div><div class="tt-mod">' + item.cost + 'g</div>');
        }

        // Hover selects, click confirms
        const capturedRi = ri;
        const capturedCi = ci;
        card.addEventListener('mouseenter', () => {
          pywebview.api.set_selection(capturedRi, capturedCi).then(handleStateUpdate).catch(console.error);
        });
        card.addEventListener('click', () => {
          pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
        });

        itemsDiv.appendChild(card);
      }

      rowDiv.appendChild(itemsDiv);
      container.appendChild(rowDiv);
    }
  }

  // Update selection/affordability classes without rebuilding DOM
  const cards = container.querySelectorAll('.shop-card');
  cards.forEach((card) => {
    const ri = parseInt(card.dataset.shopRi);
    const ci = parseInt(card.dataset.shopCi);
    const row = rows[ri];
    if (!row) return;
    const item = row.items[ci];
    if (!item) return;
    card.classList.toggle('selected', ri === state.shopRow && ci === state.shopCol);
    card.classList.toggle('unaffordable', state.gold < item.cost);
  });

  // Done button
  const doneBtn = document.getElementById('shop-done-btn');
  doneBtn.className = 'action-btn';
  if (state.shopRow >= rows.length) doneBtn.classList.add('selected');
  doneBtn.onmouseenter = () => {
    pywebview.api.set_selection(rows.length, 0).then(handleStateUpdate).catch(console.error);
  };
  doneBtn.onclick = () => {
    pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
  };

  document.getElementById('shop-message').textContent = state.message || '';
}

// ================================================================
// DRAFT RENDERER
// ================================================================

let draftBuilt = false;

function renderDraft(state, animate) {
  const container = document.getElementById('draft-cards');
  const options = state.draftOptions || [];

  if (!draftBuilt || animate) {
    draftBuilt = true;
    container.innerHTML = '';

    for (let i = 0; i < options.length; i++) {
      const opt = options[i];
      if (opt.type === 'skip') continue; // handled by skip button

      const card = document.createElement('div');
      card.className = 'draft-card' + (animate ? ' card-enter' : '');
      if (animate) card.style.animationDelay = (i * 50) + 'ms';
      card.dataset.draftIdx = i;

      let icon = '\u2659'; // default pawn
      if (opt.pieceType) icon = pieceChar(opt.pieceType, 'player');
      else if (opt.type === 'combine') icon = pieceChar(opt.to, 'player');

      card.innerHTML =
        '<span class="draft-card-icon player-color">' + icon + '</span>' +
        '<span class="draft-card-desc">' + esc(opt.desc) + '</span>';

      // Tooltip
      if (opt.desc) {
        attachTooltip(card, '<div class="tt-title">' + esc(opt.type) + '</div><div class="tt-desc">' + esc(opt.desc) + '</div>');
      }

      const idx = i;
      card.addEventListener('mouseenter', () => {
        pywebview.api.set_selection(idx).then(handleStateUpdate).catch(console.error);
      });
      card.addEventListener('click', () => {
        pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
      });

      container.appendChild(card);
    }
  }

  // Update selection classes without rebuilding
  const cards = container.querySelectorAll('.draft-card');
  cards.forEach((card) => {
    const i = parseInt(card.dataset.draftIdx);
    card.classList.toggle('selected', i === state.draftSelection);
  });

  // Skip button
  const skipBtn = document.getElementById('draft-skip-btn');
  skipBtn.className = 'action-btn';
  const skipIdx = options.findIndex(o => o.type === 'skip');
  if (skipIdx >= 0 && skipIdx === state.draftSelection) skipBtn.classList.add('selected');
  skipBtn.onclick = () => {
    pywebview.api.send_action('CANCEL', -1, -1).then(handleStateUpdate).catch(console.error);
  };

  document.getElementById('draft-message').textContent = state.message || '';
}

// ================================================================
// PLACEMENT RENDERER (place_cell, place_border)
// ================================================================

function renderPlacement(state) {
  renderBoard('placement-board', state);
  const msg = document.getElementById('placement-message');
  msg.textContent = state.message || '';

  const hint = document.getElementById('placement-hint');
  if (state.phase === 'place_cell') {
    hint.textContent = 'Place cell modifier: Arrows + ENTER, ESC to cancel';
  } else {
    hint.textContent = 'Place border modifier: Arrows + ENTER, ESC to cancel';
  }
}

// ================================================================
// PIECE MOD RENDERER (roster selection)
// ================================================================

function renderPieceMod(state) {
  const nameEl = document.getElementById('piece-mod-name');
  if (state.placingItem) {
    nameEl.textContent = 'Applying: ' + state.placingItem.name;
  }

  const container = document.getElementById('piece-mod-roster');
  container.innerHTML = '';

  // Show eligible roster pieces
  const roster = state.roster || [];
  for (let i = 0; i < roster.length; i++) {
    const r = roster[i];
    // In the actual game, eligibility is checked server-side
    const card = document.createElement('div');
    card.className = 'roster-select-card';
    if (i === state.rosterSelection) card.classList.add('selected');

    card.innerHTML =
      '<span class="piece-icon player-color">' + pieceChar(r.type, 'player') + '</span>' +
      '<span class="piece-name">' + esc(r.type) +
      (r.modifiers.length > 0 ? ' [' + r.modifiers.map(m => m.effect[0]).join('') + ']' : '') +
      '</span>';

    // Tooltip
    let pmTt = '<div class="tt-title">' + esc(r.type) + '</div>';
    if (r.modifiers && r.modifiers.length > 0) {
      for (const m of r.modifiers) {
        pmTt += '<div class="tt-mod">' + esc(m.name);
        if (m.description) pmTt += ': ' + esc(m.description);
        pmTt += '</div>';
      }
    }
    attachTooltip(card, pmTt);

    const pmIdx = i;
    card.addEventListener('mouseenter', () => {
      pywebview.api.set_selection(pmIdx).then(handleStateUpdate).catch(console.error);
    });
    card.addEventListener('click', () => {
      pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
    });

    container.appendChild(card);
  }
}

// ================================================================
// SWAP TAROT RENDERER
// ================================================================

function renderSwapTarot(state) {
  const newEl = document.getElementById('swap-tarot-new');
  if (state.placingItem) {
    newEl.textContent = 'New: ' + state.placingItem.name;
  }

  const container = document.getElementById('swap-tarot-cards');
  container.innerHTML = '';

  const tarots = state.tarotCards || [];
  for (let i = 0; i < tarots.length; i++) {
    const t = tarots[i];
    const card = document.createElement('div');
    card.className = 'tarot-select-card';
    if (i === state.rosterSelection) card.classList.add('selected');

    card.innerHTML =
      '<span class="tarot-icon" style="color:rgb(' + (t.color || [180,142,255]).join(',') + ')">' +
      (t.icon || '\u2605') + '</span>' +
      '<span class="tarot-name">' + esc(t.name) + '</span>';

    // Tooltip
    if (t.description) {
      attachTooltip(card, '<div class="tt-title">' + esc(t.name) + '</div><div class="tt-desc">' + esc(t.description) + '</div>');
    }

    const stIdx = i;
    card.addEventListener('mouseenter', () => {
      pywebview.api.set_selection(stIdx).then(handleStateUpdate).catch(console.error);
    });
    card.addEventListener('click', () => {
      pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
    });

    container.appendChild(card);
  }
}

// ================================================================
// BOSS INTRO RENDERER
// ================================================================

function renderBossIntro(state, animate) {
  const icon = document.getElementById('boss-icon');
  icon.textContent = pieceChar(state.bossType || 'king', 'enemy');

  const title = document.getElementById('boss-title');
  title.textContent = 'Boss: ' + (state.bossType || 'Unknown').toUpperCase();

  const mods = document.getElementById('boss-mods');
  const modList = state.bossMods || [];
  mods.innerHTML = modList.length > 0
    ? '<div style="color:#ff8866;font-size:0.85rem">Modifiers: ' + modList.join(', ') + '</div>'
    : '';

  if (animate) {
    // Boss intro screen shake
    triggerShake();

    // Boss ring particles from center of screen
    if (particlesEnabled) {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      for (let i = 0; i < 20; i++) {
        const angle = (Math.PI * 2 / 20) * i;
        const speed = 60 + Math.random() * 40;
        const life = 0.8 + Math.random() * 0.3;
        particles.push({
          x: cx, y: cy,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          life: life, maxLife: life,
          color: '#ff4646',
          size: 2 + Math.random() * 2,
          noGravity: true,
        });
      }
    }
  }

  const overlayCard = document.querySelector('#boss-intro-view .overlay-card');
  if (overlayCard) {
    overlayCard.onclick = () => {
      pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
    };
  }
}

// ================================================================
// TOURNAMENT END RENDERER
// ================================================================

function renderTournamentEnd(state) {
  const title = document.getElementById('tournament-result-title');
  title.textContent = state.tournamentWon ? 'Tournament Won!' : 'Tournament Over';
  title.style.color = state.tournamentWon ? '#66ff88' : '#ff6666';

  const stats = document.getElementById('tournament-stats');
  const ts = state.tournamentStats || {};
  stats.innerHTML =
    '<div class="stat-line"><span class="label">Bosses beaten</span><span class="value">' + (ts.bosses_beaten || 0) + '</span></div>' +
    '<div class="stat-line"><span class="label">Pieces survived</span><span class="value">' + (ts.pieces_survived || 0) + '</span></div>' +
    '<div class="stat-line"><span class="label">Gold earned</span><span class="value">' + (ts.gold_earned || 0) + '</span></div>';

  document.getElementById('tournament-elo').textContent = '+' + (state.eloEarned || 0) + ' ELO';

  const overlayCard = document.querySelector('#tournament-end-view .overlay-card');
  if (overlayCard) {
    overlayCard.onclick = () => {
      pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
    };
  }
}

// ================================================================
// GAME OVER RENDERER
// ================================================================

function renderGameOver(state) {
  const stats = document.getElementById('game-over-stats');
  stats.innerHTML =
    '<div style="margin: 12px 0;">' +
    '<div>Waves completed: ' + state.wave + '</div>' +
    '<div>Record: ' + state.wins + 'W / ' + state.losses + 'L</div>' +
    '<div style="color:#ffd700;">Gold earned: ' + state.gold + 'g</div>' +
    '</div>';

  const overlayCard = document.querySelector('#game-over-view .overlay-card');
  if (overlayCard) {
    overlayCard.onclick = () => {
      pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
    };
  }
}

// ================================================================
// ELO SHOP RENDERER
// ================================================================

let eloShopBuilt = false;

function renderEloShop(state) {
  document.getElementById('elo-balance').textContent = '\u25C6 ' + state.elo + ' ELO';

  const container = document.getElementById('elo-shop-cards');
  const items = state.items || [];
  const isFirstRender = !eloShopBuilt;

  // Only rebuild DOM on first render; otherwise just update classes
  if (isFirstRender) {
    eloShopBuilt = true;
    container.innerHTML = '';

    let lastCategory = '';
    for (let i = 0; i < items.length; i++) {
      const item = items[i];

      // Insert category header when category changes
      if (item.category !== lastCategory) {
        const header = document.createElement('div');
        header.className = 'elo-category-header';
        header.textContent = item.category === 'Piece' ? 'Pieces' : item.category === 'Modifier' ? 'Modifiers' : 'Upgrades';
        container.appendChild(header);
        lastCategory = item.category;
      }

      const card = document.createElement('div');
      card.className = 'elo-card card-enter';
      card.style.animationDelay = (i * 30) + 'ms';
      card.dataset.eloIdx = i;

      let descText = item.desc;
      if (item.category === 'Upgrade' && item.level > 0) {
        descText += ' (Lv.' + item.level + ')';
      }

      card.innerHTML =
        '<span class="elo-card-icon" style="color:rgb(' + item.color.join(',') + ')">' + esc(item.icon) + '</span>' +
        '<span class="elo-card-name">' + esc(item.name) + '</span>' +
        '<span class="elo-card-desc">' + esc(descText) + '</span>' +
        (item.owned
          ? '<span class="elo-card-owned">OWNED</span>'
          : '<span class="elo-card-cost">' + item.cost + ' ELO</span>');

      // Tooltip
      attachTooltip(card, '<div class="tt-title">' + esc(item.name) + '</div><div class="tt-desc">' + esc(descText) + '</div>' + (item.owned ? '' : '<div class="tt-mod">' + item.cost + ' ELO</div>'));

      // Click to select (not buy)
      const eloIdx = i;
      card.addEventListener('click', () => {
        pywebview.api.set_selection(eloIdx).then(handleStateUpdate).catch(console.error);
      });

      container.appendChild(card);
    }
  }

  // Update selection/state classes on all cards (fast DOM update)
  const cards = container.querySelectorAll('.elo-card');
  cards.forEach((card) => {
    const i = parseInt(card.dataset.eloIdx);
    const item = items[i];
    if (!item) return;

    card.classList.toggle('selected', i === state.selection);
    card.classList.toggle('owned', item.owned);
    card.classList.toggle('unaffordable', !item.owned && !item.affordable);

    // Update cost text for upgrades that may have changed
    const costEl = card.querySelector('.elo-card-cost');
    if (costEl) costEl.textContent = item.cost + ' ELO';
  });

  // Update purchase button
  const purchaseBtn = document.getElementById('elo-purchase-btn');
  const selectedItem = items[state.selection];
  if (purchaseBtn && selectedItem) {
    purchaseBtn.classList.remove('owned', 'unaffordable');
    if (selectedItem.owned) {
      purchaseBtn.textContent = selectedItem.name + ' — Owned';
      purchaseBtn.classList.add('owned');
    } else if (!selectedItem.affordable) {
      purchaseBtn.textContent = 'Purchase ' + selectedItem.name + ' (' + selectedItem.cost + ' ELO)';
      purchaseBtn.classList.add('unaffordable');
    } else {
      purchaseBtn.textContent = 'Purchase ' + selectedItem.name + ' (' + selectedItem.cost + ' ELO)';
    }
    purchaseBtn.onclick = () => {
      pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
    };
  }

  document.getElementById('elo-shop-message').textContent = state.message || '';
}

// ================================================================
// TOOLTIP SYSTEM
// ================================================================

function showTooltip(html, anchorEl) {
  const tt = document.getElementById('tooltip');
  tt.innerHTML = html;
  const rect = anchorEl.getBoundingClientRect();
  let left = rect.right + 8;
  let top = rect.top;
  if (left + 260 > window.innerWidth) left = rect.left - 268;
  if (top + 200 > window.innerHeight) top = window.innerHeight - 200;
  tt.style.left = left + 'px';
  tt.style.top = Math.max(4, top) + 'px';
  tt.classList.add('visible');
}

function hideTooltip() {
  document.getElementById('tooltip').classList.remove('visible');
}

function buildPieceTooltip(piece) {
  let html = '<div class="tt-title">' + esc(piece.type) + '</div>';
  html += '<div class="tt-team ' + piece.team + '">' + esc(piece.team) + '</div>';
  if (piece.hp != null && piece.maxHp != null) {
    html += '<div class="tt-desc">HP: ' + piece.hp + '/' + piece.maxHp + ' | ATK: ' + (piece.attack || 0) + '</div>';
  }
  if (piece.modifiers && piece.modifiers.length > 0) {
    for (const m of piece.modifiers) {
      html += '<div class="tt-mod">' + esc(m.name);
      if (m.description) html += ': ' + esc(m.description);
      html += '</div>';
    }
  }
  return html;
}

function buildCellTooltip(cell) {
  let html = '';
  if (cell.piece) {
    html += buildPieceTooltip(cell.piece);
  }
  if (cell.cellMod) {
    if (html) html += '<hr style="border-color:rgba(180,142,255,0.2);margin:6px 0">';
    html += '<div class="tt-title">' + esc(cell.cellMod.name) + '</div>';
    if (cell.cellMod.description) html += '<div class="tt-desc">' + esc(cell.cellMod.description) + '</div>';
  }
  if (cell.borderMod) {
    if (html) html += '<hr style="border-color:rgba(180,142,255,0.2);margin:6px 0">';
    html += '<div class="tt-title">' + esc(cell.borderMod.name) + '</div>';
    if (cell.borderMod.description) html += '<div class="tt-desc">' + esc(cell.borderMod.description) + '</div>';
  }
  return html;
}

function attachTooltip(el, htmlContent) {
  el.addEventListener('mouseenter', () => {
    if (htmlContent) showTooltip(htmlContent, el);
  });
  el.addEventListener('mouseleave', hideTooltip);
}

// ================================================================
// UTILITY
// ================================================================

function esc(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ================================================================
// OPTIONS & CHESSTICON OVERLAY
// ================================================================

function openOptionsOverlay() {
  clearAutoBattle();
  optionsOpen = true;
  const overlay = document.getElementById('options-overlay');
  overlay.className = 'overlay-visible';
  updateSpeedDisplay();
  updateParticlesToggle();
  // Show Cash Out button only during tournament games
  const cashoutBtn = document.getElementById('opt-cashout');
  if (cashoutBtn) {
    cashoutBtn.style.display = (currentState && currentState.tournament) ? '' : 'none';
  }
}

function closeOptionsOverlay() {
  optionsOpen = false;
  document.getElementById('options-overlay').className = 'overlay-hidden';
  // Resume auto-battle if in battle phase
  if (currentState) handleAutoBattle(currentState);
}

function openChesticonOverlay() {
  chessiconOpen = true;
  document.getElementById('options-overlay').className = 'overlay-hidden';
  document.getElementById('chessticon-overlay').className = 'overlay-visible';
  // Load data and render first tab
  loadCodexData().then(() => {
    renderChesticonTab('chessticon-content', 'pieces');
    // Mark first tab active
    document.querySelectorAll('#chessticon-overlay .chessticon-tab').forEach(t => t.classList.remove('active'));
    const first = document.querySelector('#chessticon-overlay .chessticon-tab[data-tab="pieces"]');
    if (first) first.classList.add('active');
  });
}

function closeChesticonOverlay() {
  chessiconOpen = false;
  document.getElementById('chessticon-overlay').className = 'overlay-hidden';
  // Return to options
  openOptionsOverlay();
}

function updateSpeedDisplay() {
  const el = document.getElementById('speed-value');
  if (el) el.textContent = battleSpeedMs + 'ms';
}

function updateParticlesToggle() {
  const btn = document.getElementById('particles-toggle');
  if (!btn) return;
  btn.textContent = particlesEnabled ? 'ON' : 'OFF';
  btn.className = 'toggle-btn' + (particlesEnabled ? '' : ' off');
}

function setupOverlayControls() {
  // Speed controls
  const speedDown = document.getElementById('speed-down');
  const speedUp = document.getElementById('speed-up');
  if (speedDown) {
    speedDown.addEventListener('click', () => {
      const idx = SPEED_STEPS.indexOf(battleSpeedMs);
      if (idx > 0) {
        battleSpeedMs = SPEED_STEPS[idx - 1];
      } else if (idx === -1) {
        // Find nearest lower
        for (let i = SPEED_STEPS.length - 1; i >= 0; i--) {
          if (SPEED_STEPS[i] < battleSpeedMs) { battleSpeedMs = SPEED_STEPS[i]; break; }
        }
      }
      updateSpeedDisplay();
      pywebview.api.update_settings({ battle_speed: battleSpeedMs });
    });
  }
  if (speedUp) {
    speedUp.addEventListener('click', () => {
      const idx = SPEED_STEPS.indexOf(battleSpeedMs);
      if (idx >= 0 && idx < SPEED_STEPS.length - 1) {
        battleSpeedMs = SPEED_STEPS[idx + 1];
      } else if (idx === -1) {
        for (let i = 0; i < SPEED_STEPS.length; i++) {
          if (SPEED_STEPS[i] > battleSpeedMs) { battleSpeedMs = SPEED_STEPS[i]; break; }
        }
      }
      updateSpeedDisplay();
      pywebview.api.update_settings({ battle_speed: battleSpeedMs });
    });
  }

  // Particles toggle
  const particlesBtn = document.getElementById('particles-toggle');
  if (particlesBtn) {
    particlesBtn.addEventListener('click', () => {
      particlesEnabled = !particlesEnabled;
      updateParticlesToggle();
      pywebview.api.update_settings({ particles_enabled: particlesEnabled });
    });
  }

  // Chessticon button
  const chesticonBtn = document.getElementById('opt-chessticon');
  if (chesticonBtn) {
    chesticonBtn.addEventListener('click', () => {
      openChesticonOverlay();
    });
  }

  // Resume button
  const resumeBtn = document.getElementById('opt-resume');
  if (resumeBtn) {
    resumeBtn.addEventListener('click', () => {
      closeOptionsOverlay();
    });
  }

  // Quit button
  const quitBtn = document.getElementById('opt-quit');
  if (quitBtn) {
    quitBtn.addEventListener('click', () => {
      closeOptionsOverlay();
      clearAutoBattle();
      pywebview.api.return_to_menu();
    });
  }

  // Chessticon tabs
  document.querySelectorAll('#chessticon-overlay .chessticon-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('#chessticon-overlay .chessticon-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      renderChesticonTab('chessticon-content', tab.dataset.tab);
    });
  });

  // Cash Out button
  const cashoutBtn = document.getElementById('opt-cashout');
  if (cashoutBtn) {
    cashoutBtn.addEventListener('click', () => {
      closeOptionsOverlay();
      clearAutoBattle();
      pywebview.api.cash_out().then(handleStateUpdate).catch(console.error);
    });
  }

  // Codex back button
  const codexBack = document.getElementById('codex-back');
  if (codexBack) {
    codexBack.addEventListener('click', () => {
      closeChesticonOverlay();
    });
  }
}
