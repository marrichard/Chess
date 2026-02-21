"""Shared ASCII rendering — board, pieces, UI, highlights, effects."""

from __future__ import annotations

import colorsys
import math
import time

import numpy as np
import tcod.console

from board import Board
from pieces import Piece, Team, PieceType, PIECE_LETTERS, PIECE_VALUES
from modifiers import PIECE_MODIFIER_VISUALS, CELL_MODIFIERS, BORDER_MODIFIERS

# Colors
BG_LIGHT = (190, 190, 170)
BG_DARK = (110, 110, 90)
FG_PLAYER = (80, 130, 255)
FG_ENEMY = (255, 70, 70)
FG_TEXT = (220, 220, 220)
FG_DIM = (120, 120, 120)
BG_BLACK = (15, 15, 15)
BG_PANEL = (25, 25, 35)
BG_FELT = (20, 50, 30)

HIGHLIGHT_MOVE = (40, 160, 40)
HIGHLIGHT_CAPTURE = (220, 50, 50)
HIGHLIGHT_SELECTED = (255, 255, 80)
HIGHLIGHT_CURSOR = (220, 220, 60)
HIGHLIGHT_DANGER = (180, 60, 60)
HIGHLIGHT_SPECIAL = (60, 180, 220)
HIGHLIGHT_ZONE = (35, 55, 35)

# Board tile dimensions — set dynamically each frame via fit_tile_size()
TILE_W = 5
TILE_H = 5

from piece_tiles import piece_chars


def _animate_color(
    base_color: tuple[int, int, int], anim_type: str, t: float
) -> tuple[int, int, int]:
    """Return an animated RGB color based on animation type and time."""
    r, g, b = base_color
    if anim_type == "pulse":
        # Brightness oscillation (fast)
        factor = 0.7 + 0.3 * math.sin(t * 4.0)
        return (min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor)))
    elif anim_type == "slow_pulse":
        factor = 0.75 + 0.25 * math.sin(t * 2.0)
        return (min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor)))
    elif anim_type == "shimmer":
        # Color shift: rotate hue slightly
        shift = int(30 * math.sin(t * 5.0))
        return (
            max(0, min(255, r + shift)),
            max(0, min(255, g - shift)),
            max(0, min(255, b + shift // 2)),
        )
    elif anim_type == "glow":
        factor = 0.6 + 0.4 * (0.5 + 0.5 * math.sin(t * 1.5))
        return (min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor)))
    elif anim_type == "rainbow":
        # Hue wheel cycle, 70/30 blend with base
        hue = (t * 0.5) % 1.0
        hr, hg, hb = colorsys.hsv_to_rgb(hue, 0.9, 1.0)
        return (
            min(255, int(r * 0.7 + hr * 255 * 0.3)),
            min(255, int(g * 0.7 + hg * 255 * 0.3)),
            min(255, int(b * 0.7 + hb * 255 * 0.3)),
        )
    elif anim_type == "flash":
        # Sharp on/off at ~4Hz
        on = (int(t * 4.0) % 2) == 0
        if on:
            return (min(255, r + 80), min(255, g + 80), min(255, b + 80))
        return (max(0, r - 40), max(0, g - 40), max(0, b - 40))
    elif anim_type == "fade_in":
        # Alpha ramp 0->1 over ~1s (cycles)
        alpha = min(1.0, (t % 1.0))
        return (int(r * alpha), int(g * alpha), int(b * alpha))
    elif anim_type == "strobe":
        # Rapid white flash at ~8Hz
        on = (int(t * 8.0) % 2) == 0
        if on:
            return (min(255, r + 150), min(255, g + 150), min(255, b + 150))
        return base_color
    return base_color


def fit_tile_size(console_w: int, console_h: int, board_w: int = 8, board_h: int = 8) -> int:
    """Compute the largest odd tile size that fits the board in the console."""
    global TILE_W, TILE_H
    margin = 8  # room for labels, message bar, etc.
    max_tw = (console_w - margin) // board_w
    max_th = (console_h - margin) // board_h
    avail = min(max_tw, max_th)
    # Use largest odd size (odd centers the 3x3 piece perfectly)
    if avail >= 7:
        tile = 7
    elif avail >= 5:
        tile = 5
    elif avail >= 3:
        tile = 3
    else:
        tile = 3
    TILE_W = tile
    TILE_H = tile
    return tile


def board_pixel_size(board: Board) -> tuple[int, int]:
    """Return the total character size of the board."""
    return board.width * TILE_W, board.height * TILE_H


