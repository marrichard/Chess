"""Mode 3: Auto-battler — place your army, watch them fight using chess rules."""

from __future__ import annotations

import random
import time

import numpy as np
import tcod.console

from board import Board
from pieces import Piece, PieceType, Team, PIECE_VALUES, MODIFIERS
from engine import Action, GameState
from modifiers import (
    CellModifier, BorderModifier, CELL_MODIFIERS, BORDER_MODIFIERS,
    PIECE_MODIFIER_VISUALS, make_cell_modifier, make_border_modifier,
)
import renderer
import save_data as sd
from particles import ParticleSystem

BOARD_W = 8
BOARD_H = 8

# Boss sequence for tournament mode
BOSS_SEQUENCE = [
    PieceType.PAWN, PieceType.KNIGHT, PieceType.BISHOP,
    PieceType.ROOK, PieceType.QUEEN, PieceType.KING,
]

# Boss definitions: (boss_piece_type, boss_mods, minion_list)
BOSS_TABLE = {
    PieceType.PAWN: {
        "mods": ["armored"],
        "minions": [PieceType.PAWN] * 5,
    },
    PieceType.KNIGHT: {
        "mods": ["swift"],
        "minions": [PieceType.PAWN] * 3 + [PieceType.KNIGHT] * 2,
    },
    PieceType.BISHOP: {
        "mods": ["piercing"],
        "minions": [PieceType.PAWN] * 2 + [PieceType.KNIGHT] * 2 + [PieceType.BISHOP],
    },
    PieceType.ROOK: {
        "mods": ["armored"],
        "minions": [PieceType.KNIGHT] * 2 + [PieceType.BISHOP] * 2 + [PieceType.ROOK],
    },
    PieceType.QUEEN: {
        "mods": ["flaming"],
        "minions": [PieceType.KNIGHT, PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN],
    },
    PieceType.KING: {
        "mods": ["armored", "royal"],
        "minions": [PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN],
    },
}

DIFFICULTY_MULT = {"basic": 1.0, "extreme": 1.5, "grandmaster": 2.5}


