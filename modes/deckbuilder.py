"""Mode 2: Piece Deckbuilder — place pieces to create tactical patterns for points."""

from __future__ import annotations

import random
from dataclasses import dataclass

import tcod.console

from board import Board
from pieces import Piece, PieceType, Team, PIECE_VALUES, MODIFIERS
from engine import Action, GameState
import renderer


@dataclass
class PatternResult:
    name: str
    description: str
    base_score: int
    pieces_involved: list[Piece]


def detect_patterns(board: Board) -> list[PatternResult]:
    """Detect chess tactical patterns on the board for scoring."""
    patterns = []
    player_pieces = board.get_team_pieces(Team.PLAYER)
    enemy_pieces = board.get_team_pieces(Team.ENEMY)

    if not player_pieces or not enemy_pieces:
        return patterns

    # Fork: one piece attacks two or more enemies
    for pp in player_pieces:
        attacks = pp.get_capture_moves(board)
        attacked_enemies = []
        for ax, ay in attacks:
            target = board.get_piece_at(ax, ay)
            if target and target.team == Team.ENEMY:
                attacked_enemies.append(target)
        if len(attacked_enemies) >= 2:
            val = sum(e.value for e in attacked_enemies) * 15
            patterns.append(PatternResult(
                "Fork",
                f"{pp.piece_type.value} forks {len(attacked_enemies)} pieces",
                val,
                [pp] + attacked_enemies,
            ))

    # Pin/Skewer: piece attacks through a line with two enemies
    for pp in player_pieces:
        if pp.piece_type in (PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN):
            dirs = []
            if pp.piece_type in (PieceType.BISHOP, PieceType.QUEEN):
                dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
            if pp.piece_type in (PieceType.ROOK, PieceType.QUEEN):
                dirs += [(-1,0),(1,0),(0,-1),(0,1)]
            for dx, dy in dirs:
                line_pieces = []
                for dist in range(1, max(board.width, board.height)):
                    nx, ny = pp.x + dx * dist, pp.y + dy * dist
                    if not board.in_bounds(nx, ny) or board.is_blocked(nx, ny):
                        break
                    target = board.get_piece_at(nx, ny)
                    if target:
                        if target.team == Team.ENEMY:
                            line_pieces.append(target)
                        else:
                            break
                        if len(line_pieces) >= 2:
                            break
                if len(line_pieces) >= 2:
                    if line_pieces[0].value > line_pieces[1].value:
                        name = "Pin"
                        desc = f"{pp.piece_type.value} pins {line_pieces[0].piece_type.value}"
                    else:
                        name = "Skewer"
                        desc = f"{pp.piece_type.value} skewers through {line_pieces[0].piece_type.value}"
                    val = (line_pieces[0].value + line_pieces[1].value) * 20
                    patterns.append(PatternResult(name, desc, val, [pp] + line_pieces))

    # Discovered attack: moving one piece reveals an attack from another
    # Simplified: if two player pieces attack the same enemy from different directions
    for ep in enemy_pieces:
        attackers = []
        for pp in player_pieces:
            if (ep.x, ep.y) in pp.get_capture_moves(board):
                attackers.append(pp)
        if len(attackers) >= 2:
            val = ep.value * 25
            patterns.append(PatternResult(
                "Double Attack",
                f"{len(attackers)} pieces target {ep.piece_type.value}",
                val,
                attackers + [ep],
            ))

    # Checkmate pattern: king is attacked and has no escape
    for ep in enemy_pieces:
        if ep.piece_type == PieceType.KING:
            if board.is_square_attacked_by(ep.x, ep.y, Team.PLAYER):
                # Check if king can escape
                king_moves = ep.get_valid_moves(board)
                can_escape = False
                for mx, my in king_moves:
                    if not board.is_square_attacked_by(mx, my, Team.PLAYER):
                        can_escape = True
                        break
                if not can_escape:
                    patterns.append(PatternResult(
                        "CHECKMATE!",
                        "The enemy king is trapped!",
                        200,
                        [ep],
                    ))
                else:
                    patterns.append(PatternResult(
                        "Check",
                        "The enemy king is in check",
                        30,
                        [ep],
                    ))

    # Simple placement bonus: attacking any enemy
    basic_attacks: list[Piece] = []
    for pp in player_pieces:
        for ax, ay in pp.get_capture_moves(board):
            target = board.get_piece_at(ax, ay)
            if target and target.team == Team.ENEMY and target not in basic_attacks:
                basic_attacks.append(target)
    if basic_attacks and not patterns:
        val = sum(e.value * 5 for e in basic_attacks)
        patterns.append(PatternResult(
            "Threats",
            f"Threatening {len(basic_attacks)} enemy pieces",
            val,
            basic_attacks,
        ))

    return patterns