def draw_board(
    console: tcod.console.Console,
    board: Board,
    ox: int = 1,
    oy: int = 1,
    highlights: dict[tuple[int, int], tuple[int, int, int]] | None = None,
    cursor: tuple[int, int] | None = None,
    selected: tuple[int, int] | None = None,
) -> None:
    """Draw the chess board with pieces and highlights."""
    if highlights is None:
        highlights = {}

    for by in range(board.height):
        for bx in range(board.width):
            sx = ox + bx * TILE_W
            sy = oy + by * TILE_H

            # Background color
            if (bx, by) in board.blocked_tiles:
                bg = (50, 50, 50)
            elif (bx + by) % 2 == 0:
                bg = BG_LIGHT
            else:
                bg = BG_DARK

            # Team half tinting: warm top (enemy), cool bottom (player)
            r, g, b = bg
            if by < 4:
                bg = (min(255, r + 12), max(0, g - 4), max(0, b - 4))
            else:
                bg = (max(0, r - 4), max(0, g - 2), min(255, b + 12))

            # Apply highlights
            if (bx, by) in highlights:
                bg = _blend(bg, highlights[(bx, by)], 0.5)

            if selected and (bx, by) == selected:
                bg = _blend(bg, HIGHLIGHT_SELECTED, 0.6)

            is_cursor = cursor and (bx, by) == cursor
            if is_cursor:
                bg = _blend(bg, HIGHLIGHT_CURSOR, 0.45)

            # Cell modifier overlay: blend overlay color into background
            if (bx, by) in board.cell_modifiers:
                cm = board.cell_modifiers[(bx, by)]
                bg = _blend(bg, cm.color, cm.overlay_alpha)

            # Fill the entire tile
            console.draw_rect(sx, sy, TILE_W, TILE_H, ch=ord(' '), bg=bg)

            # Draw content
            piece = board.get_piece_at(bx, by)
            now = time.time()
            if piece:
                fg = FG_PLAYER if piece.team == Team.PLAYER else FG_ENEMY

                # Piece modifier: override foreground color with animated modifier color
                if piece.modifiers:
                    for mod in piece.modifiers:
                        if mod.effect in PIECE_MODIFIER_VISUALS:
                            vis = PIECE_MODIFIER_VISUALS[mod.effect]
                            fg = _animate_color(vis["color"], vis["animation"], now)
                            break  # use first modifier's visual

                chars = piece_chars(piece.piece_type)

                # Draw the piece as a 3x3 character grid, centered in the tile
                ix = sx + (TILE_W - 3) // 2
                iy = sy + (TILE_H - 3) // 2
                for dy in range(3):
                    for dx in range(3):
                        console.print(ix + dx, iy + dy, chars[dy][dx], fg=fg, bg=bg)

                # Modifier sparkle in top-right corner
                if piece.modifiers:
                    sparkle_fg = _animate_color((255, 220, 60), "pulse", now)
                    console.print(sx + TILE_W - 1, sy, "*", fg=sparkle_fg, bg=bg)

                # Cell modifier indicator on piece: small dot in top-left
                if piece.cell_modifier:
                    console.print(sx, sy, ".", fg=piece.cell_modifier.color, bg=bg)

            elif (bx, by) in board.blocked_tiles:
                console.draw_rect(sx, sy, TILE_W, TILE_H, ch=ord('#'), fg=(60, 60, 60), bg=bg)

            elif (bx, by) in board.cell_modifiers:
                # Show cell modifier icon when no piece is present
                cm = board.cell_modifiers[(bx, by)]
                # Find the icon from registry
                icon = "?"
                for _key, tmpl in CELL_MODIFIERS.items():
                    if tmpl["effect"] == cm.effect:
                        icon = tmpl["icon"]
                        break
                cx_pos = sx + TILE_W // 2
                cy_pos = sy + TILE_H // 2
                icon_fg = _animate_color(cm.color, "glow", now)
                console.print(cx_pos, cy_pos, icon, fg=icon_fg, bg=bg)

            # Border modifier: draw colored border (before cursor border)
            if (bx, by) in board.border_modifiers and TILE_W >= 3:
                bm = board.border_modifiers[(bx, by)]
                bc = bm.border_color
                for row in range(TILE_H):
                    console.print(sx, sy + row, "|", fg=bc, bg=bg)
                    console.print(sx + TILE_W - 1, sy + row, "|", fg=bc, bg=bg)
                for col in range(TILE_W):
                    console.print(sx + col, sy, "=", fg=bc, bg=bg)
                    console.print(sx + col, sy + TILE_H - 1, "=", fg=bc, bg=bg)
                console.print(sx, sy, "#", fg=bc, bg=bg)
                console.print(sx + TILE_W - 1, sy, "#", fg=bc, bg=bg)
                console.print(sx, sy + TILE_H - 1, "#", fg=bc, bg=bg)
                console.print(sx + TILE_W - 1, sy + TILE_H - 1, "#", fg=bc, bg=bg)

            # Cursor indicator — border (only when tiles are large enough)
            if is_cursor and TILE_W >= 5:
                m = (255, 255, 200)
                for row in range(TILE_H):
                    console.print(sx, sy + row, "|", fg=m, bg=bg)
                    console.print(sx + TILE_W - 1, sy + row, "|", fg=m, bg=bg)
                for col in range(TILE_W):
                    console.print(sx + col, sy, "-", fg=m, bg=bg)
                    console.print(sx + col, sy + TILE_H - 1, "-", fg=m, bg=bg)
                console.print(sx, sy, "+", fg=m, bg=bg)
                console.print(sx + TILE_W - 1, sy, "+", fg=m, bg=bg)
                console.print(sx, sy + TILE_H - 1, "+", fg=m, bg=bg)
                console.print(sx + TILE_W - 1, sy + TILE_H - 1, "+", fg=m, bg=bg)


