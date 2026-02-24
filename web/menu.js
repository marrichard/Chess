/* Menu bridge logic — pywebview JS API integration */

let focusIndex = 0;
let currentPhase = 'main'; // 'main', 'difficulty', 'master', 'settings', 'chessticon'
let pendingAction = ''; // 'tournament' or 'free_play'
let pendingDifficulty = 'basic';

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
  } else if (currentPhase === 'master') {
    const cards = Array.from(document.querySelectorAll('#master-cards .master-card'));
    const back = document.getElementById('btn-master-back');
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
  document.getElementById('master-menu').classList.remove('active');
  document.getElementById('main-menu').classList.add('active');
  document.getElementById('settings-overlay').className = 'overlay-hidden';
  document.getElementById('chessticon-overlay').className = 'overlay-hidden';
  document.getElementById('achievements-overlay').className = 'overlay-hidden';
  updateFocus();
}

async function showMasterSelect(action, difficulty) {
  pendingAction = action;
  pendingDifficulty = difficulty || 'basic';
  currentPhase = 'master';
  focusIndex = 0;

  // Hide other phases
  document.getElementById('main-menu').classList.remove('active');
  document.getElementById('difficulty-menu').classList.remove('active');
  document.getElementById('master-menu').classList.add('active');

  // Load masters from backend
  try {
    const masters = await pywebview.api.get_masters();
    renderMasterCards(masters);
  } catch (e) {
    console.error('Failed to load masters:', e);
  }
  updateFocus();
}

function renderMasterCards(masters) {
  const container = document.getElementById('master-cards');
  container.innerHTML = '';
  for (const m of masters) {
    const card = document.createElement('button');
    card.className = 'master-card' + (m.unlocked ? '' : ' locked') + (m.selected ? ' selected' : '');
    const [r, g, b] = m.color;
    card.innerHTML = `
      <div class="master-icon" style="color: rgb(${r},${g},${b})">${m.icon}</div>
      <div class="master-info">
        <div class="master-name" style="color: rgb(${r},${g},${b})">${m.name}</div>
        <div class="master-desc">${m.description}</div>
        <div class="master-passive">&#9650; ${m.passive}</div>
        <div class="master-drawback">&#9660; ${m.drawback}</div>
      </div>
      ${m.unlocked ? '' : '<span class="lock-overlay">&#128274;</span>'}
    `;
    card.addEventListener('mouseenter', () => {
      if (currentPhase !== 'master') return;
      const cards = getVisibleCards();
      const idx = cards.indexOf(card);
      if (idx >= 0) { focusIndex = idx; updateFocus(); }
    });
    card.addEventListener('click', async () => {
      if (!m.unlocked) return;
      await pywebview.api.select_master(m.key);
      pywebview.api.start_game(pendingAction, pendingDifficulty);
    });
    container.appendChild(card);
  }
}

