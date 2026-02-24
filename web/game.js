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
  // Expansion pieces
  'assassin-player': '\u2620',          'assassin-enemy': '\u2620',
  'berserker_piece-player': '\u2694',   'berserker_piece-enemy': '\u2694',
  'cannon-player': '\u25CE',            'cannon-enemy': '\u25CE',
  'lancer-player': '\u2191',            'lancer-enemy': '\u2191',
  'duelist-player': '\u2694',           'duelist-enemy': '\u2694',
  'reaper-player': '\u2620',            'reaper-enemy': '\u2620',
  'wyvern-player': '\u2682',            'wyvern-enemy': '\u2682',
  'charger-player': '\u25B6',           'charger-enemy': '\u25B6',
  'sentinel-player': '\u2616',          'sentinel-enemy': '\u2616',
  'healer-player': '\u2695',            'healer-enemy': '\u2695',
  'bard-player': '\u266A',              'bard-enemy': '\u266A',
  'wall-player': '\u2588',              'wall-enemy': '\u2588',
  'totem-player': '\u2641',             'totem-enemy': '\u2641',
  'decoy-player': '\u2302',             'decoy-enemy': '\u2302',
  'shapeshifter-player': '\u221E',      'shapeshifter-enemy': '\u221E',
  'time_mage-player': '\u231A',         'time_mage-enemy': '\u231A',
  'imp-player': '\u2666',               'imp-enemy': '\u2666',
  'poltergeist-player': '\u2622',       'poltergeist-enemy': '\u2622',
  'alchemist_piece-player': '\u2697',   'alchemist_piece-enemy': '\u2697',
  'golem-player': '\u25A0',             'golem-enemy': '\u25A0',
  'witch-player': '\u2605',             'witch-enemy': '\u2605',
  'trickster-player': '\u2740',         'trickster-enemy': '\u2740',
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

  // Show achievement toasts
  if (state.newAchievements && state.newAchievements.length > 0) {
    showAchievementToasts(state.newAchievements);
  }

  // Detect animations
  detectAnimations(oldState, state);

  // Render the current phase
  render(state);

  // Auto-battle stepping
  handleAutoBattle(state);
}

// ================================================================
// ACHIEVEMENT TOAST
// ================================================================

let achievementToastQueue = [];
let achievementToastActive = false;

function showAchievementToasts(achievements) {
  for (const ach of achievements) {
    achievementToastQueue.push(ach);
  }
  if (!achievementToastActive) {
    showNextAchievementToast();
  }
}

function showNextAchievementToast() {
  if (achievementToastQueue.length === 0) {
    achievementToastActive = false;
    return;
  }
  achievementToastActive = true;
  const ach = achievementToastQueue.shift();

  const toast = document.createElement('div');
  toast.className = 'achievement-toast';

  let rewardHtml = '';
  if (ach.rewards && ach.rewards.length > 0) {
    const r = ach.rewards[0];
    rewardHtml = '<span class="achievement-toast-reward">Unlocked: ' + esc(r.type) + ' — ' + esc(r.key) + '</span>';
  }

  toast.innerHTML =
    '<span class="achievement-toast-icon">' + esc(ach.icon || '\u2605') + '</span>' +
    '<div class="achievement-toast-text">' +
      '<span class="achievement-toast-title">Achievement Unlocked</span>' +
      '<span class="achievement-toast-name">' + esc(ach.name) + '</span>' +
      rewardHtml +
    '</div>';

  document.body.appendChild(toast);

  // Remove after animation and show next
  setTimeout(() => {
    toast.remove();
    showNextAchievementToast();
  }, 4000);
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
    // Speed up during sudden death — halve the delay
    const speed = state.suddenDeath ? Math.max(100, Math.floor(battleSpeedMs / 2)) : battleSpeedMs;

    if (!state.manualMode) {
      // Full auto: step at configured speed
      autoBattleTimer = setTimeout(async () => {
        try {
          const result = await pywebview.api.send_action('CONFIRM', -1, -1);
          handleStateUpdate(result);
        } catch (e) { console.error(e); }
      }, speed);
    } else if (!state.playerTurn) {
      // Manual mode but enemy turn: auto-step enemy
      autoBattleTimer = setTimeout(async () => {
        try {
          const result = await pywebview.api.send_action('CONFIRM', -1, -1);
          handleStateUpdate(result);
        } catch (e) { console.error(e); }
      }, speed);
    }
  }
}

// ================================================================
// ANIMATION DETECTION
// ================================================================

