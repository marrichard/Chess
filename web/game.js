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
      // Full auto: step every 400ms
      autoBattleTimer = setTimeout(async () => {
        try {
          const result = await pywebview.api.send_action('CONFIRM', -1, -1);
          handleStateUpdate(result);
        } catch (e) { console.error(e); }
      }, 400);
    } else if (!state.playerTurn) {
      // Manual mode but enemy turn: auto-step enemy
      autoBattleTimer = setTimeout(async () => {
        try {
          const result = await pywebview.api.send_action('CONFIRM', -1, -1);
          handleStateUpdate(result);
        } catch (e) { console.error(e); }
      }, 400);
    }
  }
}

// ================================================================
// ANIMATION DETECTION
// ================================================================

function detectAnimations(oldSt, newSt) {
  if (!oldSt || !newSt) return;
  if (!oldSt.board || !newSt.board) return;

  // Detect captures (piece in old state gone in new state at same position)
  for (let y = 0; y < 8; y++) {
    for (let x = 0; x < 8; x++) {
      const oldCell = oldSt.board[y] && oldSt.board[y][x];
      const newCell = newSt.board[y] && newSt.board[y][x];
      if (oldCell && oldCell.piece && (!newCell || !newCell.piece)) {
        // Piece was captured here — spawn particle burst
        spawnCaptureBurst(x, y, oldCell.piece.team === 'player' ? '#5082ff' : '#ff4646');
      }
    }
  }

  // Detect captures at destination (new piece is different team from old piece)
  for (let y = 0; y < 8; y++) {
    for (let x = 0; x < 8; x++) {
      const oldCell = oldSt.board[y] && oldSt.board[y][x];
      const newCell = newSt.board[y] && newSt.board[y][x];
      if (oldCell && newCell && oldCell.piece && newCell.piece
          && oldCell.piece.team !== newCell.piece.team) {
        spawnCaptureBurst(x, y, oldCell.piece.team === 'player' ? '#5082ff' : '#ff4646');
        triggerShake();
      }
    }
  }

  // Detect phase change
  if (oldSt.phase !== newSt.phase) {
    // Phase transitions are handled by CSS opacity
  }
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

function spawnCaptureBurst(boardX, boardY, color) {
  // Convert board coords to screen coords
  const boardEl = document.getElementById('board');
  if (!boardEl) return;
  const rect = boardEl.getBoundingClientRect();
  const cellSize = rect.width / 8;
  const cx = rect.left + boardX * cellSize + cellSize / 2;
  const cy = rect.top + boardY * cellSize + cellSize / 2;

  for (let i = 0; i < 12; i++) {
    const angle = (Math.PI * 2 / 12) * i + Math.random() * 0.3;
    const speed = 80 + Math.random() * 60;
    particles.push({
      x: cx, y: cy,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: 0.6 + Math.random() * 0.3,
      maxLife: 0.6 + Math.random() * 0.3,
      color: color,
      size: 3 + Math.random() * 3,
    });
  }
}

let lastParticleTime = 0;
function updateParticles(time) {
  requestAnimationFrame(updateParticles);
  if (!particleCtx) return;

  const dt = lastParticleTime ? (time - lastParticleTime) / 1000 : 0.016;
  lastParticleTime = time;

  particleCtx.clearRect(0, 0, particleCtx.canvas.width, particleCtx.canvas.height);

  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.life -= dt;
    if (p.life <= 0) { particles.splice(i, 1); continue; }

    p.x += p.vx * dt;
    p.y += p.vy * dt;
    p.vy += 120 * dt; // gravity

    const alpha = Math.max(0, p.life / p.maxLife);
    particleCtx.globalAlpha = alpha;
    particleCtx.fillStyle = p.color;
    particleCtx.beginPath();
    particleCtx.arc(p.x, p.y, p.size * alpha, 0, Math.PI * 2);
    particleCtx.fill();
  }
  particleCtx.globalAlpha = 1;
}

// ================================================================
// MAIN RENDER DISPATCHER
// ================================================================

function render(state) {
  // Hide all phases
  document.querySelectorAll('.phase').forEach(p => p.classList.remove('active'));

  const phase = state.phase;

  if (phase === 'setup' || phase === 'battle') {
    document.getElementById('board-view').classList.add('active');
    renderBoardView(state);
  } else if (phase === 'result') {
    document.getElementById('result-view').classList.add('active');
    renderResult(state);
  } else if (phase === 'shop') {
    document.getElementById('shop-view').classList.add('active');
    renderShop(state);
  } else if (phase === 'draft') {
    document.getElementById('draft-view').classList.add('active');
    renderDraft(state);
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
    renderBossIntro(state);
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

  // Left panel — tarots & artifacts
  renderTarots(state);
  renderArtifacts(state);

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

  // Rebuild board cells
  boardEl.innerHTML = '';

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
        div.appendChild(pieceEl);
      }

      // Click handlers
      div.addEventListener('mousedown', () => onBoardCellClick(boardId, x, y, 'mousedown'));
      div.addEventListener('mouseup', () => onBoardCellClick(boardId, x, y, 'mouseup'));
      div.addEventListener('mouseenter', () => onBoardCellMove(boardId, x, y));

      boardEl.appendChild(div);
    }
  }
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
    badge.title = t.description || '';
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
    badge.title = a.description || '';
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
    label.textContent = labelText;
    div.appendChild(label);

    // Click to select
    div.addEventListener('click', () => {
      if (!r.placed) {
        pywebview.api.send_action('NUM_' + (i + 1), -1, -1).then(handleStateUpdate).catch(console.error);
      }
    });

    container.appendChild(div);
  }
}

