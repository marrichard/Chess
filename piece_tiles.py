"""Generate custom pixel-art chess piece tiles for the tileset.

Each piece is a large sprite split into a 3x3 grid of tiles so it spans
3 character cells wide and 3 cells tall on the board.
"""

from __future__ import annotations

import numpy as np
import tcod.tileset

from pieces import PieceType

_BASE = 0xE000


def piece_codepoints(piece_type: PieceType) -> list[int]:
    """Return the 9 codepoints for a piece's 3x3 tile grid."""
    idx = list(PieceType).index(piece_type)
    base = _BASE + idx * 9
    return [base + i for i in range(9)]


def piece_chars(piece_type: PieceType) -> list[list[str]]:
    """Return the 3x3 grid of characters for rendering a piece."""
    cps = piece_codepoints(piece_type)
    return [
        [chr(cps[0]), chr(cps[1]), chr(cps[2])],
        [chr(cps[3]), chr(cps[4]), chr(cps[5])],
        [chr(cps[6]), chr(cps[7]), chr(cps[8])],
    ]


def _scale_art(art: list[str], target_w: int, target_h: int) -> np.ndarray:
    """Scale text art to target pixel dimensions using nearest-neighbor."""
    art_h = len(art)
    art_w = max(len(row) for row in art)

    src = np.zeros((art_h, art_w), dtype=np.uint8)
    for y, row in enumerate(art):
        for x, ch in enumerate(row):
            if ch == "#":
                src[y, x] = 1

    dst = np.zeros((target_h, target_w), dtype=np.uint8)
    for y in range(target_h):
        for x in range(target_w):
            sy = int(y * art_h / target_h)
            sx = int(x * art_w / target_w)
            dst[y, x] = src[sy, sx]

    return dst


# Simple, bold pixel art — 22 wide x 22 tall.
# Scales to 66x66 at exactly 3x with a 22px tileset. Clean integer scaling.

# King: cross on top, wide body
_KING_ART = [
    "..........##..........",
    "..........##..........",
    "......##########......",
    "......##########......",
    "..........##..........",
    "..........##..........",
    ".......########.......",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    ".....############.....",
    ".....############.....",
    "....##############....",
    "...################...",
    "..##################..",
    ".####################.",
    "######################",
    "######################",
]

# Queen: 3 pointed peaks, band, body
_QUEEN_ART = [
    "..##......##......##..",
    ".####....####....####.",
    ".####....####....####.",
    "..##################..",
    "...################...",
    ".....############.....",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    ".....############.....",
    ".....############.....",
    "....##############....",
    "...################...",
    "..##################..",
    ".####################.",
    "######################",
    "######################",
]

# Rook: 3 merlons, rectangular body (no hourglass)
_ROOK_ART = [
    "...####..####..####...",
    "...####..####..####...",
    "...####..####..####...",
    "...################...",
    "...################...",
    ".....############.....",
    ".....############.....",
    ".....############.....",
    ".....############.....",
    ".....############.....",
    ".....############.....",
    ".....############.....",
    ".....############.....",
    ".....############.....",
    ".....############.....",
    ".....############.....",
    ".....############.....",
    "...################...",
    "..##################..",
    ".####################.",
    "######################",
    "######################",
]

# Bishop: pointed top with slit, body
_BISHOP_ART = [
    "..........##..........",
    ".........####.........",
    "........######........",
    ".......########.......",
    "......####..####......",
    "......####..####......",
    ".......########.......",
    ".......########.......",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    "......##########......",
    ".....############.....",
    ".....############.....",
    "....##############....",
    "...################...",
    "..##################..",
    ".####################.",
    "######################",
    "######################",
]

# Knight: horse head facing right — snout extends right, gap under jaw
_KNIGHT_ART = [
    ".......####...........",
    "......########........",
    ".....##########.......",
    "....##############....",
    "...##################.",
    "..####################",
    "..####################",
    "..###########.........",
    "...##########.........",
    "....#########.........",
    ".....########.........",
    "......########........",
    "......########........",
    ".....##########.......",
    ".....############.....",
    "....##############....",
    "...################...",
    "..##################..",
    "..##################..",
    ".####################.",
    "######################",
    "######################",
]

# Pawn: round head, thin stem, base
_PAWN_ART = [
    "......................",
    "........######........",
    ".......########.......",
    "......##########......",
    "......##########......",
    "......##########......",
    ".......########.......",
    "........######........",
    ".........####.........",
    ".........####.........",
    ".........####.........",
    "........######........",
    "........######........",
    ".......########.......",
    "......##########......",
    ".....############.....",
    "....##############....",
    "...################...",
    "..##################..",
    ".####################.",
    "######################",
    "######################",
]

_PIECE_ARTS = {
    PieceType.KING:   _KING_ART,
    PieceType.QUEEN:  _QUEEN_ART,
    PieceType.ROOK:   _ROOK_ART,
    PieceType.BISHOP: _BISHOP_ART,
    PieceType.KNIGHT: _KNIGHT_ART,
    PieceType.PAWN:   _PAWN_ART,
}


def install_piece_tiles(tileset: tcod.tileset.Tileset) -> None:
    """Install chess piece glyphs as 3x3 tile grids into the tileset."""
    tw = tileset.tile_width
    th = tileset.tile_height
    full_w = tw * 3
    full_h = th * 3

    # Draw at square dimensions to avoid distortion
    art_size = min(full_w, full_h)
    pad_x = (full_w - art_size) // 2
    pad_y = (full_h - art_size) // 2

    for piece_type, art in _PIECE_ARTS.items():
        art_bitmap = _scale_art(art, art_size, art_size)

        bitmap = np.zeros((full_h, full_w), dtype=np.uint8)
        bitmap[pad_y:pad_y + art_size, pad_x:pad_x + art_size] = art_bitmap

        full = np.zeros((full_h, full_w, 4), dtype=np.uint8)
        full[bitmap == 1] = [255, 255, 255, 255]

        # --- Shading passes (works because tcod multiplies glyph by fg) ---
        piece_mask = bitmap == 1

        # Edge darkening: pixels with at least one empty neighbor dimmed to ~180
        neighbors = (
            np.roll(bitmap, 1, axis=0) + np.roll(bitmap, -1, axis=0) +
            np.roll(bitmap, 1, axis=1) + np.roll(bitmap, -1, axis=1)
        )
        edge_mask = piece_mask & (neighbors < 4)
        full[edge_mask, :3] = 180

        # Find vertical extent of piece pixels for highlight/shadow zones
        piece_rows = np.where(piece_mask.any(axis=1))[0]
        if len(piece_rows) > 0:
            top_row = piece_rows[0]
            bot_row = piece_rows[-1]
            height_span = bot_row - top_row + 1

            # Top highlight: top 30% of piece pixels stay at 255
            top_cutoff = top_row + int(height_span * 0.3)
            top_zone = piece_mask.copy()
            top_zone[top_cutoff:, :] = False
            full[top_zone, :3] = 255

            # Bottom shadow: bottom 20% dimmed to ~140
            bot_cutoff = bot_row - int(height_span * 0.2)
            bot_zone = piece_mask.copy()
            bot_zone[:bot_cutoff, :] = False
            full[bot_zone, :3] = 140

        cps = piece_codepoints(piece_type)
        for gy in range(3):
            for gx in range(3):
                tile = full[gy * th:(gy + 1) * th, gx * tw:(gx + 1) * tw].copy()
                tileset.set_tile(cps[gy * 3 + gx], tile)
