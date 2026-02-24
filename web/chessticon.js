/* ================================================================
   chessticon.js — Ammonomicon-style codex (book layout)
   Loaded by both game.html and menu.html
   ================================================================ */

let _codexCache = null;
let _selectedEntry = null;
let _currentTab = 'pieces';

const PIECE_ICONS = {
  'pawn': '\u2659', 'knight': '\u2658', 'bishop': '\u2657',
  'rook': '\u2656', 'queen': '\u2655', 'king': '\u2654',
  'bomb': '\u2738', 'mimic': '?', 'leech': '\u2687',
  'summoner': '\u2726', 'ghost': '\u2601', 'gambler': '\u2660',
  'anchor_piece': '\u2693', 'parasite': '\u2623', 'mirror_piece': '\u25C8',
  'void': '\u25C9', 'phoenix': '\u2600', 'king_rat': '\u2689',
  'assassin': '\u2620', 'berserker_piece': '\u2694', 'cannon': '\u25CE',
  'lancer': '\u2191', 'duelist': '\u2694', 'reaper': '\u2620',
  'wyvern': '\u2682', 'charger': '\u25B6', 'sentinel': '\u2616',
  'healer': '\u2695', 'bard': '\u266A', 'wall': '\u2588',
  'totem': '\u2641', 'decoy': '\u2302', 'shapeshifter': '\u221E',
  'time_mage': '\u231A', 'imp': '\u2666', 'poltergeist': '\u2622',
  'alchemist_piece': '\u2697', 'golem': '\u25A0', 'witch': '\u2605',
  'trickster': '\u2740',
};

// ── Data loading ─────────────────────────────────────────────────────

async function loadCodexData() {
  try {
    _codexCache = await pywebview.api.get_codex_data();
  } catch (e) {
    console.error('Failed to load codex data:', e);
    _codexCache = null;
  }
  return _codexCache;
}

function codexEsc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// ── Rarity helpers ───────────────────────────────────────────────────

function rarityDotColor(rarity) {
  switch (rarity) {
    case 'rare':      return 'rgb(80, 140, 255)';
    case 'epic':      return 'rgb(180, 60, 255)';
    case 'legendary': return 'rgb(255, 200, 50)';
    default:          return '';
  }
}

// ── Tab entry normalization ──────────────────────────────────────────