class Deckbuilder:
    """Deckbuilder mode — place pieces from hand to score tactical patterns."""

    def __init__(self) -> None:
        self.board = Board(8, 8)
        self.round = 0
        self.score = 0
        self.target_score = 100

        # Collection and hand
        self.collection: list[Piece] = []
        self.hand: list[Piece] = []
        self.hand_size = 4

        # Multipliers from modifiers
        self.multipliers: list[dict] = []

        # State
        self.phase = "place"  # place, score, shop, game_over
        self.cursor = (3, 3)
        self.hand_selection = 0
        self.shop_selection = 0
        self.message = ""
        self.patterns: list[PatternResult] = []
        self.round_score = 0

        # Shop
        self.shop_items: list[dict] = []
        self.gold = 0

    def on_enter(self) -> None:
        self.round = 0
        self.score = 0
        self.target_score = 100
        self.gold = 10
        self.multipliers = []

        # Starting collection
        self.collection = [
            Piece(PieceType.PAWN, Team.PLAYER),
            Piece(PieceType.PAWN, Team.PLAYER),
            Piece(PieceType.PAWN, Team.PLAYER),
            Piece(PieceType.KNIGHT, Team.PLAYER),
            Piece(PieceType.KNIGHT, Team.PLAYER),
            Piece(PieceType.BISHOP, Team.PLAYER),
            Piece(PieceType.ROOK, Team.PLAYER),
        ]
        self._start_round()

    def _start_round(self) -> None:
        self.round += 1
        self.board.clear()
        self.phase = "place"
        self.message = ""
        self.patterns = []
        self.round_score = 0
        self.hand_selection = 0

        # Place some enemy pieces on the board
        num_enemies = min(3 + self.round, 8)
        enemy_pool = [PieceType.PAWN, PieceType.PAWN, PieceType.KNIGHT, PieceType.BISHOP]
        if self.round >= 3:
            enemy_pool.extend([PieceType.ROOK, PieceType.QUEEN])
            # Add enemy king for checkmate patterns
            king = Piece(PieceType.KING, Team.ENEMY)
            kx, ky = random.randint(2, 5), random.randint(0, 2)
            self.board.place_piece(king, kx, ky)
            num_enemies -= 1

        used = {(p.x, p.y) for p in self.board.pieces}
        for _ in range(num_enemies):
            pt = random.choice(enemy_pool)
            piece = Piece(pt, Team.ENEMY)
            for _attempt in range(30):
                ex, ey = random.randint(0, 7), random.randint(0, 4)
                if (ex, ey) not in used and self.board.is_empty(ex, ey):
                    self.board.place_piece(piece, ex, ey)
                    used.add((ex, ey))
                    break

        # Draw hand from collection
        random.shuffle(self.collection)
        self.hand = []
        for p in self.collection[:self.hand_size]:
            new_p = p.copy()
            new_p.team = Team.PLAYER
            new_p.alive = True
            self.hand.append(new_p)

    def handle_input(self, action: Action) -> GameState | None:
        if self.phase == "place":
            return self._handle_place(action)
        elif self.phase == "score":
            return self._handle_score(action)
        elif self.phase == "shop":
            return self._handle_shop(action)
        elif self.phase == "game_over":
            if action == Action.CONFIRM:
                return GameState.MENU
            return None
        return None

    def _handle_place(self, action: Action) -> GameState | None:
        cx, cy = self.cursor

        if action == Action.CANCEL:
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

        # Select from hand by number
        num_actions = {
            Action.NUM_1: 0, Action.NUM_2: 1, Action.NUM_3: 2,
            Action.NUM_4: 3, Action.NUM_5: 4, Action.NUM_6: 5,
            Action.NUM_7: 6, Action.NUM_8: 7, Action.NUM_9: 8,
        }
        if action in num_actions:
            idx = num_actions[action]
            if idx < len(self.hand):
                self.hand_selection = idx
                self.message = f"Selected {self.hand[idx].piece_type.value}. Place with ENTER."

        if action == Action.CONFIRM and self.hand:
            # Place selected piece at cursor
            if self.hand_selection < len(self.hand):
                piece = self.hand[self.hand_selection]
                if self.board.is_empty(cx, cy):
                    self.board.place_piece(piece, cx, cy)
                    self.hand.pop(self.hand_selection)
                    if self.hand_selection >= len(self.hand) and self.hand:
                        self.hand_selection = len(self.hand) - 1
                    self.message = f"Placed {piece.piece_type.value}."
                else:
                    self.message = "Square is occupied!"

        if action == Action.SPACE:
            # End turn, score
            self._do_scoring()

        return None

    def _do_scoring(self) -> None:
        self.patterns = detect_patterns(self.board)
        self.round_score = sum(p.base_score for p in self.patterns)

        # Apply multipliers
        total_mult = 1.0
        for mult in self.multipliers:
            if mult["type"] == "pattern":
                for p in self.patterns:
                    if p.name.lower() == mult["pattern"].lower():
                        total_mult += mult["value"]
            elif mult["type"] == "piece":
                for p in self.board.get_team_pieces(Team.PLAYER):
                    if p.piece_type.value == mult["piece"]:
                        total_mult += mult["value"]

        # Royal modifier doubles piece contribution
        for p in self.board.get_team_pieces(Team.PLAYER):
            if any(m.effect == "royal" for m in p.modifiers):
                total_mult += 0.5

        self.round_score = int(self.round_score * total_mult)
        self.score += self.round_score
        self.gold += max(5, self.round_score // 20)
        self.phase = "score"

    def _handle_score(self, action: Action) -> GameState | None:
        if action == Action.CONFIRM:
            if self.score >= self.target_score:
                self.target_score = int(self.target_score * 1.6)
                self._generate_shop()
                self.phase = "shop"
            else:
                self.message = f"Need {self.target_score - self.score} more points to clear!"
                self.phase = "game_over"
        return None

    def _generate_shop(self) -> None:
        self.shop_items = []
        self.shop_selection = 0

        # New pieces to buy
        pool = [PieceType.KNIGHT, PieceType.BISHOP, PieceType.ROOK]
        if self.round >= 3:
            pool.append(PieceType.QUEEN)
        for _ in range(3):
            pt = random.choice(pool)
            cost = PIECE_VALUES[pt] * 3
            self.shop_items.append({
                "type": "piece",
                "piece_type": pt,
                "cost": cost,
                "desc": f"Buy {pt.value} ({cost}g)",
            })

        # Multiplier
        mult_options = [
            {"type": "pattern", "pattern": "Fork", "value": 1.0, "cost": 8,
             "desc": "Fork x2 multiplier (8g)"},
            {"type": "pattern", "pattern": "Pin", "value": 1.0, "cost": 8,
             "desc": "Pin x2 multiplier (8g)"},
            {"type": "piece", "piece": "knight", "value": 0.5, "cost": 6,
             "desc": "Knight +50% score (6g)"},
        ]
        self.shop_items.append(random.choice(mult_options))

        # Skip
        self.shop_items.append({
            "type": "skip",
            "cost": 0,
            "desc": "Done shopping -> Next round",
        })

    def _handle_shop(self, action: Action) -> GameState | None:
        if action == Action.UP:
            self.shop_selection = (self.shop_selection - 1) % len(self.shop_items)
        elif action == Action.DOWN:
            self.shop_selection = (self.shop_selection + 1) % len(self.shop_items)
        elif action == Action.CONFIRM:
            item = self.shop_items[self.shop_selection]
            if item["type"] == "skip":
                self._start_round()
            elif item.get("cost", 0) <= self.gold:
                self.gold -= item["cost"]
                if item["type"] == "piece":
                    self.collection.append(Piece(item["piece_type"], Team.PLAYER))
                    self.message = f"Bought {item['piece_type'].value}!"
                elif item["type"] == "pattern" or item["type"] == "piece":
                    self.multipliers.append(item)
                    self.message = f"Bought multiplier!"
                # Remove purchased item, add new skip check
                self.shop_items.pop(self.shop_selection)
                if self.shop_selection >= len(self.shop_items):
                    self.shop_selection = len(self.shop_items) - 1
            else:
                self.message = "Not enough gold!"
        elif action == Action.CANCEL:
            self._start_round()
        return None

    def render(self, console: tcod.console.Console) -> None:
        if self.phase == "place":
            self._render_place(console)
        elif self.phase == "score":
            self._render_score(console)
        elif self.phase == "shop":
            self._render_shop(console)
        elif self.phase == "game_over":
            self._render_game_over(console)

    def _render_place(self, console: tcod.console.Console) -> None:
        # Show danger zones (squares attacked by enemies)
        highlights: dict[tuple[int, int], tuple[int, int, int]] = {}
        for ep in self.board.get_team_pieces(Team.ENEMY):
            for mx, my in ep.get_valid_moves(self.board):
                if (mx, my) not in highlights:
                    highlights[(mx, my)] = renderer.HIGHLIGHT_DANGER

        renderer.draw_board_border(console, self.board, ox=2, oy=2)
        renderer.draw_board(
            console, self.board, ox=2, oy=2,
            highlights=highlights, cursor=self.cursor,
        )

        # Hand
        if self.hand:
            renderer.draw_hand(console, self.hand, self.hand_selection, 2, 12)

        # Info panel
        panel_x = 20
        lines = [
            f"Round: {self.round}",
            f"Score: {self.score} / {self.target_score}",
            f"Gold: {self.gold}",
            f"Hand: {len(self.hand)} pieces",
            f"Collection: {len(self.collection)} pieces",
            "",
            "1-9: select piece",
            "Arrows: move cursor",
            "Enter: place piece",
            "Space: end turn & score",
            "Esc: quit to menu",
        ]
        renderer.draw_panel(console, panel_x, 1, 38, 14, "Deckbuilder", lines)

        if self.message:
            renderer.draw_message(console, self.message, console.height - 2)

    def _render_score(self, console: tcod.console.Console) -> None:
        renderer.draw_board_border(console, self.board, ox=2, oy=2)
        renderer.draw_board(console, self.board, ox=2, oy=2)

        lines = [f"Round Score: {self.round_score}", ""]
        for p in self.patterns:
            lines.append(f"  {p.name}: +{p.base_score}")
            lines.append(f"    {p.description}")
        if not self.patterns:
            lines.append("  No patterns found!")
        lines.append("")
        lines.append(f"Total Score: {self.score} / {self.target_score}")
        if self.score >= self.target_score:
            lines.append("TARGET MET! Press ENTER for shop.")
        else:
            lines.append("TARGET NOT MET. Press ENTER...")

        renderer.draw_panel(console, 20, 1, 38, min(20, len(lines) + 2), "Scoring", lines)

    def _render_shop(self, console: tcod.console.Console) -> None:
        renderer.draw_panel(console, 5, 2, 50, 3, "Shop", [f"Gold: {self.gold}"])
        renderer.draw_menu(
            console, "Buy Upgrades",
            [item["desc"] for item in self.shop_items],
            self.shop_selection,
            x=5, y=6, width=50,
        )
        if self.message:
            renderer.draw_message(console, self.message, console.height - 2)
        renderer.draw_message(console, "UP/DOWN + ENTER to buy, ESC to skip", console.height - 3)

    def _render_game_over(self, console: tcod.console.Console) -> None:
        renderer.draw_panel(console, 10, 8, 40, 10, "Game Over!", [
            "",
            f"  Rounds completed: {self.round}",
            f"  Final score: {self.score}",
            f"  Target was: {self.target_score}",
            "",
            "  Press ENTER to return to menu",
        ])