def draw_board_grid(
    console: tcod.console.Console,
    board: Board,
    ox: int = 1,
    oy: int = 1,
) -> None:
    """Draw dim box-drawing grid lines at tile boundaries."""
    if TILE_W < 5:
        return
    grid_fg = (40, 40, 40)
    total_w = board.width * TILE_W
    total_h = board.height * TILE_H
    # Vertical lines at column boundaries
    for bx in range(1, board.width):
        gx = ox + bx * TILE_W
        for gy_off in range(total_h):
            gy = oy + gy_off
            # Read current bg to preserve it
            bg_r, bg_g, bg_b = console.rgb['bg'][gy, gx]
            console.print(gx, gy, "\u2502", fg=grid_fg, bg=(int(bg_r), int(bg_g), int(bg_b)))
    # Horizontal lines at row boundaries
    for by in range(1, board.height):
        gy = oy + by * TILE_H
        for gx_off in range(total_w):
            gx = ox + gx_off
            bg_r, bg_g, bg_b = console.rgb['bg'][gy, gx]
            # Intersection?
            if (gx - ox) % TILE_W == 0 and (gx - ox) > 0:
                console.print(gx, gy, "\u253C", fg=grid_fg, bg=(int(bg_r), int(bg_g), int(bg_b)))
            else:
                console.print(gx, gy, "\u2500", fg=grid_fg, bg=(int(bg_r), int(bg_g), int(bg_b)))


def draw_board_labels(
    console: tcod.console.Console,
    board: Board,
    ox: int = 1,
    oy: int = 1,
) -> None:
    """Draw coordinate labels around the board."""
    for bx in range(board.width):
        sx = ox + bx * TILE_W + TILE_W // 2
        label = chr(ord("a") + bx)
        console.print(sx, oy - 1, label, fg=FG_DIM, bg=BG_BLACK)
        console.print(sx, oy + board.height * TILE_H, label, fg=FG_DIM, bg=BG_BLACK)
    for by in range(board.height):
        sy = oy + by * TILE_H + TILE_H // 2
        label = str(board.height - by)
        console.print(ox - 2, sy, label.rjust(1), fg=FG_DIM, bg=BG_BLACK)


def draw_panel(
    console: tcod.console.Console,
    x: int,
    y: int,
    width: int,
    height: int,
    title: str = "",
    lines: list[str] | None = None,
    fg: tuple[int, int, int] = FG_TEXT,
) -> None:
    """Draw a text panel with box-drawing border."""
    frame_title = f" {title} " if title else ""
    console.draw_frame(
        x, y, width, height,
        title=frame_title,
        clear=True,
        fg=(255, 220, 100) if title else fg,
        bg=BG_PANEL,
    )

    if lines:
        for i, line in enumerate(lines):
            if i + 1 < height - 1:  # stay inside frame
                console.print(x + 1, y + 1 + i, line[:width - 2], fg=fg, bg=BG_PANEL)


def draw_menu(
    console: tcod.console.Console,
    title: str,
    options: list[str],
    selected_idx: int,
    x: int = 0,
    y: int = 0,
    width: int = 0,
) -> None:
    """Draw a selectable menu."""
    if width == 0:
        width = console.width

    cx = x + (width - len(title)) // 2
    console.print(cx, y + 1, title, fg=(255, 220, 100), bg=BG_BLACK)

    for i, opt in enumerate(options):
        oy = y + 3 + i * 2
        if i == selected_idx:
            prefix = "> "
            fg = (255, 255, 255)
            bg = (60, 60, 100)
        else:
            prefix = "  "
            fg = FG_DIM
            bg = BG_BLACK
        text = f"{prefix}{opt}"
        cx = x + (width - len(text)) // 2
        console.print(cx, oy, text, fg=fg, bg=bg)


def draw_roster(
    console: tcod.console.Console,
    pieces: list[Piece],
    selected_idx: int,
    x: int,
    y: int,
    width: int,
) -> None:
    """Draw the piece roster for selection with chess symbols."""
    # Fill background
    console.draw_rect(x, y, width, 4, ch=ord(' '), bg=BG_PANEL)
    console.print(x + 1, y, "Roster:", fg=(255, 220, 100), bg=BG_PANEL)

    slot_w = 6
    for i, piece in enumerate(pieces):
        sx = x + 1 + i * slot_w
        if sx + slot_w > x + width:
            break
        sy = y + 1
        fg = FG_PLAYER if piece.team == Team.PLAYER else FG_ENEMY
        bg = HIGHLIGHT_SELECTED if i == selected_idx else BG_PANEL

        chars = piece_chars(piece.piece_type)
        # Show the center row of the 3x3 piece art
        console.print(sx + 1, sy, chars[1][0] + chars[1][1] + chars[1][2], fg=fg, bg=bg)
        name = piece.piece_type.value[:4].center(slot_w)
        console.print(sx, sy + 1, name, fg=_dim(fg, 0.6), bg=BG_PANEL)

        # Number label
        label = str(i + 1).center(slot_w)
        console.print(sx, sy + 2, label[:slot_w], fg=FG_DIM, bg=BG_PANEL)


def draw_message(
    console: tcod.console.Console,
    message: str,
    y: int | None = None,
) -> None:
    """Draw a centered message."""
    if y is None:
        y = console.height - 2
    cx = (console.width - len(message)) // 2
    console.print(max(0, cx), y, message, fg=FG_TEXT, bg=BG_BLACK)


