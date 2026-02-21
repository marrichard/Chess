"""Take a screenshot of the game board with all piece types visible."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tcod.tileset
import tcod.context
import tcod.console

from piece_tiles import install_piece_tiles
from pieces import Piece, PieceType, Team
from board import Board
from engine import make_square_tileset
import renderer

# Load font with square cells and install piece tiles
path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "consola.ttf")
tileset = make_square_tileset(path, tile_height=20)
install_piece_tiles(tileset)

# Create a board with all 6 piece types
board = Board(8, 8)
# Player pieces (bottom)
board.place_piece(Piece(PieceType.KING, Team.PLAYER), 4, 7)
board.place_piece(Piece(PieceType.QUEEN, Team.PLAYER), 3, 7)
board.place_piece(Piece(PieceType.ROOK, Team.PLAYER), 0, 7)
board.place_piece(Piece(PieceType.BISHOP, Team.PLAYER), 2, 7)
board.place_piece(Piece(PieceType.KNIGHT, Team.PLAYER), 1, 7)
board.place_piece(Piece(PieceType.PAWN, Team.PLAYER), 0, 6)
board.place_piece(Piece(PieceType.PAWN, Team.PLAYER), 1, 6)
board.place_piece(Piece(PieceType.PAWN, Team.PLAYER), 2, 6)

# Enemy pieces (top)
board.place_piece(Piece(PieceType.KING, Team.ENEMY), 4, 0)
board.place_piece(Piece(PieceType.QUEEN, Team.ENEMY), 3, 0)
board.place_piece(Piece(PieceType.ROOK, Team.ENEMY), 0, 0)
board.place_piece(Piece(PieceType.BISHOP, Team.ENEMY), 2, 0)
board.place_piece(Piece(PieceType.KNIGHT, Team.ENEMY), 1, 0)
board.place_piece(Piece(PieceType.PAWN, Team.ENEMY), 0, 1)

cols, rows = 80, 50
with tcod.context.new(columns=cols, rows=rows, tileset=tileset, title="Screenshot", vsync=True) as context:
    console = tcod.console.Console(cols, rows, order="C")
    renderer.clear(console)

    bw, bh = renderer.board_pixel_size(board)
    ox = (cols - bw) // 2
    oy = (rows - bh) // 2
    renderer.draw_board_labels(console, board, ox=ox, oy=oy)
    renderer.draw_board(console, board, ox=ox, oy=oy, cursor=(4, 7))

    context.present(console)
    context.save_screenshot("screenshot.png")
    print("Screenshot saved to screenshot.png")