function getTabEntries(tab) {
  if (!_codexCache) return [];

  switch (tab) {
    case 'pieces': {
      const factionOrder = _codexCache.faction_order || [];
      const factionIcons = _codexCache.faction_icons || {};
      const pieces = _codexCache.pieces || [];
      const entries = [];

      for (const faction of factionOrder) {
        const factionPieces = pieces.filter(p => p.faction === faction);
        if (factionPieces.length === 0) continue;
        entries.push({
          _isGroup: true,
          groupName: faction,
          groupIcon: factionIcons[faction] || '',
        });
        for (const p of factionPieces) {
          entries.push({
            key: p.key,
            name: p.unlocked ? p.name : '???',
            icon: p.unlocked ? (PIECE_ICONS[p.key] || '?') : '?',
            iconColor: '#5082ff',
            rarity: p.rarity,
            locked: !p.unlocked,
            tagline: p.tagline || '',
            _tab: 'pieces',
            _raw: p,
          });
        }
      }
      return entries;
    }

    case 'modifiers': {
      const entries = [];
      const pieceMods = _codexCache.piece_modifiers || [];
      const cellMods = _codexCache.cell_modifiers || [];
      const borderMods = _codexCache.border_modifiers || [];

      if (pieceMods.length) {
        entries.push({ _isGroup: true, groupName: 'Piece Modifiers', groupIcon: '\u2726' });
        for (const m of pieceMods) {
          entries.push({
            key: m.key, name: m.name,
            icon: '\u2726',
            iconColor: 'rgb(' + m.color.join(',') + ')',
            rarity: m.rarity, locked: false,
            tagline: m.tagline || '',
            _tab: 'modifiers', _subtype: 'piece_mod', _raw: m,
          });
        }
      }
      if (cellMods.length) {
        entries.push({ _isGroup: true, groupName: 'Cell Modifiers', groupIcon: '\u25A3' });
        for (const m of cellMods) {
          entries.push({
            key: m.key, name: m.name,
            icon: m.icon || '?',
            iconColor: 'rgb(' + m.color.join(',') + ')',
            rarity: m.rarity, locked: false,
            tagline: m.tagline || '',
            _tab: 'modifiers', _subtype: 'cell_mod', _raw: m,
          });
        }
      }
      if (borderMods.length) {
        entries.push({ _isGroup: true, groupName: 'Border Modifiers', groupIcon: '\u25A3' });
        for (const m of borderMods) {
          entries.push({
            key: m.key, name: m.name,
            icon: m.icon || '\u25A3',
            iconColor: 'rgb(' + m.color.join(',') + ')',
            rarity: m.rarity, locked: false,
            tagline: m.tagline || '',
            _tab: 'modifiers', _subtype: 'border_mod', _raw: m,
          });
        }
      }
      return entries;
    }

    case 'tarots': {
      const tarots = _codexCache.tarots || [];
      return tarots.map(t => ({
        key: t.key, name: t.name,
        icon: t.icon || '\u2605',
        iconColor: 'rgb(' + t.color.join(',') + ')',
        rarity: t.rarity, locked: false,
        tagline: t.tagline || '',
        _tab: 'tarots', _raw: t,
      }));
    }

    case 'artifacts': {
      const artifacts = _codexCache.artifacts || [];
      return artifacts.map(a => ({
        key: a.key, name: a.name,
        icon: a.icon || '\u2726',
        iconColor: 'rgb(' + a.color.join(',') + ')',
        rarity: a.rarity, locked: false,
        tagline: a.tagline || '',
        _tab: 'artifacts', _raw: a,
      }));
    }

    case 'synergies': {
      const synergies = _codexCache.synergies || [];
      return synergies.map(s => ({
        key: s.key, name: s.discovered ? s.name : '???',
        icon: s.discovered ? s.icon : '?',
        iconColor: s.discovered ? 'rgb(' + s.color.join(',') + ')' : '#555',
        rarity: 'common', locked: !s.discovered,
        tagline: s.discovered ? (s.tagline || '') : '',
        _tab: 'synergies', _raw: s,
      }));
    }

    case 'masters': {
      const masters = _codexCache.masters || [];
      return masters.map(m => ({
        key: m.key, name: m.unlocked ? m.name : '???',
        icon: m.unlocked ? m.icon : '?',
        iconColor: m.unlocked ? 'rgb(' + m.color.join(',') + ')' : '#555',
        rarity: 'common', locked: !m.unlocked,
        tagline: m.unlocked ? (m.tagline || '') : '',
        _tab: 'masters', _raw: m,
      }));
    }

    case 'achievements': {
      const achievements = _codexCache.achievements || [];
      const categories = _codexCache.achievement_categories || [];
      const entries = [];

      for (const cat of categories) {
        const catAchs = achievements.filter(a => a.category === cat);
        if (catAchs.length === 0) continue;
        entries.push({
          _isGroup: true,
          groupName: cat.charAt(0).toUpperCase() + cat.slice(1),
          groupIcon: '\u2605',
        });
        for (const a of catAchs) {
          entries.push({
            key: a.key, name: a.name,
            icon: a.icon || '?',
            iconColor: a.earned ? '#e8c060' : '#555',
            rarity: 'common', locked: !a.earned && a.hidden,
            tagline: a.tagline || '',
            _tab: 'achievements', _raw: a,
          });
        }
      }
      return entries;
    }

    default: return [];
  }
}

// ── Render index (left page) ─────────────────────────────────────────