def _wrap_text(text: str, width: int) -> list[str]:
    """Split text into lines at word boundaries to fit within width."""
    if width <= 0:
        return [text]
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def draw_shop_card(
    console: tcod.console.Console,
    x: int,
    y: int,
    width: int,
    height: int,
    icon: str,
    name: str,
    description: str,
    category: str,
    color: tuple[int, int, int],
    selected: bool,
    affordable: bool,
) -> None:
    """Draw a fixed-size vertical shop card with rich visual detail."""
    inner_w = width - 2  # inside double-line borders
    dim = not affordable and not selected

    CARD_FACE = (38, 40, 55)
    SHADOW_COLOR = (8, 15, 10)

    if selected:
        card_bg = (28, 58, 38)
        border_fg = _brighten(color, 1.5)
    elif dim:
        card_bg = _dim(CARD_FACE, 0.65)
        border_fg = _dim(color, 0.4)
    else:
        card_bg = CARD_FACE
        border_fg = color

    # --- Drop shadow (1px right + down) ---
    for sy in range(y + 1, y + height + 1):
        if sy < console.height:
            console.print(min(x + width, console.width - 1), sy, " ", bg=SHADOW_COLOR)
    for sx in range(x + 1, x + width + 1):
        if y + height < console.height:
            console.print(min(sx, console.width - 1), y + height, " ", bg=SHADOW_COLOR)

    # --- Card face fill ---
    console.draw_rect(x, y, width, height, ch=ord(' '), bg=card_bg)

    # --- Double-line border ╔═╗║╚═╝ ---
    console.print(x, y, "\u2554", fg=border_fg, bg=card_bg)
    console.print(x + width - 1, y, "\u2557", fg=border_fg, bg=card_bg)
    console.print(x, y + height - 1, "\u255a", fg=border_fg, bg=card_bg)
    console.print(x + width - 1, y + height - 1, "\u255d", fg=border_fg, bg=card_bg)
    for sx in range(x + 1, x + width - 1):
        console.print(sx, y, "\u2550", fg=border_fg, bg=card_bg)
        console.print(sx, y + height - 1, "\u2550", fg=border_fg, bg=card_bg)
    for sy in range(y + 1, y + height - 1):
        console.print(x, sy, "\u2551", fg=border_fg, bg=card_bg)
        console.print(x + width - 1, sy, "\u2551", fg=border_fg, bg=card_bg)

    # --- Category banner (colored background strip at top) ---
    banner_bg = _dim(color, 0.25) if not dim else _dim(color, 0.12)
    banner_fg = _brighten(color, 1.2) if not dim else _dim(color, 0.5)
    cat_text = category.center(inner_w)
    console.draw_rect(x + 1, y + 1, inner_w, 1, ch=ord(' '), bg=banner_bg)
    console.print(x + 1, y + 1, cat_text[:inner_w], fg=banner_fg, bg=banner_bg)

    # --- Icon area: 3 rows with tinted background ---
    icon_tint = _dim(color, 0.10) if not dim else _dim(color, 0.05)
    icon_bg = _blend(card_bg, icon_tint, 0.5) if not selected else _blend(card_bg, color, 0.08)
    icon_fg = color if not dim else _dim(color, 0.4)
    icon_start = y + 2
    for dy in range(3):
        console.draw_rect(x + 1, icon_start + dy, inner_w, 1, ch=ord(' '), bg=icon_bg)
    # Center the icon on the middle row of the icon area
    icon_cx = x + width // 2
    console.print(icon_cx, icon_start + 1, icon, fg=icon_fg, bg=icon_bg)
    # Decorative dots in icon area corners
    dot_fg = _dim(color, 0.25) if not dim else _dim(color, 0.12)
    console.print(x + 1, icon_start, "\u00b7", fg=dot_fg, bg=icon_bg)
    console.print(x + inner_w, icon_start, "\u00b7", fg=dot_fg, bg=icon_bg)
    console.print(x + 1, icon_start + 2, "\u00b7", fg=dot_fg, bg=icon_bg)
    console.print(x + inner_w, icon_start + 2, "\u00b7", fg=dot_fg, bg=icon_bg)

    # --- Name (bright, centered) ---
    name_row = icon_start + 3
    name_fg = (255, 255, 255) if not dim else _dim(FG_TEXT, 0.45)
    name_x = x + (width - len(name)) // 2
    console.print(max(x + 1, name_x), name_row, name[:inner_w], fg=name_fg, bg=card_bg)

    # --- Ornamental separator ─·─·─ ---
    sep_row = name_row + 1
    sep_fg = _dim(border_fg, 0.35)
    sep_str = ""
    for si in range(inner_w):
        sep_str += "\u00b7" if si % 2 == 1 else "\u2500"
    console.print(x + 1, sep_row, sep_str[:inner_w], fg=sep_fg, bg=card_bg)

    # --- Description (word-wrapped, centered) ---
    desc_lines = _wrap_text(description, inner_w)
    desc_fg = FG_DIM if not dim else _dim(FG_DIM, 0.45)
    desc_start = sep_row + 1
    for i, line in enumerate(desc_lines):
        row = desc_start + i
        if row >= y + height - 1:
            break
        line_x = x + (width - len(line)) // 2
        console.print(max(x + 1, line_x), row, line[:inner_w], fg=desc_fg, bg=card_bg)

    # --- Selected indicator: arrows outside the card + shadow ---
    if selected:
        mid_y = y + height // 2
        if x > 0:
            console.print(x - 1, mid_y, "\u25b6", fg=(255, 255, 200), bg=BG_FELT)
        if x + width + 1 < console.width:
            console.print(x + width + 1, mid_y, "\u25c0", fg=(255, 255, 200), bg=BG_FELT)