// pendingSlides: map of "toX,toY" → {fromX, fromY} for the next renderBoard call
let pendingSlides = {};
// pendingSpawns: set of "x,y" keys for pieces that just appeared (no matching old piece)
let pendingSpawns = {};
// pendingHits: set of "x,y" keys for pieces that took damage this frame
let pendingHits = {};
// pendingDeaths: array of {x, y, type, team, mods, deathStyle} for pieces that disappeared
let pendingDeaths = [];
function detectAnimations(oldSt, newSt) {
  pendingSlides = {};
  pendingSpawns = {};
  pendingHits = {};
  pendingDeaths = [];
  if (!oldSt || !newSt) return;
  if (!oldSt.board || !newSt.board) return;

  // Phase changed — skip movement diffing (pieces reset between phases)
  if (oldSt.phase !== newSt.phase) return;

  // Build maps: type+team+mods → list of positions for old and new boards
  const oldPieces = []; // {type, team, x, y, key, mods}
  const newPieces = [];

  for (let y = 0; y < 8; y++) {
    for (let x = 0; x < 8; x++) {
      const oc = oldSt.board[y] && oldSt.board[y][x];
      const nc = newSt.board[y] && newSt.board[y][x];
      if (oc && oc.piece) {
        const modKey = (oc.piece.modifiers || []).map(m => m.effect).sort().join(',');
        oldPieces.push({ type: oc.piece.type, team: oc.piece.team, x, y, key: oc.piece.type + '|' + oc.piece.team + '|' + modKey, mods: (oc.piece.modifiers || []).map(m => m.effect) });
      }
      if (nc && nc.piece) {
        const modKey = (nc.piece.modifiers || []).map(m => m.effect).sort().join(',');
        newPieces.push({ type: nc.piece.type, team: nc.piece.team, x, y, key: nc.piece.type + '|' + nc.piece.team + '|' + modKey, mods: (nc.piece.modifiers || []).map(m => m.effect) });
      }
    }
  }

  // Match pieces: for each new piece, find the closest old piece with same key
  // that isn't already at the same position
  const usedOld = new Set();
  const matchedNew = new Set();

  for (const np of newPieces) {
    // Check if a piece already existed here with same key — no move
    const stayIdx = oldPieces.findIndex((op, i) => !usedOld.has(i) && op.x === np.x && op.y === np.y && op.key === np.key);
    if (stayIdx >= 0) {
      usedOld.add(stayIdx);
      matchedNew.add(np);
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
      matchedNew.add(np);
      const op = oldPieces[bestIdx];
      pendingSlides[np.x + ',' + np.y] = { fromX: op.x, fromY: op.y };
    }
  }

  // Detect spawns: new pieces with no matching old piece
  for (const np of newPieces) {
    if (!matchedNew.has(np)) {
      pendingSpawns[np.x + ',' + np.y] = true;
    }
  }

  // Detect deaths: old pieces with no matching new piece
  for (let i = 0; i < oldPieces.length; i++) {
    if (!usedOld.has(i)) {
      const op = oldPieces[i];
      // Determine death style based on modifiers
      let deathStyle = 'standard';
      if (op.mods.includes('flaming') || op.mods.includes('blazing')) {
        deathStyle = 'fire';
      } else if (op.mods.includes('toxic') || op.mods.includes('venomous')) {
        deathStyle = 'poison';
      }
      pendingDeaths.push({
        x: op.x, y: op.y, type: op.type, team: op.team,
        deathStyle: deathStyle,
      });
    }
  }

  // Detect captures/disappearances and HP changes
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
            if (hpDelta < 0) {
              pendingHits[x + ',' + y] = true;
              // Spawn heal pulse for heals
            }
          }
          if (hpDelta > 0) {
            spawnHealPulse(x, y);
          }
        }
      }
    }
  }

  // Spawn death animations
  for (const death of pendingDeaths) {
    spawnDeathAnimation(death.x, death.y, death.type, death.team, death.deathStyle);
  }

  // Screen flash on kills (only for special kills, not every standard capture)
  if (pendingDeaths.length >= 2) {
    spawnScreenFlash('#ffffff', 0.35, 300);
  } else if (pendingDeaths.length === 1) {
    if (pendingDeaths[0].deathStyle === 'fire') {
      spawnScreenFlash('#ff6622', 0.2, 250);
    } else if (pendingDeaths[0].deathStyle === 'poison') {
      spawnScreenFlash('#44ff44', 0.15, 200);
    }
  }

  // Combo counter for multi-kills
  if (pendingDeaths.length >= 2) {
    showComboCounter(pendingDeaths.length);
  }

  // Board clear shockwave — all enemies wiped
  if (pendingDeaths.length > 0 && newSt.phase === 'battle') {
    let enemyCount = 0;
    for (let y = 0; y < (newSt.boardHeight || 8); y++) {
      for (let x = 0; x < (newSt.boardWidth || 8); x++) {
        const nc = newSt.board[y] && newSt.board[y][x];
        if (nc && nc.piece && nc.piece.team === 'enemy') enemyCount++;
      }
    }
    let oldEnemyCount = 0;
    for (let y = 0; y < (oldSt.boardHeight || 8); y++) {
      for (let x = 0; x < (oldSt.boardWidth || 8); x++) {
        const oc = oldSt.board[y] && oldSt.board[y][x];
        if (oc && oc.piece && oc.piece.team === 'enemy') oldEnemyCount++;
      }
    }
    if (enemyCount === 0 && oldEnemyCount > 0) {
      const lastDeath = pendingDeaths[pendingDeaths.length - 1];
      for (let r = 0; r < 3; r++) {
        setTimeout(() => {
          spawnShockwaveRing(lastDeath.x, lastDeath.y, '#ffffff');
          // Override ring size to be bigger for board clear
          const ring = particles[particles.length - 1];
          if (ring && ring.ring) ring.ringMaxRadius = 120;
        }, r * 80);
      }
      triggerShake(3);
      spawnScreenFlash('#ffffff', 0.3, 300);
    }
  }

  // ---- Combat effect dispatch based on lastAction metadata ----
  for (let y = 0; y < 8; y++) {
    for (let x = 0; x < 8; x++) {
      const nc = newSt.board[y] && newSt.board[y][x];
      if (!nc || !nc.piece || !nc.piece.lastAction) continue;
      const la = nc.piece.lastAction;
      if (la.type === 'attack') {
        const mods = la.attackerMods || [];
        // Fire projectile
        if (mods.includes('flaming') || mods.includes('blazing')) {
          spawnFireProjectile(la.fromX, la.fromY, la.targetX, la.targetY);
        }
        // Lightning chain
        if (mods.includes('frozen')) {
          spawnLightningChain(la.fromX, la.fromY, la.targetX, la.targetY, '#44ddff');
        }
        // Explosion (bomb/cannon kills)
        if (la.killed && (la.attackerType === 'bomb' || la.attackerType === 'cannon')) {
          spawnExplosion(la.targetX, la.targetY);
        }
        // Assassin shadow trail
        if (la.attackerType === 'assassin') {
          spawnShadowTrail(la.fromX, la.fromY, la.targetX, la.targetY);
          if (la.killed) spawnAssassinVignette();
        }
      }
    }
  }

  // Berserker rage pulse — detect ATK increase
  for (let y = 0; y < 8; y++) {
    for (let x = 0; x < 8; x++) {
      const oc = oldSt.board[y] && oldSt.board[y][x];
      const nc = newSt.board[y] && newSt.board[y][x];
      if (oc && oc.piece && nc && nc.piece &&
          oc.piece.type === nc.piece.type && oc.piece.team === nc.piece.team &&
          nc.piece.type === 'berserker_piece' &&
          nc.piece.attack > oc.piece.attack) {
        spawnBerserkerRagePulse(x, y);
      }
    }
  }

  // Heal beam — detect healer → healed piece
  for (let y = 0; y < 8; y++) {
    for (let x = 0; x < 8; x++) {
      const oc = oldSt.board[y] && oldSt.board[y][x];
      const nc = newSt.board[y] && newSt.board[y][x];
      if (oc && oc.piece && nc && nc.piece &&
          oc.piece.type === nc.piece.type && oc.piece.team === nc.piece.team) {
        const hpDelta = nc.piece.hp - oc.piece.hp;
        if (hpDelta > 0) {
          // Look for a healer that moved this tick
          for (let hy = 0; hy < 8; hy++) {
            for (let hx = 0; hx < 8; hx++) {
              const hc = newSt.board[hy] && newSt.board[hy][hx];
              if (hc && hc.piece && hc.piece.lastAction &&
                  hc.piece.lastAction.attackerType === 'healer' &&
                  hc.piece.team === nc.piece.team) {
                spawnHealBeam(hx, hy, x, y);
              }
            }
          }
        }
      }
    }
  }

  // Synergy pop-off — detect newly activated synergies
  if (oldSt.activeSynergies && newSt.activeSynergies) {
    const oldNames = new Set((oldSt.activeSynergies || []).map(s => s.name));
    const newSynergies = (newSt.activeSynergies || []).filter(s => !oldNames.has(s.name));
    if (newSynergies.length > 0) {
      newSynergies.forEach((syn, idx) => {
        const color = syn.color ? 'rgb(' + syn.color.join(',') + ')' : '#ffd700';
        const icon = syn.icon || '\u2726';
        setTimeout(() => showSynergyPopoff(syn.name, icon, color), idx * 500);
      });
    }
  }

  // Phoenix/Time Mage spawn effects — match pending spawns against recent deaths
  if (pendingDeaths.length > 0) {
    const deathTypes = new Set(pendingDeaths.map(d => d.type));
    for (const key in pendingSpawns) {
      const [sx, sy] = key.split(',').map(Number);
      const nc = newSt.board[sy] && newSt.board[sy][sx];
      if (!nc || !nc.piece) continue;
      if (nc.piece.type === 'phoenix' && deathTypes.has('phoenix')) {
        spawnPhoenixReviveEffect(sx, sy);
      }
      if (nc.piece.type === 'time_mage' && deathTypes.has('time_mage')) {
        spawnTimeMageRewindEffect();
      }
    }
  }

  // Detect gold change
  if (oldSt.gold !== undefined && newSt.gold !== undefined && oldSt.gold !== newSt.gold) {
    flashValue('stat-gold');
    if (newSt.gold > oldSt.gold) {
      spawnGoldSparkle();
    }
  }

  // Detect ELO change
  if (oldSt.elo !== undefined && newSt.elo !== undefined && oldSt.elo !== newSt.elo) {
    flashValue('elo-balance');
  }

  // Wave announcement
  if (oldSt.wave !== undefined && newSt.wave !== undefined && newSt.wave > oldSt.wave && newSt.phase === 'setup') {
    showWaveAnnouncement(newSt.wave);
  }

  // Sudden death announcement + vignette
  if (!oldSt.suddenDeath && newSt.suddenDeath) {
    showSuddenDeathAnnouncement();
    const bc = document.getElementById('board-container');
    if (bc) bc.classList.add('sudden-death-active');
  }

  // Boss entrance effect (when transitioning from boss_intro to battle)
  if (newSt.phase === 'battle' && oldSt.phase === 'boss_intro') {
    triggerBossEntrance();
  }

  // Battle victory effect
  if (oldSt.phase === 'battle' && newSt.phase === 'result') {
    const won = newSt.wins > (oldSt.wins || 0);
    if (won) {
      triggerVictoryEffect();
    }
  }

  // Ring collapse — spawn particles on newly dead cells
  if (oldSt.board && newSt.board && (newSt.suddenDeathRing || 0) > (oldSt.suddenDeathRing || 0)) {
    for (let y = 0; y < (newSt.boardHeight || 8); y++) {
      for (let x = 0; x < (newSt.boardWidth || 8); x++) {
        const oldCell = oldSt.board[y] && oldSt.board[y][x];
        const newCell = newSt.board[y] && newSt.board[y][x];
        if (oldCell && !oldCell.deadZone && newCell && newCell.deadZone) {
          spawnCollapseBurst(x, y);
        }
      }
    }
    triggerShake();
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

  // Damage tier classes based on magnitude
  const absDmg = Math.abs(delta);
  let removeDelay = 850;
  if (delta < 0) {
    if (absDmg >= 15) {
      popup.classList.add('dmg-cataclysmic');
      removeDelay = 1250;
      triggerShake(4);
      spawnDamageParticleBurst(pos.x, pos.y, '#ffd700');
    } else if (absDmg >= 10) {
      popup.classList.add('dmg-massive');
      removeDelay = 1050;
      triggerShake(3);
      spawnDamageTrailParticles(pos.x, pos.y, '#ffaa00');
    } else if (absDmg >= 7) {
      popup.classList.add('dmg-heavy');
      removeDelay = 950;
    } else if (absDmg >= 4) {
      popup.classList.add('dmg-medium');
      removeDelay = 900;
    }
  }

  document.body.appendChild(popup);
  setTimeout(() => popup.remove(), removeDelay);
}

function spawnDamageTrailParticles(cx, cy, color) {
  if (!particlesEnabled) return;
  for (let i = 0; i < 5; i++) {
    const life = 0.4 + Math.random() * 0.3;
    particles.push({
      x: cx + (Math.random() - 0.5) * 10,
      y: cy,
      vx: (Math.random() - 0.5) * 20,
      vy: -(30 + Math.random() * 30),
      life: life, maxLife: life,
      color: color,
      size: 1.5 + Math.random() * 1.5,
      noGravity: true,
    });
  }
}

function spawnDamageParticleBurst(cx, cy, color) {
  if (!particlesEnabled) return;
  const colors = [color, '#ffffff', '#ffcc00'];
  for (let i = 0; i < 10; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 50 + Math.random() * 60;
    const life = 0.3 + Math.random() * 0.3;
    particles.push({
      x: cx + (Math.random() - 0.5) * 8,
      y: cy + (Math.random() - 0.5) * 8,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: life, maxLife: life,
      color: colors[i % colors.length],
      size: 1.5 + Math.random() * 2,
      noGravity: true,
    });
  }
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

function showSuddenDeathAnnouncement() {
  const existing = document.querySelector('.sudden-death-announce');
  if (existing) existing.remove();

  const el = document.createElement('div');
  el.className = 'sudden-death-announce';
  el.textContent = 'SUDDEN DEATH';
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2200);
}

function spawnCollapseBurst(boardX, boardY) {
  if (!particlesEnabled) return;
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;

  for (let i = 0; i < 8; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 30 + Math.random() * 40;
    const life = 0.4 + Math.random() * 0.4;
    particles.push({
      x: pos.x + (Math.random() - 0.5) * 20,
      y: pos.y + (Math.random() - 0.5) * 20,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: life, maxLife: life,
      color: i % 3 === 0 ? '#ff2222' : (i % 3 === 1 ? '#442222' : '#221111'),
      size: 2 + Math.random() * 2,
    });
  }
}

function triggerShake(intensity) {
  const board = document.getElementById('board');
  if (!board) return;
  const tier = Math.max(1, Math.min(4, intensity || 2));
  const durations = { 1: 200, 2: 300, 3: 400, 4: 500 };
  const cls = 'shake-' + tier;
  board.classList.remove('shake-1', 'shake-2', 'shake-3', 'shake-4', 'shaking');
  void board.offsetWidth; // force reflow
  board.classList.add(cls);
  setTimeout(() => board.classList.remove(cls), durations[tier]);
}

function spawnScreenFlash(color, opacity, duration) {
  const flash = document.createElement('div');
  flash.className = 'screen-flash';
  flash.style.background = color || 'white';
  flash.style.opacity = String(opacity != null ? opacity : 0.8);
  flash.style.animation = 'none';
  document.body.appendChild(flash);
  // Fade out manually
  requestAnimationFrame(() => {
    flash.style.transition = 'opacity ' + (duration || 300) + 'ms ease-out';
    flash.style.opacity = '0';
  });
  setTimeout(() => flash.remove(), (duration || 300) + 50);
}