function renderIndex(entries) {
  const container = document.getElementById('codex-index');
  if (!container) return;
  container.innerHTML = '';

  let firstSelectable = null;

  for (const entry of entries) {
    if (entry._isGroup) {
      const header = document.createElement('div');
      header.className = 'index-group-header';
      header.innerHTML =
        '<span class="index-group-icon">' + codexEsc(entry.groupIcon) + '</span>' +
        codexEsc(entry.groupName);
      container.appendChild(header);
      continue;
    }

    const row = document.createElement('div');
    row.className = 'index-entry' + (entry.locked ? ' locked' : '');

    const dotColor = rarityDotColor(entry.rarity);
    const dotHtml = dotColor
      ? '<span class="rarity-dot" style="background:' + dotColor + '"></span>'
      : '';

    row.innerHTML =
      '<span class="index-entry-icon" style="color:' + entry.iconColor + '">' + codexEsc(entry.icon) + '</span>' +
      '<span class="index-entry-name">' + codexEsc(entry.name) + '</span>' +
      dotHtml;

    row.addEventListener('click', () => selectEntry(entry, row));

    container.appendChild(row);

    if (!firstSelectable && !entry.locked) {
      firstSelectable = { entry, row };
    }
  }

  // Auto-select first unlocked entry
  if (firstSelectable) {
    selectEntry(firstSelectable.entry, firstSelectable.row);
  } else {
    // Select first entry even if locked
    const firstRow = container.querySelector('.index-entry');
    if (firstRow && entries.length > 0) {
      const firstEntry = entries.find(e => !e._isGroup);
      if (firstEntry) selectEntry(firstEntry, firstRow);
    }
  }
}

function selectEntry(entry, rowEl) {
  _selectedEntry = entry;

  // Update selection highlight
  const container = document.getElementById('codex-index');
  if (container) {
    container.querySelectorAll('.index-entry.selected').forEach(el => el.classList.remove('selected'));
  }
  if (rowEl) rowEl.classList.add('selected');

  renderDetail(entry);
}

// ── Render detail (right page) ───────────────────────────────────────

function renderDetail(entry) {
  const container = document.getElementById('codex-detail');
  if (!container) return;
  container.innerHTML = '';

  if (!entry || (!entry._raw)) {
    container.innerHTML = '<div class="detail-placeholder">Select an entry</div>';
    return;
  }

  // Locked entry
  if (entry.locked) {
    container.innerHTML =
      '<div class="detail-header">' +
        '<span class="detail-icon">?</span>' +
        '<div class="detail-name">???</div>' +
      '</div>' +
      '<div class="detail-section">' +
        '<div class="detail-section-body locked-text">Not yet discovered</div>' +
      '</div>';
    return;
  }

  // Header
  const headerHtml =
    '<div class="detail-header">' +
      '<span class="detail-icon" style="color:' + entry.iconColor + '">' + codexEsc(entry.icon) + '</span>' +
      '<div class="detail-name">' + codexEsc(entry.name) + '</div>' +
      (entry.tagline ? '<div class="detail-tagline">"' + codexEsc(entry.tagline) + '"</div>' : '') +
      (entry.rarity && entry.rarity !== 'common'
        ? '<span class="detail-rarity ' + entry.rarity + '">' + entry.rarity + '</span>'
        : '') +
    '</div>';

  // Build tab-specific sections
  const sectionsHtml = buildDetailSections(entry);

  container.innerHTML = headerHtml + sectionsHtml;
}