def draw_shop_header(
    console: tcod.console.Console,
    y: int,
    width: int,
    start_x: int,
    gold: int,
    wave: int,
    wins: int,
    losses: int,
) -> int:
    """Draw shop header bar with ornamental gold display. Returns rows used."""
    bg = BG_FELT
    gold_fg = (255, 220, 100)

    # Gold display — prominent with diamonds
    gold_str = f"\u2666 ${gold}g \u2666"
    console.print(start_x, y, gold_str, fg=gold_fg, bg=bg)

    # Wave (center, with dashes)
    wave_str = f"\u2500\u2500 Wave {wave} \u2500\u2500"
    wave_x = start_x + (width - len(wave_str)) // 2
    console.print(wave_x, y, wave_str, fg=FG_TEXT, bg=bg)

    # Record (right)
    record_str = f"{wins}W / {losses}L"
    console.print(start_x + width - len(record_str), y, record_str, fg=FG_TEXT, bg=bg)

    # Ornamental separator: ═══ with diamond center
    sep_y = y + 1
    sep_fg = _dim(gold_fg, 0.35)
    mid = start_x + width // 2
    for sx in range(start_x, start_x + width):
        if sx == mid:
            console.print(sx, sep_y, "\u2666", fg=_dim(gold_fg, 0.5), bg=bg)
        else:
            console.print(sx, sep_y, "\u2550", fg=sep_fg, bg=bg)

    return 2


def draw_shop_price_tag(
    console: tcod.console.Console,
    x: int,
    y: int,
    width: int,
    cost: int,
    affordable: bool,
) -> None:
    """Draw a [$Xg] price tag centered below a card."""
    tag = f"${cost}g"
    tag_x = x + (width - len(tag)) // 2
    fg = (255, 220, 100) if affordable else _dim((255, 220, 100), 0.35)
    console.print(max(0, tag_x), y, tag, fg=fg, bg=BG_FELT)


def draw_shop_done_button(
    console: tcod.console.Console,
    y: int,
    width: int,
    start_x: int,
    selected: bool,
) -> int:
    """Draw 'Next Round' button centered in card area. Returns rows used."""
    return draw_felt_button(
        console, y, width, start_x,
        label="Next Round \u25b6",
        selected=selected,
    )


def draw_felt_button(
    console: tcod.console.Console,
    y: int,
    width: int,
    start_x: int,
    label: str,
    selected: bool,
    fg_normal: tuple[int, int, int] = (220, 80, 60),
    bg_selected: tuple[int, int, int] = (160, 50, 30),
) -> int:
    """Draw a framed button centered in an area on felt. Returns rows used."""
    padded = f" {label} "
    btn_w = len(padded) + 2
    btn_x = start_x + (width - btn_w) // 2

    if selected:
        fg = (255, 255, 255)
        border_fg = (255, 200, 80)
        bg = bg_selected
    else:
        fg = fg_normal
        border_fg = _dim(fg_normal, 0.5)
        bg = _dim(BG_FELT, 0.8)

    console.print(btn_x, y, "\u2554", fg=border_fg, bg=BG_FELT)
    console.print(btn_x + btn_w - 1, y, "\u2557", fg=border_fg, bg=BG_FELT)
    for sx in range(btn_x + 1, btn_x + btn_w - 1):
        console.print(sx, y, "\u2550", fg=border_fg, bg=BG_FELT)

    console.print(btn_x, y + 1, "\u2551", fg=border_fg, bg=BG_FELT)
    console.draw_rect(btn_x + 1, y + 1, btn_w - 2, 1, ch=ord(' '), bg=bg)
    console.print(btn_x + 1, y + 1, padded[:btn_w - 2], fg=fg, bg=bg)
    console.print(btn_x + btn_w - 1, y + 1, "\u2551", fg=border_fg, bg=BG_FELT)

    console.print(btn_x, y + 2, "\u255a", fg=border_fg, bg=BG_FELT)
    console.print(btn_x + btn_w - 1, y + 2, "\u255d", fg=border_fg, bg=BG_FELT)
    for sx in range(btn_x + 1, btn_x + btn_w - 1):
        console.print(sx, y + 2, "\u2550", fg=border_fg, bg=BG_FELT)

    return 3


