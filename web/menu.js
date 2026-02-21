/* Menu bridge logic — pywebview JS API integration */

let focusIndex = 0;
let currentPhase = 'main'; // 'main' or 'difficulty'

function getVisibleCards() {
  if (currentPhase === 'main') {
    const cards = Array.from(document.querySelectorAll('#main-menu .menu-card'));
    const quit = document.getElementById('btn-quit');
    // Only include visible cards
    const visible = cards.filter(c => c.style.display !== 'none');
    visible.push(quit);
    return visible;
  } else {
    const cards = Array.from(document.querySelectorAll('#difficulty-menu .difficulty-card'));
    const back = document.getElementById('btn-back');
    // Only include non-locked cards
    const visible = cards.filter(c => !c.classList.contains('locked'));
    visible.push(back);
    return visible;
  }
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
  updateFocus();
}

function activateCurrent() {
  const cards = getVisibleCards();
  if (cards.length === 0) return;
  cards[focusIndex].click();
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

// === Keyboard navigation ===
document.addEventListener('keydown', (e) => {
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
    case 'Escape':
      e.preventDefault();
      if (currentPhase === 'difficulty') {
        showMainMenu();
      } else {
        pywebview.api.quit_game();
      }
      break;
  }
});

// === Pywebview ready ===
window.addEventListener('pywebviewready', async () => {
  const data = await pywebview.api.get_save_data();
  populateMenu(data);
});
