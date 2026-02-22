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

    def move_piece(self, piece: Piece, nx: int, ny: int, rng: random.Random | None = None,
                   active_synergies: list[str] | None = None) -> Piece | None:
        """Move a piece to (nx, ny). Returns captured piece or None.

        HP combat: attacker deals damage to target. If target survives, attacker
        bounces back to origin. If target dies, attacker moves to cell.
        """
        import random as _random_mod
        _rng = rng or _random_mod
        _synergies = active_synergies or []

        old_x, old_y = piece.x, piece.y
        captured = None
        target = self.get_piece_at(nx, ny)

        if target and target.team != piece.team:
            # Fortified border modifier: piece on this cell cannot be captured
            if (target.x, target.y) in self.border_modifiers:
                bm = self.border_modifiers[(target.x, target.y)]
                if bm.effect == "fortified":
                    return None

            # --- Calculate damage ---
            damage = piece.attack

            # Gambler: 50% chance damage = 0 (unless glass_cannon synergy)
            if piece.piece_type == PieceType.GAMBLER:
                if "glass_cannon" in _synergies:
                    pass  # never misses
                elif _rng.random() < 0.5:
                    damage = 0

            # Anchor piece aura: reduce damage if target is near an anchor
            damage = max(0, damage - self.get_anchor_damage_reduction(target.x, target.y, target.team))

            # Armored modifier: -2 incoming damage (persistent, not consumed)
            if any(m.effect == "armored" for m in target.modifiers):
                damage = max(0, damage - 2)

            # Shield cell modifier: -3 incoming damage (consumed)
            has_shield = (target.cell_modifier and target.cell_modifier.effect == "shield")
            if has_shield:
                damage = max(0, damage - 3)
                target.cell_modifier = None  # consume the shield

            # Apply damage
            target.hp -= damage

            # Thorns border modifier: 2 retaliation damage to attacker
            if (target.x, target.y) in self.border_modifiers:
                bm = self.border_modifiers[(target.x, target.y)]
                if bm.effect == "thorns":
                    piece.hp -= 2
                    if piece.hp <= 0:
                        piece.alive = False

            # Leech: heal attacker equal to damage dealt
            if piece.piece_type == PieceType.LEECH and damage > 0:
                piece.hp = min(piece.max_hp, piece.hp + damage)

            # Glass cannon synergy: gambler takes double damage from retaliation
            if piece.piece_type == PieceType.GAMBLER and "glass_cannon" in _synergies:
                # Target hits back for double its attack if it survives
                if target.hp > 0 and target.attack > 0:
                    piece.hp -= target.attack * 2

            if target.hp <= 0:
                # Target dies
                target.alive = False
                captured = target

                # Attacker moves to target cell
                piece.x = nx
                piece.y = ny
                piece.has_moved = True

                # Leech on kill: steal one random modifier from victim
                if piece.piece_type == PieceType.LEECH and target.modifiers:
                    stolen = _rng.choice(target.modifiers)
                    if not any(m.effect == stolen.effect for m in piece.modifiers):
                        piece.modifiers.append(stolen)
            else:
                # Target survives — attacker bounces back to origin
                piece.has_moved = True
                # Piece stays at old_x, old_y (already there, no position change)

        else:
            # Non-capture move
            piece.x = nx
            piece.y = ny
            piece.has_moved = True

        # Void: after moving, add origin cell to blocked_tiles
        if piece.piece_type == PieceType.VOID and (piece.x != old_x or piece.y != old_y):
            self.blocked_tiles.add((old_x, old_y))

        # Pawn promotion
        if piece.alive:
            self.check_promotion(piece, _rng)

        # Flaming modifier: 2 flat damage to adjacent enemies on kill
        if any(m.effect == "flaming" for m in piece.modifiers) and captured:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    adj = self.get_piece_at(piece.x + dx, piece.y + dy)
                    if adj and adj.team != piece.team and adj.alive:
                        adj.hp -= 2
                        if adj.hp <= 0:
                            adj.alive = False

        # Rage cell modifier: 2 damage to random adjacent enemy on kill
        if captured and piece.cell_modifier and piece.cell_modifier.effect == "rage":
            adj_enemies = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    adj = self.get_piece_at(piece.x + dx, piece.y + dy)
                    if adj and adj.team != piece.team and adj.alive:
                        adj_enemies.append(adj)
            if adj_enemies:
                victim = _rng.choice(adj_enemies)
                victim.hp -= 2
                if victim.hp <= 0:
                    victim.alive = False

        # Absorb cell modifier at destination (if piece is alive and no cell mod yet)
        if piece.alive and piece.cell_modifier is None and (piece.x, piece.y) in self.cell_modifiers:
            from modifiers import apply_cell_modifier
            apply_cell_modifier(piece, self.cell_modifiers[(piece.x, piece.y)])
            del self.cell_modifiers[(piece.x, piece.y)]

        return captured

    def get_anchor_damage_reduction(self, x: int, y: int, team: Team) -> int:
        """Calculate damage reduction from friendly Anchor pieces within 2 cells."""
        reduction = 0
        for p in self.pieces:
            if p.alive and p.team == team and p.piece_type == PieceType.ANCHOR_PIECE:
                dist = abs(p.x - x) + abs(p.y - y)
                if 0 < dist <= 2:
                    reduction += 2
        return reduction

    # --- Ability hook methods ---

    def process_turn_start_abilities(self, team: Team, rng: random.Random,
                                     active_synergies: list[str] | None = None) -> list[str]:
        """Process start-of-turn abilities for a team. Returns log messages."""
        _synergies = active_synergies or []
        messages = []
        for p in list(self.get_team_pieces(team)):
            if not p.alive:
                continue

            # Summoner: spawn pawn on random adjacent empty cell
            if p.piece_type == PieceType.SUMMONER:
                empty_adj = []
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        sx, sy = p.x + dx, p.y + dy
                        if self.in_bounds(sx, sy) and self.is_empty(sx, sy):
                            empty_adj.append((sx, sy))
                if empty_adj:
                    sx, sy = rng.choice(empty_adj)
                    # Swarm Intelligence synergy: spawn Knight instead
                    spawn_type = PieceType.KNIGHT if "swarm_intelligence" in _synergies else PieceType.PAWN
                    spawn = Piece(spawn_type, team)
                    self.place_piece(spawn, sx, sy)
                    messages.append(f"Summoner spawns {spawn_type.value} at ({sx},{sy})")

            # Parasite: deal 1 damage to all adjacent enemy pieces
            if p.piece_type == PieceType.PARASITE:
                enemy_team = Team.ENEMY if team == Team.PLAYER else Team.PLAYER
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        adj = self.get_piece_at(p.x + dx, p.y + dy)
                        if adj and adj.team == enemy_team and adj.alive:
                            adj.hp -= 1
                            if adj.hp <= 0:
                                adj.alive = False
                                messages.append(f"Parasite kills {adj.piece_type.value}")
                            else:
                                messages.append(f"Parasite drains {adj.piece_type.value} (HP:{adj.hp})")
                # Life Drain synergy: also heal adjacent friendlies
                if "life_drain" in _synergies:
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            adj = self.get_piece_at(p.x + dx, p.y + dy)
                            if adj and adj.team == team and adj.alive and adj is not p:
                                adj.hp = min(adj.max_hp, adj.hp + 1)

        return messages

    def process_on_death(self, dead_piece: Piece, killer: Piece | None,
                         rng: random.Random,
                         active_synergies: list[str] | None = None) -> list[str]:
        """Process on-death abilities. Returns log messages."""
        _synergies = active_synergies or []
        messages = []

        # Bomb: 10 damage to everything in 3x3 (both teams)
        if dead_piece.piece_type == PieceType.BOMB:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    adj = self.get_piece_at(dead_piece.x + dx, dead_piece.y + dy)
                    if adj and adj.alive and adj is not dead_piece:
                        if "sacrifice" in _synergies:
                            # Sacrifice synergy: convert enemies instead of damaging
                            if adj.team != dead_piece.team:
                                adj.team = dead_piece.team
                                messages.append(f"Bomb converts {adj.piece_type.value}!")
                        else:
                            adj.hp -= 10
                            if adj.hp <= 0:
                                adj.alive = False
                                messages.append(f"Bomb explosion kills {adj.piece_type.value}!")
                                # Chain to other bombs if minefield synergy
                                if adj.piece_type == PieceType.BOMB and "minefield" in _synergies:
                                    messages.extend(self.process_on_death(adj, dead_piece, rng, _synergies))
                            else:
                                messages.append(f"Bomb damages {adj.piece_type.value} (HP:{adj.hp})")

        # Mimic: transform into killer's type, revive with full HP
        if dead_piece.piece_type == PieceType.MIMIC and killer and not dead_piece.ability_flags.get("mimic_transformed"):
            from pieces import PIECE_STATS
            dead_piece.piece_type = killer.piece_type
            if dead_piece.piece_type in PIECE_STATS:
                mhp, atk = PIECE_STATS[dead_piece.piece_type]
                dead_piece.max_hp = mhp
                dead_piece.hp = mhp
                dead_piece.attack = atk
            dead_piece.alive = True
            dead_piece.ability_flags["mimic_transformed"] = True
            messages.append(f"Mimic transforms into {dead_piece.piece_type.value}!")

        # Phoenix: revive once at random empty cell with 50% HP
        if dead_piece.piece_type == PieceType.PHOENIX and not dead_piece.ability_flags.get("phoenix_revived"):
            empty_cells = [
                (ex, ey) for ex in range(self.width) for ey in range(self.height)
                if self.is_empty(ex, ey) and not self.is_blocked(ex, ey)
            ]
            if empty_cells:
                rx, ry = rng.choice(empty_cells)
                dead_piece.alive = True
                dead_piece.x = rx
                dead_piece.y = ry
                dead_piece.hp = max(1, dead_piece.max_hp // 2)
                dead_piece.ability_flags["phoenix_revived"] = True
                messages.append(f"Phoenix revives at ({rx},{ry}) with {dead_piece.hp} HP!")

        return messages

    def process_on_damage_dealt(self, attacker: Piece, target: Piece, damage: int,
                                rng: random.Random) -> list[str]:
        """Process after-damage-dealt abilities. Returns log messages."""
        messages = []

        # Leech healing is handled inline in move_piece

        return messages

    def process_mirror_moves(self, moved_piece: Piece, old_x: int, old_y: int,
                             rng: random.Random,
                             active_synergies: list[str] | None = None) -> list[str]:
        """After any piece moves, same-team Mirror pieces make the reflected move."""
        _synergies = active_synergies or []
        messages = []
        dx = moved_piece.x - old_x
        dy = moved_piece.y - old_y
        if dx == 0 and dy == 0:
            return messages

        mirrors = [p for p in self.get_team_pieces(moved_piece.team)
                   if p.alive and p.piece_type == PieceType.MIRROR_PIECE and p is not moved_piece]

        for mirror in mirrors:
            # Infinite Recursion synergy: mirrors teleport randomly instead
            if "infinite_recursion" in _synergies:
                empty_cells = [
                    (ex, ey) for ex in range(self.width) for ey in range(self.height)
                    if self.is_empty(ex, ey)
                ]
                if empty_cells:
                    nx, ny = rng.choice(empty_cells)
                    mirror.x = nx
                    mirror.y = ny
                    # Deal 1 damage on arrival to adjacent enemies
                    enemy_team = Team.ENEMY if mirror.team == Team.PLAYER else Team.PLAYER
                    for adx in [-1, 0, 1]:
                        for ady in [-1, 0, 1]:
                            if adx == 0 and ady == 0:
                                continue
                            adj = self.get_piece_at(nx + adx, ny + ady)
                            if adj and adj.team == enemy_team and adj.alive:
                                adj.hp -= 1
                                if adj.hp <= 0:
                                    adj.alive = False
                    messages.append(f"Mirror teleports to ({nx},{ny})!")
            else:
                # Reflected move: negate dx/dy
                nx, ny = mirror.x - dx, mirror.y - dy
                if self.in_bounds(nx, ny) and not self.is_blocked(nx, ny):
                    target = self.get_piece_at(nx, ny)
                    if target and target.team != mirror.team:
                        # Attack the target
                        self.move_piece(mirror, nx, ny, rng)
                        messages.append(f"Mirror reflects: attacks {target.piece_type.value}")
                    elif not target:
                        mirror.x = nx
                        mirror.y = ny
                        messages.append(f"Mirror reflects to ({nx},{ny})")

        return messages

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
