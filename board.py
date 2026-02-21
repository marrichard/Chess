"""Grid/board logic — placement, validation, capture detection."""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pieces import Piece, Team, PieceType

if TYPE_CHECKING:
    from modifiers import CellModifier, BorderModifier


@dataclass
class Board:
    """A chess-like grid that holds pieces and obstacles."""
    width: int = 8
    height: int = 8
    pieces: list[Piece] = field(default_factory=list)
    blocked_tiles: set[tuple[int, int]] = field(default_factory=set)
    cell_modifiers: dict[tuple[int, int], CellModifier] = field(default_factory=dict)
    border_modifiers: dict[tuple[int, int], BorderModifier] = field(default_factory=dict)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_empty(self, x: int, y: int) -> bool:
        if (x, y) in self.blocked_tiles:
            return False
        return self.get_piece_at(x, y) is None

    def is_blocked(self, x: int, y: int) -> bool:
        return (x, y) in self.blocked_tiles

    def get_piece_at(self, x: int, y: int) -> Piece | None:
        for p in self.pieces:
            if p.alive and p.x == x and p.y == y:
                return p
        return None

    def get_team_pieces(self, team: Team) -> list[Piece]:
        return [p for p in self.pieces if p.alive and p.team == team]

    def place_piece(self, piece: Piece, x: int, y: int) -> bool:
        """Place a piece on the board. Returns False if position is invalid."""
        if not self.in_bounds(x, y):
            return False
        if self.is_blocked(x, y):
            return False
        if self.get_piece_at(x, y) is not None:
            return False
        piece.x = x
        piece.y = y
        piece.alive = True
        if piece not in self.pieces:
            self.pieces.append(piece)
        return True

    def move_piece(self, piece: Piece, nx: int, ny: int, rng: random.Random | None = None) -> Piece | None:
        """Move a piece to (nx, ny). Returns captured piece or None."""
        import random as _random_mod
        _rng = rng or _random_mod

        captured = None
        target = self.get_piece_at(nx, ny)
        if target and target.team != piece.team:
            # Fortified border modifier: piece on this cell cannot be captured
            if (target.x, target.y) in self.border_modifiers:
                bm = self.border_modifiers[(target.x, target.y)]
                if bm.effect == "fortified":
                    # Can't capture — move is blocked, piece doesn't move
                    return None

            # Thorns border modifier: attacker also dies
            thorns_kill_attacker = False
            if (target.x, target.y) in self.border_modifiers:
                bm = self.border_modifiers[(target.x, target.y)]
                if bm.effect == "thorns":
                    thorns_kill_attacker = True

            # Shield cell modifier: target survives one capture (like temporary armored)
            has_shield = (target.cell_modifier and target.cell_modifier.effect == "shield")

            # Check armored modifier
            if any(m.effect == "armored" for m in target.modifiers):
                target.modifiers = [m for m in target.modifiers if m.effect != "armored"]
            elif has_shield:
                target.cell_modifier = None  # consume the shield
            else:
                target.alive = False
                captured = target

            # Thorns: kill attacker after capture resolves
            if thorns_kill_attacker and captured:
                piece.alive = False

        piece.x = nx
        piece.y = ny
        piece.has_moved = True

        # Pawn promotion
        self.check_promotion(piece, _rng)

        # Flaming modifier: damage adjacent enemy pieces
        if any(m.effect == "flaming" for m in piece.modifiers) and captured:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    adj = self.get_piece_at(nx + dx, ny + dy)
                    if adj and adj.team != piece.team:
                        if any(m.effect == "armored" for m in adj.modifiers):
                            adj.modifiers = [m for m in adj.modifiers if m.effect != "armored"]
                        else:
                            adj.alive = False

        # Rage cell modifier: captures also kill one random adjacent enemy
        if captured and piece.cell_modifier and piece.cell_modifier.effect == "rage":
            adj_enemies = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    adj = self.get_piece_at(nx + dx, ny + dy)
                    if adj and adj.team != piece.team and adj.alive:
                        adj_enemies.append(adj)
            if adj_enemies:
                victim = _rng.choice(adj_enemies)
                if any(m.effect == "armored" for m in victim.modifiers):
                    victim.modifiers = [m for m in victim.modifiers if m.effect != "armored"]
                else:
                    victim.alive = False

        # Absorb cell modifier at destination (if piece is alive and no cell mod yet)
        if piece.alive and piece.cell_modifier is None and (nx, ny) in self.cell_modifiers:
            from modifiers import apply_cell_modifier
            apply_cell_modifier(piece, self.cell_modifiers[(nx, ny)])
            del self.cell_modifiers[(nx, ny)]

        return captured

    def check_promotion(self, piece: Piece, rng: random.Random | None = None) -> bool:
        """Promote a pawn that reached the far rank. Returns True if promoted."""
        if not piece.alive or piece.piece_type != PieceType.PAWN:
            return False
        import random as _random_mod
        _rng = rng or _random_mod
        promote_rank = 0 if piece.team == Team.PLAYER else self.height - 1
        if piece.y == promote_rank:
            promo_choices = [PieceType.KNIGHT, PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN]
            piece.piece_type = _rng.choice(promo_choices)
            return True
        return False

    def remove_piece(self, piece: Piece) -> None:
        piece.alive = False

    def reset_round(self) -> None:
        """Reset cell modifiers to original cells, strip absorbed cell mods from pieces."""
        from modifiers import reset_cell_modifiers
        reset_cell_modifiers(self, self.cell_modifiers)

    def clear(self) -> None:
        self.pieces.clear()
        self.blocked_tiles.clear()
        self.cell_modifiers.clear()
        # Note: border_modifiers persist across rounds, not cleared here

    def add_obstacle(self, x: int, y: int) -> None:
        self.blocked_tiles.add((x, y))

    def is_square_attacked_by(self, x: int, y: int, team: Team) -> bool:
        """Check if a square is attacked by any piece of the given team."""
        for p in self.get_team_pieces(team):
            if (x, y) in p.get_valid_moves(self):
                return True
        return False

    def get_all_valid_moves(self, team: Team) -> list[tuple[Piece, int, int]]:
        """Get all valid (piece, dest_x, dest_y) for a team."""
        result = []
        for p in self.get_team_pieces(team):
            for mx, my in p.get_valid_moves(self):
                result.append((p, mx, my))
        return result

    def count_alive(self, team: Team) -> int:
        return len(self.get_team_pieces(team))

    def copy(self) -> Board:
        new_board = Board(width=self.width, height=self.height)
        new_board.pieces = [p.copy() for p in self.pieces]
        new_board.blocked_tiles = set(self.blocked_tiles)
        new_board.cell_modifiers = {k: v.copy() for k, v in self.cell_modifiers.items()}
        new_board.border_modifiers = {k: v.copy() for k, v in self.border_modifiers.items()}
        return new_board