function buildDetailSections(entry) {
  const raw = entry._raw;
  const tab = entry._tab;
  let html = '';

  switch (tab) {
    case 'pieces': {
      // Stats grid
      html += '<div class="detail-stats">';
      html += '<span class="detail-stat-label">HP</span><span class="detail-stat-value">' + raw.hp + '</span>';
      html += '<span class="detail-stat-label">ATK</span><span class="detail-stat-value">' + raw.attack + '</span>';
      html += '<span class="detail-stat-label">Faction</span><span class="detail-stat-value">' + codexEsc(raw.faction) + '</span>';
      html += '</div>';

      if (raw.move) {
        html += '<div class="detail-section">';
        html += '<div class="detail-section-title">Movement</div>';
        html += '<div class="detail-section-body">' + codexEsc(raw.move) + '</div>';
        html += '</div>';
      }
      if (raw.ability) {
        html += '<div class="detail-section">';
        html += '<div class="detail-section-title">Ability</div>';
        html += '<div class="detail-section-body">' + codexEsc(raw.ability) + '</div>';
        html += '</div>';
      }
      break;
    }

    case 'modifiers': {
      const subtype = entry._subtype;
      if (subtype === 'piece_mod') {
        html += '<div class="detail-section">';
        html += '<div class="detail-section-title">Effect</div>';
        html += '<div class="detail-section-body">' + codexEsc(raw.description) + '</div>';
        html += '</div>';
      } else {
        // cell_mod or border_mod
        html += '<div class="detail-section">';
        html += '<div class="detail-section-title">Effect</div>';
        html += '<div class="detail-section-body">' + codexEsc(raw.description) + '</div>';
        html += '</div>';
      }
      break;
    }

    case 'tarots': {
      html += '<div class="detail-stats">';
      html += '<span class="detail-stat-label">Cost</span><span class="detail-stat-value">' + raw.cost + 'g</span>';
      html += '</div>';
      html += '<div class="detail-section">';
      html += '<div class="detail-section-title">Effect</div>';
      html += '<div class="detail-section-body">' + codexEsc(raw.description) + '</div>';
      html += '</div>';
      break;
    }

    case 'artifacts': {
      html += '<div class="detail-stats">';
      html += '<span class="detail-stat-label">Cost</span><span class="detail-stat-value">' + raw.cost + 'g</span>';
      html += '</div>';
      html += '<div class="detail-section">';
      html += '<div class="detail-section-title">Effect</div>';
      html += '<div class="detail-section-body">' + codexEsc(raw.description) + '</div>';
      html += '</div>';
      break;
    }

    case 'synergies': {
      html += '<div class="detail-section">';
      html += '<div class="detail-section-title">Effect</div>';
      html += '<div class="detail-section-body">' + codexEsc(raw.description) + '</div>';
      html += '</div>';

      if (raw.required_pieces && raw.required_pieces.length > 0) {
        html += '<div class="detail-section">';
        html += '<div class="detail-section-title">Required Pieces</div>';
        html += '<div class="detail-pieces-list">';
        for (const p of raw.required_pieces) {
          html += '<span class="detail-piece-tag">' + codexEsc(p.replace(/_/g, ' ')) + '</span>';
        }
        html += '</div></div>';
      }
      break;
    }

    case 'masters': {
      html += '<div class="detail-section">';
      html += '<div class="detail-section-title">Starting Bonus</div>';
      html += '<div class="detail-section-body">' + codexEsc(raw.description) + '</div>';
      html += '</div>';

      if (raw.passive) {
        html += '<div class="detail-section">';
        html += '<div class="detail-section-title">Passive</div>';
        html += '<div class="detail-section-body passive">\u25B2 ' + codexEsc(raw.passive) + '</div>';
        html += '</div>';
      }
      if (raw.drawback) {
        html += '<div class="detail-section">';
        html += '<div class="detail-section-title">Drawback</div>';
        html += '<div class="detail-section-body drawback">\u25BC ' + codexEsc(raw.drawback) + '</div>';
        html += '</div>';
      }
      break;
    }

    case 'achievements': {
      html += '<div class="detail-section">';
      html += '<div class="detail-section-title">Condition</div>';
      html += '<div class="detail-section-body">' + codexEsc(raw.description) + '</div>';
      html += '</div>';

      if (raw.unlocks && raw.unlocks.length > 0) {
        html += '<div class="detail-section">';
        html += '<div class="detail-section-title">Unlocks</div>';
        html += '<div class="detail-pieces-list">';
        for (const u of raw.unlocks) {
          html += '<span class="detail-piece-tag">' + codexEsc(u.type) + ': ' + codexEsc(u.key.replace(/_/g, ' ')) + '</span>';
        }
        html += '</div></div>';
      }

      html += '<div class="detail-section">';
      html += '<div class="detail-section-title">Status</div>';
      if (raw.earned) {
        html += '<div class="detail-section-body"><span class="ach-status earned">\u2713 Earned</span></div>';
      } else {
        html += '<div class="detail-section-body"><span class="ach-status locked">\u2717 Locked</span></div>';
      }
      html += '</div>';

      html += '<div class="detail-stats">';
      html += '<span class="detail-stat-label">Category</span><span class="detail-stat-value">' + codexEsc(raw.category) + '</span>';
      html += '</div>';
      break;
    }
  }

  return html;
}

