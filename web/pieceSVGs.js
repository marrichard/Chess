/* ================================================================
   pieceSVGs.js — SVG path data for all 42 piece types
   Each entry: { paths: [{ d: string, fill?: string }], viewBox: "0 0 64 64" }
   Uses "currentColor" by default; accent paths use explicit fills.
   ================================================================ */

const PIECE_SVGS = {

  // ============================================================
  // CLASSIC CHESS (6)
  // ============================================================

  pawn: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 12a8 8 0 1 1 0 16 8 8 0 0 1 0-16z" },
      { d: "M26 28h12l4 20H22l4-20z" },
      { d: "M18 48h28v6H18z" },
    ],
  },

  knight: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M22 50h20v6H22z" },
      { d: "M24 50V30l-4-6 6-4 4 4 6-10 8 2-2 10 4 4-6 6v14z" },
      { d: "M28 18l2-6 4 2-2 6z", fill: "var(--piece-accent, currentColor)" },
    ],
  },

  bishop: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 8l6 16-6 8-6-8z" },
      { d: "M24 32h16l2 14H22z" },
      { d: "M20 46h24v4H20z" },
      { d: "M18 50h28v6H18z" },
    ],
  },

  rook: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M18 10h6v8h4v-8h8v8h4v-8h6v12H18z" },
      { d: "M22 22h20v24H22z" },
      { d: "M18 46h28v4H18z" },
      { d: "M16 50h32v6H16z" },
    ],
  },

  queen: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 6l4 12h-8z" },
      { d: "M16 18l6 8 10-6 10 6 6-8 2 14H14z" },
      { d: "M20 32h24l2 14H18z" },
      { d: "M16 46h32v4H16z" },
      { d: "M14 50h36v6H14z" },
    ],
  },

  king: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M29 4h6v6h4v6h-4v4h-6v-4h-4v-6h4z" },
      { d: "M20 20h24l2 4H18z" },
      { d: "M22 24h20v22H22z" },
      { d: "M18 46h28v4H18z" },
      { d: "M16 50h32v6H16z" },
    ],
  },

  // ============================================================
  // UNDEAD / DARK (6)
  // ============================================================

  ghost: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 8c-12 0-20 10-20 22v26l6-6 6 6 8-6 8 6 6-6 6 6V30c0-12-8-22-20-22z" },
      { d: "M24 26a3 3 0 1 1 0 6 3 3 0 0 1 0-6z M40 26a3 3 0 1 1 0 6 3 3 0 0 1 0-6z", fill: "var(--piece-accent, #000)" },
    ],
  },

  reaper: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M34 4c12 2 18 12 18 18-2 4-6 6-12 6l-8 6v24h-6V34l-8-6c-6 0-10-2-12-6 0-6 6-16 18-18z" },
      { d: "M26 22a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z M38 22a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z", fill: "var(--piece-accent, #000)" },
      { d: "M8 16c4-2 10 0 14 4l-4 4c-4-2-8-2-10 0z", fill: "var(--piece-accent, currentColor)" },
    ],
  },

  phantom: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 6c-14 0-22 12-22 26v24h8l4-8 4 8h12l4-8 4 8h8V32c0-14-8-26-22-26z" },
      { d: "M24 28l8-4 8 4v4l-8 4-8-4z", fill: "var(--piece-accent, #000)" },
    ],
  },

  poltergeist: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 10c-10 0-16 8-16 18v6c-4 2-6 6-6 10h44c0-4-2-8-6-10v-6c0-10-6-18-16-18z" },
      { d: "M22 30a3 3 0 1 0 6 0 3 3 0 0 0-6 0z M36 30a3 3 0 1 0 6 0 3 3 0 0 0-6 0z", fill: "var(--piece-accent, #000)" },
      { d: "M16 44v12l6-4 6 4 4-4 4 4 6-4 6 4V44z" },
    ],
  },

  parasite: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 14c-8 0-14 6-14 14s6 14 14 14 14-6 14-14-6-14-14-14z" },
      { d: "M20 18l-8-8M44 18l8-8M20 46l-8 8M44 46l8 8" , fill: "none", stroke: "currentColor", strokeWidth: "3" },
      { d: "M28 24a3 3 0 1 1 0 6 3 3 0 0 1 0-6z M36 24a3 3 0 1 1 0 6 3 3 0 0 1 0-6z", fill: "var(--piece-accent, #000)" },
      { d: "M26 36c3 4 9 4 12 0", fill: "none", stroke: "var(--piece-accent, #000)", strokeWidth: "2" },
    ],
  },

  void: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 6C18 6 8 18 8 32s10 26 24 26 24-12 24-26S46 6 32 6zm0 8c10 0 16 8 16 18s-6 18-16 18-16-8-16-18 6-18 16-18z" },
      { d: "M32 22c-6 0-10 4-10 10s4 10 10 10 10-4 10-10-4-10-10-10z", fill: "var(--piece-accent, #000)" },
    ],
  },

  // ============================================================
  // BEAST / CREATURE (5)
  // ============================================================

  wyvern: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 10l-6 12h-14l8 10-4 14 8-4v14h8V42l8 4-4-14 8-10H30z" },
      { d: "M6 14l8 4 6-6-2 10-8 2z M58 14l-8 4-6-6 2 10 8 2z", fill: "var(--piece-accent, currentColor)" },
    ],
  },

  imp: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 16c-8 0-14 8-14 16v20h28V32c0-8-6-16-14-16z" },
      { d: "M22 16l-4-10 6 6z M42 16l4-10-6 6z" },
      { d: "M26 30a2 2 0 1 1 0 4 2 2 0 0 1 0-4z M38 30a2 2 0 1 1 0 4 2 2 0 0 1 0-4z", fill: "var(--piece-accent, #000)" },
      { d: "M28 40c2 3 6 3 8 0", fill: "none", stroke: "var(--piece-accent, #000)", strokeWidth: "2" },
      { d: "M18 38c-6 2-8 8-4 12 M46 38c6 2 8 8 4 12" },
    ],
  },

  king_rat: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 18c-10 0-18 8-18 18v16h36V36c0-10-8-18-18-18z" },
      { d: "M20 18c-2-8 2-14 6-14s4 4 6 8 M44 18c2-8-2-14-6-14s-4 4-6 8" },
      { d: "M26 32a2 2 0 1 1 0 4 2 2 0 0 1 0-4z M38 32a2 2 0 1 1 0 4 2 2 0 0 1 0-4z", fill: "var(--piece-accent, #000)" },
      { d: "M32 38l-2 4h4z M16 42l-8 6 M48 42l8 6 M16 46l-6 4 M48 46l6 4" },
    ],
  },

  mimic: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M12 20h40v32H12z" },
      { d: "M10 18h44v6H10z" },
      { d: "M14 26h36v4H14z", fill: "var(--piece-accent, #000)" },
      { d: "M18 30l4 6-4 6h4l4-6-4-6z M38 30l4 6-4 6h4l4-6-4-6z" },
      { d: "M28 14h8v4h-8z" },
    ],
  },

  phoenix: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 16l-10 16 10 8 10-16z" },
      { d: "M22 32l-12 4 10 8 12-4z M42 32l12 4-10 8-12-4z" },
      { d: "M26 44l6 14 6-14z" },
      { d: "M32 8l-2 8h4z", fill: "var(--piece-accent, currentColor)" },
      { d: "M8 36l6-4 4 6z M56 36l-6-4-4 6z", fill: "var(--piece-accent, currentColor)" },
    ],
  },

  // ============================================================
  // WARRIOR / MELEE (6)
  // ============================================================

  berserker_piece: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 12a8 8 0 1 1 0 16 8 8 0 0 1 0-16z" },
      { d: "M24 28h16v24H24z" },
      { d: "M10 16l12 8-2 4-12-6z" },
      { d: "M54 16l-12 8 2 4 12-6z" },
      { d: "M20 52h24v6H20z" },
    ],
  },

  duelist: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 14a6 6 0 1 1 0 12 6 6 0 0 1 0-12z" },
      { d: "M26 26h12v22H26z" },
      { d: "M22 48h20v6H22z" },
      { d: "M40 20l14-14 2 2-14 14z", fill: "var(--piece-accent, currentColor)" },
      { d: "M52 6l6 2-2 6z", fill: "var(--piece-accent, currentColor)" },
    ],
  },

  lancer: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 14a6 6 0 1 1 0 12 6 6 0 0 1 0-12z" },
      { d: "M26 26h12v20H26z" },
      { d: "M22 46h20v6H22z" },
      { d: "M30 4l2-2 2 2v22h-4z", fill: "var(--piece-accent, currentColor)" },
    ],
  },

  charger: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 14a7 7 0 1 1 0 14 7 7 0 0 1 0-14z" },
      { d: "M24 28h16l2 20H22z" },
      { d: "M18 48h28v6H18z" },
      { d: "M18 22l-8-4 2-4 10 4z M46 22l8-4-2-4-10 4z" },
    ],
  },

  assassin: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 10c-4 0-8 4-8 8v4h16v-4c0-4-4-8-8-8z" },
      { d: "M24 22h16v8l-4 4v14H28V34l-4-4z" },
      { d: "M22 48h20v6H22z" },
      { d: "M18 30l-8 8 2 2 8-8z M46 30l8 8-2 2-8-8z", fill: "var(--piece-accent, currentColor)" },
    ],
  },

  sentinel: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 12a7 7 0 1 1 0 14 7 7 0 0 1 0-14z" },
      { d: "M26 26h12v20H26z" },
      { d: "M20 46h24v6H20z" },
      { d: "M10 22h10v24H10z", fill: "var(--piece-accent, currentColor)" },
    ],
  },

  // ============================================================
  // MAGIC / SUPPORT (7)
  // ============================================================

  witch: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 4l-8 22h16z" },
      { d: "M20 26h24v4H20z" },
      { d: "M24 30h16v18H24z" },
      { d: "M20 48h24v6H20z" },
    ],
  },

  healer: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 10a8 8 0 1 1 0 16 8 8 0 0 1 0-16z" },
      { d: "M26 26h12v22H26z" },
      { d: "M20 48h24v6H20z" },
      { d: "M28 34h8v4h4v8h-4v4h-8v-4h-4v-8h4z", fill: "var(--piece-accent, #4ade80)" },
    ],
  },

  bard: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 12a6 6 0 1 1 0 12 6 6 0 0 1 0-12z" },
      { d: "M26 24h12v24H26z" },
      { d: "M22 48h20v6H22z" },
      { d: "M40 18c4-2 8 0 10 4s0 8-2 10l-4-2c2-2 2-4 0-6s-4-2-6-2z", fill: "var(--piece-accent, currentColor)" },
      { d: "M44 30c2 0 4 2 4 4v8c0 4-6 6-6 6v-18z", fill: "var(--piece-accent, currentColor)" },
    ],
  },

  alchemist_piece: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M26 8h12v14l10 18v6H16v-6l10-18z" },
      { d: "M16 46h32v6H16z" },
      { d: "M24 34h16v6H24z", fill: "var(--piece-accent, #a855f7)" },
      { d: "M24 8h4v4h-4z M36 8h4v4h-4z" },
    ],
  },

  summoner: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 8l16 28H16z" },
      { d: "M32 18l8 14H24z", fill: "var(--piece-accent, #000)" },
      { d: "M28 42h8v10h-8z" },
      { d: "M22 52h20v6H22z" },
    ],
  },

  trickster: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 8l4 10 10-2-6 8 6 8-10-2-4 10-4-10-10 2 6-8-6-8 10 2z" },
      { d: "M32 22c-6 0-10 4-10 10s4 10 10 10 10-4 10-10-4-10-10-10z" },
      { d: "M28 30a2 2 0 1 1 0 4 2 2 0 0 1 0-4z M36 30a2 2 0 1 1 0 4 2 2 0 0 1 0-4z", fill: "var(--piece-accent, #000)" },
    ],
  },

  time_mage: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 6C18 6 8 16 8 32s10 26 24 26 24-10 24-26S46 6 32 6zm0 6c12 0 18 8 18 20s-6 20-18 20S14 44 14 32s6-20 18-20z" },
      { d: "M30 18h4v16h10v4H30z", fill: "var(--piece-accent, currentColor)" },
    ],
  },

  // ============================================================
  // MECHANICAL / UTILITY (6)
  // ============================================================

  cannon: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M20 32h24l6-14h-4l-4 10H22l-4-10h-4z" },
      { d: "M22 32h20v12H22z" },
      { d: "M18 44h28v4H18z" },
      { d: "M16 48h32v6H16z" },
      { d: "M28 18h8v14h-8z" },
    ],
  },

  bomb: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 18c-10 0-18 8-18 18s8 18 18 18 18-8 18-18-8-18-18-18z" },
      { d: "M34 10l4-6 2 2-4 6z" },
      { d: "M30 14h4v6h-4z" },
      { d: "M36 8a3 3 0 1 1 0 6 3 3 0 0 1 0-6z", fill: "var(--piece-accent, #ff6b35)" },
    ],
  },

  totem: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M24 8h16v14H24z" },
      { d: "M22 22h20v12H22z" },
      { d: "M24 34h16v14H24z" },
      { d: "M20 48h24v6H20z" },
      { d: "M28 12a2 2 0 1 1 0 4 2 2 0 0 1 0-4z M36 12a2 2 0 1 1 0 4 2 2 0 0 1 0-4z", fill: "var(--piece-accent, #000)" },
      { d: "M26 26a2 2 0 1 1 0 4 2 2 0 0 1 0-4z M38 26a2 2 0 1 1 0 4 2 2 0 0 1 0-4z", fill: "var(--piece-accent, #000)" },
    ],
  },

  decoy: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 10a8 8 0 1 1 0 16 8 8 0 0 1 0-16z" },
      { d: "M26 26h12l2 22H24z" },
      { d: "M20 48h24v6H20z" },
      { d: "M26 18h12v2H26z", fill: "var(--piece-accent, #000)" },
    ],
  },

  wall: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M8 12h48v40H8z" },
      { d: "M8 12h24v20H8z M32 12h24v20H32z", fill: "var(--piece-accent, currentColor)" },
      { d: "M8 32h16v20H8z M24 32h16v20H24z M40 32h16v20H40z" },
      { d: "M8 12h48v4H8z" },
    ],
  },

  golem: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M22 10h20v16H22z" },
      { d: "M18 26h28v20H18z" },
      { d: "M22 46h8v10H22z M34 46h8v10H34z" },
      { d: "M10 28h8v14h-8z M46 28h8v14h-8z" },
      { d: "M26 14a2 2 0 1 1 0 4 2 2 0 0 1 0-4z M38 14a2 2 0 1 1 0 4 2 2 0 0 1 0-4z", fill: "var(--piece-accent, #4ade80)" },
    ],
  },

  // ============================================================
  // SPECIAL / META (6)
  // ============================================================

  gambler: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M12 12h40v40H12z", rx: "4" },
      { d: "M20 20a3 3 0 1 1 0 6 3 3 0 0 1 0-6z" , fill: "var(--piece-accent, #000)" },
      { d: "M41 20a3 3 0 1 1 0 6 3 3 0 0 1 0-6z", fill: "var(--piece-accent, #000)" },
      { d: "M30 30a3 3 0 1 1 0 6 3 3 0 0 1 0-6z", fill: "var(--piece-accent, #000)" },
      { d: "M20 41a3 3 0 1 1 0 6 3 3 0 0 1 0-6z", fill: "var(--piece-accent, #000)" },
      { d: "M41 41a3 3 0 1 1 0 6 3 3 0 0 1 0-6z", fill: "var(--piece-accent, #000)" },
    ],
  },

  anchor_piece: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M30 8h4v20h-4z" },
      { d: "M32 10a5 5 0 1 1 0 10 5 5 0 0 1 0-10z" },
      { d: "M20 22h24v4H20z" },
      { d: "M30 26h4v16h-4z" },
      { d: "M18 42c0-8 6-14 14-14s14 6 14 14" , fill: "none", stroke: "currentColor", strokeWidth: "4" },
      { d: "M14 40h8v6h-8z M42 40h8v6h-8z" },
    ],
  },

  mirror_piece: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M16 8h32v48H16z" },
      { d: "M20 12h24v40H20z", fill: "var(--piece-accent, #88ccff)" },
      { d: "M20 12l24 40v-40z", fill: "var(--piece-accent, #aaddff)" },
    ],
  },

  shapeshifter: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 8c-14 0-24 12-24 24s10 24 24 24 24-12 24-24-10-24-24-24z" },
      { d: "M32 16c-8 0-16 8-16 16s8 16 16 16 16-8 16-16-8-16-16-16z", fill: "var(--piece-accent, #000)" },
      { d: "M32 24c-4 0-8 4-8 8s4 8 8 8 8-4 8-8-4-8-8-8z" },
    ],
  },

  leech: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M32 8c-6 0-12 6-12 14v10c0 10 4 18 12 24 8-6 12-14 12-24V22c0-8-6-14-12-14z" },
      { d: "M28 24a2 2 0 1 1 0 4 2 2 0 0 1 0-4z M36 24a2 2 0 1 1 0 4 2 2 0 0 1 0-4z", fill: "var(--piece-accent, #000)" },
      { d: "M26 34c3 4 9 4 12 0", fill: "none", stroke: "var(--piece-accent, #000)", strokeWidth: "2" },
    ],
  },

  torch: {
    viewBox: "0 0 64 64",
    paths: [
      { d: "M28 28h8v28h-8z" },
      { d: "M24 52h16v6H24z" },
      { d: "M32 6c-6 4-10 10-10 16 0 6 4 10 10 10s10-4 10-10c0-6-4-12-10-16z", fill: "var(--piece-accent, #ff6b35)" },
      { d: "M32 12c-3 3-6 6-6 10 0 4 2 6 6 6s6-2 6-6c0-4-3-7-6-10z" },
    ],
  },
};