// ================================================================
// DEATH ANIMATIONS
// ================================================================

function spawnDeathAnimation(boardX, boardY, pieceType, team, deathStyle) {
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;

  // Piece-specific death cinematics
  if (pieceType === 'reaper') {
    // Desaturation flash on board + soul particle
    const boardEl = document.getElementById('board');
    if (boardEl) {
      boardEl.classList.remove('board-desaturate');
      void boardEl.offsetWidth;
      boardEl.classList.add('board-desaturate');
      setTimeout(() => boardEl.classList.remove('board-desaturate'), 200);
    }
    if (particlesEnabled) {
      const life = 1.2;
      particles.push({
        x: pos.x, y: pos.y,
        vx: (Math.random() - 0.5) * 5,
        vy: -(20 + Math.random() * 10),
        life: life, maxLife: life,
        color: '#ffffff',
        size: 4,
        noGravity: true,
      });
    }
  } else if (pieceType === 'void') {
    // Inversion flash on board + purple implosion particles
    const boardEl = document.getElementById('board');
    if (boardEl) {
      boardEl.classList.remove('board-invert');
      void boardEl.offsetWidth;
      boardEl.classList.add('board-invert');
      setTimeout(() => boardEl.classList.remove('board-invert'), 170);
    }
    if (particlesEnabled) {
      const colors = ['#8844cc', '#6622aa', '#aa66ff', '#4400aa'];
      for (let i = 0; i < 8; i++) {
        const angle = Math.random() * Math.PI * 2;
        const dist = 30 + Math.random() * 20;
        const life = 0.4 + Math.random() * 0.2;
        particles.push({
          x: pos.x + Math.cos(angle) * dist,
          y: pos.y + Math.sin(angle) * dist,
          vx: -Math.cos(angle) * 60,
          vy: -Math.sin(angle) * 60,
          life: life, maxLife: life,
          color: colors[i % colors.length],
          size: 2 + Math.random() * 2,
          noGravity: true,
        });
      }
    }
  } else if (pieceType === 'gambler') {
    // Gold coin particles scatter outward
    if (particlesEnabled) {
      const colors = ['#ffd700', '#ffec80', '#e8c060', '#ffc832'];
      for (let i = 0; i < 8; i++) {
        const angle = (Math.PI * 2 / 8) * i + Math.random() * 0.3;
        const speed = 80 + Math.random() * 50;
        const life = 0.5 + Math.random() * 0.3;
        particles.push({
          x: pos.x, y: pos.y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          life: life, maxLife: life,
          color: colors[i % colors.length],
          size: 2.5 + Math.random() * 2,
          noGravity: false,
        });
      }
    }
  }

  // Create temporary ghost element at piece's last position
  const boardEl = document.getElementById('board');
  if (!boardEl) return;
  const rect = boardEl.getBoundingClientRect();
  const cellSize = rect.width / 8;

  const ghost = document.createElement('div');
  ghost.className = 'death-ghost';
  ghost.style.left = (rect.left + boardX * cellSize) + 'px';
  ghost.style.top = (rect.top + boardY * cellSize) + 'px';
  ghost.style.width = cellSize + 'px';
  ghost.style.height = cellSize + 'px';

  // Add SVG piece to ghost
  if (typeof PieceRenderer !== 'undefined') {
    ghost.appendChild(PieceRenderer.create(pieceType, team, 'board'));
  }

  // Apply death animation class based on style
  if (deathStyle === 'fire') {
    ghost.classList.add('piece-dying-fire');
    spawnFireDeathParticles(boardX, boardY);
  } else if (deathStyle === 'poison') {
    ghost.classList.add('piece-dying-poison');
    spawnPoisonDeathParticles(boardX, boardY);
  } else {
    ghost.classList.add('piece-dying');
    spawnDeathParticles(boardX, boardY, team);
  }

  document.body.appendChild(ghost);
  setTimeout(() => ghost.remove(), 500);
}

function spawnDeathParticles(boardX, boardY, team) {
  if (!particlesEnabled) return;
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;
  const color = team === 'player' ? '#5082ff' : '#ff4646';
  for (let i = 0; i < 5; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 40 + Math.random() * 40;
    const life = 0.3 + Math.random() * 0.3;
    particles.push({
      x: pos.x, y: pos.y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: life, maxLife: life,
      color: color,
      size: 2 + Math.random() * 2,
    });
  }
}

function spawnFireDeathParticles(boardX, boardY) {
  if (!particlesEnabled) return;
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;
  const colors = ['#ff4400', '#ff8800', '#ffcc00', '#ff2200'];
  for (let i = 0; i < 10; i++) {
    const angle = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI;
    const speed = 60 + Math.random() * 60;
    const life = 0.4 + Math.random() * 0.3;
    particles.push({
      x: pos.x + (Math.random() - 0.5) * 10,
      y: pos.y,
      vx: Math.cos(angle) * speed * 0.5,
      vy: -(40 + Math.random() * 60),
      life: life, maxLife: life,
      color: colors[i % colors.length],
      size: 2 + Math.random() * 3,
      noGravity: true,
    });
  }
}

function spawnPoisonDeathParticles(boardX, boardY) {
  if (!particlesEnabled) return;
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;
  const colors = ['#44ff44', '#22cc22', '#88ff88', '#00aa00'];
  for (let i = 0; i < 8; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 20 + Math.random() * 30;
    const life = 0.5 + Math.random() * 0.3;
    particles.push({
      x: pos.x + (Math.random() - 0.5) * 16,
      y: pos.y + (Math.random() - 0.5) * 16,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed - 20,
      life: life, maxLife: life,
      color: colors[i % colors.length],
      size: 3 + Math.random() * 3,
      noGravity: true,
    });
  }
}

// ================================================================
// HEAL PULSE PARTICLES
// ================================================================

function spawnHealPulse(boardX, boardY) {
  if (!particlesEnabled) return;
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;
  for (let i = 0; i < 4; i++) {
    const life = 0.5 + Math.random() * 0.3;
    particles.push({
      x: pos.x + (Math.random() - 0.5) * 16,
      y: pos.y,
      vx: (Math.random() - 0.5) * 10,
      vy: -(30 + Math.random() * 20),
      life: life, maxLife: life,
      color: '#4ade80',
      size: 2 + Math.random() * 2,
      noGravity: true,
      text: '+',
    });
  }
}

// ================================================================
// GOLD SPARKLE PARTICLES
// ================================================================

function spawnGoldSparkle() {
  if (!particlesEnabled) return;
  const el = document.getElementById('stat-gold');
  if (!el) return;
  const rect = el.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;
  for (let i = 0; i < 6; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 30 + Math.random() * 30;
    const life = 0.4 + Math.random() * 0.3;
    particles.push({
      x: cx + (Math.random() - 0.5) * 20,
      y: cy + (Math.random() - 0.5) * 10,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: life, maxLife: life,
      color: i % 2 === 0 ? '#ffd700' : '#ffec80',
      size: 1.5 + Math.random() * 1.5,
      noGravity: true,
    });
  }
}

// ================================================================
// SCREEN EFFECTS
// ================================================================

function triggerBossEntrance() {
  // Red flash instead of white
  spawnScreenFlash('#ff2222', 0.3, 400);

  // Board container vignette
  const bc = document.getElementById('board-container');
  if (bc) {
    bc.classList.remove('boss-entrance');
    void bc.offsetWidth;
    bc.classList.add('boss-entrance');
    setTimeout(() => bc.classList.remove('boss-entrance'), 1200);
  }

  // Dark vignette overlay that persists during intro
  const vignette = document.createElement('div');
  vignette.className = 'boss-vignette';
  document.body.appendChild(vignette);
  setTimeout(() => vignette.remove(), 1500);

  // Extreme shake
  triggerShake(4);
}

function triggerVictoryEffect() {
  // Screen shake
  const board = document.getElementById('board');
  if (board) {
    board.classList.remove('victory-shake');
    void board.offsetWidth;
    board.classList.add('victory-shake');
    setTimeout(() => board.classList.remove('victory-shake'), 500);
  }

  // Burst of particles from center
  if (!particlesEnabled) return;
  const cx = window.innerWidth / 2;
  const cy = window.innerHeight / 2;
  for (let i = 0; i < 20; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 80 + Math.random() * 80;
    const life = 0.6 + Math.random() * 0.4;
    particles.push({
      x: cx, y: cy,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: life, maxLife: life,
      color: i % 3 === 0 ? '#5082ff' : (i % 3 === 1 ? '#ffffff' : '#ffd700'),
      size: 2 + Math.random() * 3,
      noGravity: true,
    });
  }
}

// ================================================================
// SHOCKWAVE RING PARTICLE
// ================================================================

function spawnShockwaveRing(boardX, boardY, color) {
  if (!particlesEnabled) return;
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;
  particles.push({
    x: pos.x, y: pos.y,
    vx: 0, vy: 0,
    life: 0.5, maxLife: 0.5,
    color: color || '#ffffff',
    size: 5,
    noGravity: true,
    ring: true,
    ringRadius: 5,
    ringMaxRadius: 60,
  });
}

// ================================================================
// CINEMATIC: COMBO COUNTER
// ================================================================

function showComboCounter(count) {
  const existing = document.querySelector('.combo-counter');
  if (existing) existing.remove();

  const el = document.createElement('div');
  el.className = 'combo-counter';
  el.textContent = 'x' + count;

  if (count >= 4) {
    el.classList.add('combo-x4');
    triggerShake(3);
    spawnDamageParticleBurst(window.innerWidth / 2, window.innerHeight * 0.3, '#ffd700');
  } else if (count >= 3) {
    el.classList.add('combo-x3');
    triggerShake(2);
  } else {
    el.classList.add('combo-x2');
  }

  document.body.appendChild(el);
  setTimeout(() => el.remove(), 850);
}

// ================================================================
// CINEMATIC: SYNERGY POP-OFF
// ================================================================

