/* Menu bridge logic — pywebview JS API integration */

let focusIndex = 0;
let currentPhase = 'main'; // 'main', 'difficulty', 'settings', 'chessticon'

// Settings state
let menuBattleSpeed = 400;
let menuParticlesEnabled = true;
const SPEED_STEPS = [200, 300, 400, 600, 800, 1000];

function getVisibleCards() {
  if (currentPhase === 'main') {
    const cards = Array.from(document.querySelectorAll('#main-menu .menu-card'));
    const quit = document.getElementById('btn-quit');
    // Only include visible cards
    const visible = cards.filter(c => c.style.display !== 'none');
    visible.push(quit);
    return visible;
  } else if (currentPhase === 'difficulty') {
    const cards = Array.from(document.querySelectorAll('#difficulty-menu .difficulty-card'));
    const back = document.getElementById('btn-back');
    // Only include non-locked cards
    const visible = cards.filter(c => !c.classList.contains('locked'));
    visible.push(back);
    return visible;
  }
  // settings and chessticon phases have no card navigation
  return [];
}

function updateFocus() {
  // Clear all focused states
  document.querySelectorAll('.focused').forEach(el => el.classList.remove('focused'));
  const cards = getVisibleCards();
  if (cards.length > 0) {
    focusIndex = Math.max(0, Math.min(focusIndex, cards.length - 1));
    cards[focusIndex].classList.add('focused');
    cards[focusIndex].scrollIntoView({ block: 'nearest' });
  }
}

function showDifficulty() {
  currentPhase = 'difficulty';
  focusIndex = 0;
  document.getElementById('main-menu').classList.remove('active');
  document.getElementById('difficulty-menu').classList.add('active');
  updateFocus();
}

function showMainMenu() {
  currentPhase = 'main';
  focusIndex = 0;
  document.getElementById('difficulty-menu').classList.remove('active');
  document.getElementById('main-menu').classList.add('active');
  document.getElementById('settings-overlay').className = 'overlay-hidden';
  document.getElementById('chessticon-overlay').className = 'overlay-hidden';
  updateFocus();
}

function activateCurrent() {
  const cards = getVisibleCards();
  if (cards.length === 0) return;
  cards[focusIndex].click();
}

// === Settings overlay ===
function openMenuSettings() {
  currentPhase = 'settings';
  document.getElementById('settings-overlay').className = 'overlay-visible';
  updateMenuSpeedDisplay();
  updateMenuParticlesToggle();
}

function closeMenuSettings() {
  document.getElementById('settings-overlay').className = 'overlay-hidden';
  currentPhase = 'main';
  updateFocus();
}

function updateMenuSpeedDisplay() {
  const el = document.getElementById('menu-speed-value');
  if (el) el.textContent = menuBattleSpeed + 'ms';
}

function updateMenuParticlesToggle() {
  const btn = document.getElementById('menu-particles-toggle');
  if (!btn) return;
  btn.textContent = menuParticlesEnabled ? 'ON' : 'OFF';
  btn.className = 'toggle-btn' + (menuParticlesEnabled ? '' : ' off');
}

// === Chessticon overlay ===
function openMenuChessticon() {
  currentPhase = 'chessticon';
  document.getElementById('chessticon-overlay').className = 'overlay-visible';
  loadCodexData().then(() => {
    renderChesticonTab('chessticon-content', 'pieces');
    document.querySelectorAll('#chessticon-overlay .chessticon-tab').forEach(t => t.classList.remove('active'));
    const first = document.querySelector('#chessticon-overlay .chessticon-tab[data-tab="pieces"]');
    if (first) first.classList.add('active');
  });
}

function closeMenuChessticon() {
  document.getElementById('chessticon-overlay').className = 'overlay-hidden';
  currentPhase = 'main';
  updateFocus();
}

// === Population from save data ===
function populateMenu(data) {
  // ELO
  document.getElementById('elo-badge').textContent = '\u25C6 ' + data.elo + ' ELO';

  // Stats
  const stats = data.stats || {};
  document.getElementById('stat-runs').textContent = (stats.tournaments_completed || 0) + ' Runs';
  document.getElementById('stat-wins').textContent = (stats.tournaments_won || 0) + ' Wins';
  document.getElementById('stat-bosses').textContent = (stats.bosses_beaten || 0) + ' Bosses';

  // Continue button
  const btnContinue = document.getElementById('btn-continue');
  if (data.has_continue) {
    btnContinue.style.display = '';
    document.getElementById('continue-desc').textContent = 'Resume wave ' + data.continue_wave;
  } else {
    btnContinue.style.display = 'none';
  }

  // Grandmaster lock
  const gmBtn = document.getElementById('btn-grandmaster');
  if (!data.grandmaster_unlocked) {
    gmBtn.classList.add('locked');
  } else {
    gmBtn.classList.remove('locked');
  }

  // Load settings
  if (data.settings) {
    menuBattleSpeed = data.settings.battle_speed || 400;
    menuParticlesEnabled = data.settings.particles_enabled !== false;
  }

  updateFocus();
}

