"""Mode 3: Auto-battler — place your army, watch them fight using chess rules."""

from __future__ import annotations

import random
import time

import numpy as np
import tcod.console

from board import Board
from pieces import Piece, PieceType, Team, PIECE_VALUES, PIECE_STATS, MODIFIERS, PIECE_INFO
from engine import Action, GameState
from modifiers import (
    CellModifier, BorderModifier, CELL_MODIFIERS, BORDER_MODIFIERS,
    PIECE_MODIFIER_VISUALS, make_cell_modifier, make_border_modifier,
    TAROT_CARDS, ARTIFACTS,
)
from rarity import (
    Rarity, RARITY_PROPS, get_rarity, weighted_choice as rarity_weighted_choice,
    get_shop_cost, get_sell_value, PIECE_RARITY, PIECE_MOD_RARITY,
    TAROT_RARITY, ARTIFACT_RARITY, CELL_MOD_RARITY, BORDER_MOD_RARITY,
    PIECE_SELL_VALUES,
)
from achievements import AchievementChecker, ACHIEVEMENT_MAP, process_unlocks
from synergies import check_synergies, get_synergy_display_data
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

# Sudden Death configuration
SUDDEN_DEATH_ANNOUNCE = 25   # turn to announce
SUDDEN_DEATH_SCHEDULE = {30: 0, 37: 1, 43: 2, 50: 3}  # turn -> ring to close
SAFETY_CAP = 60