function showMasterBack() {
  document.getElementById('master-menu').classList.remove('active');
  if (pendingAction === 'tournament') {
    currentPhase = 'difficulty';
    document.getElementById('difficulty-menu').classList.add('active');
  } else {
    currentPhase = 'main';
    document.getElementById('main-menu').classList.add('active');
  }
  focusIndex = 0;
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

// === Achievements overlay ===
let _achievementsData = null;
let _achievementProgress = null;
let _currentAchTab = 'all';

async function openMenuAchievements() {
  currentPhase = 'achievements';
  document.getElementById('achievements-overlay').className = 'overlay-visible';
  try {
    const [achData, progress] = await Promise.all([
      pywebview.api.get_achievements(),
      pywebview.api.get_achievement_progress(),
    ]);
    _achievementsData = achData;
    _achievementProgress = {};
    for (const p of progress) {
      _achievementProgress[p.key] = p;
    }
    document.getElementById('ach-counter').textContent =
      achData.unlocked_count + ' / ' + achData.total_count;
    renderAchievementsTab(_currentAchTab);
  } catch (e) {
    console.error('Failed to load achievements:', e);
  }
}

function closeMenuAchievements() {
  document.getElementById('achievements-overlay').className = 'overlay-hidden';
  currentPhase = 'main';
  updateFocus();
}

function renderAchievementsTab(tab) {
  const container = document.getElementById('achievements-grid');
  if (!container || !_achievementsData) return;
  container.innerHTML = '';
  _currentAchTab = tab;

  const achievements = _achievementsData.achievements || [];
  const filtered = tab === 'all'
    ? achievements
    : achievements.filter(a => a.category === tab);

  for (const ach of filtered) {
    const card = document.createElement('div');
    card.className = 'achievement-card';
    if (ach.earned) card.classList.add('earned');
    else if (ach.hidden && !ach.earned) card.classList.add('locked');

    // Build reward text
    let rewardHtml = '';
    if (ach.unlocks && ach.unlocks.length > 0) {
      const u = ach.unlocks[0];
      rewardHtml = '<span class="ach-reward">Unlocks: ' + escMenu(u.type) + ' — ' + escMenu(u.key) + '</span>';
    }

    // Progress bar for stat-based achievements
    let progressHtml = '';
    const prog = _achievementProgress[ach.key];
    if (prog && !ach.earned) {
      const pct = prog.target > 0 ? Math.min(100, (prog.current / prog.target) * 100) : 0;
      progressHtml =
        '<div class="ach-progress"><div class="ach-progress-fill" style="width:' + pct + '%"></div></div>' +
        '<span class="ach-progress-text">' + prog.current + ' / ' + prog.target + '</span>';
    }

    card.innerHTML =
      '<span class="ach-icon">' + escMenu(ach.icon) + '</span>' +
      '<span class="ach-name">' + escMenu(ach.name) + '</span>' +
      '<span class="ach-desc">' + escMenu(ach.description) + '</span>' +
      rewardHtml +
      progressHtml;

    container.appendChild(card);
  }
}

function escMenu(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// === Chessticon overlay ===
function openMenuChessticon() {
  currentPhase = 'chessticon';
  document.getElementById('chessticon-overlay').className = 'overlay-visible';
  loadCodexData().then(() => {
    renderChesticonTab('pieces');
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

  // Achievement count
  const achDesc = document.getElementById('achievement-desc');
  if (achDesc) {
    achDesc.textContent = (data.achievement_count || 0) + ' / ' + (data.achievement_total || 0) + ' unlocked';
  }

  // Load settings
  if (data.settings) {
    menuBattleSpeed = data.settings.battle_speed || 400;
    menuParticlesEnabled = data.settings.particles_enabled !== false;
  }

  updateFocus();
}

// === Mouseenter handlers — persistent selection like keyboard ===
document.querySelectorAll('#main-menu .menu-card').forEach(card => {
  card.addEventListener('mouseenter', () => {
    if (currentPhase !== 'main') return;
    const cards = getVisibleCards();
    const idx = cards.indexOf(card);
    if (idx >= 0) { focusIndex = idx; updateFocus(); }
  });
});

document.querySelectorAll('#difficulty-menu .difficulty-card').forEach(card => {
  card.addEventListener('mouseenter', () => {
    if (currentPhase !== 'difficulty') return;
    const cards = getVisibleCards();
    const idx = cards.indexOf(card);
    if (idx >= 0) { focusIndex = idx; updateFocus(); }
  });
});

document.getElementById('btn-quit').addEventListener('mouseenter', () => {
  if (currentPhase !== 'main') return;
  const cards = getVisibleCards();
  const idx = cards.indexOf(document.getElementById('btn-quit'));
  if (idx >= 0) { focusIndex = idx; updateFocus(); }
});

document.getElementById('btn-back').addEventListener('mouseenter', () => {
  if (currentPhase !== 'difficulty') return;
  const cards = getVisibleCards();
  const idx = cards.indexOf(document.getElementById('btn-back'));
  if (idx >= 0) { focusIndex = idx; updateFocus(); }
});

document.getElementById('btn-master-back').addEventListener('mouseenter', () => {
  if (currentPhase !== 'master') return;
  const cards = getVisibleCards();
  const idx = cards.indexOf(document.getElementById('btn-master-back'));
  if (idx >= 0) { focusIndex = idx; updateFocus(); }
});

// === Click handlers ===
document.querySelectorAll('#main-menu .menu-card').forEach(card => {
  card.addEventListener('click', () => {
    const action = card.dataset.action;
    if (action === 'tournament') {
      showDifficulty();
    } else if (action === 'continue') {
      pywebview.api.start_game('continue');
    } else if (action === 'free_play') {
      showMasterSelect('free_play');
    } else if (action === 'elo_shop') {
      pywebview.api.start_game('elo_shop');
    } else if (action === 'achievements') {
      openMenuAchievements();
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
    showMasterSelect('tournament', diff);
  });
});

document.getElementById('btn-quit').addEventListener('click', () => {
  pywebview.api.quit_game();
});

document.getElementById('btn-back').addEventListener('click', () => {
  showMainMenu();
});

document.getElementById('btn-master-back').addEventListener('click', () => {
  showMasterBack();
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

// === Achievements overlay controls ===
document.querySelectorAll('#ach-tabs .achievement-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('#ach-tabs .achievement-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    renderAchievementsTab(tab.dataset.achTab);
  });
});

document.getElementById('menu-ach-back').addEventListener('click', () => {
  closeMenuAchievements();
});

// === Chessticon overlay controls ===
document.querySelectorAll('#chessticon-overlay .chessticon-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('#chessticon-overlay .chessticon-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    renderChesticonTab(tab.dataset.tab);
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
    if (currentPhase === 'achievements') {
      closeMenuAchievements();
      return;
    }
    if (currentPhase === 'chessticon') {
      closeMenuChessticon();
      return;
    }
    if (currentPhase === 'settings') {
      closeMenuSettings();
      return;
    }
    if (currentPhase === 'master') {
      showMasterBack();
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
  if (currentPhase === 'settings' || currentPhase === 'chessticon' || currentPhase === 'achievements') return;

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