def draw_draft_card(
    console: tcod.console.Console,
    x: int,
    y: int,
    width: int,
    height: int,
    icon_chars: list[list[str]] | None,
    icon_char: str,
    name: str,
    description: str,
    category: str,
    color: tuple[int, int, int],
    selected: bool,
) -> None:
    """Draw a draft pick card with optional 3x3 piece art."""
    inner_w = width - 2
    CARD_FACE = (38, 40, 55)
    SHADOW_COLOR = (8, 15, 10)

    if selected:
        card_bg = (28, 58, 38)
        border_fg = _brighten(color, 1.5)
    else:
        card_bg = CARD_FACE
        border_fg = color

    # Drop shadow
    for sy in range(y + 1, y + height + 1):
        if sy < console.height:
            console.print(min(x + width, console.width - 1), sy, " ", bg=SHADOW_COLOR)
    for sx in range(x + 1, x + width + 1):
        if y + height < console.height:
            console.print(min(sx, console.width - 1), y + height, " ", bg=SHADOW_COLOR)

    # Card face
    console.draw_rect(x, y, width, height, ch=ord(' '), bg=card_bg)

    # Double-line border
    console.print(x, y, "\u2554", fg=border_fg, bg=card_bg)
    console.print(x + width - 1, y, "\u2557", fg=border_fg, bg=card_bg)
    console.print(x, y + height - 1, "\u255a", fg=border_fg, bg=card_bg)
    console.print(x + width - 1, y + height - 1, "\u255d", fg=border_fg, bg=card_bg)
    for sx in range(x + 1, x + width - 1):
        console.print(sx, y, "\u2550", fg=border_fg, bg=card_bg)
        console.print(sx, y + height - 1, "\u2550", fg=border_fg, bg=card_bg)
    for sy in range(y + 1, y + height - 1):
        console.print(x, sy, "\u2551", fg=border_fg, bg=card_bg)
        console.print(x + width - 1, sy, "\u2551", fg=border_fg, bg=card_bg)

    # Category banner
    banner_bg = _dim(color, 0.25)
    banner_fg = _brighten(color, 1.2)
    cat_text = category.center(inner_w)
    console.draw_rect(x + 1, y + 1, inner_w, 1, ch=ord(' '), bg=banner_bg)
    console.print(x + 1, y + 1, cat_text[:inner_w], fg=banner_fg, bg=banner_bg)

    # Icon area: 3 rows with tinted background
    icon_bg = _blend(card_bg, _dim(color, 0.10), 0.5)
    if selected:
        icon_bg = _blend(card_bg, color, 0.08)
    icon_start = y + 2
    for dy in range(3):
        console.draw_rect(x + 1, icon_start + dy, inner_w, 1, ch=ord(' '), bg=icon_bg)

    # Draw 3x3 piece art or single icon
    icon_fg = color
    if icon_chars:
        art_x = x + (width - 3) // 2
        for dy in range(3):
            for dx in range(3):
                console.print(art_x + dx, icon_start + dy, icon_chars[dy][dx], fg=icon_fg, bg=icon_bg)
    else:
        icon_cx = x + width // 2
        console.print(icon_cx, icon_start + 1, icon_char, fg=icon_fg, bg=icon_bg)

    # Corner dots in icon area
    dot_fg = _dim(color, 0.25)
    console.print(x + 1, icon_start, "\u00b7", fg=dot_fg, bg=icon_bg)
    console.print(x + inner_w, icon_start, "\u00b7", fg=dot_fg, bg=icon_bg)
    console.print(x + 1, icon_start + 2, "\u00b7", fg=dot_fg, bg=icon_bg)
    console.print(x + inner_w, icon_start + 2, "\u00b7", fg=dot_fg, bg=icon_bg)

    # Name
    name_row = icon_start + 3
    name_fg = (255, 255, 255)
    name_x = x + (width - len(name)) // 2
    console.print(max(x + 1, name_x), name_row, name[:inner_w], fg=name_fg, bg=card_bg)

    # Ornamental separator
    sep_row = name_row + 1
    sep_fg = _dim(border_fg, 0.35)
    sep_str = ""
    for si in range(inner_w):
        sep_str += "\u00b7" if si % 2 == 1 else "\u2500"
    console.print(x + 1, sep_row, sep_str[:inner_w], fg=sep_fg, bg=card_bg)

    # Description
    desc_lines = _wrap_text(description, inner_w)
    desc_fg = FG_DIM
    desc_start = sep_row + 1
    for i, line in enumerate(desc_lines):
        row = desc_start + i
        if row >= y + height - 1:
            break
        line_x = x + (width - len(line)) // 2
        console.print(max(x + 1, line_x), row, line[:inner_w], fg=desc_fg, bg=card_bg)

    # Selected indicator: arrows outside card + shadow
    if selected:
        mid_y = y + height // 2
        if x > 0:
            console.print(x - 1, mid_y, "\u25b6", fg=(255, 255, 200), bg=BG_FELT)
        if x + width + 1 < console.width:
            console.print(x + width + 1, mid_y, "\u25c0", fg=(255, 255, 200), bg=BG_FELT)