def _layout(console: tcod.console.Console) -> dict:
    """Calculate layout positions: board centered, panels in margins.

    Ensures panels get at least MIN_PANEL_W columns by shrinking tiles
    in a loop until things fit (or tiles hit minimum size).
    """
    MIN_PANEL_W = 14
    GAP = 2  # gap between board edge and panel
    cw, ch = console.width, console.height
    bw, bh = renderer.board_pixel_size(Board(BOARD_W, BOARD_H))

    # Shrink tiles until board + 2 panels fit
    while bw + 2 * (MIN_PANEL_W + GAP + 1) > cw and renderer.TILE_W > 3:
        renderer.TILE_W = max(3, renderer.TILE_W - 2)
        renderer.TILE_H = max(3, renderer.TILE_H - 2)
        bw, bh = renderer.board_pixel_size(Board(BOARD_W, BOARD_H))

    # Distribute remaining space evenly to panels
    remaining = cw - bw
    half = remaining // 2

    # Board position: leave room for left panel
    board_ox = max(half, MIN_PANEL_W + GAP + 1)
    # Recompute actual panel widths
    left_x = 1
    left_w = max(MIN_PANEL_W, board_ox - GAP)
    right_x = board_ox + bw + GAP
    right_w = max(MIN_PANEL_W, cw - right_x - 1)

    # If right panel overflows console, shift board left
    if right_x + right_w >= cw:
        board_ox = max(left_w + GAP, cw - bw - MIN_PANEL_W - GAP - 1)
        right_x = board_ox + bw + GAP
        right_w = max(MIN_PANEL_W, cw - right_x - 1)
        left_w = max(MIN_PANEL_W, board_ox - GAP)

    board_oy = max(2, (ch - bh) // 2 - 1)
    if board_oy + bh >= ch - 2:
        board_oy = max(1, ch - bh - 3)

    left_y = board_oy
    right_y = board_oy

    roster_y = board_oy + bh + 2

    return {
        "board_ox": board_ox,
        "board_oy": board_oy,
        "bw": bw,
        "bh": bh,
        "left_x": left_x,
        "left_w": left_w,
        "left_y": left_y,
        "right_x": right_x,
        "right_w": right_w,
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

    # 1. Material advantage weighted by HP fraction
    for p in allies:
        hp_frac = p.hp / p.max_hp if p.max_hp > 0 else 1.0
        score += p.value * 10 * hp_frac
        # Bonus for can-kill-this-turn threats
        for mx, my in p.get_capture_moves(board):
            target = board.get_piece_at(mx, my)
            if target and target.hp <= p.attack:
                score += target.value * 5  # bonus for killable targets
        # New piece bonuses
        if p.piece_type == PieceType.SUMMONER:
            adj_empty = sum(1 for dx in [-1,0,1] for dy in [-1,0,1]
                           if (dx or dy) and board.in_bounds(p.x+dx, p.y+dy) and board.is_empty(p.x+dx, p.y+dy))
            score += adj_empty * 0.3
        elif p.piece_type == PieceType.PARASITE:
            adj_enemies_count = sum(1 for dx in [-1,0,1] for dy in [-1,0,1]
                                    if (dx or dy) and board.get_piece_at(p.x+dx, p.y+dy)
                                    and board.get_piece_at(p.x+dx, p.y+dy).team == enemy_team)
            score += adj_enemies_count * 0.5
        elif p.piece_type == PieceType.ANCHOR_PIECE:
            nearby_friends = sum(1 for a in allies if a is not p and abs(a.x-p.x)+abs(a.y-p.y) <= 2)
            score += nearby_friends * 0.4
        elif p.piece_type == PieceType.BOMB:
            adj_enemies_count = sum(1 for dx in [-1,0,1] for dy in [-1,0,1]
                                    if (dx or dy) and board.get_piece_at(p.x+dx, p.y+dy)
                                    and board.get_piece_at(p.x+dx, p.y+dy).team == enemy_team)
            score += adj_enemies_count * 1.0
        elif p.piece_type == PieceType.GAMBLER:
            score -= 1.0  # penalize unreliability
    for p in enemies:
        hp_frac = p.hp / p.max_hp if p.max_hp > 0 else 1.0
        score -= p.value * 10 * hp_frac

    center_x, center_y = board.width / 2.0, board.height / 2.0

    # 2. Our pieces: threats, position, proximity
    for p in allies:
        # Center control
        dist_to_center = abs(p.x - center_x) + abs(p.y - center_y)
        score += max(0, 4 - dist_to_center) * 0.2

        # Advance toward nearest enemy (cheap proximity heuristic)
        if enemies:
            nearest_dist = min(abs(p.x - e.x) + abs(p.y - e.y) for e in enemies)
            score += max(0, 8 - nearest_dist) * 0.3

        # Safety: penalize being adjacent to more enemies than allies
        adj_enemies = 0
        adj_allies = 0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                adj = board.get_piece_at(p.x + dx, p.y + dy)
                if adj:
                    if adj.team == enemy_team:
                        adj_enemies += 1
                    elif adj.team == ally_team:
                        adj_allies += 1
        if adj_enemies > adj_allies:
            score -= p.value * 0.3

    # 3. Enemy pieces: center and proximity penalty (symmetric, lightweight)
    for p in enemies:
        dist_to_center = abs(p.x - center_x) + abs(p.y - center_y)
        score -= max(0, 4 - dist_to_center) * 0.2

    return score


def _apply_move(board: Board, piece: Piece, mx: int, my: int, rng: random.Random,
                 active_synergies: list[str] | None = None) -> None:
    """Apply a move on a board (mutates in place). Handles captures, promotion, and death triggers."""
    old_x, old_y = piece.x, piece.y
    target = board.get_piece_at(mx, my)
    if target and target.team != piece.team:
        board.move_piece(piece, mx, my, rng=rng, active_synergies=active_synergies)
        # Process on-death triggers for the target (Bomb, Mimic, Phoenix)
        if target and not target.alive:
            board.process_on_death(target, piece, rng, active_synergies)
        # Also check if attacker died (e.g. thorns)
        if not piece.alive:
            board.process_on_death(piece, target, rng, active_synergies)
    else:
        piece.x, piece.y = mx, my
        piece.has_moved = True
        board.check_promotion(piece, rng)

    # Process mirror reflected moves
    if piece.alive:
        board.process_mirror_moves(piece, old_x, old_y, rng, active_synergies)

    # Clean up dead pieces so subsequent evaluation is accurate
    board.pieces = [p for p in board.pieces if p.alive]
    board._grid_dirty = True


def minimax_choose_move(
    team: Team, board: Board,
    rng: random.Random | None = None,
    excluded: dict[int, tuple[int, int]] | None = None,
    piece_streaks: dict[int, int] | None = None,
    active_synergies: list[str] | None = None,
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

    # --- Move pruning: prioritize captures and limit breadth ---
    MAX_OUR_MOVES = 20
    MAX_ENEMY_MOVES = 12

    if len(moves) > MAX_OUR_MOVES:
        # Prioritize: captures first, then non-captures sorted by piece value
        captures = []
        non_captures = []
        for m in moves:
            p, mx, my = m
            target = board.get_piece_at(mx, my)
            if target and target.team != p.team:
                captures.append(m)
            else:
                non_captures.append(m)
        _rng.shuffle(non_captures)
        moves = captures + non_captures[:MAX_OUR_MOVES - len(captures)]
        if len(moves) > MAX_OUR_MOVES:
            moves = moves[:MAX_OUR_MOVES]

    scores: list[float] = []

    for piece, mx, my in moves:
        # Clone board, apply our move
        clone = board.copy()
        p_idx = piece_indices.get(id(piece))
        if p_idx is None:
            scores.append(-999.0)
            continue
        clone_piece = clone.pieces[p_idx]
        _apply_move(clone, clone_piece, mx, my, _rng, active_synergies)

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

        # Prune enemy moves to limit search breadth
        if len(enemy_moves) > MAX_ENEMY_MOVES:
            e_captures = []
            e_non_captures = []
            for em in enemy_moves:
                ep, emx, emy = em
                et = clone.get_piece_at(emx, emy)
                if et and et.team != ep.team:
                    e_captures.append(em)
                else:
                    e_non_captures.append(em)
            _rng.shuffle(e_non_captures)
            enemy_moves = e_captures + e_non_captures[:MAX_ENEMY_MOVES - len(e_captures)]
            if len(enemy_moves) > MAX_ENEMY_MOVES:
                enemy_moves = enemy_moves[:MAX_ENEMY_MOVES]

        # Build enemy piece index for this clone
        e_piece_indices: dict[int, int] = {}
        for idx2, bp2 in enumerate(clone.pieces):
            e_piece_indices[id(bp2)] = idx2

        # Find the opponent's move that minimizes our score
        worst_for_us = float('inf')
        for ep, emx, emy in enemy_moves:
            clone2 = clone.copy()
            e_idx = e_piece_indices.get(id(ep))
            if e_idx is None:
                continue
            clone2_piece = clone2.pieces[e_idx]
            _apply_move(clone2, clone2_piece, emx, emy, _rng, active_synergies)

            val = evaluate_board(clone2, team)
            if val < worst_for_us:
                worst_for_us = val

        if worst_for_us == float('inf'):
            # No enemy moves evaluated — fallback
            worst_for_us = evaluate_board(clone, team)

        scores.append(worst_for_us)

    # Aggression bonus: prefer capture moves over passive positioning
    for i, (piece, mx, my) in enumerate(moves):
        target = board.get_piece_at(mx, my)
        if target and target.team != piece.team:
            scores[i] += 2.0

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
        master_key: str = "the_strategist",
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
        self.sudden_death_active: bool = False
        self.sudden_death_ring: int = 0  # next ring to close

        self.draft_options: list[dict] = []
        self.draft_selection = 0

        # Modifier system
        self.gold = 0
        self.cell_modifiers: list[CellModifier] = []    # owned but unplaced
        self.border_modifiers: list[BorderModifier] = []  # owned but unplaced

        # Shop
        self.shop_items: list[dict] = []
        self.shop_row: int = 0    # which section row (0=piece mods, 1=board, 2=specials, last=done)
        self.shop_col: int = 0    # which item within current row

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

        # Last actions for frontend animation (cleared each tick)
        self._last_actions: dict[tuple[int, int], dict] = {}

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

        # --- Master system ---
        from masters import MASTERS, DEFAULT_MASTER
        self.master_key: str = master_key if master_key in MASTERS else DEFAULT_MASTER
        self.master = MASTERS[self.master_key]

        # --- Synergy system ---
        self.active_synergies: list[str] = []

        # --- Achievement system ---
        self._achievement_checker = AchievementChecker()
        self.new_achievements: list[dict] = []  # populated per-phase for frontend toasts
        self.run_stats: dict = {
            "max_damage_hit": 0,
            "max_pieces_alive": 0,
            "pieces_lost_this_battle": 0,
            "total_gold_earned_run": 0,
            "total_gold_spent_run": 0,
            "shop_purchases_run": 0,
            "items_sold_run": 0,
            "unique_piece_types_used": set(),
            "max_mods_on_piece": 0,
            "gilded_win_streak": 0,
            "random_events_count": 0,
            "max_kills_one_piece": {},  # piece_id -> kill count
            "ondeath_this_turn": 0,
            "max_ondeath_in_turn": 0,
            "king_damage_dealt": 0,
            "overkill_3x": False,
            "phoenix_revives_this_battle": 0,
            "tarots_used_this_run": set(),
            "artifacts_used_this_run": set(),
        }
        self.run_start_time: float = time.time()

        # --- Tarot & Artifact system ---
        self.tarot_cards: list[dict] = []   # held tarots (key dicts from TAROT_CARDS)
        self.artifacts: list[dict] = []     # held artifacts (key dicts from ARTIFACTS)
        self.tarot_slots: int = 1           # max tarots (1 base + ELO upgrades)
        self.artifact_slots: int = 2        # max artifacts (2 base + ELO upgrades)
        # Track one-time-per-wave effects
        self.anchor_chain_used: bool = False
        self.first_capture_this_turn: bool = True

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

        # Reset tarot/artifact state
        self.tarot_cards = []
        self.artifacts = []
        self.tarot_slots = 1
        self.artifact_slots = 2

        # Reset run stats for achievements
        self.new_achievements = []
        self.run_stats = {
            "max_damage_hit": 0,
            "max_pieces_alive": 0,
            "pieces_lost_this_battle": 0,
            "total_gold_earned_run": 0,
            "total_gold_spent_run": 0,
            "shop_purchases_run": 0,
            "items_sold_run": 0,
            "unique_piece_types_used": set(),
            "max_mods_on_piece": 0,
            "gilded_win_streak": 0,
            "random_events_count": 0,
            "max_kills_one_piece": {},
            "ondeath_this_turn": 0,
            "max_ondeath_in_turn": 0,
            "king_damage_dealt": 0,
            "overkill_3x": False,
            "phoenix_revives_this_battle": 0,
            "tarots_used_this_run": set(),
            "artifacts_used_this_run": set(),
        }
        self.run_start_time = time.time()

        if self.tournament and self.save_data:
            # Apply unlocks from save data
            self.max_lives = 3 + self.save_data.upgrades.get("extra_life", 0)
            self.gold = 5 * self.save_data.upgrades.get("start_gold", 0)
            self.tarot_slots = 1 + self.save_data.upgrades.get("tarot_slot", 0)
            self.artifact_slots = 2 + self.save_data.upgrades.get("artifact_slot", 0)

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

        # --- Apply master starting bonuses ---
        self._apply_master_start()

        # Track starting roster piece types for achievements
        for p in self.roster:
            self.run_stats["unique_piece_types_used"].add(p.piece_type.value)

        self._start_wave()

    def _apply_master_start(self) -> None:
        """Apply the selected master's starting bonus."""
        mk = self.master_key

        if mk == "the_strategist":
            # +1 extra roster slot (add a Pawn)
            self.roster.append(Piece(PieceType.PAWN, Team.PLAYER))

        elif mk == "the_arsonist":
            # All starting pieces gain Flaming
            for p in self.roster:
                if not any(m.effect == "flaming" for m in p.modifiers):
                    p.modifiers.append(MODIFIERS["flaming"])

        elif mk == "the_blacksmith":
            # Start with Forge Hammer artifact
            self.artifacts.append(ARTIFACTS["forge_hammer"])

        elif mk == "the_gambler":
            # Start with 15 gold, Lucky Coin artifact
            self.gold += 15
            self.artifacts.append(ARTIFACTS["lucky_coin"])

        elif mk == "the_necromancer":
            # Start with Phoenix and Bomb
            self.roster.append(Piece(PieceType.PHOENIX, Team.PLAYER))
            self.roster.append(Piece(PieceType.BOMB, Team.PLAYER))
            # Drawback: -2 max HP on all pieces
            for p in self.roster:
                p.max_hp = max(1, p.max_hp - 2)
                p.hp = min(p.hp, p.max_hp)

        elif mk == "the_tactician":
            # Start with The Tactician tarot
            self.tarot_cards.append(TAROT_CARDS["the_tactician"])

        elif mk == "the_pauper":
            # Start with 0 gold, 4 extra Pawns
            self.gold = 0
            for _ in range(4):
                pawn = Piece(PieceType.PAWN, Team.PLAYER)
                pawn.max_hp += 3
                pawn.hp = pawn.max_hp
                self.roster.append(pawn)

        elif mk == "the_collector":
            # +1 tarot slot, +1 artifact slot
            self.tarot_slots += 1
            self.artifact_slots += 1
            # Drawback: -1 ATK on all pieces
            for p in self.roster:
                p.attack = max(0, p.attack - 1)

        elif mk == "the_berserker":
            # +3 ATK to all pieces
            for p in self.roster:
                p.attack += 3

        elif mk == "the_warden":
            # Start with 2 Anchor Pieces
            self.roster.append(Piece(PieceType.ANCHOR_PIECE, Team.PLAYER))
            self.roster.append(Piece(PieceType.ANCHOR_PIECE, Team.PLAYER))

        elif mk == "the_alchemist":
            # Start with 3 random cell mods pre-placed
            cell_keys = list(CELL_MODIFIERS.keys())
            for _ in range(3):
                key = self.rng.choice(cell_keys)
                cx, cy = self.rng.randint(0, 7), self.rng.randint(4, 7)
                if (cx, cy) not in self.board.cell_modifiers:
                    cm = make_cell_modifier(key, cx, cy)
                    self.board.cell_modifiers[(cx, cy)] = cm
                    self.cell_modifiers.append(cm)

        elif mk == "the_hivemind":
            # Start with 3 King Rats
            for _ in range(3):
                self.roster.append(Piece(PieceType.KING_RAT, Team.PLAYER))

        elif mk == "the_phantom":
            # Start with 2 Ghosts, -3 max HP drawback
            self.roster.append(Piece(PieceType.GHOST, Team.PLAYER))
            self.roster.append(Piece(PieceType.GHOST, Team.PLAYER))
            for p in self.roster:
                p.max_hp = max(1, p.max_hp - 3)
                p.hp = min(p.hp, p.max_hp)

        elif mk == "the_merchant":
            # Start with 20 gold and The Merchant tarot
            self.gold += 20
            self.tarot_cards.append(TAROT_CARDS["the_merchant"])

        elif mk == "the_anarchist":
            # Start with Chaos Orb artifact
            self.artifacts.append(ARTIFACTS["chaos_orb"])

        elif mk == "the_mirror_master":
            # No starting roster — will copy enemy first wave
            self.roster = []

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
            "hp": p.hp,
            "max_hp": p.max_hp,
            "attack": p.attack,
            "ability_flags": dict(p.ability_flags),
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
        # Restore HP/attack (falls back to __post_init__ defaults if missing)
        if "hp" in d:
            p.hp = d["hp"]
        if "max_hp" in d:
            p.max_hp = d["max_hp"]
        if "attack" in d:
            p.attack = d["attack"]
        if "ability_flags" in d:
            p.ability_flags = dict(d["ability_flags"])
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

        # Serialize run_stats — convert sets to lists for JSON
        serializable_run_stats = {}
        for k, v in self.run_stats.items():
            if isinstance(v, set):
                serializable_run_stats[k] = list(v)
            else:
                serializable_run_stats[k] = v

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
            "tarot_cards": [dict(t) for t in self.tarot_cards],
            "artifacts": [dict(a) for a in self.artifacts],
            "tarot_slots": self.tarot_slots,
            "artifact_slots": self.artifact_slots,
            "master_key": self.master_key,
            "run_stats": serializable_run_stats,
            "run_start_time": self.run_start_time,
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

        # Restore tarot & artifact state
        self.tarot_cards = state.get("tarot_cards", [])
        self.artifacts = state.get("artifacts", [])
        self.tarot_slots = state.get("tarot_slots", 1)
        self.artifact_slots = state.get("artifact_slots", 2)

        # Restore run stats (convert lists back to sets)
        saved_run_stats = state.get("run_stats")
        if saved_run_stats:
            set_keys = {"unique_piece_types_used", "tarots_used_this_run", "artifacts_used_this_run"}
            for k, v in saved_run_stats.items():
                if k in set_keys and isinstance(v, list):
                    self.run_stats[k] = set(v)
                else:
                    self.run_stats[k] = v
        self.run_start_time = state.get("run_start_time", time.time())

        # Restore master from saved state
        saved_master = state.get("master_key", "the_strategist")
        from masters import MASTERS, DEFAULT_MASTER
        self.master_key = saved_master if saved_master in MASTERS else DEFAULT_MASTER
        self.master = MASTERS[self.master_key]

        # _start_wave increments wave, so offset by -1 to land on saved wave
        saved_phase = state.get("phase", "setup")
        self.wave -= 1
        self._start_wave()
        # Restore the exact phase from the save (start_wave may set a different one)
        self.phase = saved_phase
        # If restored into shop phase, regenerate shop items (not serialized)
        if saved_phase == "shop":
            self._generate_shop()

    def _auto_save(self) -> None:
        """Save current run state to disk at checkpoint phases."""
        sd.save_run(self.to_run_state())

    def _update_cursor_from_board(self, bx: int, by: int) -> None:
        """Set cursor from JS-provided board coordinates."""
        if self.board.in_bounds(bx, by):
            self.cursor = (bx, by)

    def to_render_state(self) -> dict:
        """Serialize everything JS needs to render the current phase."""
        # Compute warning zone for sudden death
        warning_cells: set[tuple[int, int]] = set()
        if self.sudden_death_active and self.phase == "battle":
            warning_cells = self.board.get_warning_cells(self.sudden_death_ring)

        # Build 8x8 board grid
        board_grid = []
        for row_y in range(self.board.height):
            row = []
            for col_x in range(self.board.width):
                piece = self.board.get_piece_at(col_x, row_y)
                piece_data = None
                if piece:
                    mods = [{"name": m.name, "effect": m.effect, "description": m.description, "rarity": PIECE_MOD_RARITY.get(m.effect, Rarity.COMMON).value} for m in piece.modifiers]
                    cm = None
                    if piece.cell_modifier:
                        cm = piece.cell_modifier.effect
                    info = PIECE_INFO.get(piece.piece_type, {})
                    piece_rarity = PIECE_RARITY.get(piece.piece_type.value, Rarity.COMMON)
                    # Look up last action for this cell
                    last_action = self._last_actions.get((col_x, row_y))
                    piece_data = {
                        "type": piece.piece_type.value,
                        "team": piece.team.value,
                        "modifiers": mods,
                        "cellMod": cm,
                        "hp": piece.hp,
                        "maxHp": piece.max_hp,
                        "attack": piece.attack,
                        "moveDesc": info.get("move", ""),
                        "ability": info.get("ability", ""),
                        "rarity": piece_rarity.value,
                        "lastAction": last_action,
                    }

                cell_mod = None
                cm_obj = self.board.cell_modifiers.get((col_x, row_y))
                if cm_obj:
                    from modifiers import CELL_MODIFIERS
                    cm_desc = CELL_MODIFIERS.get(cm_obj.effect, {}).get("description", "")
                    cell_mod = {
                        "name": cm_obj.name,
                        "effect": cm_obj.effect,
                        "color": list(cm_obj.color),
                        "description": cm_desc,
                    }

                border_mod = None
                bm_obj = self.board.border_modifiers.get((col_x, row_y))
                if bm_obj:
                    from modifiers import BORDER_MODIFIERS
                    bm_desc = BORDER_MODIFIERS.get(bm_obj.effect, {}).get("description", "")
                    border_mod = {
                        "name": bm_obj.name,
                        "effect": bm_obj.effect,
                        "color": list(bm_obj.border_color),
                        "description": bm_desc,
                    }

                row.append({
                    "x": col_x,
                    "y": row_y,
                    "piece": piece_data,
                    "cellMod": cell_mod,
                    "borderMod": border_mod,
                    "blocked": self.board.is_blocked(col_x, row_y),
                    "deadZone": (col_x, row_y) in self.board.dead_zone,
                    "warningZone": (col_x, row_y) in warning_cells,
                })
            board_grid.append(row)

        # Highlights map
        highlights = {}
        if self.phase == "setup":
            for bx in range(self.board.width):
                for by in range(4, self.board.height):
                    if self.board.is_empty(bx, by):
                        highlights[f"{bx},{by}"] = "zone"
        if self.selected_piece:
            highlights[f"{self.selected_piece.x},{self.selected_piece.y}"] = "selected"
            for mx, my in self.valid_moves:
                target = self.board.get_piece_at(mx, my)
                if target and target.team != self.selected_piece.team:
                    highlights[f"{mx},{my}"] = "capture"
                else:
                    highlights[f"{mx},{my}"] = "move"

        # Roster info
        roster_data = []
        for p in self.roster:
            mods = [{"name": m.name, "effect": m.effect, "description": m.description, "rarity": PIECE_MOD_RARITY.get(m.effect, Rarity.COMMON).value} for m in p.modifiers]
            info = PIECE_INFO.get(p.piece_type, {})
            piece_rarity = PIECE_RARITY.get(p.piece_type.value, Rarity.COMMON)
            roster_data.append({
                "type": p.piece_type.value,
                "team": p.team.value,
                "placed": p in self.placed,
                "alive": p.alive,
                "modifiers": mods,
                "hp": p.hp,
                "maxHp": p.max_hp,
                "attack": p.attack,
                "moveDesc": info.get("move", ""),
                "ability": info.get("ability", ""),
                "rarity": piece_rarity.value,
            })

        # Selected piece info
        sel_piece = None
        if self.selected_piece and self.selected_piece.alive:
            sel_piece = {
                "x": self.selected_piece.x,
                "y": self.selected_piece.y,
                "type": self.selected_piece.piece_type.value,
            }

        state = {
            "phase": self.phase,
            "board": board_grid,
            "boardWidth": self.board.width,
            "boardHeight": self.board.height,
            "cursor": list(self.cursor),
            "highlights": highlights,
            "wave": self.wave,
            "gold": self.gold,
            "wins": self.wins,
            "losses": self.losses,
            "maxLives": self.max_lives,
            "lives": self.max_lives - self.losses,
            "message": self.message,
            "battleLog": self.battle_log[-14:],
            "battleTurn": self.battle_turn,
            "suddenDeath": self.sudden_death_active,
            "suddenDeathRing": self.sudden_death_ring,
            "manualMode": self.manual_mode,
            "playerTurn": self.battle_player_turn,
            "tournament": self.tournament,
            "difficulty": self.difficulty,
            "roster": roster_data,
            "rosterSelection": self.roster_selection,
            "selectedPiece": sel_piece,
            "validMoves": [list(m) for m in self.valid_moves],
            "tarotCards": [dict(t) for t in self.tarot_cards],
            "artifacts": [dict(a) for a in self.artifacts],
            "tarotSlots": self.tarot_slots,
            "artifactSlots": self.artifact_slots,
            "seed": self.seed,
            "activeSynergies": get_synergy_display_data(self.active_synergies),
            "master": {
                "key": self.master.key,
                "name": self.master.name,
                "icon": self.master.icon,
                "color": list(self.master.color),
                "passive": self.master.passive_desc,
                "drawback": self.master.drawback_desc,
            },
            "newAchievements": list(self.new_achievements),
        }

        # Clear achievements after sending to frontend
        self.new_achievements = []

        # Phase-specific data
        if self.phase == "shop":
            shop_rows = self._get_shop_rows()
            rows_data = []
            for r in shop_rows:
                items_data = []
                for flat_idx, item in r["items"]:
                    items_data.append({
                        "index": flat_idx,
                        "type": item["type"],
                        "key": item.get("key", ""),
                        "name": item["name"],
                        "cost": item["cost"],
                        "description": item.get("description", ""),
                        "category": item.get("category", ""),
                        "color": list(item.get("color", (200, 200, 200))),
                        "icon": item.get("icon", "?"),
                        "rarity": item.get("rarity", "common"),
                    })
                rows_data.append({
                    "label": r["label"],
                    "color": list(r["color"]),
                    "items": items_data,
                })
            state["shopRows"] = rows_data
            state["shopRow"] = self.shop_row
            state["shopCol"] = self.shop_col

        if self.phase == "draft":
            draft_data = []
            for opt in self.draft_options:
                d = {"type": opt["type"], "desc": opt["desc"]}
                if opt["type"] == "add":
                    d["pieceType"] = opt["piece_type"].value
                    d["rarity"] = opt.get("rarity", "common")
                elif opt["type"] == "combine":
                    d["from"] = opt["from"].value
                    d["to"] = opt["to"].value
                    d["count"] = opt["count"]
                draft_data.append(d)
            state["draftOptions"] = draft_data
            state["draftSelection"] = self.draft_selection

        if self.phase in ("place_cell", "place_border", "place_piece_mod", "swap_tarot"):
            placing = None
            if self.placing_item:
                placing = {
                    "type": self.placing_item["type"],
                    "name": self.placing_item.get("name", ""),
                    "key": self.placing_item.get("key", ""),
                }
            state["placingItem"] = placing

        if self.phase == "boss_intro":
            boss_type = self.boss_sequence[self.boss_index] if self.boss_index < len(self.boss_sequence) else None
            state["bossType"] = boss_type.value if boss_type else ""
            boss_info = BOSS_TABLE.get(boss_type, {}) if boss_type else {}
            state["bossMods"] = boss_info.get("mods", [])

        if self.phase == "tournament_end":
            state["tournamentStats"] = dict(self.tournament_stats)
            state["eloEarned"] = self.elo_earned
            won = int(self.tournament_stats.get("bosses_beaten", 0)) >= len(self.boss_sequence)
            state["tournamentWon"] = won

        if self.phase == "game_over":
            state["playAgain"] = self.play_again

        return state

    def _start_wave(self) -> None:
        self.wave += 1
        self.board.clear()
        self.placed = []
        self.held_piece = None
        self.battle_log = []
        self.battle_turn = 0
        self.battle_player_turn = True
        self.sudden_death_active = False
        self.sudden_death_ring = 0
        self.roster_selection = 0
        self.cursor = (3, 5)
        self.message = "Place pieces on your half, then SPACE to fight."

        for p in self.roster:
            p.alive = True
            p.has_moved = False
            p.cell_modifier = None  # strip absorbed cell mods
            p.hp = p.max_hp  # reset HP to full each wave

        # Check synergies at wave start
        board_cell_mods = list(self.board.cell_modifiers.values())
        board_border_mods = list(self.board.border_modifiers.values())
        self.active_synergies = check_synergies(
            self.roster, Team.PLAYER,
            master_key=self.master_key,
            held_artifacts=self.artifacts,
            held_tarots=self.tarot_cards,
            board_cell_mods=board_cell_mods,
            board_border_mods=board_border_mods,
            has_infinity_loop=self._has_artifact("infinity_loop"),
        )

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

        # --- Apply tarot & artifact wave-start effects ---
        self._apply_wave_start_effects()

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
            pool.extend([PieceType.BISHOP, PieceType.KNIGHT, PieceType.DUELIST, PieceType.DECOY])
        if self.wave >= 3:
            pool.extend([PieceType.BOMB, PieceType.KING_RAT, PieceType.LANCER, PieceType.CHARGER,
                         PieceType.BARD, PieceType.WALL])
        if self.wave >= 4:
            pool.extend([PieceType.ROOK, PieceType.QUEEN, PieceType.LEECH, PieceType.PARASITE,
                         PieceType.ASSASSIN, PieceType.BERSERKER_PIECE, PieceType.CANNON,
                         PieceType.SENTINEL, PieceType.HEALER, PieceType.TOTEM])
        if self.wave >= 5:
            pool.extend([PieceType.GHOST, PieceType.MIMIC, PieceType.SUMMONER,
                         PieceType.REAPER, PieceType.WYVERN, PieceType.ALCHEMIST_PIECE,
                         PieceType.GOLEM, PieceType.WITCH, PieceType.TRICKSTER])
        if self.wave >= 6:
            pool.extend([PieceType.PHOENIX, PieceType.GAMBLER, PieceType.VOID,
                         PieceType.SHAPESHIFTER, PieceType.TIME_MAGE, PieceType.IMP,
                         PieceType.POLTERGEIST])

        # De-duplicate pool and assign rarity-based weights
        unique_pool = list(dict.fromkeys(pool))  # preserves order, removes dupes
        weights = []
        for pt in unique_pool:
            r = PIECE_RARITY.get(pt.value, Rarity.COMMON)
            weights.append(RARITY_PROPS[r]["weight"])

        used = set()
        for _ in range(num_enemies):
            pt = self.rng.choices(unique_pool, weights=weights, k=1)[0]
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

    def _calculate_elo(self, cash_out: bool = False) -> int:
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
            if cash_out:
                total *= 0.333  # Cash out: 1/3 earnings
            else:
                total *= 0.25   # Loss penalty: 1/4 earnings

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
        elif self.phase == "swap_tarot":
            return self._handle_swap_tarot(action)
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
        old_x, old_y = piece.x, piece.y
        target = self.board.get_piece_at(mx, my)
        if target and target.team != piece.team:
            target_type = target.piece_type
            target_hp_before = target.hp
            captured = self.board.move_piece(piece, mx, my, rng=self.rng,
                                             active_synergies=self.active_synergies)
            self._check_anchor_chain()

            if captured:
                # The Pawn: pawns that capture promote to the killed piece type
                if (self._has_tarot("the_pawn") and piece.alive
                        and piece.piece_type == PieceType.PAWN
                        and target_type != PieceType.PAWN):
                    piece.piece_type = target_type
                    self.battle_log.append(f"Pawn promotes to {target_type.value}!")
                log = f"Player {piece.piece_type.value} kills {target_type.value}!"
                self._trigger_shake(0.3)
                sx, sy = self._board_to_screen(mx, my)
                self.particles.spawn("capture_burst", sx, sy, color=renderer.FG_PLAYER)
                # Process on-death abilities
                death_msgs = self.board.process_on_death(target, piece, self.rng,
                                                          self.active_synergies)
                self.battle_log.extend(death_msgs)
            else:
                # Bounce-back: target survived
                dmg = target_hp_before - target.hp
                log = f"Player {piece.piece_type.value} hits {target_type.value} for {dmg} (HP:{target.hp}/{target.max_hp}) — bounced back"

            # Process mirror moves
            mirror_msgs = self.board.process_mirror_moves(piece, old_x, old_y, self.rng,
                                                           self.active_synergies)
            self.battle_log.extend(mirror_msgs)
        else:
            piece.x, piece.y = mx, my
            piece.has_moved = True
            self.board._grid_dirty = True
            log = f"Player {piece.piece_type.value} moves"
            # Process mirror moves for non-capture moves too
            mirror_msgs = self.board.process_mirror_moves(piece, old_x, old_y, self.rng,
                                                           self.active_synergies)
            self.battle_log.extend(mirror_msgs)

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

    def _check_anchor_chain(self) -> None:
        """Anchor Chain artifact: first player piece to die each wave survives instead."""
        if self.anchor_chain_used or not self._has_artifact("anchor_chain"):
            return
        # Check if any player piece just died (alive=False but still in pieces list)
        for p in self.board.pieces:
            if p.team == Team.PLAYER and not p.alive and p in self.roster:
                p.alive = True
                self.board._grid_dirty = True
                self.anchor_chain_used = True
                self.battle_log.append(f"Anchor Chain saves {p.piece_type.value}!")
                break

    def _enemy_step(self) -> None:
        """Execute one AI enemy turn, then switch back to player."""
        # Process turn-start abilities for enemy
        ability_msgs = self.board.process_turn_start_abilities(Team.ENEMY, self.rng,
                                                                self.active_synergies)
        self.battle_log.extend(ability_msgs)

        pieces = self.board.get_team_pieces(Team.ENEMY)
        if not pieces:
            self._end_battle()
            return

        result = minimax_choose_move(
            Team.ENEMY, self.board, rng=self.rng,
            excluded=self._prev_positions,
            piece_streaks=self._piece_noncapture_streak,
            active_synergies=self.active_synergies,
        )

        if result:
            best_piece, mx, my = result
            old_x, old_y = best_piece.x, best_piece.y
            target = self.board.get_piece_at(mx, my)
            is_capture = target and target.team != best_piece.team
            self._record_move(best_piece, best_piece.x, best_piece.y, captured=bool(is_capture))
            if is_capture:
                target_type = target.piece_type
                target_hp_before = target.hp
                captured = self.board.move_piece(best_piece, mx, my, rng=self.rng,
                                                  active_synergies=self.active_synergies)
                self._check_anchor_chain()
                if captured:
                    log = f"Enemy {best_piece.piece_type.value} kills {target_type.value}!"
                    self._trigger_shake(0.3)
                    sx, sy = self._board_to_screen(mx, my)
                    self.particles.spawn("capture_burst", sx, sy, color=renderer.FG_ENEMY)
                    death_msgs = self.board.process_on_death(target, best_piece, self.rng,
                                                              self.active_synergies)
                    self.battle_log.extend(death_msgs)
                else:
                    dmg = target_hp_before - target.hp
                    log = f"Enemy {best_piece.piece_type.value} hits {target_type.value} for {dmg} (HP:{target.hp}) — bounced"
            else:
                old_type = best_piece.piece_type
                best_piece.x, best_piece.y = mx, my
                best_piece.has_moved = True
                self.board._grid_dirty = True
                if self.board.check_promotion(best_piece, self.rng):
                    log = f"Enemy {old_type.value} promotes to {best_piece.piece_type.value}!"
                    sx, sy = self._board_to_screen(mx, my)
                    self.particles.spawn("capture_burst", sx, sy, color=(255, 100, 100))
                else:
                    log = f"Enemy {best_piece.piece_type.value} moves"
            # Mirror moves
            mirror_msgs = self.board.process_mirror_moves(best_piece, old_x, old_y, self.rng,
                                                           self.active_synergies)
            self.battle_log.extend(mirror_msgs)
        else:
            # Stuck pieces take 1 damage each turn from attrition
            stuck_pieces = self.board.get_team_pieces(Team.ENEMY)
            for sp in stuck_pieces:
                sp.hp -= 1
                if sp.hp <= 0:
                    sp.alive = False
            self.board.pieces = [p for p in self.board.pieces if p.alive]
            self.board._grid_dirty = True
            killed = len(stuck_pieces) - self.board.count_alive(Team.ENEMY)
            if killed > 0:
                log = f"Enemy pieces stuck — {killed} crushed!"
            else:
                log = "Enemy pieces stuck — taking attrition damage"

        self.battle_log.append(log)
        if len(self.battle_log) > 14:
            self.battle_log = self.battle_log[-14:]
        self.message = log

        # Process turn-start abilities for player (start of player's next turn)
        player_ability_msgs = self.board.process_turn_start_abilities(Team.PLAYER, self.rng,
                                                                       self.active_synergies)
        self.battle_log.extend(player_ability_msgs)

        self.battle_player_turn = True
        self.battle_turn += 1

        if self.board.count_alive(Team.PLAYER) == 0 or self.board.count_alive(Team.ENEMY) == 0:
            self._end_battle()
        elif self.phase == "battle":
            self._check_sudden_death()

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

    def _check_sudden_death(self) -> None:
        """Check and process sudden death events for the current turn."""
        turn = self.battle_turn

        # Announcement
        if turn == SUDDEN_DEATH_ANNOUNCE and not self.sudden_death_active:
            self.sudden_death_active = True
            self.battle_log.append("--- SUDDEN DEATH! The board will shrink! ---")
            self.message = "SUDDEN DEATH!"

        # Ring closures
        if turn in SUDDEN_DEATH_SCHEDULE:
            ring = SUDDEN_DEATH_SCHEDULE[turn]
            killed, pushed = self.board.close_ring(ring)
            self.sudden_death_ring = ring + 1

            ring_names = {0: "outer edge", 1: "second ring", 2: "third ring", 3: "center"}
            self.battle_log.append(f"Ring collapse! The {ring_names.get(ring, 'ring')} crumbles!")

            if pushed:
                self.battle_log.append(f"  {len(pushed)} piece(s) pushed inward")

            for p in killed:
                team_name = "Player" if p.team == Team.PLAYER else "Enemy"
                self.battle_log.append(f"  {team_name} {p.piece_type.value} crushed in the squeeze!")
                death_msgs = self.board.process_on_death(p, None, self.rng, self.active_synergies)
                self.battle_log.extend(death_msgs)

            # Clean up dead pieces
            self.board.pieces = [p for p in self.board.pieces if p.alive]
            self.board._grid_dirty = True

            # Check if battle ends from collapse
            player_alive = self.board.count_alive(Team.PLAYER)
            enemy_alive = self.board.count_alive(Team.ENEMY)
            if player_alive == 0 or enemy_alive == 0:
                self._end_battle()
                return

            # If entire board is dead zone, force kill remaining pieces
            max_ring = min(self.board.width, self.board.height) // 2
            if self.sudden_death_ring >= max_ring:
                # No playable cells left — kill everyone
                for p in self.board.pieces:
                    p.alive = False
                self.board.pieces.clear()
                self.battle_log.append("The arena is completely destroyed!")
                self._end_battle()
                return

        # Safety cap
        if turn >= SAFETY_CAP and self.phase == "battle":
            self.battle_log.append("The arena collapses completely!")
            self._end_battle()

    def _battle_step(self) -> None:
        team = Team.PLAYER if self.battle_player_turn else Team.ENEMY

        # Clear last actions from previous tick (for frontend animations)
        self._last_actions = {}

        # Reset per-turn on-death counter
        self.run_stats["ondeath_this_turn"] = 0

        # Process turn-start abilities
        ability_msgs = self.board.process_turn_start_abilities(team, self.rng,
                                                                self.active_synergies)
        self.battle_log.extend(ability_msgs)

        pieces = self.board.get_team_pieces(team)
        if not pieces:
            self._end_battle()
            return

        result = minimax_choose_move(
            team, self.board, rng=self.rng,
            excluded=self._prev_positions,
            piece_streaks=self._piece_noncapture_streak,
            active_synergies=self.active_synergies,
        )

        if result:
            best_piece, mx, my = result
            old_x, old_y = best_piece.x, best_piece.y
            target = self.board.get_piece_at(mx, my)
            is_capture = target and target.team != best_piece.team
            self._record_move(best_piece, best_piece.x, best_piece.y, captured=bool(is_capture))
            # Record last action for frontend animations
            if is_capture:
                self._last_actions[(mx, my)] = {
                    "type": "attack",
                    "targetX": mx,
                    "targetY": my,
                    "fromX": old_x,
                    "fromY": old_y,
                }
            else:
                self._last_actions[(mx, my)] = {"type": "move"}
            if is_capture:
                target_type = target.piece_type
                target_hp_before = target.hp
                target_max_hp = target.max_hp
                captured = self.board.move_piece(best_piece, mx, my, rng=self.rng,
                                                  active_synergies=self.active_synergies)
                self._check_anchor_chain()

                # --- Achievement stat tracking ---
                dmg = target_hp_before - (target.hp if not captured else 0)
                if dmg > self.run_stats["max_damage_hit"]:
                    self.run_stats["max_damage_hit"] = dmg
                    if self.save_data:
                        prev = self.save_data.stats.get("max_damage_single_hit", 0)
                        if dmg > prev:
                            self.save_data.stats["max_damage_single_hit"] = dmg
                # Overkill: damage >= 3x target max HP
                if captured and dmg >= target_max_hp * 3:
                    self.run_stats["overkill_3x"] = True
                # King damage tracking
                if best_piece.team == Team.PLAYER and best_piece.piece_type == PieceType.KING:
                    self.run_stats["king_damage_dealt"] += dmg
                # Kill tracking per piece
                if captured and best_piece.team == Team.PLAYER:
                    pid = id(best_piece)
                    kills = self.run_stats["max_kills_one_piece"]
                    kills[pid] = kills.get(pid, 0) + 1

                if captured:
                    log = f"{team.value} {best_piece.piece_type.value} kills {target_type.value}!"
                    self._trigger_shake(0.3)
                    sx, sy = self._board_to_screen(mx, my)
                    cap_color = renderer.FG_PLAYER if best_piece.team == Team.PLAYER else renderer.FG_ENEMY
                    self.particles.spawn("capture_burst", sx, sy, color=cap_color)
                    # Track alive pieces before on-death (for phoenix revive detection)
                    alive_before = set(id(p) for p in self.board.pieces if p.alive and p.team == Team.PLAYER)
                    death_msgs = self.board.process_on_death(target, best_piece, self.rng,
                                                              self.active_synergies)
                    self.battle_log.extend(death_msgs)
                    # On-death trigger tracking
                    if death_msgs:
                        self.run_stats["ondeath_this_turn"] += len(death_msgs)
                        if self.run_stats["ondeath_this_turn"] > self.run_stats["max_ondeath_in_turn"]:
                            self.run_stats["max_ondeath_in_turn"] = self.run_stats["ondeath_this_turn"]
                    # Phoenix revive detection: pieces that were dead are now alive
                    alive_after = set(id(p) for p in self.board.pieces if p.alive and p.team == Team.PLAYER)
                    revived = alive_after - alive_before
                    if revived:
                        self.run_stats["phoenix_revives_this_battle"] += len(revived)
                        if self.save_data:
                            self.save_data.stats["total_revives"] = \
                                self.save_data.stats.get("total_revives", 0) + len(revived)
                else:
                    log = f"{team.value} {best_piece.piece_type.value} hits {target_type.value} for {dmg} (HP:{target.hp}) — bounced"
            else:
                old_type = best_piece.piece_type
                best_piece.x, best_piece.y = mx, my
                best_piece.has_moved = True
                self.board._grid_dirty = True
                if self.board.check_promotion(best_piece, self.rng):
                    log = f"{team.value} {old_type.value} promotes to {best_piece.piece_type.value}!"
                    sx, sy = self._board_to_screen(mx, my)
                    self.particles.spawn("capture_burst", sx, sy, color=(255, 220, 100))
                else:
                    log = f"{team.value} {best_piece.piece_type.value} moves"
            # Mirror moves
            mirror_msgs = self.board.process_mirror_moves(best_piece, old_x, old_y, self.rng,
                                                           self.active_synergies)
            self.battle_log.extend(mirror_msgs)
        else:
            # Stuck pieces take 1 damage each turn from attrition
            stuck_pieces = self.board.get_team_pieces(team)
            for sp in stuck_pieces:
                sp.hp -= 1
                if sp.hp <= 0:
                    sp.alive = False
            self.board.pieces = [p for p in self.board.pieces if p.alive]
            self.board._grid_dirty = True
            killed = len(stuck_pieces) - self.board.count_alive(team)
            if killed > 0:
                log = f"{team.value} pieces stuck — {killed} crushed!"
            else:
                log = f"{team.value} pieces stuck — taking attrition damage"

        self.battle_log.append(log)
        if len(self.battle_log) > 14:
            self.battle_log = self.battle_log[-14:]
        self.message = log

        self.battle_player_turn = not self.battle_player_turn
        if self.battle_player_turn:
            self.battle_turn += 1

        if self.board.count_alive(Team.PLAYER) == 0 or self.board.count_alive(Team.ENEMY) == 0:
            self._end_battle()
        elif self.phase == "battle":
            self._check_sudden_death()

    def _end_battle(self) -> None:
        player_alive = self.board.count_alive(Team.PLAYER)
        enemy_alive = self.board.count_alive(Team.ENEMY)
        won = player_alive > 0 and enemy_alive == 0

        # Track pieces alive for achievements
        self.run_stats["max_pieces_alive"] = max(
            self.run_stats["max_pieces_alive"], player_alive)

        if won:
            self.wins += 1
            # Gold reward: 2 + surviving pieces
            earned = 2 + player_alive
            # Royal modifier: surviving Royal pieces earn double score contribution
            royal_mult = 3 if self._has_artifact("iron_crown") else 2
            for p in self.board.get_team_pieces(Team.PLAYER):
                if any(m.effect == "royal" for m in p.modifiers):
                    earned += p.value * (royal_mult - 1)
            # Gold Tooth artifact: +2g per copy
            earned += 2 * self._artifact_count("gold_tooth")
            # The Merchant tarot: +3g per wave
            if self._has_tarot("the_merchant"):
                earned += 3
            # Dragon's Hoard: already applied at wave start

            # Merchant master drawback: waves give 50% less gold
            if self.master_key == "the_merchant":
                earned = earned // 2

            # Salvage Kit: +1 gold per friendly death (count dead roster pieces)
            if self._has_artifact("salvage_kit"):
                dead_count = sum(1 for p in self.roster if not p.alive)
                earned += dead_count

            # Trophy Rack: +1 gold per unique enemy type killed this run
            if self._has_artifact("trophy_rack"):
                killed_types = {p.piece_type.value for p in self.board.pieces
                               if not p.alive and p.team == Team.ENEMY}
                earned += len(killed_types)

            self.gold += earned
            self.run_stats["total_gold_earned_run"] += earned
            self.message = f"Victory! ({player_alive} survive) +{earned}g"
            self.battle_log.append(f"=== VICTORY === (+{earned}g)")
            self._trigger_flash((40, 200, 40))
            # Crown Jewel artifact: +1 ELO per wave won
            if self._has_artifact("crown_jewel") and self.tournament:
                self.elo_earned += 1

            # Gilded win streak tracking
            has_gilded = any(
                any(m.effect == "gilded" for m in p.modifiers)
                for p in self.board.get_team_pieces(Team.PLAYER)
            )
            if has_gilded:
                self.run_stats["gilded_win_streak"] += 1
            else:
                self.run_stats["gilded_win_streak"] = 0

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
                        self._check_battle_achievements(won=True)
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
            self.losses += 1
            self.gold += 1  # consolation gold for draw
            self.message = "Draw! -1 life (+1g)"
            self.battle_log.append("=== DRAW === -1 life (+1g)")
            self._trigger_flash((200, 150, 40))
            if self.tournament:
                self.tournament_stats["gold_earned"] += 1
                self.wave_in_round += 1

        # --- Achievement check after battle ---
        self._check_battle_achievements(won=won)

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

    def _check_elemental_trio(self) -> bool:
        """Check if player has fire, ice, and poison modifiers active."""
        player_pieces = self.board.get_team_pieces(Team.PLAYER)
        fire_effects = {"flaming", "blazing"}
        ice_effects = {"frozen"}
        poison_effects = {"toxic"}
        has_fire = has_ice = has_poison = False
        for p in player_pieces:
            for m in p.modifiers:
                if m.effect in fire_effects:
                    has_fire = True
                if m.effect in ice_effects:
                    has_ice = True
                if m.effect in poison_effects:
                    has_poison = True
        return has_fire and has_ice and has_poison

    def _check_mirror_match(self) -> bool:
        """Check if enemy composition matches player composition."""
        player_types = sorted(
            p.piece_type.value for p in self.board.get_team_pieces(Team.PLAYER)
        )
        enemy_types = sorted(
            p.piece_type.value for p in self.board.get_team_pieces(Team.ENEMY)
        )
        return player_types == enemy_types and len(player_types) > 0

    def _check_battle_achievements(self, won: bool) -> None:
        """Check achievements after a battle and process unlocks."""
        if not self.save_data:
            return

        player_pieces = self.board.get_team_pieces(Team.PLAYER)
        pieces_lost = sum(1 for p in self.roster if not p.alive)

        # Check if all surviving pieces are above 50% HP
        all_above_half = all(p.hp > p.max_hp // 2 for p in player_pieces) if player_pieces else False

        battle_stats = {
            "won": won,
            "player_survived": len(player_pieces),
            "pieces_lost": pieces_lost,
            "battle_turns": self.battle_turn,
            "max_damage_hit": self.run_stats.get("max_damage_hit", 0),
            "max_pieces_alive": self.run_stats.get("max_pieces_alive", 0),
            "overkill_3x": self.run_stats.get("overkill_3x", False),
            "max_ondeath_in_turn": self.run_stats.get("max_ondeath_in_turn", 0),
            "elemental_trio": self._check_elemental_trio(),
            "max_kills_one_piece": max(self.run_stats.get("max_kills_one_piece", {}).values(), default=0),
            "king_damage_dealt": self.run_stats.get("king_damage_dealt", 0),
            "phoenix_revives_this_battle": self.run_stats.get("phoenix_revives_this_battle", 0),
            "all_above_half_hp": all_above_half,
            "mirror_match": self._check_mirror_match(),
        }

        run_state = {
            "active_synergy_count": len(self.active_synergies),
            "artifact_count": len(self.artifacts),
            "tarot_count": len(self.tarot_cards),
            "unique_piece_types_used": len(self.run_stats.get("unique_piece_types_used", set())),
            "max_mods_on_piece": self.run_stats.get("max_mods_on_piece", 0),
            "gilded_win_streak": self.run_stats.get("gilded_win_streak", 0),
            "total_gold_earned_run": self.run_stats.get("total_gold_earned_run", 0),
            "random_events_count": self.run_stats.get("random_events_count", 0),
        }

        newly = self._achievement_checker.check_end_of_battle(run_state, battle_stats, self.save_data)
        if newly:
            process_unlocks(newly, self.save_data)
            self._build_achievement_toasts(newly)

        # Also check stat-based achievements
        stat_newly = self._achievement_checker.check_stats(self.save_data)
        if stat_newly:
            process_unlocks(stat_newly, self.save_data)
            self._build_achievement_toasts(stat_newly)

        # Reset per-battle stats
        self.run_stats["max_kills_one_piece"] = {}
        self.run_stats["phoenix_revives_this_battle"] = 0
        self.run_stats["ondeath_this_turn"] = 0
        self.run_stats["max_ondeath_in_turn"] = 0
        self.run_stats["overkill_3x"] = False
        self.run_stats["king_damage_dealt"] = 0

    def _check_run_achievements(self, won: bool) -> None:
        """Check run-end achievements."""
        if not self.save_data:
            return

        elapsed = time.time() - self.run_start_time
        roster_types = {p.piece_type.value for p in self.roster}
        pawns_only = all(
            p.piece_type in (PieceType.PAWN, PieceType.KING)
            for p in self.roster
        )

        # Compute total HP for lucky seven check
        total_hp = sum(p.hp for p in self.roster if p.alive)

        run_state = {
            "gold": self.gold,
            "total_hp": total_hp,
            "wave": self.wave,
            "difficulty": self.difficulty,
            "losses": self.losses,
            "max_lives": self.max_lives,
            "lives_remaining": self.max_lives - self.losses,
            "max_roster_size": len(self.roster),
            "shop_purchases": self.run_stats.get("shop_purchases_run", 0),
            "elapsed_seconds": elapsed,
            "pawns_only": pawns_only,
            "infinity_loop_triggered": False,
        }

        newly = self._achievement_checker.check_end_of_run(run_state, self.save_data, won)
        if newly:
            process_unlocks(newly, self.save_data)
            self._build_achievement_toasts(newly)

        # Update persistent stats
        stats = self.save_data.stats
        stats["total_gold_earned"] = stats.get("total_gold_earned", 0) + self.run_stats.get("total_gold_earned_run", 0)
        stats["total_gold_spent"] = stats.get("total_gold_spent", 0) + self.run_stats.get("total_gold_spent_run", 0)
        stats["items_sold"] = stats.get("items_sold", 0) + self.run_stats.get("items_sold_run", 0)
        stats["shop_items_bought"] = stats.get("shop_items_bought", 0) + self.run_stats.get("shop_purchases_run", 0)

        # Update set-type stats
        for t_key in self.run_stats.get("tarots_used_this_run", set()):
            used = stats.get("tarots_used_set", [])
            if t_key not in used:
                used.append(t_key)
            stats["tarots_used_set"] = used
        stats["different_tarots_used"] = len(stats.get("tarots_used_set", []))

        for a_key in self.run_stats.get("artifacts_used_this_run", set()):
            collected = stats.get("artifacts_collected_set", [])
            if a_key not in collected:
                collected.append(a_key)
            stats["artifacts_collected_set"] = collected
        stats["different_artifacts_collected"] = len(stats.get("artifacts_collected_set", []))

        if won:
            masters_won = stats.get("masters_won_with", [])
            if self.master_key not in masters_won:
                masters_won.append(self.master_key)
            stats["masters_won_with"] = masters_won
            stats["different_masters_won_with"] = len(masters_won)

            # Fastest tournament
            if elapsed > 0:
                fastest = stats.get("fastest_tournament_seconds", 0)
                if fastest == 0 or elapsed < fastest:
                    stats["fastest_tournament_seconds"] = int(elapsed)

        # Check stat-based achievements again after updating
        stat_newly = self._achievement_checker.check_stats(self.save_data)
        if stat_newly:
            process_unlocks(stat_newly, self.save_data)
            self._build_achievement_toasts(stat_newly)

    def _build_achievement_toasts(self, newly_unlocked: list[str]) -> None:
        """Build frontend-friendly toast data from newly unlocked achievement keys."""
        for key in newly_unlocked:
            ach = ACHIEVEMENT_MAP.get(key)
            if not ach:
                continue
            rewards = []
            for unlock in ach.unlocks:
                rewards.append({"type": unlock["type"], "key": unlock["key"]})
            self.new_achievements.append({
                "name": ach.name,
                "icon": ach.icon,
                "rewards": rewards,
            })

    def _cash_out(self) -> None:
        """Cash out of tournament early for 1/3 ELO instead of 1/4 penalty."""
        self.elo_earned = self._calculate_elo(cash_out=True)

        if self.save_data:
            self.save_data.elo += self.elo_earned
            self.save_data.stats["tournaments_completed"] = self.save_data.stats.get("tournaments_completed", 0) + 1
            self.save_data.stats["total_elo_earned"] = self.save_data.stats.get("total_elo_earned", 0) + self.elo_earned
            self.save_data.stats["bosses_beaten"] = self.save_data.stats.get("bosses_beaten", 0) + int(self.tournament_stats["bosses_beaten"])

            import save_data as sd_module
            sd_module.save(self.save_data)

        sd.clear_run()
        self.phase = "tournament_end"

    def _finish_tournament(self, won: bool) -> None:
        """End the tournament, calculate ELO, save results."""
        self.elo_earned = self._calculate_elo()

        if self.save_data:
            self.save_data.elo += self.elo_earned
            self.save_data.stats["tournaments_completed"] = self.save_data.stats.get("tournaments_completed", 0) + 1
            self.save_data.stats["total_elo_earned"] = self.save_data.stats.get("total_elo_earned", 0) + self.elo_earned
            self.save_data.stats["bosses_beaten"] = self.save_data.stats.get("bosses_beaten", 0) + int(self.tournament_stats["bosses_beaten"])

            # Track boss types beaten
            boss_types = self.save_data.stats.get("boss_types_beaten", [])
            for i in range(int(self.tournament_stats["bosses_beaten"])):
                if i < len(self.boss_sequence):
                    bt = self.boss_sequence[i].value
                    if bt not in boss_types:
                        boss_types.append(bt)
            self.save_data.stats["boss_types_beaten"] = boss_types

            if won:
                self.save_data.stats["tournaments_won"] = self.save_data.stats.get("tournaments_won", 0) + 1
                # Beating Extreme unlocks Grandmaster
                if self.difficulty == "extreme":
                    self.save_data.grandmaster_unlocked = True

            # Run-end achievement checks
            self._check_run_achievements(won)

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

        pool = [PieceType.PAWN, PieceType.KNIGHT, PieceType.BISHOP,
                PieceType.DUELIST, PieceType.DECOY, PieceType.LANCER]
        if self.wave >= 3:
            pool.extend([PieceType.ROOK, PieceType.BOMB, PieceType.LEECH, PieceType.KING_RAT,
                         PieceType.CHARGER, PieceType.BARD, PieceType.WALL, PieceType.CANNON,
                         PieceType.BERSERKER_PIECE, PieceType.TRICKSTER, PieceType.IMP])
        if self.wave >= 4:
            pool.extend([PieceType.MIMIC, PieceType.PARASITE, PieceType.SUMMONER,
                         PieceType.ASSASSIN, PieceType.SENTINEL, PieceType.HEALER,
                         PieceType.TOTEM, PieceType.ALCHEMIST_PIECE])
        if self.wave >= 5:
            pool.extend([PieceType.QUEEN, PieceType.GHOST, PieceType.PHOENIX, PieceType.GAMBLER,
                         PieceType.REAPER, PieceType.WYVERN, PieceType.GOLEM, PieceType.WITCH,
                         PieceType.SHAPESHIFTER, PieceType.TIME_MAGE, PieceType.POLTERGEIST])
        if self.wave >= 6:
            pool.extend([PieceType.ANCHOR_PIECE, PieceType.MIRROR_PIECE, PieceType.VOID])

        pool_keys = [pt.value for pt in pool]
        wave_bonus = self.wave * 0.1
        for _ in range(3):
            key = rarity_weighted_choice(pool_keys, "piece", self.rng, wave_bonus)
            pt = PieceType(key)
            rarity = PIECE_RARITY.get(key, Rarity.COMMON)
            self.draft_options.append({
                "type": "add", "piece_type": pt,
                "rarity": rarity.value,
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

        leech_count = sum(1 for p in self.roster if p.piece_type == PieceType.LEECH)
        if leech_count >= 2:
            self.draft_options.append({
                "type": "combine", "from": PieceType.LEECH,
                "to": PieceType.GAMBLER, "count": 2,
                "desc": "Combine 2 Leeches -> 1 Gambler",
            })

        king_rat_count = sum(1 for p in self.roster if p.piece_type == PieceType.KING_RAT)
        if king_rat_count >= 2:
            self.draft_options.append({
                "type": "combine", "from": PieceType.KING_RAT,
                "to": PieceType.VOID, "count": 2,
                "desc": "Combine 2 King Rats -> 1 Void",
            })

        self.draft_options.append({"type": "skip", "desc": "Skip -> Next wave"})

    # --- Tarot / Artifact helpers ---

    def _has_tarot(self, effect: str) -> bool:
        """Check if player holds a tarot with the given effect."""
        return any(t["effect"] == effect for t in self.tarot_cards)

    def _has_artifact(self, effect: str) -> bool:
        """Check if player holds an artifact with the given effect."""
        return any(a["effect"] == effect for a in self.artifacts)

    def _artifact_count(self, effect: str) -> int:
        """Count how many copies of an artifact the player holds."""
        return sum(1 for a in self.artifacts if a["effect"] == effect)

    def _has_synergy(self, effect: str) -> bool:
        """Check if a synergy is currently active."""
        return effect in self.active_synergies

    def _apply_wave_start_effects(self) -> None:
        """Apply tarot and artifact passive effects at wave start."""
        # Reset per-wave tracking
        self.anchor_chain_used = False
        self.first_capture_this_turn = True

        # --- Tarot effects ---

        # The Flame: all roster pieces gain flaming
        if self._has_tarot("the_flame"):
            for p in self.roster:
                if not any(m.effect == "flaming" for m in p.modifiers):
                    p.modifiers.append(MODIFIERS["flaming"])

        # The Fortress: all roster pieces gain armored
        if self._has_tarot("the_fortress"):
            for p in self.roster:
                if not any(m.effect == "armored" for m in p.modifiers):
                    p.modifiers.append(MODIFIERS["armored"])

        # The Pawn: remove old temp pawns, add 3 fresh ones
        if self._has_tarot("the_pawn"):
            self.roster = [p for p in self.roster if not getattr(p, '_temp_pawn', False)]
            for _ in range(3):
                pawn = Piece(PieceType.PAWN, Team.PLAYER)
                pawn._temp_pawn = True  # type: ignore[attr-defined]
                self.roster.append(pawn)

        # The Titan: all pieces +5 HP, can't be one-shot
        if self._has_tarot("the_titan"):
            for p in self.roster:
                p.max_hp += 5
                p.hp += 5

        # The Swarm: 2 extra Pawns, Pawn ATK scales
        if self._has_tarot("the_swarm"):
            for _ in range(2):
                pawn = Piece(PieceType.PAWN, Team.PLAYER)
                pawn._temp_pawn = True  # type: ignore[attr-defined]
                self.roster.append(pawn)

        # The Crown: strongest piece gets +3 ATK and Armored
        if self._has_tarot("the_crown"):
            strongest = max(self.roster, key=lambda p: p.attack, default=None)
            if strongest:
                strongest.attack += 3
                if not any(m.effect == "armored" for m in strongest.modifiers):
                    strongest.modifiers.append(MODIFIERS["armored"])

        # The Gambit: sacrifice random piece, distribute ATK
        if self._has_tarot("the_gambit") and len(self.roster) > 1:
            victim = self.rng.choice(self.roster)
            distributed_atk = victim.attack
            self.roster.remove(victim)
            if self.roster and distributed_atk > 0:
                per_piece = max(1, distributed_atk // len(self.roster))
                for p in self.roster:
                    p.attack += per_piece

        # The Architect: 2 random cell mods on player half
        if self._has_tarot("the_architect"):
            cell_keys = list(CELL_MODIFIERS.keys())
            for _ in range(2):
                key = self.rng.choice(cell_keys)
                empty_cells = [
                    (x, y) for x in range(self.board.width) for y in range(4, self.board.height)
                    if (x, y) not in self.board.cell_modifiers
                ]
                if empty_cells:
                    cx, cy = self.rng.choice(empty_cells)
                    cm = make_cell_modifier(key, cx, cy)
                    self.board.cell_modifiers[(cx, cy)] = cm

        # --- Artifact effects ---

        # Chaos Orb: switch a random enemy to player side
        if self._has_artifact("chaos_orb"):
            enemies = self.board.get_team_pieces(Team.ENEMY)
            if enemies:
                switched = self.rng.choice(enemies)
                switched.team = Team.PLAYER
                self.roster.append(switched)
                self.placed.append(switched)

        # Pandemonium: spawn a random cell modifier on an empty cell
        if self._has_artifact("pandemonium"):
            cell_keys = list(CELL_MODIFIERS.keys())
            key = self.rng.choice(cell_keys)
            empty_cells = [
                (x, y) for x in range(self.board.width) for y in range(self.board.height)
                if self.board.is_empty(x, y)
                and (x, y) not in self.board.cell_modifiers
                and (x, y) not in self.board.border_modifiers
            ]
            if empty_cells:
                cx, cy = self.rng.choice(empty_cells)
                cm = make_cell_modifier(key, cx, cy)
                self.board.cell_modifiers[(cx, cy)] = cm
                self.cell_modifiers.append(cm)

        # Pandora's Box: 3 random mods on random pieces at wave start
        if self._has_artifact("pandoras_box"):
            mod_keys = list(PIECE_MODIFIER_VISUALS.keys())
            for _ in range(3):
                if self.roster:
                    target = self.rng.choice(self.roster)
                    mod_key = self.rng.choice(mod_keys)
                    if mod_key in MODIFIERS:
                        target.modifiers.append(MODIFIERS[mod_key])

        # Blood Altar: sacrifice piece, all others +2 ATK
        if self._has_artifact("blood_altar") and len(self.roster) > 1:
            victim = self.rng.choice(self.roster)
            self.roster.remove(victim)
            for p in self.roster:
                p.attack += 2

        # Soul Jar: revive stored dead pieces at 50% HP
        if self._has_artifact("soul_jar"):
            stored = [p for p in self.roster if not p.alive][:3]
            for p in stored:
                p.alive = True
                p.hp = max(1, p.max_hp // 2)

        # Training Dummy: surviving pieces gain +1 HP
        if self._has_artifact("training_dummy"):
            for p in self.roster:
                if p.alive:
                    p.max_hp += 1
                    p.hp += 1

        # Dragon's Hoard: +3 gold per wave
        if self._has_artifact("dragons_hoard"):
            self.gold += 3

        # Grimoire: +2 tarot slots (applied once via ability_flags)
        if self._has_artifact("grimoire") and not hasattr(self, '_grimoire_applied'):
            self.tarot_slots += 2
            self._grimoire_applied = True

        # Arsenal: +2 artifact slots (applied once)
        if self._has_artifact("arsenal") and not hasattr(self, '_arsenal_applied'):
            self.artifact_slots += 2
            self._arsenal_applied = True

        # Battle Standard: pieces within 2 cells of King gain +1 ATK (set flag)
        if self._has_artifact("battle_standard"):
            for p in self.roster:
                p.ability_flags["battle_standard"] = True

        # Chain Mail: set flag on armored pieces
        if self._has_artifact("chain_mail"):
            for p in self.roster:
                p.ability_flags["chain_mail"] = True

        # Ember Stone: set flag for fire damage bonus
        if self._has_artifact("ember_stone"):
            for p in self.roster:
                p.ability_flags["ember_stone"] = True

        # Frost Shard: set flag for extended chill
        if self._has_artifact("frost_shard"):
            for p in self.roster:
                p.ability_flags["frost_shard"] = True

        # Venom Gland: set flag for double poison ticks
        if self._has_artifact("venom_gland"):
            for p in self.roster:
                p.ability_flags["venom_gland"] = True

        # Berserker's Torc: below 50% HP → +3 ATK (applied in combat, set flag)
        if self._has_artifact("berserkers_torc"):
            for p in self.roster:
                p.ability_flags["berserkers_torc"] = True

        # --- Master passives at wave start ---
        mk = self.master_key

        # Strategist: +1 HP per wave survived
        if mk == "the_strategist" and self.wave > 0:
            for p in self.roster:
                if p.alive:
                    p.max_hp += 1
                    p.hp += 1

        # Berserker: pieces lose 1 HP at turn start (handled in board abilities)
        # This is per-turn, not wave start — handled via ability_flags
        if mk == "the_berserker":
            for p in self.roster:
                p.ability_flags["berserker_master_drain"] = True

    # --- Shop ---

    def _generate_shop(self) -> None:
        """Generate random shop offerings: piece mods, cell mods, border mods."""
        self.shop_items = []
        self.shop_row = 0
        self.shop_col = 0

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

        wave_bonus = self.wave * 0.1

        # Offer 1-2 piece modifiers (rarity-weighted)
        for _ in range(self.rng.randint(1, 2)):
            key = rarity_weighted_choice(available_mod_keys, "piece_mod", self.rng, wave_bonus)
            mod = MODIFIERS[key]
            rarity = PIECE_MOD_RARITY.get(key, Rarity.COMMON)
            base_cost = 5
            self.shop_items.append({
                "type": "piece_mod", "key": key, "mod": mod,
                "cost": get_shop_cost(base_cost, rarity),
                "rarity": rarity.value,
                "icon": "*",
                "category": "Piece Mod",
                "color": PIECE_MODIFIER_VISUALS[key]["color"],
                "name": mod.name,
                "description": mod.description,
            })

        # Offer 1-2 cell modifiers (rarity-weighted)
        cell_mod_keys = list(CELL_MODIFIERS.keys())
        for _ in range(self.rng.randint(1, 2)):
            key = rarity_weighted_choice(cell_mod_keys, "cell_mod", self.rng, wave_bonus)
            tmpl = CELL_MODIFIERS[key]
            rarity = CELL_MOD_RARITY.get(key, Rarity.COMMON)
            base_cost = 3
            self.shop_items.append({
                "type": "cell_mod", "key": key,
                "cost": get_shop_cost(base_cost, rarity),
                "rarity": rarity.value,
                "icon": tmpl["icon"],
                "category": "Cell Mod",
                "color": tmpl["color"],
                "name": tmpl["name"],
                "description": tmpl["description"],
            })

        # Offer 1 border modifier (rarity-weighted)
        border_mod_keys = list(BORDER_MODIFIERS.keys())
        key = rarity_weighted_choice(border_mod_keys, "border_mod", self.rng, wave_bonus)
        tmpl = BORDER_MODIFIERS[key]
        rarity = BORDER_MOD_RARITY.get(key, Rarity.COMMON)
        base_cost = 4
        self.shop_items.append({
            "type": "border_mod", "key": key,
            "cost": get_shop_cost(base_cost, rarity),
            "rarity": rarity.value,
            "icon": "#",
            "category": "Border Mod",
            "color": tmpl["border_color"],
            "name": tmpl["name"],
            "description": tmpl["description"],
        })

        # Offer a tarot card (wave 2+, ~50% chance, rarity-weighted)
        if self.wave >= 2 and self.rng.random() < 0.5:
            held_keys = {t["effect"] for t in self.tarot_cards}
            available_tarots = [k for k in TAROT_CARDS if k not in held_keys]
            if available_tarots:
                key = rarity_weighted_choice(available_tarots, "tarot", self.rng, wave_bonus)
                t = TAROT_CARDS[key]
                rarity = TAROT_RARITY.get(key, Rarity.COMMON)
                cost = get_shop_cost(t["cost"], rarity)
                # Merchant discount
                if self._has_tarot("the_merchant"):
                    cost = max(1, cost - 2)
                self.shop_items.append({
                    "type": "tarot", "key": key,
                    "cost": cost,
                    "rarity": rarity.value,
                    "icon": t["icon"],
                    "category": "Tarot",
                    "color": t["color"],
                    "name": t["name"],
                    "description": t["description"],
                })

        # Offer an artifact (wave 1+, ~40% chance, guaranteed wave 3+, rarity-weighted)
        offer_artifact = self.wave >= 3 or (self.wave >= 1 and self.rng.random() < 0.4)
        if offer_artifact:
            held_keys = {a["effect"] for a in self.artifacts}
            available_arts = [k for k in ARTIFACTS if k not in held_keys]
            if available_arts:
                key = rarity_weighted_choice(available_arts, "artifact", self.rng, wave_bonus)
                a = ARTIFACTS[key]
                rarity = ARTIFACT_RARITY.get(key, Rarity.COMMON)
                cost = get_shop_cost(a["cost"], rarity)
                if self._has_tarot("the_merchant"):
                    cost = max(1, cost - 2)
                self.shop_items.append({
                    "type": "artifact", "key": key,
                    "cost": cost,
                    "rarity": rarity.value,
                    "icon": a["icon"],
                    "category": "Artifact",
                    "color": a["color"],
                    "name": a["name"],
                    "description": a["description"],
                })

        # Extra items from Lucky Coin artifact
        extra_items = sum(1 for a in self.artifacts if a["effect"] == "lucky_coin")
        for _ in range(extra_items):
            key = self.rng.choice(available_mod_keys)
            mod = MODIFIERS[key]
            rarity = get_rarity("piece_mod", key)
            self.shop_items.append({
                "type": "piece_mod", "key": key, "mod": mod,
                "cost": get_shop_cost(5, rarity),
                "rarity": rarity.value,
                "icon": "*",
                "category": "Piece Mod",
                "color": PIECE_MODIFIER_VISUALS[key]["color"],
                "name": mod.name,
                "description": mod.description,
            })

        # Extra items from Merchant tarot
        if self._has_tarot("the_merchant"):
            for _ in range(2):
                if self.rng.random() < 0.5:
                    key = self.rng.choice(available_mod_keys)
                    mod = MODIFIERS[key]
                    rarity = get_rarity("piece_mod", key)
                    cost = max(1, get_shop_cost(5, rarity) - 2)
                    self.shop_items.append({
                        "type": "piece_mod", "key": key, "mod": mod,
                        "cost": cost,
                        "rarity": rarity.value,
                        "icon": "*",
                        "category": "Piece Mod",
                        "color": PIECE_MODIFIER_VISUALS[key]["color"],
                        "name": mod.name,
                        "description": mod.description,
                    })
                else:
                    key = self.rng.choice(cell_mod_keys)
                    tmpl = CELL_MODIFIERS[key]
                    rarity = get_rarity("cell_mod", key)
                    cost = max(1, get_shop_cost(3, rarity) - 2)
                    self.shop_items.append({
                        "type": "cell_mod", "key": key,
                        "cost": cost,
                        "rarity": rarity.value,
                        "icon": tmpl["icon"],
                        "category": "Cell Mod",
                        "color": tmpl["color"],
                        "name": tmpl["name"],
                        "description": tmpl["description"],
                    })

        # --- Master passives for shop ---

        # Gambler: 2 extra random items
        if self.master.passive == "gambler_passive":
            for _ in range(2):
                roll = self.rng.random()
                if roll < 0.4:
                    key = self.rng.choice(available_mod_keys)
                    mod = MODIFIERS[key]
                    rarity = get_rarity("piece_mod", key)
                    self.shop_items.append({
                        "type": "piece_mod", "key": key, "mod": mod,
                        "cost": get_shop_cost(5, rarity), "rarity": rarity.value,
                        "icon": "*", "category": "Piece Mod",
                        "color": PIECE_MODIFIER_VISUALS[key]["color"],
                        "name": mod.name, "description": mod.description,
                    })
                elif roll < 0.7:
                    key = self.rng.choice(cell_mod_keys)
                    tmpl = CELL_MODIFIERS[key]
                    rarity = get_rarity("cell_mod", key)
                    self.shop_items.append({
                        "type": "cell_mod", "key": key,
                        "cost": get_shop_cost(3, rarity), "rarity": rarity.value,
                        "icon": tmpl["icon"], "category": "Cell Mod",
                        "color": tmpl["color"],
                        "name": tmpl["name"], "description": tmpl["description"],
                    })
                else:
                    key = self.rng.choice(border_mod_keys)
                    tmpl = BORDER_MODIFIERS[key]
                    rarity = get_rarity("border_mod", key)
                    self.shop_items.append({
                        "type": "border_mod", "key": key,
                        "cost": get_shop_cost(4, rarity), "rarity": rarity.value,
                        "icon": "#", "category": "Border Mod",
                        "color": tmpl["border_color"],
                        "name": tmpl["name"], "description": tmpl["description"],
                    })

        # Gambler drawback: randomize all prices (0.5x to 2x)
        if self.master.drawback == "gambler_drawback":
            for item in self.shop_items:
                mult = 0.5 + self.rng.random() * 1.5
                item["cost"] = max(1, int(item["cost"] * mult))

        # Blacksmith passive: piece modifiers cost 2 less
        if self.master.passive == "blacksmith_passive":
            for item in self.shop_items:
                if item["type"] == "piece_mod":
                    item["cost"] = max(1, item["cost"] - 2)

        # Pauper drawback: non-Pawn pieces cost double
        if self.master.drawback == "pauper_drawback":
            for item in self.shop_items:
                if item["type"] == "piece" and item.get("key") != "pawn":
                    item["cost"] *= 2

        # Anarchist drawback: cannot buy tarots — remove them
        if self.master.drawback == "anarchist_drawback":
            self.shop_items = [it for it in self.shop_items if it["type"] != "tarot"]

    def _get_shop_rows(self) -> list[dict]:
        """Build categorized rows from shop_items for multi-row display."""
        rows = []
        piece_mods = [(i, it) for i, it in enumerate(self.shop_items) if it["type"] == "piece_mod"]
        board_mods = [(i, it) for i, it in enumerate(self.shop_items) if it["type"] in ("cell_mod", "border_mod")]
        specials = [(i, it) for i, it in enumerate(self.shop_items) if it["type"] in ("tarot", "artifact")]

        if piece_mods:
            rows.append({"label": "Piece Modifiers", "items": piece_mods, "color": (200, 160, 255)})
        if board_mods:
            rows.append({"label": "Board Modifiers", "items": board_mods, "color": (100, 200, 100)})
        if specials:
            rows.append({"label": "Specials", "items": specials, "color": (255, 200, 80)})

        # Sell row: roster pieces that can be sold
        sell_items = []
        for i, p in enumerate(self.roster):
            if p.alive and len(self.roster) > 1:  # can't sell last piece
                rarity = PIECE_RARITY.get(p.piece_type.value, Rarity.COMMON)
                sell_val = PIECE_SELL_VALUES.get(rarity, 1)
                sell_items.append((1000 + i, {
                    "type": "sell_piece",
                    "key": p.piece_type.value,
                    "roster_idx": i,
                    "cost": -sell_val,  # negative = gain gold
                    "rarity": rarity.value,
                    "icon": "\u2716",
                    "category": "Sell",
                    "color": (200, 80, 80),
                    "name": f"Sell {p.piece_type.value}",
                    "description": f"Sell for {sell_val}g",
                }))
        if sell_items:
            rows.append({"label": "Sell Pieces", "items": sell_items, "color": (200, 80, 80)})

        return rows

    def _clamp_shop_cursor(self) -> None:
        """Clamp shop_row/shop_col after an item is removed."""
        rows = self._get_shop_rows()
        num_rows = len(rows)
        if self.shop_row > num_rows:
            self.shop_row = num_rows  # done row
        if self.shop_row < num_rows:
            row_len = len(rows[self.shop_row]["items"])
            self.shop_col = min(self.shop_col, max(0, row_len - 1))
        else:
            self.shop_col = 0

    def _handle_shop(self, action: Action) -> GameState | None:
        rows = self._get_shop_rows()
        num_rows = len(rows)
        total_nav_rows = num_rows + 1  # +1 for done button

        if action == Action.MOUSE_CLICK:
            hit = self._hit_test(self.mouse_tile[0], self.mouse_tile[1])
            if hit:
                if hit["action"] == "button":
                    if self.shop_row >= num_rows:
                        action = Action.CONFIRM  # already on done, confirm
                    else:
                        self.shop_row = num_rows
                        self.shop_col = 0
                        return None
                elif hit["action"] == "card":
                    row_idx = hit["row"]
                    col_idx = hit["col"]
                    if self.shop_row == row_idx and self.shop_col == col_idx:
                        action = Action.CONFIRM  # re-click = buy
                    else:
                        self.shop_row = row_idx
                        self.shop_col = col_idx
                        return None
            else:
                return None

        if action == Action.UP:
            self.shop_row = (self.shop_row - 1) % total_nav_rows
            if self.shop_row < num_rows:
                self.shop_col = min(self.shop_col, len(rows[self.shop_row]["items"]) - 1)
            else:
                self.shop_col = 0
            return None
        if action == Action.DOWN:
            self.shop_row = (self.shop_row + 1) % total_nav_rows
            if self.shop_row < num_rows:
                self.shop_col = min(self.shop_col, len(rows[self.shop_row]["items"]) - 1)
            else:
                self.shop_col = 0
            return None
        if action == Action.LEFT:
            if self.shop_row < num_rows:
                row_len = len(rows[self.shop_row]["items"])
                self.shop_col = (self.shop_col - 1) % row_len
            return None
        if action == Action.RIGHT:
            if self.shop_row < num_rows:
                row_len = len(rows[self.shop_row]["items"])
                self.shop_col = (self.shop_col + 1) % row_len
            return None

        if action == Action.CONFIRM:
            if self.shop_row >= num_rows:
                # Done button
                self._generate_draft()
                self.phase = "draft"
                self._auto_save()
                return None

            if self.shop_row >= len(rows) or self.shop_col >= len(rows[self.shop_row]["items"]):
                return None
            flat_idx, item = rows[self.shop_row]["items"][self.shop_col]

            if item["type"] != "sell_piece" and self.gold < item["cost"]:
                self.message = "Not enough gold!"
                return None

            if item["type"] == "piece_mod":
                max_mods = 2 if self._has_artifact("forge_hammer") else 1
                eligible = [p for p in self.roster if len(p.modifiers) < max_mods]
                if not eligible:
                    self.message = "All pieces already have modifiers!"
                    return None
                self.gold -= item["cost"]
                self.run_stats["shop_purchases_run"] += 1
                self.run_stats["total_gold_spent_run"] += item["cost"]
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

            elif item["type"] == "tarot":
                tarot_data = TAROT_CARDS[item["key"]]
                effective_slots = self.tarot_slots + self._artifact_count("heretics_tome")
                if len(self.tarot_cards) < effective_slots:
                    self.gold -= item["cost"]
                    self.tarot_cards.append(dict(tarot_data))
                    self.run_stats["tarots_used_this_run"].add(item["key"])
                    self.run_stats["shop_purchases_run"] += 1
                    self.run_stats["total_gold_spent_run"] += item["cost"]
                    self.message = f"Acquired {tarot_data['name']}!"
                    self.shop_items.pop(flat_idx)
                    self._clamp_shop_cursor()
                else:
                    self.gold -= item["cost"]
                    self.run_stats["tarots_used_this_run"].add(item["key"])
                    self.run_stats["shop_purchases_run"] += 1
                    self.run_stats["total_gold_spent_run"] += item["cost"]
                    self.placing_item = item
                    self.roster_selection = 0
                    self.phase = "swap_tarot"
                    self.message = "Slots full! Pick a tarot to replace (1-9, ENTER) or ESC to cancel."

            elif item["type"] == "artifact":
                artifact_data = ARTIFACTS[item["key"]]
                if len(self.artifacts) < self.artifact_slots:
                    self.gold -= item["cost"]
                    self.artifacts.append(dict(artifact_data))
                    self.run_stats["artifacts_used_this_run"].add(item["key"])
                    self.run_stats["shop_purchases_run"] += 1
                    self.run_stats["total_gold_spent_run"] += item["cost"]
                    self.message = f"Acquired {artifact_data['name']}!"
                    self.shop_items.pop(flat_idx)
                    self._clamp_shop_cursor()
                else:
                    self.message = f"Artifact slots full! ({len(self.artifacts)}/{self.artifact_slots})"

            elif item["type"] == "sell_piece":
                # Sell a roster piece for gold
                roster_idx = item["roster_idx"]
                if roster_idx < len(self.roster) and len(self.roster) > 1:
                    sold_piece = self.roster.pop(roster_idx)
                    sell_val = abs(item["cost"])
                    self.gold += sell_val
                    self.run_stats["items_sold_run"] += 1
                    self.message = f"Sold {sold_piece.piece_type.value} for {sell_val}g!"
                    self._clamp_shop_cursor()

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
        max_mods = 2 if self._has_artifact("forge_hammer") else 1
        eligible = [p for p in self.roster if len(p.modifiers) < max_mods]
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
                # Track max mods on a single piece for achievements
                mod_count = len(piece.modifiers)
                if mod_count > self.run_stats.get("max_mods_on_piece", 0):
                    self.run_stats["max_mods_on_piece"] = mod_count
                self.message = f"Applied {mod.name} to {piece.piece_type.value}!"
                self.placing_item = None
                self.phase = "shop"
        elif action == Action.CANCEL:
            self.gold += self.placing_item["cost"]
            self.placing_item = None
            self.phase = "shop"
            self.message = "Cancelled — gold refunded."
        return None

    def _handle_swap_tarot(self, action: Action) -> GameState | None:
        """Pick which held tarot to replace with the newly purchased one."""
        if action == Action.MOUSE_CLICK:
            action = Action.CONFIRM
        num_actions = {
            Action.NUM_1: 0, Action.NUM_2: 1, Action.NUM_3: 2,
            Action.NUM_4: 3, Action.NUM_5: 4,
        }
        if action in num_actions:
            idx = num_actions[action]
            if idx < len(self.tarot_cards):
                self.roster_selection = idx
                self.message = f"Replace {self.tarot_cards[idx]['name']}? ENTER to confirm."
        elif action in (Action.LEFT, Action.UP):
            self.roster_selection = (self.roster_selection - 1) % len(self.tarot_cards)
        elif action in (Action.RIGHT, Action.DOWN):
            self.roster_selection = (self.roster_selection + 1) % len(self.tarot_cards)
        elif action == Action.CONFIRM:
            if self.roster_selection < len(self.tarot_cards):
                old_name = self.tarot_cards[self.roster_selection]["name"]
                new_tarot = TAROT_CARDS[self.placing_item["key"]]
                self.tarot_cards[self.roster_selection] = dict(new_tarot)
                self.message = f"Replaced {old_name} with {new_tarot['name']}!"
                # Remove the tarot from shop items
                try:
                    shop_idx = next(i for i, it in enumerate(self.shop_items)
                                    if it.get("key") == self.placing_item["key"] and it["type"] == "tarot")
                    self.shop_items.pop(shop_idx)
                except StopIteration:
                    pass
                self.placing_item = None
                self.phase = "shop"
                self._clamp_shop_cursor()
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
                self.run_stats["unique_piece_types_used"].add(opt["piece_type"].value)
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
                self.run_stats["unique_piece_types_used"].add(opt["to"].value)
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
        elif self.phase == "swap_tarot":
            self._render_swap_tarot(console)
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
        # Tarot / Artifact summary
        if self.tarot_cards:
            info_lines.append("")
            for t in self.tarot_cards:
                info_lines.append(f"T: {t['name']}")
        if self.artifacts:
            info_lines.append("")
            for a in self.artifacts:
                info_lines.append(f"A: {a['name']}")

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
        # Compact tarot/artifact list
        if self.tarot_cards or self.artifacts:
            status_lines.append("")
            for t in self.tarot_cards:
                status_lines.append(f"T:{t['name']}")
            for a in self.artifacts:
                status_lines.append(f"A:{a['name']}")

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
            renderer.draw_message(console, "Click/Enter: move | Esc: skip | Tab: auto")
        else:
            renderer.draw_message(console, "Enter: step | Esc: skip | Tab: manual")

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

        rows = self._get_shop_rows()
        num_sections = len(rows)

        # Compute layout width
        total_w = min(cw - 4, 80)
        start_x = max(1, (cw - total_w) // 2)

        # --- Held items bar at top ---
        held_bar_y = 1
        effective_slots = self.tarot_slots + self._artifact_count("heretics_tome")
        held_bar_h = renderer.draw_held_items_bar(
            console, start_x, held_bar_y, total_w,
            self.tarot_cards, self.artifacts,
            effective_slots, self.artifact_slots,
        )

        # --- Header bar ---
        header_y = held_bar_y + held_bar_h + 1
        renderer.draw_shop_header(
            console, y=header_y, width=total_w, start_x=start_x,
            gold=self.gold, wave=self.wave,
            wins=self.wins, losses=self.losses,
        )

        # --- Vertical budget for card sections ---
        content_top = header_y + 2
        button_h = 3
        controls_h = 2
        avail_h = ch - content_top - button_h - controls_h - 1

        if num_sections > 0:
            section_h = avail_h // num_sections
        else:
            section_h = avail_h
        card_h = max(7, min(10, section_h - 2))  # 2 = label + price row

        # --- Draw each section ---
        cur_y = content_top
        for row_idx, row in enumerate(rows):
            # Section label
            renderer.draw_shop_section_label(
                console, cur_y, total_w, start_x,
                row["label"], row["color"],
            )
            cur_y += 1

            # Cards in this row
            items = row["items"]
            num_cards = len(items)
            gap = 2
            card_w = min(18, max(12, (total_w - gap * max(0, num_cards - 1)) // max(1, num_cards)))
            cards_total_w = card_w * num_cards + gap * max(0, num_cards - 1)
            cards_x = start_x + (total_w - cards_total_w) // 2

            for col_idx, (flat_idx, item) in enumerate(items):
                cx = cards_x + col_idx * (card_w + gap)
                sel = (row_idx == self.shop_row and col_idx == self.shop_col)
                affordable = (self.gold >= item["cost"])

                renderer.draw_shop_card(
                    console, cx, cur_y, card_w, card_h,
                    icon=item["icon"],
                    name=item["name"],
                    description=item["description"],
                    category=item["category"],
                    color=item["color"],
                    selected=sel,
                    affordable=affordable,
                )

                renderer.draw_shop_price_tag(
                    console, cx, cur_y + card_h, card_w,
                    cost=item["cost"], affordable=affordable,
                )

                self._click_regions.append({
                    "x": cx, "y": cur_y, "w": card_w, "h": card_h,
                    "row": row_idx, "col": col_idx,
                    "index": flat_idx, "action": "card",
                })

            cur_y += card_h + 2  # card + price row + gap

        # --- Roster summary ---
        counts: dict[str, int] = {}
        for p in self.roster:
            name = p.piece_type.value
            counts[name] = counts.get(name, 0) + 1
        roster_str = "Roster: " + ", ".join(f"{v}x {k}" for k, v in counts.items())
        if len(roster_str) > total_w:
            roster_str = roster_str[:total_w]
        rx = start_x + (total_w - len(roster_str)) // 2
        console.print(max(0, rx), cur_y, roster_str, fg=renderer.FG_DIM, bg=renderer.BG_FELT)
        cur_y += 1

        # --- "Next Round" done button ---
        done_y = max(cur_y, ch - button_h - controls_h - 1)
        done_selected = (self.shop_row >= num_sections)
        renderer.draw_shop_done_button(
            console, done_y, width=total_w, start_x=start_x,
            selected=done_selected,
        )
        self._click_regions.append({
            "x": start_x, "y": done_y, "w": total_w, "h": 3,
            "action": "button",
        })

        # --- Controls hint (bottom) ---
        controls = "L/R: browse | U/D: section | Enter: buy | Esc: skip"
        if len(controls) > cw - 2:
            controls = controls[:cw - 2]
        cx = (cw - len(controls)) // 2
        console.print(max(0, cx), ch - 2, controls, fg=renderer.FG_DIM, bg=renderer.BG_FELT)

        # Message bar
        if self.message:
            msg = self.message
            if len(msg) > cw - 2:
                msg = msg[:cw - 2]
            mx = (cw - len(msg)) // 2
            console.print(max(0, mx), ch - 1, msg, fg=renderer.FG_TEXT, bg=renderer.BG_FELT)

    def _render_swap_tarot(self, console: tcod.console.Console) -> None:
        """Render tarot swap screen when slots are full."""
        cw, ch = console.width, console.height
        pw = min(55, cw - 4)
        px = (cw - pw) // 2
        py = max(2, ch // 2 - 8)

        if self.placing_item:
            new_name = TAROT_CARDS[self.placing_item["key"]]["name"]
        else:
            new_name = "?"

        lines = [
            f"New: {new_name}",
            "",
            "Pick a tarot to replace (1-9, arrows + ENTER):",
            "ESC to cancel (refund)",
            "",
        ]
        for i, t in enumerate(self.tarot_cards):
            marker = ">" if i == self.roster_selection else " "
            lines.append(f" {marker} [{i+1}] {t['name']}: {t['description']}")

        renderer.draw_panel(console, px, py, pw, len(lines) + 2, "Swap Tarot", lines)

        if self.message:
            renderer.draw_message(console, self.message)

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

        max_mods = 2 if self._has_artifact("forge_hammer") else 1
        eligible = [p for p in self.roster if len(p.modifiers) < max_mods]
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
        if len(roster_str) > total_w:
            roster_str = roster_str[:total_w]
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
        controls = "L/R: browse | Enter: pick | Esc: skip"
        if len(controls) > cw - 2:
            controls = controls[:cw - 2]
        cx = (cw - len(controls)) // 2
        console.print(max(0, cx), ch - 2, controls, fg=renderer.FG_DIM, bg=renderer.BG_FELT)

        # Message bar
        if self.message:
            msg = self.message
            if len(msg) > cw - 2:
                msg = msg[:cw - 2]
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