def _layout(console: tcod.console.Console) -> dict:
    """Calculate layout positions: board centered, panels in margins."""
    cw, ch = console.width, console.height
    bw, bh = renderer.board_pixel_size(Board(BOARD_W, BOARD_H))

    # Center the board, ensure it doesn't clip at bottom
    board_ox = (cw - bw) // 2
    board_oy = max(2, (ch - bh) // 2 - 1)
    if board_oy + bh >= ch - 2:
        board_oy = max(1, ch - bh - 3)

    # Left panel: everything left of the board
    left_x = 1
    left_w = board_ox - 3
    left_y = board_oy

    # Right panel: everything right of the board
    right_x = board_ox + bw + 2
    right_w = cw - right_x - 1
    right_y = board_oy

    # Roster below the board
    roster_y = board_oy + bh + 2

    return {
        "board_ox": board_ox,
        "board_oy": board_oy,
        "bw": bw,
        "bh": bh,
        "left_x": left_x,
        "left_w": max(left_w, 10),
        "left_y": left_y,
        "right_x": right_x,
        "right_w": max(right_w, 10),
        "right_y": right_y,
        "roster_y": roster_y,
    }


def evaluate_board(board: Board, team: Team) -> float:
    """Static evaluation of a board position for *team*. Higher = better for team.

    Considers material, threats (pieces we attack), safety, advancement,
    and mobility so that non-capture moves are meaningfully differentiated.
    """
    ally_team = team
    enemy_team = Team.ENEMY if team == Team.PLAYER else Team.PLAYER

    score = 0.0
    allies = board.get_team_pieces(ally_team)
    enemies = board.get_team_pieces(enemy_team)

    # 1. Material advantage (dominant factor, scaled up)
    for p in allies:
        score += p.value * 10
    for p in enemies:
        score -= p.value * 10

    center_x, center_y = board.width / 2.0, board.height / 2.0

    # 2. Our pieces: threats, mobility, position, safety
    for p in allies:
        moves = p.get_valid_moves(board)

        # Threats: bonus for each enemy we can capture from here.
        # This makes pieces move to attacking positions.
        for emx, emy in moves:
            target = board.get_piece_at(emx, emy)
            if target and target.team == enemy_team:
                score += target.value * 2

        # Mobility: more legal moves = better positioned piece
        score += len(moves) * 0.1

        # Center control
        dist_to_center = abs(p.x - center_x) + abs(p.y - center_y)
        score += max(0, 4 - dist_to_center) * 0.2

        # Advance toward nearest enemy
        if enemies:
            nearest_dist = min(abs(p.x - e.x) + abs(p.y - e.y) for e in enemies)
            score += max(0, 8 - nearest_dist) * 0.15

        # Safety: penalty for being on an attacked square
        if board.is_square_attacked_by(p.x, p.y, enemy_team):
            # Worse if undefended
            if board.is_square_attacked_by(p.x, p.y, ally_team):
                score -= p.value * 0.5
            else:
                score -= p.value * 2

    # 3. Enemy pieces: penalize their threats and mobility (symmetric)
    for p in enemies:
        moves = p.get_valid_moves(board)

        for emx, emy in moves:
            target = board.get_piece_at(emx, emy)
            if target and target.team == ally_team:
                score -= target.value * 2

        score -= len(moves) * 0.1

    return score


def _apply_move(board: Board, piece: Piece, mx: int, my: int, rng: random.Random) -> None:
    """Apply a move on a board (mutates in place). Handles captures and promotion."""
    target = board.get_piece_at(mx, my)
    if target and target.team != piece.team:
        board.move_piece(piece, mx, my, rng=rng)
    else:
        piece.x, piece.y = mx, my
        piece.has_moved = True
        board.check_promotion(piece, rng)


def minimax_choose_move(
    team: Team, board: Board,
    rng: random.Random | None = None,
    excluded: dict[int, tuple[int, int]] | None = None,
    piece_streaks: dict[int, int] | None = None,
) -> tuple[Piece, int, int] | None:
    """Depth-2 minimax: pick our best move assuming the opponent replies optimally.

    For each of our moves, we simulate the opponent's best response,
    then pick the move where the worst-case outcome is still best for us.

    excluded: map of id(piece) -> (prev_x, prev_y) to filter oscillation.
    piece_streaks: map of id(piece) -> consecutive non-capture moves (penalizes hogging).
    """
    _rng = rng or random.Random()
    enemy_team = Team.ENEMY if team == Team.PLAYER else Team.PLAYER

    moves = board.get_all_valid_moves(team)
    if not moves:
        return None

    # Filter out oscillation moves
    if excluded:
        filtered = [
            (p, mx, my) for p, mx, my in moves
            if excluded.get(id(p)) != (mx, my)
        ]
        if filtered:
            moves = filtered

    # Pre-find piece indices for fast clone lookup
    piece_indices: dict[int, int] = {}
    for idx, bp in enumerate(board.pieces):
        piece_indices[id(bp)] = idx

    scores: list[float] = []

    for piece, mx, my in moves:
        # Clone board, apply our move
        clone = board.copy()
        p_idx = piece_indices.get(id(piece))
        if p_idx is None:
            scores.append(-999.0)
            continue
        clone_piece = clone.pieces[p_idx]
        _apply_move(clone, clone_piece, mx, my, _rng)

        # Check if this move ends the game
        if clone.count_alive(enemy_team) == 0:
            scores.append(9999.0)  # instant win
            continue

        # Opponent's best reply (depth 2)
        enemy_moves = clone.get_all_valid_moves(enemy_team)
        if not enemy_moves:
            # Opponent has no moves — evaluate position as-is
            scores.append(evaluate_board(clone, team))
            continue

        # Find the opponent's move that minimizes our score
        worst_for_us = float('inf')
        for ep, emx, emy in enemy_moves:
            clone2 = clone.copy()
            # Find this enemy piece in the clone
            e_idx = None
            for idx2, bp2 in enumerate(clone.pieces):
                if bp2 is ep:
                    e_idx = idx2
                    break
            if e_idx is None:
                continue
            clone2_piece = clone2.pieces[e_idx]
            _apply_move(clone2, clone2_piece, emx, emy, _rng)

            val = evaluate_board(clone2, team)
            if val < worst_for_us:
                worst_for_us = val

        if worst_for_us == float('inf'):
            # No enemy moves evaluated — fallback
            worst_for_us = evaluate_board(clone, team)

        scores.append(worst_for_us)

    # Apply streak penalty to discourage one piece hogging all turns
    if piece_streaks:
        for i, (piece, mx, my) in enumerate(moves):
            streak = piece_streaks.get(id(piece), 0)
            if streak > 1:
                scores[i] -= streak * 0.5

    best_score = max(scores)
    best_indices = [i for i, s in enumerate(scores) if s == best_score]
    idx = _rng.choice(best_indices)
    piece, mx, my = moves[idx]
    return (piece, mx, my)


class AutoBattler:
    """Auto-battler mode — draft army, place pieces, watch battles resolve."""

    def __init__(
        self,
        tournament: bool = False,
        difficulty: str = "basic",
        save_data=None,
    ) -> None:
        self.board = Board(BOARD_W, BOARD_H)
        self.wave = 0
        self.wins = 0
        self.losses = 0

        self.roster: list[Piece] = []
        self.placed: list[Piece] = []

        self.phase = "setup"
        self.cursor = (3, 5)
        self.roster_selection = 0
        self.message = ""

        self.battle_turn = 0
        self.battle_log: list[str] = []
        self.battle_player_turn = True

        self.draft_options: list[dict] = []
        self.draft_selection = 0

        # Modifier system
        self.gold = 0
        self.cell_modifiers: list[CellModifier] = []    # owned but unplaced
        self.border_modifiers: list[BorderModifier] = []  # owned but unplaced

        # Shop
        self.shop_items: list[dict] = []
        self.shop_selection = 0

        # Placement sub-phase (for placing cell/border mods after purchase)
        self.placing_item: dict | None = None

        # Held piece for repositioning during setup
        self.held_piece: Piece | None = None

        # Seeded RNG
        self.seed: int = 0
        self.rng: random.Random = random.Random()

        # Mouse / tooltip
        self.mouse_tile: tuple[int, int] = (0, 0)
        self.last_layout: dict | None = None

        # Click regions (populated each render pass)
        self._click_regions: list[dict] = []

        # Drag-and-drop state for setup and battle phases
        self.dragging: bool = False
        self.drag_origin: tuple[int, int] | None = None

        # Manual battle mode
        self.manual_mode: bool = True
        self.selected_piece: Piece | None = None
        self.valid_moves: list[tuple[int, int]] = []

        # Anti-oscillation: track previous position per piece (by id)
        self._prev_positions: dict[int, tuple[int, int]] = {}
        # Anti-hogging: count consecutive non-capture moves per piece
        self._piece_noncapture_streak: dict[int, int] = {}

        # Animation systems
        self.particles = ParticleSystem()

        # Screen shake
        self.shake_offset: tuple[int, int] = (0, 0)
        self.shake_until: float = 0.0

        # Screen flash
        self.flash_color: tuple[int, int, int] = (0, 0, 0)
        self.flash_until: float = 0.0

        # Phase transitions (fade from black)
        self.transition_alpha: float = 1.0  # 1.0 = fully visible
        self.transition_start: float = 0.0

        # --- Tournament mode ---
        self.tournament: bool = tournament
        self.difficulty: str = difficulty
        self.boss_sequence: list[PieceType] = list(BOSS_SEQUENCE)
        self.boss_index: int = 0
        self.waves_per_round: int = 2
        self.wave_in_round: int = 0
        self.tournament_stats: dict[str, float] = {
            "pieces_survived": 0,
            "gold_earned": 0,
            "bosses_beaten": 0,
        }
        self.save_data = save_data
        self.elo_earned: int = 0
        self.max_lives: int = 3
        self.play_again: bool = False

    def on_enter(self) -> None:
        self.wave = 0
        self.wins = 0
        self.losses = 0
        self.gold = 0
        self.cell_modifiers = []
        self.border_modifiers = []
        self.seed = random.randint(0, 2**32 - 1)
        self.rng = random.Random(self.seed)

        # Tournament: reset tracking
        self.boss_index = 0
        self.wave_in_round = 0
        self.tournament_stats = {"pieces_survived": 0, "gold_earned": 0, "bosses_beaten": 0}
        self.elo_earned = 0

        if self.tournament and self.save_data:
            # Apply unlocks from save data
            self.max_lives = 3 + self.save_data.upgrades.get("extra_life", 0)
            self.gold = 5 * self.save_data.upgrades.get("start_gold", 0)

            # Build roster from unlocked pieces
            base_pieces = list(self.save_data.unlocked_pieces)
            self.roster = []
            for pname in base_pieces:
                pt = PieceType(pname)
                self.roster.append(Piece(pt, Team.PLAYER))

            # Extra piece slots
            extra = self.save_data.upgrades.get("extra_piece", 0)
            for _ in range(extra):
                self.roster.append(Piece(PieceType.PAWN, Team.PLAYER))
        else:
            self.max_lives = 3
            self.roster = [
                Piece(PieceType.PAWN, Team.PLAYER),
                Piece(PieceType.PAWN, Team.PLAYER),
                Piece(PieceType.PAWN, Team.PLAYER),
                Piece(PieceType.KNIGHT, Team.PLAYER),
                Piece(PieceType.BISHOP, Team.PLAYER),
            ]

        self._start_wave()

    # --- Run state serialization ---

    def _serialize_piece(self, p: Piece) -> dict:
        mods = [{"name": m.name, "desc": m.description, "effect": m.effect} for m in p.modifiers]
        cm = None
        if p.cell_modifier is not None:
            cm = {
                "name": p.cell_modifier.name,
                "effect": p.cell_modifier.effect,
                "color": list(p.cell_modifier.color),
                "overlay_alpha": p.cell_modifier.overlay_alpha,
                "origin_x": p.cell_modifier.origin_x,
                "origin_y": p.cell_modifier.origin_y,
            }
        return {
            "piece_type": p.piece_type.value,
            "team": p.team.value,
            "x": p.x,
            "y": p.y,
            "modifiers": mods,
            "has_moved": p.has_moved,
            "alive": p.alive,
            "cell_modifier": cm,
        }

    def _deserialize_piece(self, d: dict) -> Piece:
        p = Piece(
            piece_type=PieceType(d["piece_type"]),
            team=Team(d["team"]),
            x=d.get("x", 0),
            y=d.get("y", 0),
            has_moved=d.get("has_moved", False),
            alive=d.get("alive", True),
        )
        for md in d.get("modifiers", []):
            key = md["effect"]
            if key in MODIFIERS:
                p.modifiers.append(MODIFIERS[key])
        cm = d.get("cell_modifier")
        if cm:
            p.cell_modifier = CellModifier(
                name=cm["name"], effect=cm["effect"],
                color=tuple(cm["color"]), overlay_alpha=cm["overlay_alpha"],
                origin_x=cm.get("origin_x", 0), origin_y=cm.get("origin_y", 0),
            )
        return p

    def _serialize_cell_modifier(self, cm: CellModifier) -> dict:
        return {
            "name": cm.name, "effect": cm.effect,
            "color": list(cm.color), "overlay_alpha": cm.overlay_alpha,
            "origin_x": cm.origin_x, "origin_y": cm.origin_y,
        }

    def _serialize_border_modifier(self, bm: BorderModifier) -> dict:
        return {
            "name": bm.name, "effect": bm.effect,
            "border_color": list(bm.border_color),
            "x": bm.x, "y": bm.y,
        }

    def to_run_state(self) -> dict:
        """Serialize all run-critical state into a plain dict."""
        roster = [self._serialize_piece(p) for p in self.roster]
        cell_mods = [self._serialize_cell_modifier(cm) for cm in self.cell_modifiers]
        border_mods = [self._serialize_border_modifier(bm) for bm in self.border_modifiers]

        # Board-placed cell/border modifiers (keyed by "x,y")
        board_cell_mods = {}
        for (cx, cy), cm in self.board.cell_modifiers.items():
            board_cell_mods[f"{cx},{cy}"] = self._serialize_cell_modifier(cm)
        board_border_mods = {}
        for (bx, by), bm in self.board.border_modifiers.items():
            board_border_mods[f"{bx},{by}"] = self._serialize_border_modifier(bm)

        return {
            "wave": self.wave,
            "wins": self.wins,
            "losses": self.losses,
            "gold": self.gold,
            "seed": self.seed,
            "phase": self.phase,
            "tournament": self.tournament,
            "difficulty": self.difficulty,
            "boss_index": self.boss_index,
            "wave_in_round": self.wave_in_round,
            "tournament_stats": dict(self.tournament_stats),
            "max_lives": self.max_lives,
            "roster": roster,
            "cell_modifiers": cell_mods,
            "border_modifiers": border_mods,
            "board_cell_modifiers": board_cell_mods,
            "board_border_modifiers": board_border_mods,
        }

    def restore_from_run_state(self, state: dict, save_data) -> None:
        """Rebuild run from a serialized state dict (used instead of on_enter)."""
        self.save_data = save_data
        self.wave = state["wave"]
        self.wins = state["wins"]
        self.losses = state["losses"]
        self.gold = state["gold"]
        self.seed = state["seed"]
        self.rng = random.Random(self.seed)
        # Advance RNG to match where we were (approximate — by consuming wave*100 values)
        for _ in range(self.wave * 100):
            self.rng.random()

        self.tournament = state["tournament"]
        self.difficulty = state.get("difficulty", "basic")
        self.boss_index = state.get("boss_index", 0)
        self.wave_in_round = state.get("wave_in_round", 0)
        self.tournament_stats = state.get("tournament_stats", {
            "pieces_survived": 0, "gold_earned": 0, "bosses_beaten": 0,
        })
        self.max_lives = state.get("max_lives", 3)
        self.elo_earned = 0

        # Rebuild roster
        self.roster = [self._deserialize_piece(d) for d in state.get("roster", [])]

        # Rebuild owned modifiers
        self.cell_modifiers = []
        for cmd in state.get("cell_modifiers", []):
            self.cell_modifiers.append(CellModifier(
                name=cmd["name"], effect=cmd["effect"],
                color=tuple(cmd["color"]), overlay_alpha=cmd["overlay_alpha"],
                origin_x=cmd.get("origin_x", 0), origin_y=cmd.get("origin_y", 0),
            ))
        self.border_modifiers = []
        for bmd in state.get("border_modifiers", []):
            self.border_modifiers.append(BorderModifier(
                name=bmd["name"], effect=bmd["effect"],
                border_color=tuple(bmd["border_color"]),
                x=bmd.get("x", 0), y=bmd.get("y", 0),
            ))

        # Rebuild board state
        self.board.clear()

        # Restore board cell modifiers
        for key, cmd in state.get("board_cell_modifiers", {}).items():
            cx, cy = (int(v) for v in key.split(","))
            self.board.cell_modifiers[(cx, cy)] = CellModifier(
                name=cmd["name"], effect=cmd["effect"],
                color=tuple(cmd["color"]), overlay_alpha=cmd["overlay_alpha"],
                origin_x=cmd.get("origin_x", 0), origin_y=cmd.get("origin_y", 0),
            )

        # Restore board border modifiers
        for key, bmd in state.get("board_border_modifiers", {}).items():
            bx, by = (int(v) for v in key.split(","))
            self.board.border_modifiers[(bx, by)] = BorderModifier(
                name=bmd["name"], effect=bmd["effect"],
                border_color=tuple(bmd["border_color"]),
                x=bmd.get("x", 0), y=bmd.get("y", 0),
            )

        # _start_wave increments wave, so offset by -1 to land on saved wave
        saved_phase = state.get("phase", "setup")
        self.wave -= 1
        self._start_wave()
        # Restore the exact phase from the save (start_wave may set a different one)
        self.phase = saved_phase

    def _auto_save(self) -> None:
        """Save current run state to disk at checkpoint phases."""
        sd.save_run(self.to_run_state())

    def _start_wave(self) -> None:
        self.wave += 1
        self.board.clear()
        self.placed = []
        self.held_piece = None
        self.battle_log = []
        self.battle_turn = 0
        self.battle_player_turn = True
        self.roster_selection = 0
        self.cursor = (3, 5)
        self.message = "Place pieces on your half, then SPACE to fight."

        for p in self.roster:
            p.alive = True
            p.has_moved = False
            p.cell_modifier = None  # strip absorbed cell mods

        # Restore owned cell modifiers to their origin positions on board
        for cm in self.cell_modifiers:
            self.board.cell_modifiers[(cm.origin_x, cm.origin_y)] = cm

        # Restore owned border modifiers to their positions on board
        for bm in self.border_modifiers:
            self.board.border_modifiers[(bm.x, bm.y)] = bm

        if self.tournament:
            # Tournament wave structure
            if self.wave_in_round < self.waves_per_round:
                # Normal wave
                self._generate_enemies()
                self.phase = "setup"
            else:
                # Boss wave
                self._generate_boss_wave()
                self.phase = "boss_intro"
        else:
            self._generate_enemies()
            self.phase = "setup"

        self._auto_save()

    def _generate_enemies(self) -> None:
        num_enemies = min(3 + self.wave, 8)

        # Difficulty scaling for tournament
        if self.tournament:
            if self.difficulty == "extreme":
                num_enemies += 2
            elif self.difficulty == "grandmaster":
                num_enemies += 3
            num_enemies = min(num_enemies, 12)

        pool = [PieceType.PAWN, PieceType.PAWN, PieceType.PAWN, PieceType.KNIGHT]
        if self.wave >= 2:
            pool.extend([PieceType.BISHOP, PieceType.KNIGHT])
        if self.wave >= 4:
            pool.extend([PieceType.ROOK, PieceType.QUEEN])

        used = set()
        for _ in range(num_enemies):
            pt = self.rng.choice(pool)
            piece = Piece(pt, Team.ENEMY)

            # Difficulty: random mods on regular enemies
            if self.tournament and self.difficulty in ("extreme", "grandmaster"):
                chance = 0.3 if self.difficulty == "extreme" else 0.5
                if self.rng.random() < chance:
                    mod_key = self.rng.choice(list(PIECE_MODIFIER_VISUALS.keys()))
                    piece.modifiers.append(MODIFIERS[mod_key])

            for _attempt in range(30):
                ex, ey = self.rng.randint(0, 7), self.rng.randint(0, 2)
                if (ex, ey) not in used:
                    self.board.place_piece(piece, ex, ey)
                    used.add((ex, ey))
                    break

    def _generate_boss_wave(self) -> None:
        """Generate a boss wave with a named boss piece and supporting minions."""
        boss_type = self.boss_sequence[self.boss_index]
        boss_info = BOSS_TABLE[boss_type]

        used = set()

        # Create boss piece with modifiers
        boss = Piece(boss_type, Team.ENEMY)
        for mod_key in boss_info["mods"]:
            boss.modifiers.append(MODIFIERS[mod_key])

        # Grandmaster: boss gets an extra modifier
        if self.difficulty == "grandmaster":
            extra_mod_key = self.rng.choice(list(PIECE_MODIFIER_VISUALS.keys()))
            if not any(m.effect == extra_mod_key for m in boss.modifiers):
                boss.modifiers.append(MODIFIERS[extra_mod_key])

        # Place boss in center top
        boss_x = self.rng.randint(2, 5)
        boss_y = 0
        self.board.place_piece(boss, boss_x, boss_y)
        used.add((boss_x, boss_y))

        # Create minions
        minion_types = list(boss_info["minions"])

        # Difficulty scaling: extra minions
        if self.difficulty == "extreme":
            for _ in range(2):
                minion_types.append(self.rng.choice(minion_types) if minion_types else PieceType.PAWN)
        elif self.difficulty == "grandmaster":
            for _ in range(3):
                minion_types.append(self.rng.choice(minion_types) if minion_types else PieceType.PAWN)

        for pt in minion_types:
            minion = Piece(pt, Team.ENEMY)

            # Difficulty: random mods on minions
            if self.difficulty in ("extreme", "grandmaster"):
                chance = 0.3 if self.difficulty == "extreme" else 0.5
                if self.rng.random() < chance:
                    mod_key = self.rng.choice(list(PIECE_MODIFIER_VISUALS.keys()))
                    minion.modifiers.append(MODIFIERS[mod_key])

            for _attempt in range(30):
                ex, ey = self.rng.randint(0, 7), self.rng.randint(0, 2)
                if (ex, ey) not in used:
                    self.board.place_piece(minion, ex, ey)
                    used.add((ex, ey))
                    break

    def _calculate_elo(self) -> int:
        """Calculate ELO earned at tournament end."""
        stats = self.tournament_stats
        bosses = int(stats["bosses_beaten"])
        base = 50 * bosses
        survival_bonus = 5 * int(stats["pieces_survived"])
        gold_bonus = stats["gold_earned"] * 0.1
        clear_bonus = 100 if bosses >= len(self.boss_sequence) else 0
        raw_total = base + survival_bonus + gold_bonus + clear_bonus

        mult = DIFFICULTY_MULT.get(self.difficulty, 1.0)
        total = raw_total * mult

        # Penalty for not clearing
        if bosses < len(self.boss_sequence):
            total *= 0.25

        return int(total)

    # --- Input handling ---

    def handle_input(self, action: Action) -> GameState | None:
        if self.phase == "setup":
            return self._handle_setup(action)
        elif self.phase == "battle":
            return self._handle_battle(action)
        elif self.phase == "result":
            return self._handle_result(action)
        elif self.phase == "shop":
            return self._handle_shop(action)
        elif self.phase == "place_cell":
            return self._handle_place_cell(action)
        elif self.phase == "place_border":
            return self._handle_place_border(action)
        elif self.phase == "place_piece_mod":
            return self._handle_place_piece_mod(action)
        elif self.phase == "draft":
            return self._handle_draft(action)
        elif self.phase == "boss_intro":
            return self._handle_boss_intro(action)
        elif self.phase == "tournament_end":
            return self._handle_tournament_end(action)
        elif self.phase == "game_over":
            if action in (Action.CONFIRM, Action.MOUSE_CLICK):
                return GameState.MENU
            if action == Action.SPACE:
                self.play_again = True
                return GameState.MENU
            return None
        return None

    def _handle_boss_intro(self, action: Action) -> GameState | None:
        if action in (Action.CONFIRM, Action.MOUSE_CLICK):
            self.phase = "setup"
            self._start_transition()
        return None

    def _handle_tournament_end(self, action: Action) -> GameState | None:
        if action in (Action.CONFIRM, Action.MOUSE_CLICK):
            return GameState.MENU
        if action == Action.SPACE:
            self.play_again = True
            return GameState.MENU
        return None

    def on_mouse_move(self, tile_pos: tuple[int, int]) -> None:
        """Convert mouse tile coords to board coords and update cursor."""
        self.mouse_tile = tile_pos
        bx, by = self._tile_to_board(tile_pos[0], tile_pos[1])
        if self.board.in_bounds(bx, by):
            self.cursor = (bx, by)

    def _tile_to_board(self, tx: int, ty: int) -> tuple[int, int]:
        """Convert console tile coords to board cell coords using last layout."""
        if not self.last_layout:
            return (-1, -1)
        ox = self.last_layout["board_ox"]
        oy = self.last_layout["board_oy"]
        bx = (tx - ox) // renderer.TILE_W
        by = (ty - oy) // renderer.TILE_H
        return (bx, by)

    def _hit_test(self, tx: int, ty: int) -> dict | None:
        """Test if console tile (tx, ty) falls inside any click region."""
        for r in self._click_regions:
            if r["x"] <= tx < r["x"] + r["w"] and r["y"] <= ty < r["y"] + r["h"]:
                return r
        return None

    # --- Animation helpers ---

    def has_active_animations(self) -> bool:
        """Return True if any animation is active (particles, shake, flash, transition, modifier glow)."""
        now = time.time()
        if (
            self.particles.active
            or now < self.shake_until
            or now < self.flash_until
            or self.transition_alpha < 1.0
        ):
            return True
        # Continuous time-based animations: piece modifiers and cell/border modifiers
        if self.board.cell_modifiers or self.board.border_modifiers:
            return True
        for p in self.board.pieces:
            if p.alive and p.modifiers:
                return True
        return False

    def _trigger_shake(self, duration: float = 0.3) -> None:
        self.shake_until = time.time() + duration

    def _trigger_flash(self, color: tuple[int, int, int], duration: float = 0.4) -> None:
        self.flash_color = color
        self.flash_until = time.time() + duration

    def _start_transition(self) -> None:
        self.transition_alpha = 0.0
        self.transition_start = time.time()

    def _update_shake(self) -> None:
        now = time.time()
        if now < self.shake_until:
            self.shake_offset = (random.randint(-1, 1), random.randint(-1, 1))
        else:
            self.shake_offset = (0, 0)

    def _apply_flash(self, console: tcod.console.Console) -> None:
        now = time.time()
        if now >= self.flash_until:
            return
        remaining = self.flash_until - now
        total_duration = 0.4
        fade = min(1.0, remaining / total_duration)
        intensity = fade * 0.3  # 30% max blend
        fc = np.array(self.flash_color, dtype=np.float32)
        bg = console.rgb['bg']
        blended = bg.astype(np.float32) * (1.0 - intensity) + fc * intensity
        bg[:] = np.clip(blended, 0, 255).astype(np.uint8)

    def _update_transition(self) -> None:
        if self.transition_alpha >= 1.0:
            return
        elapsed = time.time() - self.transition_start
        self.transition_alpha = min(1.0, elapsed / 0.5)  # 0.5s fade-in

    def _apply_transition(self, console: tcod.console.Console) -> None:
        if self.transition_alpha >= 1.0:
            return
        alpha = self.transition_alpha
        console.rgb['fg'][:] = (console.rgb['fg'].astype(np.float32) * alpha).astype(np.uint8)
        console.rgb['bg'][:] = (console.rgb['bg'].astype(np.float32) * alpha).astype(np.uint8)

    def _board_to_screen(self, bx: int, by: int) -> tuple[int, int]:
        """Convert board coords to screen console coords (center of tile)."""
        if not self.last_layout:
            return (0, 0)
        ox = self.last_layout["board_ox"]
        oy = self.last_layout["board_oy"]
        return (ox + bx * renderer.TILE_W + renderer.TILE_W // 2,
                oy + by * renderer.TILE_H + renderer.TILE_H // 2)

    def _handle_setup(self, action: Action) -> GameState | None:
        cx, cy = self.cursor

        if action == Action.MOUSE_CLICK:
            existing = self.board.get_piece_at(cx, cy)
            if existing and existing.team == Team.PLAYER and existing in self.placed:
                # Pick up a placed piece (start drag)
                existing.alive = False
                self.held_piece = existing
                self.dragging = True
                self.drag_origin = (existing.x, existing.y)
                self.message = f"Dragging {existing.piece_type.value}. Release to place."
            elif self.held_piece and cy >= 4 and self.board.is_empty(cx, cy):
                # Place held piece
                self.board.place_piece(self.held_piece, cx, cy)
                self.message = f"Placed {self.held_piece.piece_type.value}."
                self.held_piece = None
                self.dragging = False
                self.drag_origin = None
            elif not self.held_piece and cy >= 4 and self.board.is_empty(cx, cy):
                # Place from roster
                unplaced = [p for p in self.roster if p not in self.placed]
                if unplaced and self.roster_selection < len(unplaced):
                    piece = unplaced[self.roster_selection]
                    self.board.place_piece(piece, cx, cy)
                    self.placed.append(piece)
                    self.message = f"Placed {piece.piece_type.value}."
                    remaining = [p for p in self.roster if p not in self.placed]
                    if self.roster_selection >= len(remaining):
                        self.roster_selection = max(0, len(remaining) - 1)
            elif cy < 4:
                self.message = "Place on your half (bottom 4 rows)!"
            return None

        if action == Action.MOUSE_UP:
            if self.dragging and self.held_piece:
                if cy >= 4 and self.board.is_empty(cx, cy):
                    # Drop on valid cell
                    self.board.place_piece(self.held_piece, cx, cy)
                    self.message = f"Placed {self.held_piece.piece_type.value}."
                    self.held_piece = None
                else:
                    # Return to origin
                    if self.drag_origin:
                        ox, oy = self.drag_origin
                        self.board.place_piece(self.held_piece, ox, oy)
                    self.message = "Returned piece to original position."
                    self.held_piece = None
                self.dragging = False
                self.drag_origin = None
            return None

        if action == Action.CANCEL:
            if self.held_piece:
                # Return held piece to roster
                self.placed.remove(self.held_piece)
                self.held_piece.alive = False
                self.held_piece = None
                self.message = "Piece returned to roster."
            else:
                return GameState.MENU

        if action in (Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT):
            dx, dy = 0, 0
            if action == Action.UP:
                dy = -1
            elif action == Action.DOWN:
                dy = 1
            elif action == Action.LEFT:
                dx = -1
            elif action == Action.RIGHT:
                dx = 1
            nx, ny = cx + dx, cy + dy
            if self.board.in_bounds(nx, ny):
                self.cursor = (nx, ny)

        num_actions = {
            Action.NUM_1: 0, Action.NUM_2: 1, Action.NUM_3: 2,
            Action.NUM_4: 3, Action.NUM_5: 4, Action.NUM_6: 5,
            Action.NUM_7: 6, Action.NUM_8: 7, Action.NUM_9: 8,
        }
        if action in num_actions and not self.held_piece:
            idx = num_actions[action]
            unplaced = [p for p in self.roster if p not in self.placed]
            if idx < len(unplaced):
                self.roster_selection = idx
                self.message = f"Selected {unplaced[idx].piece_type.value}. ENTER to place."

        if action == Action.CONFIRM:
            if self.held_piece:
                # Place held piece at cursor
                if cy >= 4 and self.board.is_empty(cx, cy):
                    self.board.place_piece(self.held_piece, cx, cy)
                    self.message = f"Placed {self.held_piece.piece_type.value}."
                    self.held_piece = None
                elif cy < 4:
                    self.message = "Place on your half (bottom 4 rows)!"
                else:
                    self.message = "Square occupied!"
            else:
                # Check if cursor is on a placed friendly piece → pick it up
                existing = self.board.get_piece_at(cx, cy)
                if existing and existing.team == Team.PLAYER and existing in self.placed:
                    existing.alive = False
                    self.held_piece = existing
                    self.message = f"Picked up {existing.piece_type.value}. ENTER to place, ESC to return."
                else:
                    # Place from roster (existing behavior)
                    unplaced = [p for p in self.roster if p not in self.placed]
                    if unplaced and cy >= 4:
                        if self.roster_selection < len(unplaced):
                            piece = unplaced[self.roster_selection]
                            if self.board.is_empty(cx, cy):
                                self.board.place_piece(piece, cx, cy)
                                self.placed.append(piece)
                                self.message = f"Placed {piece.piece_type.value}."
                                remaining = [p for p in self.roster if p not in self.placed]
                                if self.roster_selection >= len(remaining):
                                    self.roster_selection = max(0, len(remaining) - 1)
                            else:
                                self.message = "Square occupied!"
                    elif cy < 4:
                        self.message = "Place on your half (bottom 4 rows)!"

        if action == Action.SPACE:
            if self.held_piece:
                self.message = "Place held piece first!"
            elif self.placed:
                self.phase = "battle"
                self.selected_piece = None
                self.valid_moves = []
                self.message = "Your turn! Click a piece to select."
                self.battle_log = ["=== Battle Start ==="]
                self._prev_positions.clear()
                self._piece_noncapture_streak.clear()
                self._start_transition()
            else:
                self.message = "Place at least one piece first!"

        return None

    def _handle_battle(self, action: Action) -> GameState | None:
        if action == Action.TAB:
            self.manual_mode = not self.manual_mode
            self.selected_piece = None
            self.valid_moves = []
            self.dragging = False
            self.message = "Manual mode" if self.manual_mode else "Auto mode"
            return None
        if self.manual_mode and self.battle_player_turn:
            return self._handle_player_turn(action)
        else:
            # AI mode / enemy turn fallback
            if action == Action.MOUSE_CLICK:
                action = Action.CONFIRM
            if action == Action.CONFIRM:
                self._battle_step()
            elif action == Action.CANCEL:
                while self.phase == "battle":
                    self._battle_step()
        return None

    def _handle_player_turn(self, action: Action) -> GameState | None:
        cx, cy = self.cursor

        if action == Action.MOUSE_CLICK:
            if self.selected_piece:
                # Check if clicking a valid move destination
                if (cx, cy) in self.valid_moves:
                    self._execute_player_move(self.selected_piece, cx, cy)
                    return None
                # Check if clicking a different player piece
                clicked = self.board.get_piece_at(cx, cy)
                if clicked and clicked.team == Team.PLAYER:
                    self._select_piece(clicked)
                    self.dragging = True
                    return None
                # Clicking invalid square → deselect
                self._deselect_piece()
            else:
                # No piece selected — try to select one
                clicked = self.board.get_piece_at(cx, cy)
                if clicked and clicked.team == Team.PLAYER:
                    self._select_piece(clicked)
                    self.dragging = True
            return None

        if action == Action.MOUSE_UP:
            if self.dragging and self.selected_piece:
                if (cx, cy) in self.valid_moves:
                    self._execute_player_move(self.selected_piece, cx, cy)
                else:
                    # Dropped on invalid square — keep selected but stop drag
                    self.dragging = False
                return None
            self.dragging = False
            return None

        if action == Action.CONFIRM:
            if self.selected_piece:
                if (cx, cy) in self.valid_moves:
                    self._execute_player_move(self.selected_piece, cx, cy)
                    return None
                # Cursor on a different player piece → switch
                clicked = self.board.get_piece_at(cx, cy)
                if clicked and clicked.team == Team.PLAYER:
                    self._select_piece(clicked)
                    return None
                # Invalid square → deselect
                self._deselect_piece()
            else:
                clicked = self.board.get_piece_at(cx, cy)
                if clicked and clicked.team == Team.PLAYER:
                    self._select_piece(clicked)
            return None

        if action == Action.CANCEL:
            if self.selected_piece:
                self._deselect_piece()
            else:
                # Skip to end (existing behavior)
                while self.phase == "battle":
                    self._battle_step()
            return None

        return None

    def _select_piece(self, piece: Piece) -> None:
        self.selected_piece = piece
        self.valid_moves = piece.get_valid_moves(self.board)
        self.dragging = False
        if self.valid_moves:
            self.message = f"Selected {piece.piece_type.value}. Click a destination."
        else:
            self.message = f"{piece.piece_type.value} has no valid moves!"

    def _deselect_piece(self) -> None:
        self.selected_piece = None
        self.valid_moves = []
        self.dragging = False
        self.message = "Your turn! Click a piece to select."

    def _execute_player_move(self, piece: Piece, mx: int, my: int) -> None:
        """Execute the player's chosen move, log it, then auto-step enemy."""
        target = self.board.get_piece_at(mx, my)
        if target and target.team != piece.team:
            self.board.move_piece(piece, mx, my, rng=self.rng)
            log = f"Player {piece.piece_type.value} captures {target.piece_type.value}!"
            self._trigger_shake(0.3)
            sx, sy = self._board_to_screen(mx, my)
            self.particles.spawn("capture_burst", sx, sy, color=renderer.FG_PLAYER)
        else:
            piece.x, piece.y = mx, my
            piece.has_moved = True
            log = f"Player {piece.piece_type.value} moves"

        self.battle_log.append(log)
        if len(self.battle_log) > 14:
            self.battle_log = self.battle_log[-14:]
        self.message = log

        # Clear selection
        self.selected_piece = None
        self.valid_moves = []
        self.dragging = False

        # Switch to enemy turn
        self.battle_player_turn = False

        # Check win condition after player move
        if self.board.count_alive(Team.PLAYER) == 0 or self.board.count_alive(Team.ENEMY) == 0:
            self._end_battle()
            return

        # Auto-step enemy turn
        self._enemy_step()

    def _enemy_step(self) -> None:
        """Execute one AI enemy turn, then switch back to player."""
        pieces = self.board.get_team_pieces(Team.ENEMY)
        if not pieces:
            self._end_battle()
            return

        result = minimax_choose_move(
            Team.ENEMY, self.board, rng=self.rng,
            excluded=self._prev_positions,
            piece_streaks=self._piece_noncapture_streak,
        )

        if result:
            best_piece, mx, my = result
            target = self.board.get_piece_at(mx, my)
            is_capture = target and target.team != best_piece.team
            self._record_move(best_piece, best_piece.x, best_piece.y, captured=bool(is_capture))
            if is_capture:
                self.board.move_piece(best_piece, mx, my, rng=self.rng)
                log = f"Enemy {best_piece.piece_type.value} captures {target.piece_type.value}!"
                self._trigger_shake(0.3)
                sx, sy = self._board_to_screen(mx, my)
                self.particles.spawn("capture_burst", sx, sy, color=renderer.FG_ENEMY)
            else:
                old_type = best_piece.piece_type
                best_piece.x, best_piece.y = mx, my
                best_piece.has_moved = True
                if self.board.check_promotion(best_piece, self.rng):
                    log = f"Enemy {old_type.value} promotes to {best_piece.piece_type.value}!"
                    sx, sy = self._board_to_screen(mx, my)
                    self.particles.spawn("capture_burst", sx, sy, color=(255, 100, 100))
                else:
                    log = f"Enemy {best_piece.piece_type.value} moves"
        else:
            log = "Enemy pieces stuck"

        self.battle_log.append(log)
        if len(self.battle_log) > 14:
            self.battle_log = self.battle_log[-14:]
        self.message = log

        self.battle_player_turn = True
        self.battle_turn += 1

        if self.board.count_alive(Team.PLAYER) == 0 or self.board.count_alive(Team.ENEMY) == 0:
            self._end_battle()
        elif self.battle_turn > 50:
            self.battle_log.append("Stalemate!")
            self._end_battle()

    def _filter_oscillation(self, moves: list[tuple[Piece, int, int]]) -> list[tuple[Piece, int, int]]:
        """Remove moves that return a piece to its previous position."""
        filtered = []
        for piece, mx, my in moves:
            prev = self._prev_positions.get(id(piece))
            if prev and prev == (mx, my):
                continue  # skip: would oscillate
            filtered.append((piece, mx, my))
        return filtered if filtered else moves  # fall back to all moves if everything filtered

    def _record_move(self, piece: Piece, old_x: int, old_y: int, captured: bool = False) -> None:
        """Record a piece's pre-move position for anti-oscillation and streak tracking."""
        self._prev_positions[id(piece)] = (old_x, old_y)
        if captured:
            # Reset streak on capture
            self._piece_noncapture_streak[id(piece)] = 0
        else:
            self._piece_noncapture_streak[id(piece)] = self._piece_noncapture_streak.get(id(piece), 0) + 1

    def _battle_step(self) -> None:
        team = Team.PLAYER if self.battle_player_turn else Team.ENEMY

        pieces = self.board.get_team_pieces(team)
        if not pieces:
            self._end_battle()
            return

        result = minimax_choose_move(
            team, self.board, rng=self.rng,
            excluded=self._prev_positions,
            piece_streaks=self._piece_noncapture_streak,
        )

        if result:
            best_piece, mx, my = result
            target = self.board.get_piece_at(mx, my)
            is_capture = target and target.team != best_piece.team
            self._record_move(best_piece, best_piece.x, best_piece.y, captured=bool(is_capture))
            if is_capture:
                self.board.move_piece(best_piece, mx, my, rng=self.rng)
                log = f"{team.value} {best_piece.piece_type.value} captures {target.piece_type.value}!"
                # Visual feedback: shake + capture burst
                self._trigger_shake(0.3)
                sx, sy = self._board_to_screen(mx, my)
                cap_color = renderer.FG_PLAYER if best_piece.team == Team.PLAYER else renderer.FG_ENEMY
                self.particles.spawn("capture_burst", sx, sy, color=cap_color)
            else:
                old_type = best_piece.piece_type
                best_piece.x, best_piece.y = mx, my
                best_piece.has_moved = True
                if self.board.check_promotion(best_piece, self.rng):
                    log = f"{team.value} {old_type.value} promotes to {best_piece.piece_type.value}!"
                    sx, sy = self._board_to_screen(mx, my)
                    self.particles.spawn("capture_burst", sx, sy, color=(255, 220, 100))
                else:
                    log = f"{team.value} {best_piece.piece_type.value} moves"
        else:
            log = f"{team.value} pieces stuck"

        self.battle_log.append(log)
        if len(self.battle_log) > 14:
            self.battle_log = self.battle_log[-14:]
        self.message = log

        self.battle_player_turn = not self.battle_player_turn
        if self.battle_player_turn:
            self.battle_turn += 1

        if self.board.count_alive(Team.PLAYER) == 0 or self.board.count_alive(Team.ENEMY) == 0:
            self._end_battle()
        elif self.battle_turn > 50:
            self.battle_log.append("Stalemate!")
            self._end_battle()

    def _end_battle(self) -> None:
        player_alive = self.board.count_alive(Team.PLAYER)
        enemy_alive = self.board.count_alive(Team.ENEMY)

        if player_alive > 0 and enemy_alive == 0:
            self.wins += 1
            # Gold reward: 2 + surviving pieces
            earned = 2 + player_alive
            # Royal modifier: surviving Royal pieces earn double score contribution
            for p in self.board.get_team_pieces(Team.PLAYER):
                if any(m.effect == "royal" for m in p.modifiers):
                    earned += p.value  # extra value on top of survival bonus
            self.gold += earned
            self.message = f"Victory! ({player_alive} survive) +{earned}g"
            self.battle_log.append(f"=== VICTORY === (+{earned}g)")
            self._trigger_flash((40, 200, 40))

            # Tournament stat tracking
            if self.tournament:
                self.tournament_stats["pieces_survived"] += player_alive
                self.tournament_stats["gold_earned"] += earned

                # Check if this was a boss wave
                if self.wave_in_round >= self.waves_per_round:
                    self.tournament_stats["bosses_beaten"] += 1
                    self.boss_index += 1
                    self.wave_in_round = 0

                    # Check if tournament complete
                    if self.boss_index >= len(self.boss_sequence):
                        self._finish_tournament(won=True)
                        return
                else:
                    self.wave_in_round += 1

        elif enemy_alive > 0 and player_alive == 0:
            self.losses += 1
            self.message = "Defeat!"
            self.battle_log.append("=== DEFEAT ===")
            self._trigger_flash((200, 40, 40))

            if self.tournament:
                if self.wave_in_round >= self.waves_per_round:
                    # Lost boss wave — don't advance
                    self.wave_in_round = 0  # reset round, retry from normal waves
                else:
                    self.wave_in_round += 1
        else:
            self.gold += 1  # consolation gold for draw
            self.message = "Draw! (+1g)"
            self.battle_log.append("=== DRAW === (+1g)")
            if self.tournament:
                self.tournament_stats["gold_earned"] += 1
                self.wave_in_round += 1

        if self.tournament and self.losses >= self.max_lives:
            self._finish_tournament(won=False)
            return

        if not self.tournament:
            if self.losses >= 3:
                self.phase = "game_over"
                sd.clear_run()
            else:
                self.phase = "result"
        else:
            self.phase = "result"
        self._start_transition()

    def _finish_tournament(self, won: bool) -> None:
        """End the tournament, calculate ELO, save results."""
        self.elo_earned = self._calculate_elo()

        if self.save_data:
            self.save_data.elo += self.elo_earned
            self.save_data.stats["tournaments_completed"] = self.save_data.stats.get("tournaments_completed", 0) + 1
            self.save_data.stats["total_elo_earned"] = self.save_data.stats.get("total_elo_earned", 0) + self.elo_earned
            self.save_data.stats["bosses_beaten"] = self.save_data.stats.get("bosses_beaten", 0) + int(self.tournament_stats["bosses_beaten"])

            if won:
                self.save_data.stats["tournaments_won"] = self.save_data.stats.get("tournaments_won", 0) + 1
                # Beating Extreme unlocks Grandmaster
                if self.difficulty == "extreme":
                    self.save_data.grandmaster_unlocked = True

            import save_data as sd_module
            sd_module.save(self.save_data)

        sd.clear_run()
        self.phase = "tournament_end"
        self._start_transition()

    def _handle_result(self, action: Action) -> GameState | None:
        if action == Action.MOUSE_CLICK:
            action = Action.CONFIRM
        if action == Action.CONFIRM:
            self._generate_shop()
            self.phase = "shop"
            self._auto_save()
        return None

    def _generate_draft(self) -> None:
        self.draft_options = []
        self.draft_selection = 0

        pool = [PieceType.PAWN, PieceType.KNIGHT, PieceType.BISHOP]
        if self.wave >= 3:
            pool.append(PieceType.ROOK)
        if self.wave >= 5:
            pool.append(PieceType.QUEEN)

        for _ in range(3):
            pt = self.rng.choice(pool)
            self.draft_options.append({
                "type": "add", "piece_type": pt,
                "desc": f"Draft a {pt.value}",
            })

        pawn_count = sum(1 for p in self.roster if p.piece_type == PieceType.PAWN)
        if pawn_count >= 3:
            self.draft_options.append({
                "type": "combine", "from": PieceType.PAWN,
                "to": PieceType.KNIGHT, "count": 3,
                "desc": "Combine 3 Pawns -> 1 Knight",
            })

        knight_count = sum(1 for p in self.roster if p.piece_type == PieceType.KNIGHT)
        if knight_count >= 2:
            self.draft_options.append({
                "type": "combine", "from": PieceType.KNIGHT,
                "to": PieceType.ROOK, "count": 2,
                "desc": "Combine 2 Knights -> 1 Rook",
            })

        self.draft_options.append({"type": "skip", "desc": "Skip -> Next wave"})

    # --- Shop ---

    def _generate_shop(self) -> None:
        """Generate random shop offerings: piece mods, cell mods, border mods."""
        self.shop_items = []
        self.shop_selection = 0

        # Determine available modifier keys
        if self.tournament and self.save_data:
            available_mod_keys = [
                k for k in PIECE_MODIFIER_VISUALS.keys()
                if k in self.save_data.unlocked_modifiers
            ]
        else:
            available_mod_keys = list(PIECE_MODIFIER_VISUALS.keys())

        if not available_mod_keys:
            available_mod_keys = list(PIECE_MODIFIER_VISUALS.keys())

        # Offer 1-2 piece modifiers
        for _ in range(self.rng.randint(1, 2)):
            key = self.rng.choice(available_mod_keys)
            mod = MODIFIERS[key]
            self.shop_items.append({
                "type": "piece_mod", "key": key, "mod": mod,
                "cost": 5,
                "icon": "*",
                "category": "Piece Mod",
                "color": PIECE_MODIFIER_VISUALS[key]["color"],
                "name": mod.name,
                "description": mod.description,
            })

        # Offer 1-2 cell modifiers
        cell_mod_keys = list(CELL_MODIFIERS.keys())
        for _ in range(self.rng.randint(1, 2)):
            key = self.rng.choice(cell_mod_keys)
            tmpl = CELL_MODIFIERS[key]
            self.shop_items.append({
                "type": "cell_mod", "key": key,
                "cost": 3,
                "icon": tmpl["icon"],
                "category": "Cell Mod",
                "color": tmpl["color"],
                "name": tmpl["name"],
                "description": tmpl["description"],
            })

        # Offer 1 border modifier
        border_mod_keys = list(BORDER_MODIFIERS.keys())
        key = self.rng.choice(border_mod_keys)
        tmpl = BORDER_MODIFIERS[key]
        self.shop_items.append({
            "type": "border_mod", "key": key,
            "cost": 4,
            "icon": "#",
            "category": "Border Mod",
            "color": tmpl["border_color"],
            "name": tmpl["name"],
            "description": tmpl["description"],
        })

        # Always offer "Done shopping"
        self.shop_items.append({
            "type": "done", "cost": 0,
            "icon": ">",
            "category": "done",
            "color": renderer.FG_DIM,
            "name": "Done",
            "description": "Proceed to draft phase",
        })

    def _handle_shop(self, action: Action) -> GameState | None:
        done_idx = next(
            (i for i, it in enumerate(self.shop_items) if it["type"] == "done"),
            len(self.shop_items) - 1,
        )
        if action == Action.MOUSE_CLICK:
            hit = self._hit_test(self.mouse_tile[0], self.mouse_tile[1])
            if hit:
                idx = hit["index"]
                if hit["action"] == "button":
                    self.shop_selection = idx
                    action = Action.CONFIRM  # fall through to CONFIRM
                elif idx == self.shop_selection:
                    action = Action.CONFIRM  # click already-selected card → buy
                else:
                    self.shop_selection = idx
                    return None
            else:
                return None
        if action == Action.DOWN:
            if self.shop_selection != done_idx:
                self.shop_selection = done_idx
            return None
        if action == Action.UP:
            if self.shop_selection == done_idx:
                purchasable = [it for it in self.shop_items if it["type"] != "done"]
                self.shop_selection = max(0, len(purchasable) - 1)
            return None
        if action == Action.LEFT:
            self.shop_selection = (self.shop_selection - 1) % len(self.shop_items)
        elif action == Action.RIGHT:
            self.shop_selection = (self.shop_selection + 1) % len(self.shop_items)
        elif action == Action.CONFIRM:
            item = self.shop_items[self.shop_selection]
            if item["type"] == "done":
                self._generate_draft()
                self.phase = "draft"
                self._auto_save()
                return None

            if self.gold < item["cost"]:
                self.message = "Not enough gold!"
                return None

            if item["type"] == "piece_mod":
                # Check if any roster piece can receive a modifier
                eligible = [p for p in self.roster if not p.modifiers]
                if not eligible:
                    self.message = "All pieces already have modifiers!"
                    return None
                self.gold -= item["cost"]
                self.placing_item = item
                self.roster_selection = 0
                self.phase = "place_piece_mod"
                self.message = f"Pick a piece for {item['mod'].name} (1-9, ENTER)"

            elif item["type"] == "cell_mod":
                self.gold -= item["cost"]
                self.placing_item = item
                self.cursor = (3, 5)
                self.phase = "place_cell"
                self.message = f"Place {CELL_MODIFIERS[item['key']]['name']} on a cell (arrows + ENTER)"

            elif item["type"] == "border_mod":
                self.gold -= item["cost"]
                self.placing_item = item
                self.cursor = (3, 5)
                self.phase = "place_border"
                self.message = f"Place {BORDER_MODIFIERS[item['key']]['name']} on a cell (arrows + ENTER)"

        elif action == Action.CANCEL:
            self._generate_draft()
            self.phase = "draft"
            self._auto_save()
        return None

    def _handle_place_cell(self, action: Action) -> GameState | None:
        """Cursor-based placement of a cell modifier on the board."""
        if action == Action.MOUSE_CLICK:
            action = Action.CONFIRM
        cx, cy = self.cursor
        if action in (Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT):
            dx, dy = 0, 0
            if action == Action.UP: dy = -1
            elif action == Action.DOWN: dy = 1
            elif action == Action.LEFT: dx = -1
            elif action == Action.RIGHT: dx = 1
            nx, ny = cx + dx, cy + dy
            if self.board.in_bounds(nx, ny):
                self.cursor = (nx, ny)
        elif action == Action.CONFIRM:
            if (cx, cy) in self.board.cell_modifiers:
                self.message = "Cell already has a modifier!"
                return None
            if (cx, cy) in self.board.border_modifiers:
                self.message = "Cell has a border modifier!"
                return None
            item = self.placing_item
            cm = make_cell_modifier(item["key"], cx, cy)
            self.board.cell_modifiers[(cx, cy)] = cm
            self.cell_modifiers.append(cm)
            self.placing_item = None
            self.message = f"Placed {cm.name}!"
            self.phase = "shop"
        elif action == Action.CANCEL:
            # Refund
            self.gold += self.placing_item["cost"]
            self.placing_item = None
            self.phase = "shop"
            self.message = "Cancelled — gold refunded."
        return None

    def _handle_place_border(self, action: Action) -> GameState | None:
        """Cursor-based placement of a border modifier on the board."""
        if action == Action.MOUSE_CLICK:
            action = Action.CONFIRM
        cx, cy = self.cursor
        if action in (Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT):
            dx, dy = 0, 0
            if action == Action.UP: dy = -1
            elif action == Action.DOWN: dy = 1
            elif action == Action.LEFT: dx = -1
            elif action == Action.RIGHT: dx = 1
            nx, ny = cx + dx, cy + dy
            if self.board.in_bounds(nx, ny):
                self.cursor = (nx, ny)
        elif action == Action.CONFIRM:
            if (cx, cy) in self.board.border_modifiers:
                self.message = "Cell already has a border modifier!"
                return None
            item = self.placing_item
            bm = make_border_modifier(item["key"], cx, cy)
            self.board.border_modifiers[(cx, cy)] = bm
            self.border_modifiers.append(bm)
            self.placing_item = None
            self.message = f"Placed {bm.name}!"
            self.phase = "shop"
        elif action == Action.CANCEL:
            self.gold += self.placing_item["cost"]
            self.placing_item = None
            self.phase = "shop"
            self.message = "Cancelled — gold refunded."
        return None

    def _handle_place_piece_mod(self, action: Action) -> GameState | None:
        """Pick a roster piece to receive the purchased piece modifier."""
        if action == Action.MOUSE_CLICK:
            action = Action.CONFIRM
        eligible = [p for p in self.roster if not p.modifiers]
        if not eligible:
            self.placing_item = None
            self.phase = "shop"
            return None

        num_actions = {
            Action.NUM_1: 0, Action.NUM_2: 1, Action.NUM_3: 2,
            Action.NUM_4: 3, Action.NUM_5: 4, Action.NUM_6: 5,
            Action.NUM_7: 6, Action.NUM_8: 7, Action.NUM_9: 8,
        }
        if action in num_actions:
            idx = num_actions[action]
            if idx < len(eligible):
                self.roster_selection = idx
                self.message = f"Selected {eligible[idx].piece_type.value}. ENTER to apply."
        elif action in (Action.LEFT, Action.UP):
            self.roster_selection = (self.roster_selection - 1) % len(eligible)
        elif action in (Action.RIGHT, Action.DOWN):
            self.roster_selection = (self.roster_selection + 1) % len(eligible)
        elif action == Action.CONFIRM:
            if self.roster_selection < len(eligible):
                piece = eligible[self.roster_selection]
                mod = self.placing_item["mod"]
                piece.modifiers.append(MODIFIERS[self.placing_item["key"]])
                self.message = f"Applied {mod.name} to {piece.piece_type.value}!"
                self.placing_item = None
                self.phase = "shop"
        elif action == Action.CANCEL:
            self.gold += self.placing_item["cost"]
            self.placing_item = None
            self.phase = "shop"
            self.message = "Cancelled — gold refunded."
        return None

    def _handle_draft(self, action: Action) -> GameState | None:
        skip_idx = next(
            (i for i, o in enumerate(self.draft_options) if o["type"] == "skip"),
            len(self.draft_options) - 1,
        )
        card_indices = [i for i, o in enumerate(self.draft_options) if o["type"] != "skip"]
        if action == Action.MOUSE_CLICK:
            hit = self._hit_test(self.mouse_tile[0], self.mouse_tile[1])
            if hit:
                idx = hit["index"]
                if hit["action"] == "button":
                    self.draft_selection = idx
                    action = Action.CONFIRM
                elif idx == self.draft_selection:
                    action = Action.CONFIRM
                else:
                    self.draft_selection = idx
                    return None
            else:
                return None
        if action == Action.DOWN:
            if self.draft_selection != skip_idx:
                self.draft_selection = skip_idx
            return None
        if action == Action.UP:
            if self.draft_selection == skip_idx and card_indices:
                self.draft_selection = card_indices[-1]
            return None
        if action == Action.LEFT:
            if self.draft_selection == skip_idx:
                return None  # skip is a single button, no horizontal nav
            if card_indices:
                pos = card_indices.index(self.draft_selection) if self.draft_selection in card_indices else 0
                pos = (pos - 1) % len(card_indices)
                self.draft_selection = card_indices[pos]
        elif action == Action.RIGHT:
            if self.draft_selection == skip_idx:
                return None
            if card_indices:
                pos = card_indices.index(self.draft_selection) if self.draft_selection in card_indices else 0
                pos = (pos + 1) % len(card_indices)
                self.draft_selection = card_indices[pos]
        elif action == Action.CONFIRM:
            opt = self.draft_options[self.draft_selection]
            if opt["type"] == "add":
                self.roster.append(Piece(opt["piece_type"], Team.PLAYER))
                self.message = f"Drafted {opt['piece_type'].value}!"
            elif opt["type"] == "combine":
                removed = 0
                new_roster = []
                for p in self.roster:
                    if p.piece_type == opt["from"] and removed < opt["count"]:
                        removed += 1
                    else:
                        new_roster.append(p)
                new_roster.append(Piece(opt["to"], Team.PLAYER))
                self.roster = new_roster
                self.message = f"Combined into {opt['to'].value}!"
            self._start_wave()
        elif action == Action.CANCEL:
            self._start_wave()
        return None

    # --- Rendering ---

    def render(self, console: tcod.console.Console) -> None:
        renderer.fit_tile_size(console.width, console.height)
        self._update_transition()

        # Phase-specific render (calls _draw_board_centered which applies shake + vignette + glow)
        if self.phase == "setup":
            self._render_setup(console)
        elif self.phase == "battle":
            self._render_battle(console)
        elif self.phase == "result":
            self._render_result(console)
        elif self.phase == "shop":
            self._render_shop(console)
        elif self.phase in ("place_cell", "place_border"):
            self._render_placement(console)
        elif self.phase == "place_piece_mod":
            self._render_place_piece_mod(console)
        elif self.phase == "draft":
            self._render_draft(console)
        elif self.phase == "boss_intro":
            self._render_boss_intro(console)
        elif self.phase == "tournament_end":
            self._render_tournament_end(console)
        elif self.phase == "game_over":
            self._render_game_over(console)

        # Overlay effects: particles, transition, flash
        self.particles.update()
        self.particles.draw(console)
        self._apply_transition(console)
        self._apply_flash(console)

    def _draw_board_centered(
        self,
        console: tcod.console.Console,
        highlights: dict[tuple[int, int], tuple[int, int, int]] | None = None,
        cursor: tuple[int, int] | None = None,
    ) -> dict:
        """Draw the board in the center of the screen. Returns layout dict."""
        self._update_shake()
        lay = _layout(console)
        self.last_layout = lay
        # Apply shake offset to board position
        board_ox = lay["board_ox"] + self.shake_offset[0]
        board_oy = lay["board_oy"] + self.shake_offset[1]
        renderer.draw_board_labels(console, self.board, ox=board_ox, oy=board_oy)
        renderer.draw_board(
            console, self.board, ox=board_ox, oy=board_oy,
            highlights=highlights, cursor=cursor,
        )
        renderer.draw_board_grid(console, self.board, ox=board_ox, oy=board_oy)
        renderer.apply_board_vignette(console, self.board, ox=board_ox, oy=board_oy)
        renderer.apply_modifier_glow(console, self.board, ox=board_ox, oy=board_oy)
        return lay

    def _render_setup(self, console: tcod.console.Console) -> None:
        # Highlight placement zone
        highlights: dict[tuple[int, int], tuple[int, int, int]] = {}
        for bx in range(self.board.width):
            for by in range(4, self.board.height):
                if self.board.is_empty(bx, by):
                    highlights[(bx, by)] = renderer.HIGHLIGHT_ZONE

        lay = self._draw_board_centered(console, highlights=highlights, cursor=self.cursor)

        # Left panel — game info
        info_lines = [
            f"Wave: {self.wave}",
            f"Record: {self.wins}W / {self.losses}L",
            f"Lives: {self.max_lives - self.losses}",
            f"Gold: {self.gold}g",
            f"Seed: {self.seed}",
            "",
            f"Roster: {len(self.roster)} pieces",
            f"Placed: {len(self.placed)}",
        ]
        if self.tournament:
            info_lines.insert(0, f"[{self.difficulty.upper()}]")
        if self.held_piece:
            info_lines.append("")
            info_lines.append(f"Holding: {self.held_piece.piece_type.value}")

        panel_h = len(info_lines) + 2
        renderer.draw_panel(
            console, lay["left_x"], lay["left_y"],
            lay["left_w"], panel_h, "Status", info_lines,
        )

        # Tournament progress below status panel
        if self.tournament:
            prog_y = lay["left_y"] + panel_h + 1
            renderer.draw_tournament_progress(
                console, lay["left_x"] + 1, prog_y,
                self.boss_index, len(self.boss_sequence),
            )

        # Right panel — controls
        ctrl_lines = [
            "1-9    select piece",
            "Arrows move cursor",
            "Enter  place/pick up",
            "Space  START BATTLE",
            "Esc    quit/unhold",
            "F11    fullscreen",
        ]
        renderer.draw_panel(
            console, lay["right_x"], lay["right_y"],
            lay["right_w"], len(ctrl_lines) + 2, "Controls", ctrl_lines,
        )

        # Roster below board
        unplaced = [p for p in self.roster if p not in self.placed]
        if unplaced:
            roster_w = lay["bw"] + 4
            roster_x = lay["board_ox"] - 2
            renderer.draw_roster(
                console, unplaced, self.roster_selection,
                roster_x, lay["roster_y"], roster_w,
            )

        # Tooltip
        cx, cy = self.cursor
        if self.board.in_bounds(cx, cy):
            tooltip_x = lay["right_x"]
            tooltip_y = lay["right_y"] + len(ctrl_lines) + 3
            renderer.draw_tooltip(
                console, self.board, cx, cy,
                tooltip_x, tooltip_y, lay["right_w"],
            )

        # Draw held piece floating at mouse cursor
        if self.held_piece and self.dragging:
            from piece_tiles import piece_chars
            chars = piece_chars(self.held_piece.piece_type)
            mx, my = self.mouse_tile
            # Center the 3x3 glyph on the mouse tile
            ix = mx - 1
            iy = my - 1
            fg = renderer.FG_PLAYER
            for dy in range(3):
                for dx in range(3):
                    px, py = ix + dx, iy + dy
                    if 0 <= px < console.width and 0 <= py < console.height:
                        console.print(px, py, chars[dy][dx], fg=fg)

        if self.message:
            renderer.draw_message(console, self.message)

    def _render_battle(self, console: tcod.console.Console) -> None:
        # Build highlights for manual mode
        highlights: dict[tuple[int, int], tuple[int, int, int]] = {}
        if self.manual_mode and self.battle_player_turn and self.selected_piece:
            # Highlight selected piece
            highlights[(self.selected_piece.x, self.selected_piece.y)] = renderer.HIGHLIGHT_SELECTED
            # Highlight valid moves
            for mx, my in self.valid_moves:
                target = self.board.get_piece_at(mx, my)
                if target and target.team == Team.ENEMY:
                    highlights[(mx, my)] = renderer.HIGHLIGHT_CAPTURE
                else:
                    highlights[(mx, my)] = renderer.HIGHLIGHT_MOVE

        lay = self._draw_board_centered(console, highlights=highlights, cursor=self.cursor)

        # Left panel — battle status
        status_lines = [
            f"Wave: {self.wave}",
            f"Turn: {self.battle_turn}",
            "",
            f"Player: {self.board.count_alive(Team.PLAYER)} alive",
            f"Enemy:  {self.board.count_alive(Team.ENEMY)} alive",
        ]
        if self.tournament:
            status_lines.insert(0, f"[{self.difficulty.upper()}]")
        if self.manual_mode and self.battle_player_turn and self.selected_piece:
            status_lines.append("")
            status_lines.append(f"Selected: {self.selected_piece.piece_type.value}")

        panel_h = len(status_lines) + 2
        renderer.draw_panel(
            console, lay["left_x"], lay["left_y"],
            lay["left_w"], panel_h, "Battle", status_lines,
        )

        # Tournament progress
        if self.tournament:
            prog_y = lay["left_y"] + panel_h + 1
            renderer.draw_tournament_progress(
                console, lay["left_x"] + 1, prog_y,
                self.boss_index, len(self.boss_sequence),
            )

        # Right panel — battle log
        log_height = min(len(self.battle_log) + 2, lay["bh"] + 2)
        log_lines = self.battle_log[-(log_height - 2):]
        renderer.draw_panel(
            console, lay["right_x"], lay["right_y"],
            lay["right_w"], log_height, "Log", log_lines,
        )

        # Tooltip
        cx, cy = self.cursor
        if self.board.in_bounds(cx, cy):
            tooltip_x = lay["left_x"]
            tooltip_y = lay["left_y"] + len(status_lines) + 3
            renderer.draw_tooltip(
                console, self.board, cx, cy,
                tooltip_x, tooltip_y, lay["left_w"],
            )

        # Draw floating piece during drag
        if self.manual_mode and self.dragging and self.selected_piece:
            from piece_tiles import piece_chars
            chars = piece_chars(self.selected_piece.piece_type)
            mx, my = self.mouse_tile
            ix = mx - 1
            iy = my - 1
            fg = renderer.FG_PLAYER
            for dy in range(3):
                for dx in range(3):
                    px, py = ix + dx, iy + dy
                    if 0 <= px < console.width and 0 <= py < console.height:
                        console.print(px, py, chars[dy][dx], fg=fg)

        # Controls message
        if self.manual_mode and self.battle_player_turn:
            renderer.draw_message(console, "Click/Enter: select & move  |  Esc: deselect/skip  |  Tab: auto mode")
        else:
            renderer.draw_message(console, "ENTER: step  |  ESC: skip to end  |  Tab: manual mode")

    def _render_result(self, console: tcod.console.Console) -> None:
        lay = self._draw_board_centered(console)

        cw, ch = console.width, console.height
        pw = min(50, cw - 4)
        px = (cw - pw) // 2
        py = ch // 2 - 4
        lines = [
            "",
            f"  Record: {self.wins}W / {self.losses}L",
            f"  Lives remaining: {self.max_lives - self.losses}",
            f"  Gold: {self.gold}g",
            "",
        ]
        if self.tournament:
            lines.append(f"  Boss: {self.boss_index}/{len(self.boss_sequence)}")
        for log_line in self.battle_log[-3:]:
            lines.append(f"  {log_line}")
        lines.append("")
        lines.append("  Press ENTER to shop")

        renderer.draw_panel(console, px, py, pw, len(lines) + 2, "Result", lines)

    def _render_boss_intro(self, console: tcod.console.Console) -> None:
        """Render the boss introduction screen."""
        boss_type = self.boss_sequence[self.boss_index]
        renderer.draw_boss_intro(
            console,
            boss_type=boss_type.value,
            round_num=self.boss_index + 1,
            total_rounds=len(self.boss_sequence),
            difficulty=self.difficulty,
        )

    def _render_tournament_end(self, console: tcod.console.Console) -> None:
        """Render tournament end results with ELO breakdown."""
        cw, ch = console.width, console.height
        pw = min(55, cw - 4)
        px = (cw - pw) // 2
        py = max(2, ch // 2 - 10)

        stats = self.tournament_stats
        bosses = int(stats["bosses_beaten"])
        won = bosses >= len(self.boss_sequence)

        title = "TOURNAMENT VICTORY!" if won else "TOURNAMENT OVER"
        title_color = (80, 255, 80) if won else (255, 80, 80)

        lines = [
            "",
            f"  Difficulty: {self.difficulty.capitalize()}",
            f"  Bosses beaten: {bosses}/{len(self.boss_sequence)}",
            f"  Record: {self.wins}W / {self.losses}L",
            "",
            "  --- ELO Breakdown ---",
            f"  Base (50 x {bosses} bosses):     {50 * bosses}",
            f"  Survival (5 x {int(stats['pieces_survived'])}):   {5 * int(stats['pieces_survived'])}",
            f"  Gold bonus:              {int(stats['gold_earned'] * 0.1)}",
        ]
        if won:
            lines.append(f"  Clear bonus:             100")
        mult = DIFFICULTY_MULT.get(self.difficulty, 1.0)
        lines.append(f"  Difficulty mult:         x{mult}")
        if not won:
            lines.append(f"  Loss penalty:            x0.25")
        lines.append("")
        lines.append(f"  ELO EARNED: {self.elo_earned}")
        if self.save_data:
            lines.append(f"  Total ELO:  {self.save_data.elo}")
        lines.append("")
        lines.append("  ENTER: return to menu")
        lines.append("  SPACE: play again")

        ph = len(lines) + 2
        # Draw dark background
        console.draw_rect(0, 0, cw, ch, ch=ord(' '), bg=(10, 10, 20))
        renderer.draw_panel(console, px, py, pw, ph, title, lines, fg=title_color)

    def _render_shop(self, console: tcod.console.Console) -> None:
        self._click_regions = []
        cw, ch = console.width, console.height

        # Fill entire screen with felt green
        console.draw_rect(0, 0, cw, ch, ch=ord(' '), bg=renderer.BG_FELT)

        # Separate purchasable items from "done"
        purchasable = [it for it in self.shop_items if it["type"] != "done"]
        done_idx = next(
            (i for i, it in enumerate(self.shop_items) if it["type"] == "done"),
            len(self.shop_items) - 1,
        )

        # Compute card dimensions
        num_cards = max(1, len(purchasable))
        gap = 3  # columns between cards (room for shadows + breathing)
        card_w = min(22, max(14, (cw - 6 - gap * (num_cards - 1)) // num_cards))
        total_w = card_w * num_cards + gap * (num_cards - 1)
        start_x = (cw - total_w) // 2

        # Fixed card height — banner + icon(3) + name + sep + desc(3) + borders
        card_h = 12

        # Compute total content height to vertically center:
        # header(2) + gap(1) + cards(card_h) + shadow(1) + price(1) + gap(1) + roster(1) + gap(1) + button(3) = card_h + 11
        content_h = card_h + 11
        # Top margin: center the block, leave room for controls at bottom
        top_y = max(1, (ch - content_h - 2) // 2)

        # --- Header bar ---
        renderer.draw_shop_header(
            console, y=top_y, width=total_w, start_x=start_x,
            gold=self.gold, wave=self.wave,
            wins=self.wins, losses=self.losses,
        )

        # --- Card row ---
        cards_y = top_y + 3
        for i, item in enumerate(purchasable):
            cx = start_x + i * (card_w + gap)
            sel = (i == self.shop_selection)
            affordable = (self.gold >= item["cost"])
            renderer.draw_shop_card(
                console, cx, cards_y, card_w, card_h,
                icon=item["icon"],
                name=item["name"],
                description=item["description"],
                category=item["category"],
                color=item["color"],
                selected=sel,
                affordable=affordable,
            )

            # Price tag below card (skip shadow row)
            renderer.draw_shop_price_tag(
                console, cx, cards_y + card_h + 1, card_w,
                cost=item["cost"], affordable=affordable,
            )

            # Register click region for this card
            self._click_regions.append({
                "x": cx, "y": cards_y, "w": card_w, "h": card_h,
                "index": i, "action": "card",
            })

        # --- Roster summary ---
        roster_y = cards_y + card_h + 3
        counts: dict[str, int] = {}
        for p in self.roster:
            name = p.piece_type.value
            counts[name] = counts.get(name, 0) + 1
        roster_str = "Roster: " + ", ".join(f"{v}x {k}" for k, v in counts.items())
        rx = start_x + (total_w - len(roster_str)) // 2
        console.print(max(0, rx), roster_y, roster_str, fg=renderer.FG_DIM, bg=renderer.BG_FELT)

        # --- "Next Round" done button ---
        done_y = roster_y + 2
        done_selected = (self.shop_selection == done_idx)
        renderer.draw_shop_done_button(
            console, done_y, width=total_w, start_x=start_x,
            selected=done_selected,
        )
        self._click_regions.append({
            "x": start_x, "y": done_y, "w": total_w, "h": 3,
            "index": done_idx, "action": "button",
        })

        # --- Controls hint (bottom) ---
        controls = "Left/Right: browse  |  Enter: buy  |  Esc: skip"
        cx = (cw - len(controls)) // 2
        console.print(max(0, cx), ch - 2, controls, fg=renderer.FG_DIM, bg=renderer.BG_FELT)

        # Message bar
        if self.message:
            msg = self.message
            mx = (cw - len(msg)) // 2
            console.print(max(0, mx), ch - 1, msg, fg=renderer.FG_TEXT, bg=renderer.BG_FELT)

    def _render_placement(self, console: tcod.console.Console) -> None:
        """Render board with cursor for placing cell/border modifier."""
        highlights: dict[tuple[int, int], tuple[int, int, int]] = {}
        lay = self._draw_board_centered(console, highlights=highlights, cursor=self.cursor)

        # Info panel
        if self.placing_item:
            item_type = self.placing_item["type"]
            if item_type == "cell_mod":
                name = CELL_MODIFIERS[self.placing_item["key"]]["name"]
            else:
                name = BORDER_MODIFIERS[self.placing_item["key"]]["name"]
            info_lines = [
                f"Placing: {name}",
                "",
                "Arrows: move cursor",
                "Enter:  place here",
                "Esc:    cancel (refund)",
            ]
        else:
            info_lines = ["No item to place"]
        renderer.draw_panel(
            console, lay["left_x"], lay["left_y"],
            lay["left_w"], len(info_lines) + 2, "Place Modifier", info_lines,
        )
        if self.message:
            renderer.draw_message(console, self.message)

    def _render_place_piece_mod(self, console: tcod.console.Console) -> None:
        """Render roster selection for applying a piece modifier."""
        cw, ch = console.width, console.height

        eligible = [p for p in self.roster if not p.modifiers]
        if self.placing_item:
            mod_name = self.placing_item["mod"].name
        else:
            mod_name = "?"

        pw = min(50, cw - 4)
        px = (cw - pw) // 2
        py = max(2, ch // 2 - 8)

        renderer.draw_panel(console, px, py, pw, 5, f"Apply {mod_name}", [
            f"Gold: {self.gold}g",
            "Pick a piece (1-9 or arrows + ENTER)",
            "",
        ])

        # Draw roster of eligible pieces below
        if eligible:
            roster_w = pw
            roster_x = px
            roster_y = py + 6
            renderer.draw_roster(
                console, eligible, self.roster_selection,
                roster_x, roster_y, roster_w,
            )

        if self.message:
            renderer.draw_message(console, self.message)

    def _render_draft(self, console: tcod.console.Console) -> None:
        self._click_regions = []
        cw, ch = console.width, console.height

        # Fill with felt green
        console.draw_rect(0, 0, cw, ch, ch=ord(' '), bg=renderer.BG_FELT)

        # Separate card options from skip, preserving original indices
        card_opts = [(i, o) for i, o in enumerate(self.draft_options) if o["type"] != "skip"]
        skip_idx = next(
            (i for i, o in enumerate(self.draft_options) if o["type"] == "skip"),
            len(self.draft_options) - 1,
        )

        # Card dimensions
        num_cards = max(1, len(card_opts))  # card_opts is list of (idx, opt) tuples
        gap = 3
        card_w = min(22, max(14, (cw - 6 - gap * (num_cards - 1)) // num_cards))
        total_w = card_w * num_cards + gap * (num_cards - 1)
        start_x = (cw - total_w) // 2
        card_h = 12

        # Vertical centering
        content_h = card_h + 11
        top_y = max(1, (ch - content_h - 2) // 2)

        # Header
        roster_summary: dict[str, int] = {}
        for p in self.roster:
            name = p.piece_type.value
            roster_summary[name] = roster_summary.get(name, 0) + 1
        renderer.draw_shop_header(
            console, y=top_y, width=total_w, start_x=start_x,
            gold=self.gold, wave=self.wave,
            wins=self.wins, losses=self.losses,
        )

        # Title below header
        title = "\u2500\u2500 Choose a Draft Pick \u2500\u2500"
        tx = start_x + (total_w - len(title)) // 2
        console.print(max(0, tx), top_y + 2, title, fg=(255, 220, 100), bg=renderer.BG_FELT)

        # Card row
        cards_y = top_y + 4
        from piece_tiles import piece_chars

        for i, (opt_idx, opt) in enumerate(card_opts):
            cx = start_x + i * (card_w + gap)
            sel = (opt_idx == self.draft_selection)

            if opt["type"] == "add":
                pt = opt["piece_type"]
                icon_art = piece_chars(pt)
                icon_ch = ""
                card_name = pt.value
                card_desc = "Add to your roster"
                card_cat = "Draft"
                card_color = renderer.FG_PLAYER
            else:
                # combine
                icon_art = None
                icon_ch = "\u21d2"
                card_name = f"{opt['count']} {opt['from'].value}"
                card_desc = f"Merge into 1 {opt['to'].value}"
                card_cat = "Combine"
                card_color = (255, 180, 60)

            renderer.draw_draft_card(
                console, cx, cards_y, card_w, card_h,
                icon_chars=icon_art,
                icon_char=icon_ch,
                name=card_name,
                description=card_desc,
                category=card_cat,
                color=card_color,
                selected=sel,
            )

            # Register click region for this draft card
            self._click_regions.append({
                "x": cx, "y": cards_y, "w": card_w, "h": card_h,
                "index": opt_idx, "action": "card",
            })

        # Roster summary
        roster_y = cards_y + card_h + 2
        roster_str = "Roster: " + ", ".join(f"{v}x {k}" for k, v in roster_summary.items())
        rx = start_x + (total_w - len(roster_str)) // 2
        console.print(max(0, rx), roster_y, roster_str, fg=renderer.FG_DIM, bg=renderer.BG_FELT)

        # Skip button
        skip_y = roster_y + 2
        skip_selected = (self.draft_selection == skip_idx)
        renderer.draw_felt_button(
            console, skip_y, width=total_w, start_x=start_x,
            label="Skip \u25b6 Next Wave",
            selected=skip_selected,
            fg_normal=(180, 180, 180),
            bg_selected=(60, 60, 80),
        )
        self._click_regions.append({
            "x": start_x, "y": skip_y, "w": total_w, "h": 3,
            "index": skip_idx, "action": "button",
        })

        # Controls hint
        controls = "Left/Right: browse  |  Enter: pick  |  Esc: skip"
        cx = (cw - len(controls)) // 2
        console.print(max(0, cx), ch - 2, controls, fg=renderer.FG_DIM, bg=renderer.BG_FELT)

        # Message bar
        if self.message:
            msg = self.message
            mx = (cw - len(msg)) // 2
            console.print(max(0, mx), ch - 1, msg, fg=renderer.FG_TEXT, bg=renderer.BG_FELT)

    def _render_game_over(self, console: tcod.console.Console) -> None:
        cw, ch = console.width, console.height
        pw = 44
        ph = 11
        px = (cw - pw) // 2
        py = (ch - ph) // 2
        renderer.draw_panel(console, px, py, pw, ph, "Game Over!", [
            "",
            f"  Waves survived: {self.wave - 1}",
            f"  Record: {self.wins}W / {self.losses}L",
            f"  Seed: {self.seed}",
            "",
            "  ENTER: return to menu",
            "  SPACE: play again",
        ])