// ================================================================
// RESULT RENDERER
// ================================================================

function renderResult(state) {
  const title = document.getElementById('result-title');
  const body = document.getElementById('result-body');

  const won = state.wins > (oldState ? oldState.wins : 0);
  title.textContent = won ? 'Victory!' : (state.losses > (oldState ? oldState.losses : 0) ? 'Defeat' : 'Draw');
  title.style.color = won ? '#66ff88' : '#ff6666';

  let html = '<div style="margin: 12px 0;">';
  html += '<div>Wave ' + state.wave + ' complete</div>';
  html += '<div>Record: ' + state.wins + 'W / ' + state.losses + 'L</div>';
  html += '<div style="color:#ffd700;">Gold: ' + state.gold + 'g</div>';
  html += '</div>';

  body.innerHTML = html;
}

// ================================================================
// SHOP RENDERER
// ================================================================

function renderShop(state) {
  document.getElementById('shop-gold').textContent = state.gold + 'g';

  const container = document.getElementById('shop-rows');
  container.innerHTML = '';

  const rows = state.shopRows || [];
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
      card.className = 'shop-card';
      if (ri === state.shopRow && ci === state.shopCol) card.classList.add('selected');
      if (state.gold < item.cost) card.classList.add('unaffordable');

      card.innerHTML =
        '<span class="shop-card-icon" style="color:rgb(' + item.color.join(',') + ')">' + esc(item.icon) + '</span>' +
        '<span class="shop-card-name">' + esc(item.name) + '</span>' +
        '<span class="shop-card-desc">' + esc(item.description) + '</span>' +
        '<span class="shop-card-cost">' + item.cost + 'g</span>';

      // Click: if already selected, buy; otherwise just visual feedback
      const capturedRi = ri;
      const capturedCi = ci;
      card.addEventListener('click', () => {
        if (capturedRi === state.shopRow && capturedCi === state.shopCol) {
          pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
        } else {
          // Navigate shop cursor to this item via UP/DOWN/LEFT/RIGHT
          // For simplicity, just send CONFIRM and let the server handle it
          pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
        }
      });

      itemsDiv.appendChild(card);
    }

    rowDiv.appendChild(itemsDiv);
    container.appendChild(rowDiv);
  }

  // Done button
  const doneBtn = document.getElementById('shop-done-btn');
  doneBtn.className = 'action-btn';
  if (state.shopRow >= rows.length) doneBtn.classList.add('selected');
  doneBtn.onclick = () => {
    pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
  };

  document.getElementById('shop-message').textContent = state.message || '';
}

// ================================================================
// DRAFT RENDERER
// ================================================================

function renderDraft(state) {
  const container = document.getElementById('draft-cards');
  container.innerHTML = '';

  const options = state.draftOptions || [];
  for (let i = 0; i < options.length; i++) {
    const opt = options[i];
    if (opt.type === 'skip') continue; // handled by skip button

    const card = document.createElement('div');
    card.className = 'draft-card';
    if (i === state.draftSelection) card.classList.add('selected');

    let icon = '\u2659'; // default pawn
    if (opt.pieceType) icon = pieceChar(opt.pieceType, 'player');
    else if (opt.type === 'combine') icon = pieceChar(opt.to, 'player');

    card.innerHTML =
      '<span class="draft-card-icon player-color">' + icon + '</span>' +
      '<span class="draft-card-desc">' + esc(opt.desc) + '</span>';

    const idx = i;
    card.addEventListener('click', () => {
      // Select and confirm
      if (idx === state.draftSelection) {
        pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
      }
    });

    container.appendChild(card);
  }

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
    card.title = t.description || '';

    container.appendChild(card);
  }
}

// ================================================================
// BOSS INTRO RENDERER
// ================================================================

function renderBossIntro(state) {
  const icon = document.getElementById('boss-icon');
  icon.textContent = pieceChar(state.bossType || 'king', 'enemy');

  const title = document.getElementById('boss-title');
  title.textContent = 'Boss: ' + (state.bossType || 'Unknown').toUpperCase();

  const mods = document.getElementById('boss-mods');
  const modList = state.bossMods || [];
  mods.innerHTML = modList.length > 0
    ? '<div style="color:#ff8866;font-size:0.85rem">Modifiers: ' + modList.join(', ') + '</div>'
    : '';
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
}

// ================================================================
// ELO SHOP RENDERER
// ================================================================

function renderEloShop(state) {
  document.getElementById('elo-balance').textContent = '\u25C6 ' + state.elo + ' ELO';

  const container = document.getElementById('elo-shop-cards');
  container.innerHTML = '';

  const items = state.items || [];
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    const card = document.createElement('div');
    card.className = 'elo-card';
    if (i === state.selection) card.classList.add('selected');
    if (item.owned) card.classList.add('owned');
    else if (!item.affordable) card.classList.add('unaffordable');

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

    container.appendChild(card);
  }

  document.getElementById('elo-shop-message').textContent = state.message || '';
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