function showSynergyPopoff(name, icon, color) {
  const el = document.createElement('div');
  el.className = 'synergy-popoff';
  el.style.color = color;
  el.textContent = icon + ' ' + name;
  document.body.appendChild(el);
  triggerShake(1);
  setTimeout(() => el.remove(), 1300);
}

// ================================================================
// CINEMATIC: PIECE-SPECIFIC DEATH EFFECTS
// ================================================================

function spawnPhoenixReviveEffect(boardX, boardY) {
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;
  spawnScreenFlash('#ff6622', 0.2, 250);
  if (!particlesEnabled) return;
  const colors = ['#ff4400', '#ff8800', '#ffcc00', '#ff6622'];
  for (let i = 0; i < 12; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 50 + Math.random() * 50;
    const life = 0.4 + Math.random() * 0.3;
    particles.push({
      x: pos.x, y: pos.y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: life, maxLife: life,
      color: colors[i % colors.length],
      size: 2 + Math.random() * 2,
      noGravity: true,
    });
  }
}

function spawnTimeMageRewindEffect() {
  const overlay = document.createElement('div');
  overlay.className = 'scanline-overlay';
  document.body.appendChild(overlay);
  setTimeout(() => overlay.remove(), 250);
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
  // Shockwave ring
  spawnShockwaveRing(boardX, boardY, color);
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

let lastParticleTime = 0;
let ambientTimer = 0;
let auraTimer = 0;

// Modifier colors for aura particles
const MOD_AURA_COLORS = {
  flaming: '#ff6b35', blazing: '#ff9900', swift: '#00dddd', armored: '#8888cc',
  toxic: '#44cc44', venomous: '#22aa22', vampiric: '#cc2222', ethereal: '#88ccff',
  royal: '#ffd700', unstable: '#ff2222', haunted: '#8844cc', frozen: '#44aaff',
  thorny: '#66aa33',
};

function spawnModifierAuras(dt) {
  auraTimer += dt;
  if (auraTimer < 0.8) return; // spawn every 0.8s
  auraTimer = 0;
  if (!currentState || !currentState.board) return;

  for (let y = 0; y < 8; y++) {
    for (let x = 0; x < 8; x++) {
      const cell = currentState.board[y] && currentState.board[y][x];
      if (!cell || !cell.piece || cell.piece.team !== 'player') continue;
      if (!cell.piece.modifiers || cell.piece.modifiers.length === 0) continue;

      const pos = boardToScreen(x, y);
      if (!pos) continue;

      // Pick first modifier with a known aura color
      for (const mod of cell.piece.modifiers) {
        const color = MOD_AURA_COLORS[mod.effect];
        if (!color) continue;
        const angle = Math.random() * Math.PI * 2;
        const dist = 8 + Math.random() * 8;
        const life = 0.6 + Math.random() * 0.4;
        particles.push({
          x: pos.x + Math.cos(angle) * dist,
          y: pos.y + Math.sin(angle) * dist,
          vx: Math.cos(angle + Math.PI / 2) * 15,
          vy: Math.sin(angle + Math.PI / 2) * 15 - 5,
          life: life, maxLife: life,
          color: color,
          size: 1 + Math.random(),
          noGravity: true,
          ambient: true,
        });
        break; // Only one aura particle per piece per spawn cycle
      }
    }
  }
}

// ================================================================
// COMBAT EFFECT SPAWNERS
// ================================================================

function spawnFireProjectile(fromBX, fromBY, toBX, toBY) {
  if (!particlesEnabled) return;
  const from = boardToScreen(fromBX, fromBY);
  const to = boardToScreen(toBX, toBY);
  if (!from || !to) return;
  const colors = ['#ff4400', '#ff8800', '#ffcc00', '#ff2200'];
  const dx = to.x - from.x, dy = to.y - from.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const perpX = -dy / dist, perpY = dx / dist;
  for (let i = 0; i < 18; i++) {
    const delay = Math.random() * 200;
    const travelTime = 0.25 + Math.random() * 0.1;
    const arc = (Math.random() - 0.5) * 20;
    setTimeout(() => {
      if (!particlesEnabled) return;
      const life = travelTime + 0.1;
      particles.push({
        x: from.x + (Math.random() - 0.5) * 6,
        y: from.y + (Math.random() - 0.5) * 6,
        vx: dx / travelTime + perpX * arc,
        vy: dy / travelTime + perpY * arc - 15,
        life: life, maxLife: life,
        color: colors[i % colors.length],
        size: 2 + Math.random() * 2,
        noGravity: true,
        trail: true,
      });
    }, delay);
  }
  // Impact burst at target after travel time
  setTimeout(() => {
    if (!particlesEnabled) return;
    for (let i = 0; i < 8; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 40 + Math.random() * 40;
      const life = 0.3 + Math.random() * 0.2;
      particles.push({
        x: to.x, y: to.y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: life, maxLife: life,
        color: colors[Math.floor(Math.random() * colors.length)],
        size: 2 + Math.random() * 2,
        noGravity: true,
      });
    }
  }, 250);
  spawnScreenFlash('#ff6600', 0.15, 200);
}

function spawnLightningChain(fromBX, fromBY, toBX, toBY, color) {
  if (!particlesEnabled) return;
  const from = boardToScreen(fromBX, fromBY);
  const to = boardToScreen(toBX, toBY);
  if (!from || !to) return;
  color = color || '#44ddff';
  const dx = to.x - from.x, dy = to.y - from.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const perpX = -dy / dist, perpY = dx / dist;
  // Generate jagged midpoints
  const segments = 6 + Math.floor(Math.random() * 3);
  const pts = [{x: from.x, y: from.y}];
  for (let i = 1; i < segments; i++) {
    const t = i / segments;
    const offset = (Math.random() - 0.5) * 30;
    pts.push({
      x: from.x + dx * t + perpX * offset,
      y: from.y + dy * t + perpY * offset,
    });
  }
  pts.push({x: to.x, y: to.y});
  // Main bolt
  const life = 0.3;
  const bolt = {
    x: 0, y: 0, vx: 0, vy: 0,
    life: life, maxLife: life,
    color: color,
    size: 0,
    noGravity: true,
    lightning: true,
    lightningPts: pts,
  };
  // 30% chance for a fork from a random midpoint
  if (Math.random() < 0.3 && pts.length > 3) {
    const forkIdx = 1 + Math.floor(Math.random() * (pts.length - 3));
    const forkStart = pts[forkIdx];
    const forkAngle = Math.atan2(dy, dx) + (Math.random() - 0.5) * 1.2;
    const forkLen = dist * (0.3 + Math.random() * 0.2);
    const forkPts = [{x: forkStart.x, y: forkStart.y}];
    for (let i = 1; i <= 3; i++) {
      const t = i / 3;
      forkPts.push({
        x: forkStart.x + Math.cos(forkAngle) * forkLen * t + (Math.random() - 0.5) * 10,
        y: forkStart.y + Math.sin(forkAngle) * forkLen * t + (Math.random() - 0.5) * 10,
      });
    }
    bolt.lightningFork = forkPts;
  }
  particles.push(bolt);
  // Impact sparks at target
  for (let i = 0; i < 6; i++) {
    const angle = Math.random() * Math.PI * 2;
    const speed = 40 + Math.random() * 30;
    const sLife = 0.2 + Math.random() * 0.15;
    particles.push({
      x: to.x + (Math.random() - 0.5) * 6,
      y: to.y + (Math.random() - 0.5) * 6,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: sLife, maxLife: sLife,
      color: '#ffffff',
      size: 1.5 + Math.random(),
      noGravity: true,
    });
  }
}

function spawnExplosion(boardX, boardY) {
  if (!particlesEnabled) return;
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;
  const outerColors = ['#ff8800', '#ffcc00'];
  const innerColors = ['#ffffff', '#ffffcc'];
  // 30 radial burst particles
  for (let i = 0; i < 30; i++) {
    const angle = (Math.PI * 2 / 30) * i + Math.random() * 0.2;
    const speed = 150 + Math.random() * 100;
    const life = 0.3 + Math.random() * 0.2;
    const isInner = i < 8;
    particles.push({
      x: pos.x + (Math.random() - 0.5) * 4,
      y: pos.y + (Math.random() - 0.5) * 4,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: life, maxLife: life,
      color: isInner ? innerColors[i % 2] : outerColors[i % 2],
      size: isInner ? 3 + Math.random() * 2 : 2 + Math.random() * 3,
      noGravity: true,
    });
  }
  // 3 concentric shockwave rings
  for (let r = 0; r < 3; r++) {
    setTimeout(() => {
      particles.push({
        x: pos.x, y: pos.y,
        vx: 0, vy: 0,
        life: 0.4, maxLife: 0.4,
        color: r === 0 ? '#ffffff' : '#ff8800',
        size: 0,
        noGravity: true,
        ring: true,
        ringRadius: 5 + r * 8,
        ringMaxRadius: 70 + r * 20,
      });
    }, r * 60);
  }
  triggerShake(3);
  spawnScreenFlash('#ffffff', 0.3, 200);
  // Brief heat distortion on board
  const boardEl = document.getElementById('board');
  if (boardEl) {
    boardEl.style.filter = 'contrast(1.2) brightness(1.1)';
    setTimeout(() => { boardEl.style.filter = ''; }, 200);
  }
}

function spawnShadowTrail(fromBX, fromBY, toBX, toBY) {
  if (!particlesEnabled) return;
  const from = boardToScreen(fromBX, fromBY);
  const to = boardToScreen(toBX, toBY);
  if (!from || !to) return;
  const colors = ['#1a0033', '#330066', '#220044'];
  const dx = to.x - from.x, dy = to.y - from.y;
  for (let i = 0; i < 8; i++) {
    const t = i / 7;
    const life = 0.3 + Math.random() * 0.15;
    particles.push({
      x: from.x + dx * t + (Math.random() - 0.5) * 10,
      y: from.y + dy * t + (Math.random() - 0.5) * 10,
      vx: (Math.random() - 0.5) * 8,
      vy: -(5 + Math.random() * 10),
      life: life, maxLife: life,
      color: colors[i % colors.length],
      size: 3 + Math.random() * 2,
      noGravity: true,
    });
  }
}

function spawnAssassinVignette() {
  const vig = document.createElement('div');
  vig.className = 'assassin-vignette';
  document.body.appendChild(vig);
  setTimeout(() => vig.remove(), 400);
}

function spawnBerserkerRagePulse(boardX, boardY) {
  if (!particlesEnabled) return;
  const pos = boardToScreen(boardX, boardY);
  if (!pos) return;
  // Red shockwave ring
  particles.push({
    x: pos.x, y: pos.y,
    vx: 0, vy: 0,
    life: 0.4, maxLife: 0.4,
    color: '#ff2200',
    size: 0,
    noGravity: true,
    ring: true,
    ringRadius: 5,
    ringMaxRadius: 50,
  });
  // 6 aggressive red particles
  const colors = ['#ff2200', '#cc0000', '#ff4400'];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI * 2 / 6) * i + Math.random() * 0.3;
    const speed = 60 + Math.random() * 40;
    const life = 0.3 + Math.random() * 0.2;
    particles.push({
      x: pos.x, y: pos.y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: life, maxLife: life,
      color: colors[i % colors.length],
      size: 2 + Math.random() * 2,
      noGravity: true,
    });
  }
  spawnScreenFlash('#ff2200', 0.12, 100);
  triggerShake(1);
}