def _brighten(c: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Brighten a color by a factor (>1.0 to brighten)."""
    return (
        min(255, int(c[0] * factor)),
        min(255, int(c[1] * factor)),
        min(255, int(c[2] * factor)),
    )


def clear(console: tcod.console.Console) -> None:
    console.clear(fg=FG_TEXT, bg=BG_BLACK)


def apply_board_vignette(
    console: tcod.console.Console,
    board: Board,
    ox: int,
    oy: int,
) -> None:
    """Darken 2 rings of edge cells for a vignette effect."""
    total_w = board.width * TILE_W
    total_h = board.height * TILE_H
    # Ring definitions: (cells from edge, darkening factor)
    rings = [(0, 0.85), (1, 0.92)]
    for ring_dist, factor in rings:
        for by in range(board.height):
            for bx in range(board.width):
                edge_dist = min(bx, by, board.width - 1 - bx, board.height - 1 - by)
                if edge_dist == ring_dist:
                    sy = oy + by * TILE_H
                    sx = ox + bx * TILE_W
                    # Clamp to console bounds
                    y1 = max(0, sy)
                    y2 = min(console.height, sy + TILE_H)
                    x1 = max(0, sx)
                    x2 = min(console.width, sx + TILE_W)
                    if y1 < y2 and x1 < x2:
                        bg_slice = console.rgb['bg'][y1:y2, x1:x2]
                        bg_slice[:] = (bg_slice.astype(np.float32) * factor).astype(np.uint8)


def apply_modifier_glow(
    console: tcod.console.Console,
    board: Board,
    ox: int,
    oy: int,
) -> None:
    """Additive-blend modifier colors into surrounding cells (radius 2, 15% max)."""
    for (mx, my), cm in board.cell_modifiers.items():
        color = np.array(cm.color, dtype=np.float32)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if dx == 0 and dy == 0:
                    continue
                bx, by = mx + dx, my + dy
                if not board.in_bounds(bx, by):
                    continue
                dist = max(abs(dx), abs(dy))
                intensity = 0.15 if dist == 1 else 0.07
                sy = oy + by * TILE_H
                sx = ox + bx * TILE_W
                y1 = max(0, sy)
                y2 = min(console.height, sy + TILE_H)
                x1 = max(0, sx)
                x2 = min(console.width, sx + TILE_W)
                if y1 < y2 and x1 < x2:
                    bg_slice = console.rgb['bg'][y1:y2, x1:x2]
                    blended = bg_slice.astype(np.float32) + color * intensity
                    bg_slice[:] = np.clip(blended, 0, 255).astype(np.uint8)


def draw_capture_sparkle(
    console: tcod.console.Console,
    cx: int,
    cy: int,
    progress: float,
    color: tuple[int, int, int] = (255, 255, 100),
) -> None:
    """Draw a sparkle effect at console position using draw_semigraphics.

    progress: 0.0 (start) to 1.0 (end) of animation.
    Creates 8 sparkle points radiating outward rendered as 2x sub-pixel.
    """
    if progress >= 1.0:
        return
    # 6x6 RGB buffer (3x3 cells at 2x2 sub-pixel resolution)
    buf = np.zeros((6, 6, 3), dtype=np.uint8)
    # 8 sparkle directions
    dirs = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    radius = progress * 2.5
    alpha = max(0.0, 1.0 - progress)
    for ddx, ddy in dirs:
        px = int(3 + ddx * radius)
        py = int(3 + ddy * radius)
        if 0 <= px < 6 and 0 <= py < 6:
            buf[py, px] = (
                int(color[0] * alpha),
                int(color[1] * alpha),
                int(color[2] * alpha),
            )
    # Center bright pixel
    if alpha > 0.3:
        buf[3, 3] = (int(255 * alpha), int(255 * alpha), int(255 * alpha))
    # draw_semigraphics renders 2x2 pixels per cell -> 3x3 cells
    start_x = cx - 1
    start_y = cy - 1
    if 0 <= start_x and start_x + 3 <= console.width and 0 <= start_y and start_y + 3 <= console.height:
        console.draw_semigraphics(buf, x=start_x, y=start_y)


def _blend(
    c1: tuple[int, int, int], c2: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    return (
        int(c1[0] * (1 - t) + c2[0] * t),
        int(c1[1] * (1 - t) + c2[1] * t),
        int(c1[2] * (1 - t) + c2[2] * t),
    )


def _dim(c: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (int(c[0] * t), int(c[1] * t), int(c[2] * t))


def draw_tooltip(
    console: tcod.console.Console,
    board: Board,
    bx: int,
    by: int,
    x: int,
    y: int,
    width: int,
) -> None:
    """Draw a tooltip panel showing info about the cell at (bx, by)."""
    bx, by = int(bx), int(by)
    if not board.in_bounds(bx, by):
        return

    lines: list[tuple[str, tuple[int, int, int]]] = []
    lines.append((f"Cell ({chr(ord('a') + bx)}{board.height - by})", FG_TEXT))

    # Cell modifier info
    if (bx, by) in board.cell_modifiers:
        cm = board.cell_modifiers[(bx, by)]
        lines.append((f"Cell mod: {cm.name}", cm.color))
        for _key, tmpl in CELL_MODIFIERS.items():
            if tmpl["effect"] == cm.effect:
                lines.append((f"  {tmpl['description']}", FG_DIM))
                break

    # Border modifier info
    if (bx, by) in board.border_modifiers:
        bm = board.border_modifiers[(bx, by)]
        lines.append((f"Border: {bm.name}", bm.border_color))
        for _key, tmpl in BORDER_MODIFIERS.items():
            if tmpl["effect"] == bm.effect:
                lines.append((f"  {tmpl['description']}", FG_DIM))
                break

    # Piece info
    piece = board.get_piece_at(bx, by)
    if piece:
        team_str = "Player" if piece.team == Team.PLAYER else "Enemy"
        fg = FG_PLAYER if piece.team == Team.PLAYER else FG_ENEMY
        lines.append((f"{team_str} {piece.piece_type.value} (val {piece.value})", fg))
        if piece.modifiers:
            for mod in piece.modifiers:
                lines.append((f"  Mod: {mod.name}", (200, 200, 100)))
                lines.append((f"    {mod.description}", FG_DIM))
        if piece.cell_modifier:
            lines.append((f"  Absorbed: {piece.cell_modifier.name}", piece.cell_modifier.color))

    if (bx, by) in board.blocked_tiles:
        lines.append(("Blocked tile", FG_DIM))

    if len(lines) <= 1:
        lines.append(("Empty", FG_DIM))

    height = len(lines) + 2  # +2 for frame border
    # Clamp position to stay on screen
    if x + width > console.width:
        x = max(0, console.width - width)
    if y + height > console.height:
        y = max(0, console.height - height)

    # Render on offscreen console, then blit with transparency
    tip = tcod.console.Console(width, height, order="C")
    tip.draw_frame(0, 0, width, height, title="", clear=True, fg=FG_DIM, bg=BG_PANEL)
    for i, (text, fg) in enumerate(lines):
        tip.print(1, 1 + i, text[:width - 2], fg=fg, bg=BG_PANEL)
    tip.blit(console, dest_x=x, dest_y=y, bg_alpha=0.85)


# --- Tournament / Menu helpers ---


def draw_menu_option(
    console: tcod.console.Console,
    x: int,
    y: int,
    w: int,
    label: str,
    desc: str,
    selected: bool,
    locked: bool = False,
) -> None:
    """Draw a menu list item with highlight, description, and optional lock."""
    if locked:
        fg_label = (80, 80, 80)
        fg_desc = (50, 50, 50)
        bg = BG_BLACK
        prefix = "  [LOCKED] "
    elif selected:
        fg_label = (255, 255, 255)
        fg_desc = (180, 180, 180)
        bg = (40, 40, 80)
        prefix = "> "
    else:
        fg_label = FG_TEXT
        fg_desc = FG_DIM
        bg = BG_BLACK
        prefix = "  "

    console.draw_rect(x, y, w, 2, ch=ord(' '), bg=bg)
    console.print(x + 1, y, f"{prefix}{label}", fg=fg_label, bg=bg)
    console.print(x + 3, y + 1, desc[:w - 4], fg=fg_desc, bg=bg)


def draw_boss_intro(
    console: tcod.console.Console,
    boss_type: str,
    round_num: int,
    total_rounds: int,
    difficulty: str,
) -> None:
    """Draw a full-screen boss introduction panel."""
    cw, ch = console.width, console.height
    console.draw_rect(0, 0, cw, ch, ch=ord(' '), bg=(10, 10, 20))

    # Boss name
    boss_name = f"THE {boss_type.upper()}"
    name_x = (cw - len(boss_name)) // 2
    name_y = ch // 2 - 4
    console.print(name_x, name_y, boss_name, fg=(255, 80, 80), bg=(10, 10, 20))

    # Decorative lines
    deco = "\u2550" * (len(boss_name) + 8)
    dx = (cw - len(deco)) // 2
    console.print(dx, name_y - 1, deco, fg=(120, 40, 40), bg=(10, 10, 20))
    console.print(dx, name_y + 1, deco, fg=(120, 40, 40), bg=(10, 10, 20))

    # Boss piece art (centered)
    from pieces import PieceType
    boss_pt_map = {
        "pawn": PieceType.PAWN, "knight": PieceType.KNIGHT,
        "bishop": PieceType.BISHOP, "rook": PieceType.ROOK,
        "queen": PieceType.QUEEN, "king": PieceType.KING,
    }
    pt = boss_pt_map.get(boss_type.lower())
    if pt:
        chars = piece_chars(pt)
        ax = (cw - 3) // 2
        ay = name_y + 3
        for dy in range(3):
            for dx_c in range(3):
                console.print(ax + dx_c, ay + dy, chars[dy][dx_c],
                              fg=(255, 100, 100), bg=(10, 10, 20))

    # Round info
    round_str = f"Round {round_num} of {total_rounds}"
    rx = (cw - len(round_str)) // 2
    console.print(rx, name_y + 7, round_str, fg=FG_TEXT, bg=(10, 10, 20))

    # Difficulty
    diff_colors = {
        "basic": (100, 200, 100),
        "extreme": (255, 180, 60),
        "grandmaster": (255, 60, 60),
    }
    diff_fg = diff_colors.get(difficulty, FG_TEXT)
    diff_str = f"Difficulty: {difficulty.capitalize()}"
    ddx = (cw - len(diff_str)) // 2
    console.print(ddx, name_y + 9, diff_str, fg=diff_fg, bg=(10, 10, 20))

    # Prompt
    prompt = "Press ENTER to fight"
    px = (cw - len(prompt)) // 2
    console.print(px, ch - 4, prompt, fg=(200, 200, 200), bg=(10, 10, 20))


def draw_elo_display(
    console: tcod.console.Console,
    x: int,
    y: int,
    elo: int,
) -> None:
    """Draw a small ELO counter widget."""
    label = f"\u2666 ELO: {elo}"
    console.print(x, y, label, fg=(255, 215, 0), bg=BG_BLACK)


def draw_tournament_progress(
    console: tcod.console.Console,
    x: int,
    y: int,
    boss_index: int,
    total_bosses: int,
) -> None:
    """Draw progress dots/bar for tournament boss progression."""
    label = "Progress: "
    console.print(x, y, label, fg=FG_TEXT, bg=BG_PANEL)
    dot_x = x + len(label)
    for i in range(total_bosses):
        if i < boss_index:
            console.print(dot_x + i * 2, y, "\u25c9", fg=(80, 255, 80), bg=BG_PANEL)
        elif i == boss_index:
            console.print(dot_x + i * 2, y, "\u25cb", fg=(255, 220, 60), bg=BG_PANEL)
        else:
            console.print(dot_x + i * 2, y, "\u25cb", fg=FG_DIM, bg=BG_PANEL)
