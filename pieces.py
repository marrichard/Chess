"""Chess piece definitions, movement rules, and modifier system."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from board import Board


class PieceType(Enum):
    PAWN = "pawn"
    KNIGHT = "knight"
    BISHOP = "bishop"
    ROOK = "rook"
    QUEEN = "queen"
    KING = "king"


class Team(Enum):
    PLAYER = "player"
    ENEMY = "enemy"


# Display characters
PIECE_CHARS = {
    (PieceType.KING, Team.PLAYER): "\u2654",
    (PieceType.QUEEN, Team.PLAYER): "\u2655",
    (PieceType.ROOK, Team.PLAYER): "\u2656",
    (PieceType.BISHOP, Team.PLAYER): "\u2657",
    (PieceType.KNIGHT, Team.PLAYER): "\u2658",
    (PieceType.PAWN, Team.PLAYER): "\u2659",
    (PieceType.KING, Team.ENEMY): "\u265A",
    (PieceType.QUEEN, Team.ENEMY): "\u265B",
    (PieceType.ROOK, Team.ENEMY): "\u265C",
    (PieceType.BISHOP, Team.ENEMY): "\u265D",
    (PieceType.KNIGHT, Team.ENEMY): "\u265E",
    (PieceType.PAWN, Team.ENEMY): "\u265F",
}

# Fallback single-letter display
PIECE_LETTERS = {
    (PieceType.KING, Team.PLAYER): "K",
    (PieceType.QUEEN, Team.PLAYER): "Q",
    (PieceType.ROOK, Team.PLAYER): "R",
    (PieceType.BISHOP, Team.PLAYER): "B",
    (PieceType.KNIGHT, Team.PLAYER): "N",
    (PieceType.PAWN, Team.PLAYER): "P",
    (PieceType.KING, Team.ENEMY): "k",
    (PieceType.QUEEN, Team.ENEMY): "q",
    (PieceType.ROOK, Team.ENEMY): "r",
    (PieceType.BISHOP, Team.ENEMY): "b",
    (PieceType.KNIGHT, Team.ENEMY): "n",
    (PieceType.PAWN, Team.ENEMY): "p",
}

# Piece value for scoring/AI
PIECE_VALUES = {
    PieceType.PAWN: 1,
    PieceType.KNIGHT: 3,
    PieceType.BISHOP: 3,
    PieceType.ROOK: 5,
    PieceType.QUEEN: 9,
    PieceType.KING: 100,
}


@dataclass
class Modifier:
    """A roguelike upgrade applied to a piece."""
    name: str
    description: str
    # Effect callbacks are checked by game logic
    effect: str  # e.g. "flaming", "armored", "swift", "piercing"


@dataclass
class Piece:
    """A chess piece with position and optional modifiers."""
    piece_type: PieceType
    team: Team
    x: int = 0
    y: int = 0
    modifiers: list[Modifier] = field(default_factory=list)
    has_moved: bool = False
    alive: bool = True
    cell_modifier: object | None = None  # CellModifier absorbed from a cell

    @property
    def char(self) -> str:
        return PIECE_LETTERS.get((self.piece_type, self.team), "?")

    @property
    def value(self) -> int:
        return PIECE_VALUES.get(self.piece_type, 0)

    def get_raw_moves(self, board_w: int, board_h: int) -> list[tuple[int, int]]:
        """Get all potential move destinations ignoring other pieces."""
        moves = []
        x, y = self.x, self.y

        if self.piece_type == PieceType.PAWN:
            direction = -1 if self.team == Team.PLAYER else 1
            # Forward move
            ny = y + direction
            if 0 <= ny < board_h:
                moves.append((x, ny))
            # Double move from starting position
            if not self.has_moved:
                ny2 = y + 2 * direction
                if 0 <= ny2 < board_h:
                    moves.append((x, ny2))
            # Diagonal captures
            for dx in [-1, 1]:
                nx = x + dx
                ny = y + direction
                if 0 <= nx < board_w and 0 <= ny < board_h:
                    moves.append((nx, ny))

        elif self.piece_type == PieceType.KNIGHT:
            for dx, dy in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < board_w and 0 <= ny < board_h:
                    moves.append((nx, ny))

        elif self.piece_type == PieceType.BISHOP:
            for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        elif self.piece_type == PieceType.ROOK:
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        elif self.piece_type == PieceType.QUEEN:
            for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        elif self.piece_type == PieceType.KING:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))

        return moves

    def get_valid_moves(self, board: Board) -> list[tuple[int, int]]:
        """Get valid moves considering the board state."""
        valid = []
        x, y = self.x, self.y

        if self.piece_type == PieceType.PAWN:
            direction = -1 if self.team == Team.PLAYER else 1
            # Forward (must be empty)
            ny = y + direction
            if 0 <= ny < board.height:
                if board.is_empty(x, ny):
                    valid.append((x, ny))
                    # Double move
                    if not self.has_moved:
                        ny2 = y + 2 * direction
                        if 0 <= ny2 < board.height and board.is_empty(x, ny2):
                            valid.append((x, ny2))
            # Diagonal captures (must have enemy)
            for dx in [-1, 1]:
                nx = x + dx
                ny = y + direction
                if 0 <= nx < board.width and 0 <= ny < board.height:
                    target = board.get_piece_at(nx, ny)
                    if target and target.team != self.team:
                        valid.append((nx, ny))

        elif self.piece_type == PieceType.KNIGHT:
            for dx, dy in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < board.width and 0 <= ny < board.height:
                    target = board.get_piece_at(nx, ny)
                    if not target or target.team != self.team:
                        valid.append((nx, ny))

        elif self.piece_type in (PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN):
            dirs = []
            if self.piece_type in (PieceType.BISHOP, PieceType.QUEEN):
                dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
            if self.piece_type in (PieceType.ROOK, PieceType.QUEEN):
                dirs += [(-1,0),(1,0),(0,-1),(0,1)]
            has_piercing = any(m.effect == "piercing" for m in self.modifiers)
            has_phase = (self.cell_modifier and self.cell_modifier.effect == "phase")
            for dx, dy in dirs:
                skipped = False
                for dist in range(1, max(board.width, board.height)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if not (0 <= nx < board.width and 0 <= ny < board.height):
                        break
                    if board.is_blocked(nx, ny):
                        break
                    target = board.get_piece_at(nx, ny)
                    if target:
                        if target.team == self.team:
                            # Phase: can pass through friendly pieces
                            if has_phase:
                                continue
                            # Piercing: skip one blocker (friend or foe)
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                        else:
                            valid.append((nx, ny))
                            # Piercing: can skip one blocker and still capture behind
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                    valid.append((nx, ny))

        elif self.piece_type == PieceType.KING:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < board.width and 0 <= ny < board.height:
                        if not board.is_blocked(nx, ny):
                            target = board.get_piece_at(nx, ny)
                            if not target or target.team != self.team:
                                valid.append((nx, ny))

        # Swift modifier: king-style moves in addition to normal moves
        has_extra_move = any(m.effect == "swift" for m in self.modifiers)
        # Haste cell modifier: same as swift but temporary
        if self.cell_modifier and self.cell_modifier.effect == "haste":
            has_extra_move = True
        if has_extra_move:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < board.width and 0 <= ny < board.height:
                        if not board.is_blocked(nx, ny):
                            target = board.get_piece_at(nx, ny)
                            if not target or target.team != self.team:
                                if (nx, ny) not in valid:
                                    valid.append((nx, ny))

        # Phase cell modifier for non-sliding pieces (knight): allow moving
        # through friendly-occupied squares (knight already jumps, so no change)

        return valid

    def get_capture_moves(self, board: Board) -> list[tuple[int, int]]:
        """Get only moves that result in a capture."""
        return [
            (mx, my) for mx, my in self.get_valid_moves(board)
            if board.get_piece_at(mx, my) and board.get_piece_at(mx, my).team != self.team
        ]

    def copy(self) -> Piece:
        p = Piece(
            piece_type=self.piece_type,
            team=self.team,
            x=self.x,
            y=self.y,
            modifiers=list(self.modifiers),
            has_moved=self.has_moved,
            alive=self.alive,
        )
        if self.cell_modifier and hasattr(self.cell_modifier, 'copy'):
            p.cell_modifier = self.cell_modifier.copy()
        else:
            p.cell_modifier = self.cell_modifier
        return p


# Predefined modifiers
MODIFIERS = {
    "flaming": Modifier("Flaming", "Captures also damage adjacent tiles", "flaming"),
    "armored": Modifier("Armored", "Survives one capture attempt", "armored"),
    "swift": Modifier("Swift", "Can also move one square in any direction", "swift"),
    "piercing": Modifier("Piercing", "Sliding pieces can capture through one piece", "piercing"),
    "royal": Modifier("Royal", "Worth double points when scoring", "royal"),
}
