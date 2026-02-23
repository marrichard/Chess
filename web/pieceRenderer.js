/* ================================================================
   pieceRenderer.js — Abstraction layer for piece rendering
   Supports SVG mode (inline <svg>) and IMG mode (sprite sheets).
   Switch modes: PieceRenderer.setMode('svg') or PieceRenderer.setMode('img')
   ================================================================ */

const PieceRenderer = {
  mode: 'svg', // 'svg' | 'img'

  // Size presets in px
  SIZES: {
    board: 56,
    roster: 28,
    shop: 36,
    draft: 44,
  },

  /**
   * Create a DOM element for a piece.
   * @param {string} pieceType - e.g. 'pawn', 'knight', 'ghost'
   * @param {string} team - 'player' or 'enemy'
   * @param {string} sizeClass - 'board', 'roster', 'shop', or 'draft'
   * @returns {HTMLElement} <svg> or <img> element
   */
  create(pieceType, team, sizeClass) {
    if (this.mode === 'img') {
      return this._createImg(pieceType, team, sizeClass);
    }
    return this._createSVG(pieceType, team, sizeClass);
  },

  setMode(newMode) {
    this.mode = newMode;
  },

  _createSVG(pieceType, team, sizeClass) {
    const svgData = (typeof PIECE_SVGS !== 'undefined') && PIECE_SVGS[pieceType];
    if (!svgData) {
      // Fallback: return a text span with the unicode char
      return this._createFallback(pieceType, team, sizeClass);
    }

    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', svgData.viewBox || '0 0 64 64');
    if (sizeClass === 'board') {
      // Board pieces: fill CSS box, sized by .piece-svg-board class
      svg.setAttribute('width', '100%');
      svg.setAttribute('height', '100%');
    } else {
      const size = this.SIZES[sizeClass] || 40;
      svg.setAttribute('width', size);
      svg.setAttribute('height', size);
    }
    svg.classList.add('piece-svg', 'piece-svg-' + sizeClass);
    svg.style.display = 'block';

    // Set team color via CSS custom properties
    const teamColor = team === 'player' ? '#5082ff' : '#ff4646';
    const accentColor = team === 'player' ? '#3060cc' : '#cc2020';
    svg.style.color = teamColor;
    svg.style.setProperty('--piece-fill', teamColor);
    svg.style.setProperty('--piece-accent', accentColor);

    for (const pathData of svgData.paths) {
      if (pathData.stroke || pathData.strokeWidth) {
        // Path with stroke (e.g. legs, whiskers)
        const path = document.createElementNS(ns, 'path');
        path.setAttribute('d', pathData.d);
        path.setAttribute('fill', pathData.fill || 'none');
        path.setAttribute('stroke', pathData.stroke || 'currentColor');
        path.setAttribute('stroke-width', pathData.strokeWidth || '2');
        path.setAttribute('stroke-linecap', 'round');
        svg.appendChild(path);
      } else {
        const path = document.createElementNS(ns, 'path');
        path.setAttribute('d', pathData.d);
        path.setAttribute('fill', pathData.fill || 'currentColor');
        svg.appendChild(path);
      }
    }

    return svg;
  },

  _createImg(pieceType, team, sizeClass) {
    const img = document.createElement('img');
    img.src = 'sprites/' + pieceType + '_' + team + '.png';
    img.alt = pieceType;
    // Board pieces scale via CSS; others use fixed px sizes
    if (sizeClass !== 'board') {
      const size = this.SIZES[sizeClass] || 40;
      img.width = size;
      img.height = size;
    }
    img.classList.add('piece-svg', 'piece-svg-' + sizeClass);
    img.style.display = 'block';
    img.onerror = () => {
      // On missing sprite, swap to a fallback
      const fallback = this._createFallback(pieceType, team, sizeClass);
      img.replaceWith(fallback);
    };
    return img;
  },

  _createFallback(pieceType, team, sizeClass) {
    const span = document.createElement('span');
    span.className = 'piece-fallback piece-svg-' + sizeClass;
    span.textContent = (typeof pieceChar === 'function') ? pieceChar(pieceType, team) : '?';
    const teamColor = team === 'player' ? '#5082ff' : '#ff4646';
    span.style.color = teamColor;
    // Board pieces scale via CSS; others use fixed px sizes
    if (sizeClass !== 'board') {
      const size = this.SIZES[sizeClass] || 40;
      span.style.fontSize = Math.floor(size * 0.7) + 'px';
      span.style.lineHeight = size + 'px';
      span.style.width = size + 'px';
      span.style.height = size + 'px';
    }
    span.style.display = 'block';
    span.style.textAlign = 'center';
    return span;
  },
};