// ── Tab counts & completion ──────────────────────────────────────────

function updateTabCounts() {
  if (!_codexCache) return;

  const tabs = document.querySelectorAll('.chessticon-tab');
  for (const tabBtn of tabs) {
    const tabName = tabBtn.getAttribute('data-tab');
    const countSpan = tabBtn.querySelector('.tab-count');
    if (!countSpan) continue;

    const counts = getTabCounts(tabName);
    if (counts) {
      countSpan.textContent = counts.discovered + '/' + counts.total;
    }
  }
}

function getTabCounts(tab) {
  if (!_codexCache) return null;

  switch (tab) {
    case 'pieces': {
      const pieces = _codexCache.pieces || [];
      return { discovered: pieces.filter(p => p.unlocked).length, total: pieces.length };
    }
    case 'modifiers': {
      const pm = (_codexCache.piece_modifiers || []).length;
      const cm = (_codexCache.cell_modifiers || []).length;
      const bm = (_codexCache.border_modifiers || []).length;
      const total = pm + cm + bm;
      return { discovered: total, total: total }; // always visible
    }
    case 'tarots': {
      const tarots = _codexCache.tarots || [];
      return { discovered: tarots.length, total: tarots.length };
    }
    case 'artifacts': {
      const artifacts = _codexCache.artifacts || [];
      return { discovered: artifacts.length, total: artifacts.length };
    }
    case 'synergies': {
      const synergies = _codexCache.synergies || [];
      return { discovered: synergies.filter(s => s.discovered).length, total: synergies.length };
    }
    case 'masters': {
      const masters = _codexCache.masters || [];
      return { discovered: masters.filter(m => m.unlocked).length, total: masters.length };
    }
    case 'achievements': {
      const achs = _codexCache.achievements || [];
      return { discovered: achs.filter(a => a.earned).length, total: achs.length };
    }
    default: return null;
  }
}

function updateCompletionCounter() {
  if (!_codexCache) return;

  const el = document.getElementById('codex-completion');
  if (!el) return;

  let discovered = 0;
  let total = 0;

  const allTabs = ['pieces', 'modifiers', 'tarots', 'artifacts', 'synergies', 'masters', 'achievements'];
  for (const tab of allTabs) {
    const counts = getTabCounts(tab);
    if (counts) {
      discovered += counts.discovered;
      total += counts.total;
    }
  }

  const pct = total > 0 ? Math.round((discovered / total) * 100) : 0;
  el.textContent = pct + '% Complete';
}

// ── Main render entry point ──────────────────────────────────────────

function renderChesticonTab(tab) {
  _currentTab = tab;
  _selectedEntry = null;

  const entries = getTabEntries(tab);
  renderIndex(entries);

  // Reset detail
  const detail = document.getElementById('codex-detail');
  if (detail && !_selectedEntry) {
    detail.innerHTML = '<div class="detail-placeholder">Select an entry</div>';
  }

  updateTabCounts();
  updateCompletionCounter();

  // Track codex tab view for achievements
  try { pywebview.api.mark_codex_viewed(tab); } catch (e) { /* ignore */ }
}
