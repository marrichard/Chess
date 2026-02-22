/* ================================================================
   chessticon.js — Shared Chessticon codex rendering
   Loaded by both game.html and menu.html
   ================================================================ */

let _codexCache = null;

const PIECE_ICONS = {
  'pawn': '\u2659', 'knight': '\u2658', 'bishop': '\u2657',
  'rook': '\u2656', 'queen': '\u2655', 'king': '\u2654',
  'bomb': '\u2738', 'mimic': '?', 'leech': '\u2687',
  'summoner': '\u2726', 'ghost': '\u2601', 'gambler': '\u2660',
  'anchor_piece': '\u2693', 'parasite': '\u2623', 'mirror_piece': '\u25C8',
  'void': '\u25C9', 'phoenix': '\u2600', 'king_rat': '\u2689',
};

async function loadCodexData() {
  try {
    _codexCache = await pywebview.api.get_codex_data();
  } catch (e) {
    console.error('Failed to load codex data:', e);
    _codexCache = null;
  }
  return _codexCache;
}

function renderChesticonTab(containerId, tab) {
  const container = document.getElementById(containerId);
  if (!container || !_codexCache) return;
  container.innerHTML = '';

  switch (tab) {
    case 'pieces': renderPiecesTab(container); break;
    case 'modifiers': renderModifiersTab(container); break;
    case 'tarots': renderTarotsTab(container); break;
    case 'artifacts': renderArtifactsTab(container); break;
    case 'synergies': renderSynergiesTab(container); break;
  }
}

function codexEsc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

function renderPiecesTab(container) {
  const pieces = _codexCache.pieces || [];
  for (const p of pieces) {
    const card = document.createElement('div');
    card.className = 'codex-card' + (p.unlocked ? '' : ' locked');

    const icon = PIECE_ICONS[p.key] || '?';
    const name = p.unlocked ? codexEsc(p.name) : '???';
    const stats = p.unlocked
      ? 'HP: ' + p.hp + ' | ATK: ' + p.attack
      : '???';

    card.innerHTML =
      '<span class="codex-icon" style="color:#5082ff">' + icon + '</span>' +
      '<span class="codex-name">' + name + '</span>' +
      '<span class="codex-stats">' + stats + '</span>';

    container.appendChild(card);
  }
}

function renderModifiersTab(container) {
  // Cell modifiers
  const cellHeader = document.createElement('div');
  cellHeader.className = 'codex-subheader';
  cellHeader.textContent = 'Cell Modifiers';
  container.appendChild(cellHeader);

  const cellMods = _codexCache.cell_modifiers || [];
  for (const m of cellMods) {
    const card = document.createElement('div');
    card.className = 'codex-card';
    card.innerHTML =
      '<span class="codex-icon" style="color:rgb(' + m.color.join(',') + ')">' + codexEsc(m.icon) + '</span>' +
      '<span class="codex-name">' + codexEsc(m.name) + '</span>' +
      '<span class="codex-desc">' + codexEsc(m.description) + '</span>';
    container.appendChild(card);
  }

  // Border modifiers
  const borderHeader = document.createElement('div');
  borderHeader.className = 'codex-subheader';
  borderHeader.textContent = 'Border Modifiers';
  container.appendChild(borderHeader);

  const borderMods = _codexCache.border_modifiers || [];
  for (const m of borderMods) {
    const card = document.createElement('div');
    card.className = 'codex-card';
    card.innerHTML =
      '<span class="codex-icon" style="color:rgb(' + m.color.join(',') + ')">\u25A3</span>' +
      '<span class="codex-name">' + codexEsc(m.name) + '</span>' +
      '<span class="codex-desc">' + codexEsc(m.description) + '</span>';
    container.appendChild(card);
  }
}

function renderTarotsTab(container) {
  const tarots = _codexCache.tarots || [];
  for (const t of tarots) {
    const card = document.createElement('div');
    card.className = 'codex-card';
    card.innerHTML =
      '<span class="codex-icon" style="color:rgb(' + t.color.join(',') + ')">' + codexEsc(t.icon) + '</span>' +
      '<span class="codex-name">' + codexEsc(t.name) + '</span>' +
      '<span class="codex-desc">' + codexEsc(t.description) + '</span>' +
      '<span class="codex-stats">' + t.cost + 'g</span>';
    container.appendChild(card);
  }
}

function renderArtifactsTab(container) {
  const artifacts = _codexCache.artifacts || [];
  for (const a of artifacts) {
    const card = document.createElement('div');
    card.className = 'codex-card';
    card.innerHTML =
      '<span class="codex-rarity ' + codexEsc(a.rarity) + '">' + codexEsc(a.rarity) + '</span>' +
      '<span class="codex-icon" style="color:rgb(' + a.color.join(',') + ')">' + codexEsc(a.icon) + '</span>' +
      '<span class="codex-name">' + codexEsc(a.name) + '</span>' +
      '<span class="codex-desc">' + codexEsc(a.description) + '</span>';
    container.appendChild(card);
  }
}

function renderSynergiesTab(container) {
  const synergies = _codexCache.synergies || [];
  for (const s of synergies) {
    const card = document.createElement('div');
    card.className = 'codex-card' + (s.discovered ? '' : ' locked');

    const name = s.discovered ? codexEsc(s.name) : '???';
    const desc = s.discovered ? codexEsc(s.description) : 'Not yet discovered';
    const pieces = s.discovered
      ? s.required_pieces.map(p => codexEsc(p.replace('_', ' '))).join(', ')
      : '???';

    card.innerHTML =
      '<span class="codex-icon" style="color:rgb(' + s.color.join(',') + ')">' + codexEsc(s.icon) + '</span>' +
      '<span class="codex-name">' + name + '</span>' +
      '<span class="codex-desc">' + desc + '</span>' +
      '<span class="codex-stats">Requires: ' + pieces + '</span>';

    container.appendChild(card);
  }
}