function spawnHealBeam(fromBX, fromBY, toBX, toBY) {
  if (!particlesEnabled) return;
  const from = boardToScreen(fromBX, fromBY);
  const to = boardToScreen(toBX, toBY);
  if (!from || !to) return;
  const colors = ['#44ff88', '#88ffaa', '#ffd700'];
  const dx = to.x - from.x, dy = to.y - from.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  const perpX = -dy / dist, perpY = dx / dist;
  for (let i = 0; i < 10; i++) {
    const delay = i * 25;
    setTimeout(() => {
      if (!particlesEnabled) return;
      const t = i / 9;
      const arc = Math.sin(t * Math.PI) * 20;
      const life = 0.4 + Math.random() * 0.2;
      particles.push({
        x: from.x + dx * t + perpX * arc + (Math.random() - 0.5) * 4,
        y: from.y + dy * t + perpY * arc + (Math.random() - 0.5) * 4,
        vx: (Math.random() - 0.5) * 10,
        vy: -(3 + Math.random() * 5),
        life: life, maxLife: life,
        color: colors[i % colors.length],
        size: 1.5 + Math.random() * 1.5 + Math.sin(Date.now() * 0.01) * 0.5,
        noGravity: true,
      });
    }, delay);
  }
}

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

    // Modifier aura particles — spawn orbiting motes for player pieces with modifiers
    spawnModifierAuras(dt);
  }

  // Cap particle count for performance
  if (particles.length > 400) {
    particles.splice(0, particles.length - 400);
  }

  particleCtx.clearRect(0, 0, particleCtx.canvas.width, particleCtx.canvas.height);
  particleCtx.globalCompositeOperation = 'lighter';

  // Trail particle spawning — fire trails spawn child particles
  const trailSpawns = [];
  for (let i = 0; i < particles.length; i++) {
    const p = particles[i];
    if (p.trail && p.life > 0.3 * p.maxLife) {
      p._trailFrame = (p._trailFrame || 0) + 1;
      if (p._trailFrame % 2 === 0) {
        trailSpawns.push({
          x: p.x + (Math.random() - 0.5) * 4,
          y: p.y + (Math.random() - 0.5) * 4,
          vx: (Math.random() - 0.5) * 8,
          vy: (Math.random() - 0.5) * 8 - 5,
          life: p.maxLife * 0.4, maxLife: p.maxLife * 0.4,
          color: p.color,
          size: p.size * 0.5,
          noGravity: true,
        });
      }
    }
  }
  for (const ts of trailSpawns) particles.push(ts);

  // Single-pass update + draw with in-place compaction (avoids O(n^2) splice)
  let alive = 0;
  for (let i = 0; i < particles.length; i++) {
    const p = particles[i];
    p.life -= dt;
    if (p.life <= 0) continue;

    // Wobble (skip for lightning)
    if (!p.lightning) {
      p.vx += (Math.random() - 0.5) * 40 * dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      if (!p.noGravity) p.vy += 120 * dt; // gravity
    }

    const alpha = p.ambient ? 0.15 : Math.max(0, p.life / p.maxLife);
    particleCtx.globalAlpha = alpha;
    particleCtx.fillStyle = p.color;

    // Lightning bolt — jagged line segments with glow
    if (p.lightning) {
      // Jitter 2-3 random midpoints for crackling feel
      const pts = p.lightningPts;
      for (let j = 0; j < 3; j++) {
        const idx = 1 + Math.floor(Math.random() * (pts.length - 2));
        if (idx > 0 && idx < pts.length - 1) {
          pts[idx].x += (Math.random() - 0.5) * 6;
          pts[idx].y += (Math.random() - 0.5) * 6;
        }
      }
      // Thick dim glow layer
      particleCtx.strokeStyle = p.color;
      particleCtx.lineWidth = 6 * alpha;
      particleCtx.globalAlpha = alpha * 0.4;
      particleCtx.beginPath();
      particleCtx.moveTo(pts[0].x, pts[0].y);
      for (let j = 1; j < pts.length; j++) particleCtx.lineTo(pts[j].x, pts[j].y);
      particleCtx.stroke();
      // Thin bright core
      particleCtx.strokeStyle = '#ffffff';
      particleCtx.lineWidth = 2 * alpha;
      particleCtx.globalAlpha = alpha;
      particleCtx.beginPath();
      particleCtx.moveTo(pts[0].x, pts[0].y);
      for (let j = 1; j < pts.length; j++) particleCtx.lineTo(pts[j].x, pts[j].y);
      particleCtx.stroke();
      // Draw fork if present
      if (p.lightningFork) {
        const fk = p.lightningFork;
        particleCtx.strokeStyle = p.color;
        particleCtx.lineWidth = 3 * alpha;
        particleCtx.globalAlpha = alpha * 0.5;
        particleCtx.beginPath();
        particleCtx.moveTo(fk[0].x, fk[0].y);
        for (let j = 1; j < fk.length; j++) particleCtx.lineTo(fk[j].x, fk[j].y);
        particleCtx.stroke();
      }
    }
    // Ring particles — expanding circle outline
    else if (p.ring) {
      const progress = 1 - (p.life / p.maxLife);
      const radius = p.ringRadius + (p.ringMaxRadius - p.ringRadius) * progress;
      particleCtx.strokeStyle = p.color;
      particleCtx.lineWidth = 2 * alpha;
      particleCtx.beginPath();
      particleCtx.arc(p.x, p.y, radius, 0, Math.PI * 2);
      particleCtx.stroke();
    }
    // Text particles (e.g., heal "+")
    else if (p.text) {
      particleCtx.font = (p.size * 4) + 'px monospace';
      particleCtx.textAlign = 'center';
      particleCtx.fillText(p.text, p.x, p.y);
    }
    // Standard dot particles
    else {
      particleCtx.beginPath();
      particleCtx.arc(p.x, p.y, p.size * (p.ambient ? 1 : alpha), 0, Math.PI * 2);
      particleCtx.fill();
    }

    particles[alive++] = p;
  }
  particles.length = alive;
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
  if (phase !== 'map') mapBuilt = false;

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
  } else if (phase === 'map') {
    document.getElementById('map-view').classList.add('active');
    renderMap(state, isNewPhase);
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

  // Master info
  const masterEl = document.getElementById('stat-master');
  if (masterEl && state.master) {
    masterEl.textContent = state.master.icon + ' ' + state.master.name;
    const [r, g, b] = state.master.color;
    masterEl.style.color = `rgb(${r},${g},${b})`;
    masterEl.title = state.master.passive + ' / ' + state.master.drawback;
  }

  // Sudden death vignette
  const bc = document.getElementById('board-container');
  if (bc) {
    bc.classList.toggle('sudden-death-active', !!state.suddenDeath);
  }

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

// Board cell cache — keyed by boardId
const _boardCache = {};

function renderBoard(boardId, state) {
  const boardEl = document.getElementById(boardId);
  if (!boardEl) return;

  const grid = state.board;
  const highlights = state.highlights || {};
  const cursor = state.cursor || [-1, -1];
  const W = state.boardWidth;
  const H = state.boardHeight;

  // Turn indicator glow
  boardEl.classList.remove('player-turn', 'enemy-turn');
  if (state.phase === 'battle') {
    boardEl.classList.add(state.playerTurn ? 'player-turn' : 'enemy-turn');
  }

  // Create cell grid once per board, reuse across renders
  const dimKey = W + 'x' + H;
  let cache = _boardCache[boardId];
  // Reinit if dimensions changed or cells were detached from DOM
  if (!cache || cache.dimKey !== dimKey || cache.cells[0].parentNode !== boardEl) {
    boardEl.innerHTML = '';
    const cells = [];
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const div = document.createElement('div');
        // Stable event listeners — tooltip reads _cellData from element
        div.addEventListener('mousedown', () => onBoardCellClick(boardId, x, y, 'mousedown'));
        div.addEventListener('mouseup', () => onBoardCellClick(boardId, x, y, 'mouseup'));
        div.addEventListener('mouseenter', function() {
          onBoardCellMove(boardId, x, y);
          if (this._cellData) {
            const ttHtml = buildCellTooltip(this._cellData);
            if (ttHtml) showTooltip(ttHtml, this);
          }
        });
        div.addEventListener('mouseleave', hideTooltip);
        boardEl.appendChild(div);
        cells.push(div);
      }
    }
    cache = { dimKey: dimKey, cells: cells, fps: new Array(W * H).fill('') };
    _boardCache[boardId] = cache;
  }

  const cells = cache.cells;
  const fps = cache.fps;
  const slidingPieces = [];

  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const idx = y * W + x;
      const div = cells[idx];
      const cell = grid[y][x];
      const key = x + ',' + y;

      // Store current cell data for tooltip handler
      div._cellData = cell;

      // Update cell classes (always — these change with cursor/highlights)
      const isLight = (x + y) % 2 === 0;
      let cls = 'cell ' + (isLight ? 'light' : 'dark');
      if (highlights[key]) cls += ' highlight-' + highlights[key];
      if (x === cursor[0] && y === cursor[1]) cls += ' cursor-active';
      if (cell.deadZone) cls += ' dead-zone';
      else if (cell.blocked) cls += ' blocked';
      if (cell.warningZone) cls += ' warning-zone';
      if (cell.borderMod) cls += ' has-border-mod';
      if (div.className !== cls) div.className = cls;

      // Border mod style
      if (cell.borderMod) {
        div.style.setProperty('--border-mod-color', 'rgb(' + cell.borderMod.color.join(',') + ')');
      } else {
        div.style.removeProperty('--border-mod-color');
      }

      // Build content fingerprint — skip child rebuild if unchanged
      let fp = '';
      if (cell.cellMod) fp += 'cm:' + cell.cellMod.name;
      if (cell.borderMod) fp += '|bm:' + cell.borderMod.name;
      if (cell.piece) {
        fp += '|p:' + cell.piece.type + ':' + cell.piece.team;
        fp += ':' + cell.piece.hp + '/' + cell.piece.maxHp;
        if (cell.piece.modifiers) {
          for (const mod of cell.piece.modifiers) fp += ':' + mod.effect;
        }
        if (cell.piece.lastAction && cell.piece.lastAction.type === 'attack') fp += ':atk';
      }
      if (pendingSlides[key]) fp += '|sl';
      if (pendingSpawns[key]) fp += '|sp';
      if (pendingHits[key]) fp += '|ht';

      if (fp === fps[idx]) continue; // unchanged — skip child DOM ops
      fps[idx] = fp;

      // Clear children (much cheaper than boardEl.innerHTML = '' for whole board)
      while (div.firstChild) div.removeChild(div.lastChild);
      div.title = '';

      // Cell modifier overlay
      if (cell.cellMod) {
        const overlay = document.createElement('div');
        overlay.className = 'cell-mod-overlay';
        overlay.style.backgroundColor = 'rgb(' + cell.cellMod.color.join(',') + ')';
        div.title = cell.cellMod.name;
        div.appendChild(overlay);
      }

      // Border modifier title
      if (cell.borderMod) {
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

        // SVG piece rendering (falls back to unicode if PieceRenderer unavailable)
        if (typeof PieceRenderer !== 'undefined') {
          pieceEl.appendChild(PieceRenderer.create(cell.piece.type, cell.piece.team, 'board'));
        } else {
          pieceEl.textContent = pieceChar(cell.piece.type, cell.piece.team);
        }

        // Attack lunge animation
        if (cell.piece.lastAction && cell.piece.lastAction.type === 'attack') {
          const la = cell.piece.lastAction;
          pieceEl.style.setProperty('--lunge-x', (la.targetX - la.fromX) || 0);
          pieceEl.style.setProperty('--lunge-y', (la.targetY - la.fromY) || 0);
          pieceEl.classList.add('piece-attacking');
        }

        // Spawn animation
        if (pendingSpawns[key]) {
          pieceEl.classList.add('piece-spawning');
        }

        // Damage flash
        if (pendingHits[key]) {
          pieceEl.classList.add('piece-hit');
        }

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
        const slide = pendingSlides[key];
        if (slide) {
          const dx = (slide.fromX - x) * 100;
          const dy = (slide.fromY - y) * 100;
          pieceEl.style.transform = 'translate(' + dx + '%, ' + dy + '%)';
          pieceEl.classList.add('sliding');
          slidingPieces.push(pieceEl);
        }

        div.appendChild(pieceEl);
      }
    }
  }

  // Flush slide animations: force layout read, then clear transforms
  if (slidingPieces.length > 0) {
    void boardEl.offsetHeight;
    requestAnimationFrame(() => {
      for (const el of slidingPieces) {
        el.style.transform = 'translate(0, 0)';
      }
      setTimeout(() => {
        for (const el of slidingPieces) {
          el.style.transform = '';
          el.classList.remove('sliding');
        }
      }, 220);
    });
  }

  // Clear pending animation state after rendering
  pendingSlides = {};
  pendingSpawns = {};
  pendingHits = {};
  pendingDeaths = [];
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
    if (entry.includes('SUDDEN DEATH') || entry.includes('Ring collapse') || entry.includes('crushed in the squeeze')) div.classList.add('sudden-death-log');
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
    if (r.rarity && r.rarity !== 'common') div.classList.add('rarity-' + r.rarity);

    const icon = document.createElement('span');
    icon.className = 'piece-icon player-color';
    if (typeof PieceRenderer !== 'undefined') {
      icon.appendChild(PieceRenderer.create(r.type, 'player', 'roster'));
    } else {
      icon.textContent = pieceChar(r.type, 'player');
    }
    div.appendChild(icon);

    const label = document.createElement('span');
    label.className = 'piece-label';
    let labelText = pieceDisplayName(r.type);
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
    attachTooltip(div, buildPieceTooltip(r));

    container.appendChild(div);
  }
}