// === Click handlers ===
document.querySelectorAll('#main-menu .menu-card').forEach(card => {
  card.addEventListener('click', () => {
    const action = card.dataset.action;
    if (action === 'tournament') {
      showDifficulty();
    } else if (action === 'continue') {
      pywebview.api.start_game('continue');
    } else if (action === 'free_play') {
      pywebview.api.start_game('free_play');
    } else if (action === 'elo_shop') {
      pywebview.api.start_game('elo_shop');
    } else if (action === 'chessticon') {
      openMenuChessticon();
    } else if (action === 'settings') {
      openMenuSettings();
    }
  });
});

document.querySelectorAll('#difficulty-menu .difficulty-card').forEach(card => {
  card.addEventListener('click', () => {
    if (card.classList.contains('locked')) return;
    const diff = card.dataset.difficulty;
    pywebview.api.start_game('tournament', diff);
  });
});

document.getElementById('btn-quit').addEventListener('click', () => {
  pywebview.api.quit_game();
});

document.getElementById('btn-back').addEventListener('click', () => {
  showMainMenu();
});

// === Settings overlay controls ===
document.getElementById('menu-speed-down').addEventListener('click', () => {
  const idx = SPEED_STEPS.indexOf(menuBattleSpeed);
  if (idx > 0) {
    menuBattleSpeed = SPEED_STEPS[idx - 1];
  } else if (idx === -1) {
    for (let i = SPEED_STEPS.length - 1; i >= 0; i--) {
      if (SPEED_STEPS[i] < menuBattleSpeed) { menuBattleSpeed = SPEED_STEPS[i]; break; }
    }
  }
  updateMenuSpeedDisplay();
  pywebview.api.update_settings({ battle_speed: menuBattleSpeed });
});

document.getElementById('menu-speed-up').addEventListener('click', () => {
  const idx = SPEED_STEPS.indexOf(menuBattleSpeed);
  if (idx >= 0 && idx < SPEED_STEPS.length - 1) {
    menuBattleSpeed = SPEED_STEPS[idx + 1];
  } else if (idx === -1) {
    for (let i = 0; i < SPEED_STEPS.length; i++) {
      if (SPEED_STEPS[i] > menuBattleSpeed) { menuBattleSpeed = SPEED_STEPS[i]; break; }
    }
  }
  updateMenuSpeedDisplay();
  pywebview.api.update_settings({ battle_speed: menuBattleSpeed });
});

document.getElementById('menu-particles-toggle').addEventListener('click', () => {
  menuParticlesEnabled = !menuParticlesEnabled;
  updateMenuParticlesToggle();
  pywebview.api.update_settings({ particles_enabled: menuParticlesEnabled });
});

document.getElementById('menu-settings-back').addEventListener('click', () => {
  closeMenuSettings();
});

// === Chessticon overlay controls ===
document.querySelectorAll('#chessticon-overlay .chessticon-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('#chessticon-overlay .chessticon-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    renderChesticonTab('chessticon-content', tab.dataset.tab);
  });
});

document.getElementById('menu-codex-back').addEventListener('click', () => {
  closeMenuChessticon();
});

// === Keyboard navigation ===
document.addEventListener('keydown', (e) => {
  // Handle overlay ESC
  if (e.key === 'Escape') {
    e.preventDefault();
    if (currentPhase === 'chessticon') {
      closeMenuChessticon();
      return;
    }
    if (currentPhase === 'settings') {
      closeMenuSettings();
      return;
    }
    if (currentPhase === 'difficulty') {
      showMainMenu();
      return;
    }
    pywebview.api.quit_game();
    return;
  }

  // Block card nav when in overlay
  if (currentPhase === 'settings' || currentPhase === 'chessticon') return;

  const cards = getVisibleCards();
  if (cards.length === 0) return;

  switch (e.key) {
    case 'ArrowUp':
    case 'ArrowLeft':
      e.preventDefault();
      focusIndex = (focusIndex - 1 + cards.length) % cards.length;
      updateFocus();
      break;
    case 'ArrowDown':
    case 'ArrowRight':
      e.preventDefault();
      focusIndex = (focusIndex + 1) % cards.length;
      updateFocus();
      break;
    case 'Enter':
      e.preventDefault();
      activateCurrent();
      break;
  }
});

// === Pywebview ready ===
window.addEventListener('pywebviewready', async () => {
  const data = await pywebview.api.get_save_data();
  populateMenu(data);
});