// ================================================================
// RESULT RENDERER
// ================================================================

function renderResult(state, animate) {
  const title = document.getElementById('result-title');
  const body = document.getElementById('result-body');

  const msg = (state.message || '').toLowerCase();
  const won = msg.includes('victory');
  const lost = msg.includes('defeat');
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

    let itemIndex = 0;
    for (let ri = 0; ri < rows.length; ri++) {
      const row = rows[ri];

      // Shelf wrapper
      const shelf = document.createElement('div');
      shelf.className = 'shop-shelf';

      // Category label tag
      const tag = document.createElement('div');
      tag.className = 'shelf-label-tag';
      tag.style.color = 'rgb(' + row.color.join(',') + ')';
      tag.textContent = row.label;
      shelf.appendChild(tag);

      // Plank container
      const plank = document.createElement('div');
      plank.className = 'shelf-plank';

      // Items row
      const itemsDiv = document.createElement('div');
      itemsDiv.className = 'shelf-items';

      for (let ci = 0; ci < row.items.length; ci++) {
        const item = row.items[ci];
        const el = document.createElement('div');
        el.className = 'shelf-item';
        if (animate) el.style.setProperty('--i', itemIndex);
        el.dataset.shopRi = ri;
        el.dataset.shopCi = ci;
        itemIndex++;

        // Rarity class
        if (item.rarity && item.rarity !== 'common') {
          el.classList.add('rarity-' + item.rarity);
        }
        // Sell item styling
        if (item.cost < 0 || item.type === 'sell_piece') {
          el.classList.add('sell-item');
        }

        const costDisplay = (item.cost < 0)
          ? '+' + Math.abs(item.cost) + 'g'
          : item.cost + 'g';

        // Glow disc (behind icon, for rarity)
        const glow = document.createElement('div');
        glow.className = 'shelf-item-glow';
        el.appendChild(glow);

        // Icon
        const icon = document.createElement('span');
        icon.className = 'shelf-item-icon';
        icon.style.color = 'rgb(' + item.color.join(',') + ')';
        icon.textContent = item.icon;
        el.appendChild(icon);

        // Name
        const name = document.createElement('span');
        name.className = 'shelf-item-name';
        name.textContent = item.name;
        el.appendChild(name);

        // Price
        const price = document.createElement('span');
        price.className = 'shelf-item-price';
        price.textContent = costDisplay;
        el.appendChild(price);

        // Tooltip
        if (item.description) {
          const ttCost = item.cost < 0 ? '+' + Math.abs(item.cost) + 'g' : item.cost + 'g';
          attachTooltip(el, '<div class="tt-title">' + esc(item.name) + '</div><div class="tt-desc">' + esc(item.description) + '</div><div class="tt-mod">' + ttCost + '</div>');
        }

        // Hover selects (immediate client-side + backend sync), click confirms
        const capturedRi = ri;
        const capturedCi = ci;
        el.addEventListener('mouseenter', () => {
          // Immediate client-side selection update
          container.querySelectorAll('.shelf-item.selected').forEach(s => s.classList.remove('selected'));
          el.classList.add('selected');
          const doneBtn = document.getElementById('shop-done-btn');
          if (doneBtn) doneBtn.classList.remove('selected');
          // Sync backend
          pywebview.api.set_selection(capturedRi, capturedCi).then(handleStateUpdate).catch(console.error);
        });
        el.addEventListener('click', () => {
          pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
        });

        itemsDiv.appendChild(el);
      }

      plank.appendChild(itemsDiv);

      // Wood plank surface
      const surface = document.createElement('div');
      surface.className = 'shelf-plank-surface';
      plank.appendChild(surface);

      // Wood plank edge
      const edge = document.createElement('div');
      edge.className = 'shelf-plank-edge';
      plank.appendChild(edge);

      // Shadow below plank
      const shadow = document.createElement('div');
      shadow.className = 'shelf-plank-shadow';
      plank.appendChild(shadow);

      shelf.appendChild(plank);
      container.appendChild(shelf);
    }
  }

  // Update selection/affordability classes without rebuilding DOM
  const items = container.querySelectorAll('.shelf-item');
  items.forEach((el) => {
    const ri = parseInt(el.dataset.shopRi);
    const ci = parseInt(el.dataset.shopCi);
    const row = rows[ri];
    if (!row) return;
    const item = row.items[ci];
    if (!item) return;
    el.classList.toggle('selected', ri === state.shopRow && ci === state.shopCol);
    el.classList.toggle('unaffordable', item.cost > 0 && state.gold < item.cost);
  });

  // Done button
  const doneBtn = document.getElementById('shop-done-btn');
  doneBtn.className = 'action-btn';
  if (state.shopRow >= rows.length) doneBtn.classList.add('selected');
  doneBtn.onmouseenter = () => {
    // Immediate client-side selection update
    container.querySelectorAll('.shelf-item.selected').forEach(s => s.classList.remove('selected'));
    doneBtn.classList.add('selected');
    // Sync backend
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

// ================================================================
// ENCOUNTER MAP RENDERER
// ================================================================

let mapBuilt = false;

function renderMap(state, animate) {
  const container = document.getElementById('map-nodes-container');
  const segInfo = document.getElementById('map-segment-info');
  const mapData = state.mapData;

  if (!mapData) return;

  const floors = mapData.floors || [];
  const currentFloor = mapData.currentFloor;
  const choices = mapData.choices || [];
  const hasBoss = mapData.hasBoss;
  const bossNode = mapData.bossNode;

  // Segment info
  if (hasBoss && bossNode) {
    segInfo.textContent = 'Round ' + (mapData.bossIndex + 1) + ' / ' + mapData.totalBosses;
  } else {
    segInfo.textContent = 'Floor ' + (currentFloor + 1) + ' / ' + floors.length;
  }

  if (!mapBuilt || animate) {
    mapBuilt = true;
    container.innerHTML = '';

    let nodeDelay = 0;

    // Boss row at TOP — wax seal destination
    if (hasBoss && bossNode) {
      const bossRow = document.createElement('div');
      bossRow.className = 'map-boss-row';

      const bNode = document.createElement('div');
      bNode.className = 'map-boss-node';
      bNode.dataset.floor = 'boss';

      if (currentFloor < floors.length) {
        bNode.classList.add('future');
      }

      const bIcon = document.createElement('div');
      bIcon.className = 'boss-icon';
      bIcon.textContent = pieceChar(bossNode.type, 'enemy');
      bNode.appendChild(bIcon);

      const bName = document.createElement('div');
      bName.className = 'boss-name';
      bName.textContent = bossNode.name;
      bNode.appendChild(bName);

      bossRow.appendChild(bNode);

      // "BOSS" label as a separate div below the seal
      const bLabel = document.createElement('div');
      bLabel.className = 'map-boss-label';
      bLabel.textContent = 'BOSS';
      bossRow.appendChild(bLabel);

      container.appendChild(bossRow);
    }

    // Build floor rows in REVERSE order (last floor at top, first at bottom)
    for (let fi = floors.length - 1; fi >= 0; fi--) {
      const floor = floors[fi];
      const row = document.createElement('div');
      row.className = 'map-floor-row';
      row.dataset.floor = fi;

      if (fi < currentFloor) {
        row.classList.add('completed');
      } else if (fi === currentFloor) {
        row.classList.add('current');
      } else {
        row.classList.add('future');
      }

      for (let ni = 0; ni < floor.length; ni++) {
        const enc = floor[ni];
        const node = document.createElement('div');
        node.className = 'map-node';
        node.dataset.floor = fi;
        node.dataset.node = ni;
        node.style.setProperty('--node-delay', nodeDelay);
        nodeDelay += 60;

        // Mark chosen nodes
        if (fi < currentFloor && choices[fi] === ni) {
          node.classList.add('chosen');
        }

        // --- Header row: icon + label + gold ---
        const header = document.createElement('div');
        header.className = 'map-node-header';

        const icon = document.createElement('span');
        icon.className = 'map-node-icon';
        icon.textContent = '\u2694';
        header.appendChild(icon);

        const label = document.createElement('span');
        label.className = 'map-node-label';
        label.textContent = enc.enemy_count_base + ' foes';
        header.appendChild(label);

        const goldLabel = document.createElement('span');
        goldLabel.className = 'map-node-gold';
        goldLabel.textContent = enc.reward_gold_min + '-' + enc.reward_gold_max + 'g';
        header.appendChild(goldLabel);

        node.appendChild(header);

        // --- Inline modifiers ---
        const mods = enc.modifiers || [];
        if (mods.length > 0) {
          // Ink divider between header and mods
          const divider = document.createElement('div');
          divider.className = 'map-node-divider';
          node.appendChild(divider);

          const modsContainer = document.createElement('div');
          modsContainer.className = 'map-node-mods';

          for (let mi = 0; mi < mods.length; mi++) {
            const mod = mods[mi];
            const modEl = document.createElement('div');
            modEl.className = 'map-node-mod';
            if (mod.color) {
              modEl.style.borderLeftColor = 'rgb(' + mod.color[0] + ',' + mod.color[1] + ',' + mod.color[2] + ')';
            }

            const modName = document.createElement('div');
            modName.className = 'map-node-mod-name';
            if (mod.icon) {
              const modIcon = document.createElement('span');
              modIcon.className = 'mod-icon';
              modIcon.textContent = mod.icon;
              modName.appendChild(modIcon);
            }
            modName.appendChild(document.createTextNode(mod.name || ''));
            modEl.appendChild(modName);

            if (mod.description) {
              const modDesc = document.createElement('div');
              modDesc.className = 'map-node-mod-desc';
              modDesc.textContent = mod.description;
              modEl.appendChild(modDesc);
            }

            modsContainer.appendChild(modEl);
          }

          node.appendChild(modsContainer);
        }

        // --- Guaranteed drops ---
        if (enc.guaranteed_drops && enc.guaranteed_drops.length > 0) {
          const dropsEl = document.createElement('div');
          dropsEl.className = 'map-node-drops';
          var labels = enc.guaranteed_drops.map(function(d) {
            if (d === 'artifact') return '\u2B50 artifact';
            if (d === 'legendary_chance') return '\u2728 legendary%';
            return d;
          });
          dropsEl.textContent = labels.join(', ');
          node.appendChild(dropsEl);
        }

        // --- Events: current floor only ---
        if (fi === currentFloor) {
          node.addEventListener('mouseenter', (function(idx) {
            return function() {
              pywebview.api.set_selection(idx).then(handleStateUpdate).catch(console.error);
            };
          })(ni));

          node.addEventListener('click', (function(idx) {
            return function() {
              pywebview.api.set_selection(idx).then(function() {
                pywebview.api.send_action('CONFIRM', -1, -1).then(handleStateUpdate).catch(console.error);
              }).catch(console.error);
            };
          })(ni));
        }

        row.appendChild(node);
      }

      container.appendChild(row);
    }

    // Draw SVG paths after DOM is built
    requestAnimationFrame(function() {
      drawMapPaths(mapData);
    });
  }

  // Update selection highlight on current floor
  const allNodes = container.querySelectorAll('.map-floor-row.current .map-node');
  for (let n = 0; n < allNodes.length; n++) {
    allNodes[n].classList.toggle('selected', n === mapData.selection);
  }
}

function drawMapPaths(mapData) {
  var svg = document.getElementById('map-paths');
  var container = document.getElementById('map-nodes-container');
  if (!svg || !container) return;

  svg.innerHTML = '';

  var containerRect = container.getBoundingClientRect();
  svg.setAttribute('width', containerRect.width);
  svg.setAttribute('height', containerRect.height);

  var floors = mapData.floors || [];
  var currentFloor = mapData.currentFloor;
  var choices = mapData.choices || [];

  // Helper: draw ink-style cubic bezier path between two elements
  function drawInkPath(upperEl, lowerEl, cls, floorIdx) {
    var uRect = upperEl.getBoundingClientRect();
    var lRect = lowerEl.getBoundingClientRect();
    var x1 = lRect.left + lRect.width / 2 - containerRect.left;
    var y1 = lRect.top - containerRect.top;
    var x2 = uRect.left + uRect.width / 2 - containerRect.left;
    var y2 = uRect.top + uRect.height - containerRect.top;

    // Seeded wobble for hand-drawn feel (stable across re-renders)
    var seed = (floorIdx * 127 + Math.round(x1) * 31 + Math.round(x2) * 17) % 100;
    var wobbleX = ((seed % 20) - 10) * 0.8;
    var wobbleY = ((seed % 15) - 7) * 0.5;

    var midY = (y1 + y2) / 2;
    var cp1x = x1 + wobbleX;
    var cp1y = midY + wobbleY;
    var cp2x = x2 - wobbleX;
    var cp2y = midY - wobbleY;

    var d = 'M ' + x1 + ' ' + y1 + ' C ' + cp1x + ' ' + cp1y + ', ' + cp2x + ' ' + cp2y + ', ' + x2 + ' ' + y2;

    var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', d);
    path.classList.add(cls);
    svg.appendChild(path);
  }

  // Connect adjacent floor rows
  for (var fi = 0; fi < floors.length - 1; fi++) {
    var lowerRow = container.querySelector('[data-floor="' + fi + '"].map-floor-row');
    var upperRow = container.querySelector('[data-floor="' + (fi + 1) + '"].map-floor-row');
    if (!lowerRow || !upperRow) continue;

    var lowerNodes = lowerRow.querySelectorAll('.map-node');
    var upperNodes = upperRow.querySelectorAll('.map-node');

    for (var li = 0; li < lowerNodes.length; li++) {
      for (var ui = 0; ui < upperNodes.length; ui++) {
        var cls;
        if (fi < currentFloor - 1) {
          if (choices[fi] === li && choices[fi + 1] === ui) {
            cls = 'path-chosen';
          } else {
            cls = 'path-dimmed';
          }
        } else if (fi === currentFloor - 1 && fi < choices.length) {
          if (choices[fi] === li) {
            cls = 'path-chosen';
          } else {
            cls = 'path-dimmed';
          }
        } else if (fi >= currentFloor) {
          cls = 'path-future';
        } else {
          cls = 'path-dimmed';
        }
        drawInkPath(upperNodes[ui], lowerNodes[li], cls, fi);
      }
    }
  }

  // Paths from last floor to boss node
  if (mapData.hasBoss) {
    var lastFloorIdx = floors.length - 1;
    var lastRow = container.querySelector('[data-floor="' + lastFloorIdx + '"].map-floor-row');
    var bossEl = container.querySelector('.map-boss-node');
    if (lastRow && bossEl) {
      var lastNodes = lastRow.querySelectorAll('.map-node');
      for (var bi = 0; bi < lastNodes.length; bi++) {
        drawInkPath(bossEl, lastNodes[bi], 'path-future', lastFloorIdx);
      }
    }
  }
}

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
      card.style.setProperty('--i', i);
      card.dataset.draftIdx = i;

      let draftPieceType = opt.pieceType || (opt.type === 'combine' ? opt.to : null);

      // Rarity class for draft cards
      if (opt.rarity && opt.rarity !== 'common') {
        card.classList.add('rarity-' + opt.rarity);
      }

      // Legendary reveal animation — enhanced cinematic
      if (opt.rarity === 'legendary' && animate) {
        card.classList.add('legendary-reveal');

        // Screen dim overlay appears before legendary card
        const dim = document.createElement('div');
        dim.className = 'legendary-dim';
        document.body.appendChild(dim);
        setTimeout(() => dim.remove(), 1300);

        // Extra delay so legendary enters after other cards
        card.style.setProperty('--i', options.length + 2);

        // On card land: golden particle burst + shake
        const landDelay = (options.length + 2) * 80 + 400;
        setTimeout(() => {
          triggerShake(2);
          const cardRect = card.getBoundingClientRect();
          if (cardRect && particlesEnabled) {
            const cx = cardRect.left + cardRect.width / 2;
            const cy = cardRect.top + cardRect.height / 2;
            const colors = ['#ffd700', '#ffec80', '#e8c060', '#ffffff'];
            for (let p = 0; p < 12; p++) {
              const angle = Math.random() * Math.PI * 2;
              const speed = 40 + Math.random() * 50;
              const life = 0.4 + Math.random() * 0.3;
              particles.push({
                x: cx, y: cy,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: life, maxLife: life,
                color: colors[p % colors.length],
                size: 2 + Math.random() * 2,
                noGravity: true,
              });
            }
          }
          // Persistent golden pulse glow
          card.classList.add('legendary-pulse-glow');
        }, landDelay);
      }

      const draftRarityClass = (opt.rarity && opt.rarity !== 'common') ? ' rarity-' + opt.rarity : '';

      // Build icon element
      const iconSpan = document.createElement('span');
      iconSpan.className = 'draft-card-icon player-color';
      if (draftPieceType && typeof PieceRenderer !== 'undefined') {
        iconSpan.appendChild(PieceRenderer.create(draftPieceType, 'player', 'draft'));
      } else {
        let icon = '\u2659';
        if (opt.pieceType) icon = pieceChar(opt.pieceType, 'player');
        else if (opt.type === 'combine') icon = pieceChar(opt.to, 'player');
        iconSpan.textContent = icon;
      }

      // Build card structure: stripe + body (icon + desc)
      const stripe = document.createElement('div');
      stripe.className = 'card-rarity-stripe' + draftRarityClass;

      const body = document.createElement('div');
      body.className = 'card-body';
      body.appendChild(iconSpan);

      // Show piece name + ability on card face instead of "Draft a pawn"
      const nameSpan = document.createElement('span');
      nameSpan.className = 'draft-card-name';
      if (opt.pieceType) nameSpan.textContent = pieceDisplayName(opt.pieceType);
      else if (opt.to) nameSpan.textContent = pieceDisplayName(opt.to);
      else nameSpan.textContent = opt.desc;
      body.appendChild(nameSpan);

      const descSpan = document.createElement('span');
      descSpan.className = 'draft-card-desc';
      if (opt.ability) {
        descSpan.textContent = opt.ability;
      } else if (opt.moveDesc) {
        descSpan.textContent = opt.moveDesc;
      } else {
        descSpan.textContent = opt.desc;
      }
      body.appendChild(descSpan);

      card.appendChild(stripe);
      card.appendChild(body);

      // Tooltip — show piece info (move, ability, stats) instead of internal type
      {
        let ttPieceName = '';
        if (opt.pieceType) ttPieceName = pieceDisplayName(opt.pieceType);
        else if (opt.to) ttPieceName = pieceDisplayName(opt.to);
        const ttTitle = ttPieceName || esc(opt.desc);
        let ttHtml = '<div class="tt-title">' + esc(ttTitle) + '</div>';
        if (opt.rarity && opt.rarity !== 'common') {
          ttHtml += '<div class="tt-rarity rarity-' + opt.rarity + '">' + opt.rarity.toUpperCase() + '</div>';
        }
        if (opt.moveDesc) ttHtml += '<div class="tt-move">' + esc(opt.moveDesc) + '</div>';
        if (opt.ability) ttHtml += '<div class="tt-ability">' + esc(opt.ability) + '</div>';
        if (opt.hp || opt.attack) {
          ttHtml += '<div class="tt-stats">HP: ' + (opt.hp || 0) + '  ATK: ' + (opt.attack || 0) + '</div>';
        }
        if (opt.type === 'combine') {
          ttHtml += '<div class="tt-desc">' + esc(opt.desc) + '</div>';
        }
        attachTooltip(card, ttHtml);
      }

      const idx = i;
      card.addEventListener('mouseenter', () => {
        // Immediate client-side selection update
        container.querySelectorAll('.draft-card.selected').forEach(s => s.classList.remove('selected'));
        card.classList.add('selected');
        const skipBtn = document.getElementById('draft-skip-btn');
        if (skipBtn) skipBtn.classList.remove('selected');
        // Sync backend
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
  skipBtn.onmouseenter = () => {
    // Immediate client-side selection update
    container.querySelectorAll('.draft-card.selected').forEach(s => s.classList.remove('selected'));
    skipBtn.classList.add('selected');
    // Sync backend
    if (skipIdx >= 0) pywebview.api.set_selection(skipIdx).then(handleStateUpdate).catch(console.error);
  };
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

    const pmIcon = document.createElement('span');
    pmIcon.className = 'piece-icon player-color';
    if (typeof PieceRenderer !== 'undefined') {
      pmIcon.appendChild(PieceRenderer.create(r.type, 'player', 'roster'));
    } else {
      pmIcon.textContent = pieceChar(r.type, 'player');
    }
    card.appendChild(pmIcon);
    const pmName = document.createElement('span');
    pmName.className = 'piece-name';
    pmName.textContent = pieceDisplayName(r.type) + (r.modifiers.length > 0 ? ' [' + r.modifiers.map(m => m.effect[0]).join('') + ']' : '');
    card.appendChild(pmName);

    // Tooltip
    let pmTt = '<div class="tt-title">' + esc(pieceDisplayName(r.type)) + '</div>';
    if (r.moveDesc) pmTt += '<div class="tt-move">' + esc(r.moveDesc) + '</div>';
    if (r.ability) pmTt += '<div class="tt-ability">' + esc(r.ability) + '</div>';
    if (r.hp || r.attack) pmTt += '<div class="tt-stats">HP: ' + r.hp + '/' + r.maxHp + '  ATK: ' + r.attack + '</div>';
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
      // Immediate client-side selection update
      container.querySelectorAll('.roster-select-card.selected').forEach(s => s.classList.remove('selected'));
      card.classList.add('selected');
      // Sync backend
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
      // Immediate client-side selection update
      container.querySelectorAll('.tarot-select-card.selected').forEach(s => s.classList.remove('selected'));
      card.classList.add('selected');
      // Sync backend
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
  icon.innerHTML = '';
  if (typeof PieceRenderer !== 'undefined') {
    icon.appendChild(PieceRenderer.create(state.bossType || 'king', 'enemy', 'draft'));
  } else {
    icon.textContent = pieceChar(state.bossType || 'king', 'enemy');
  }

  const title = document.getElementById('boss-title');
  title.textContent = 'Boss: ' + (state.bossType || 'Unknown').toUpperCase();

  const mods = document.getElementById('boss-mods');
  const modList = state.bossMods || [];
  mods.innerHTML = modList.length > 0
    ? '<div style="color:#ff8866;font-size:0.85rem">Modifiers: ' + modList.join(', ') + '</div>'
    : '';

  if (animate) {
    // Boss name slam animation
    title.classList.remove('boss-name-slam');
    void title.offsetWidth;
    title.classList.add('boss-name-slam');

    // Mods fade in after name lands
    if (mods.firstChild) {
      mods.classList.remove('boss-mods-fade');
      void mods.offsetWidth;
      mods.classList.add('boss-mods-fade');
    }

    // Heavy screen shake
    triggerShake(4);

    // Red flash
    spawnScreenFlash('#ff2222', 0.25, 350);

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
      card.style.setProperty('--i', i);
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

      // Hover + click to select
      const eloIdx = i;
      card.addEventListener('mouseenter', () => {
        // Immediate client-side selection update
        container.querySelectorAll('.elo-card.selected').forEach(s => s.classList.remove('selected'));
        card.classList.add('selected');
        // Sync backend
        pywebview.api.set_selection(eloIdx).then(handleStateUpdate).catch(console.error);
      });
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

function pieceDisplayName(rawType) {
  if (!rawType) return '';
  return rawType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function buildPieceTooltip(piece) {
  let html = '<div class="tt-title">' + esc(pieceDisplayName(piece.type)) + '</div>';
  if (piece.rarity && piece.rarity !== 'common') {
    html += '<div class="tt-rarity rarity-' + piece.rarity + '">' + piece.rarity.toUpperCase() + '</div>';
  }
  if (piece.moveDesc) {
    html += '<div class="tt-move">' + esc(piece.moveDesc) + '</div>';
  }
  if (piece.ability) {
    html += '<div class="tt-ability">' + esc(piece.ability) + '</div>';
  }
  if (piece.hp != null && piece.maxHp != null) {
    html += '<div class="tt-sep"></div>';
    html += '<div class="tt-stats">HP ' + piece.hp + '/' + piece.maxHp + '  ·  ATK ' + (piece.attack || 0) + '</div>';
  }
  if (piece.modifiers && piece.modifiers.length > 0) {
    html += '<div class="tt-sep"></div>';
    for (const m of piece.modifiers) {
      const modRarityClass = (m.rarity && m.rarity !== 'common') ? ' rarity-' + m.rarity : '';
      html += '<div class="tt-mod' + modRarityClass + '">\u2694 ' + esc(m.name) + '</div>';
      if (m.description) html += '<div class="tt-desc">  ' + esc(m.description) + '</div>';
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
    if (html) html += '<div class="tt-sep"></div>';
    html += '<div class="tt-title">' + esc(cell.cellMod.name) + '</div>';
    if (cell.cellMod.description) html += '<div class="tt-desc">' + esc(cell.cellMod.description) + '</div>';
  }
  if (cell.borderMod) {
    if (html) html += '<div class="tt-sep"></div>';
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
    renderChesticonTab('pieces');
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
      renderChesticonTab(tab.dataset.tab);
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
