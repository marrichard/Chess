"""Mode 1: Tactics Puzzler — solve chess capture puzzles under a move limit."""

from __future__ import annotations

import random

import tcod.console

from board import Board
from pieces import Piece, PieceType, Team, PIECE_VALUES, MODIFIERS
from engine import Action, GameState
import renderer


# Encounter templates: (player_pieces, enemy_pieces, move_limit, obstacle_count)
def _gen_encounter(difficulty: int) -> dict:
    """Generate a procedural encounter based on difficulty (1+)."""
    rng = random.Random()

    # Piece pool weighted by difficulty
    player_pool = [PieceType.PAWN, PieceType.KNIGHT, PieceType.BISHOP, PieceType.ROOK]
    enemy_pool = [PieceType.PAWN, PieceType.PAWN, PieceType.KNIGHT, PieceType.BISHOP]
    if difficulty >= 3:
        player_pool.append(PieceType.QUEEN)
        enemy_pool.extend([PieceType.ROOK, PieceType.KNIGHT])
    if difficulty >= 5:
        enemy_pool.extend([PieceType.QUEEN, PieceType.ROOK])

    num_player = min(2 + difficulty // 3, 5)
    num_enemy = min(3 + difficulty // 2, 7)
    move_limit = max(3, 6 - difficulty // 3)
    num_obstacles = min(difficulty // 2, 4)

    player_types = [rng.choice(player_pool) for _ in range(num_player)]
    enemy_types = [rng.choice(enemy_pool) for _ in range(num_enemy)]

    return {
        "player_types": player_types,
        "enemy_types": enemy_types,
        "move_limit": move_limit,
        "obstacles": num_obstacles,
    }


class TacticsPuzzler:
    """Tactics puzzler mode — capture all enemies within a move limit."""

    def __init__(self) -> None:
        self.board = Board(8, 8)
        self.difficulty = 1
        self.encounter = 0
        self.score = 0
        self.moves_left = 5
        self.total_moves = 0

        # Selection state
        self.cursor = (0, 0)
        self.selected_piece: Piece | None = None
        self.valid_moves: list[tuple[int, int]] = []
        self.phase = "play"  # play, reward, game_over
        self.message = ""

        # Reward state
        self.reward_options: list[dict] = []
        self.reward_selection = 0

        # Player's persistent roster (carried between encounters)
        self.roster: list[Piece] = []

    def on_enter(self) -> None:
        self.difficulty = 1
        self.encounter = 0
        self.score = 0
        self.roster = []
        self._start_encounter()

    def _start_encounter(self) -> None:
        self.encounter += 1
        self.board.clear()
        self.selected_piece = None
        self.valid_moves = []
        self.phase = "play"
        self.message = ""

        enc = _gen_encounter(self.difficulty)
        self.moves_left = enc["move_limit"]
        self.total_moves = 0

        # Place obstacles
        for _ in range(enc["obstacles"]):
            for _attempt in range(20):
                ox, oy = random.randint(2, 5), random.randint(2, 5)
                if self.board.is_empty(ox, oy):
                    self.board.add_obstacle(ox, oy)
                    break

        # Place player pieces (bottom rows)
        used = set(self.board.blocked_tiles)
        if self.roster:
            # Use roster pieces
            for p in self.roster:
                p.alive = True
                p.has_moved = False
                for _attempt in range(30):
                    px, py = random.randint(0, 7), random.randint(5, 7)
                    if (px, py) not in used and self.board.get_piece_at(px, py) is None:
                        self.board.place_piece(p, px, py)
                        used.add((px, py))
                        break
        else:
            # First encounter — create from template
            for pt in enc["player_types"]:
                piece = Piece(pt, Team.PLAYER)
                for _attempt in range(30):
                    px, py = random.randint(0, 7), random.randint(5, 7)
                    if (px, py) not in used and self.board.get_piece_at(px, py) is None:
                        self.board.place_piece(piece, px, py)
                        used.add((px, py))
                        break
            self.roster = list(self.board.get_team_pieces(Team.PLAYER))

        # Place enemy pieces (top rows)
        for pt in enc["enemy_types"]:
            piece = Piece(pt, Team.ENEMY)
            for _attempt in range(30):
                ex, ey = random.randint(0, 7), random.randint(0, 3)
                if (ex, ey) not in used and self.board.get_piece_at(ex, ey) is None:
                    self.board.place_piece(piece, ex, ey)
                    used.add((ex, ey))
                    break

        self.cursor = (self.roster[0].x, self.roster[0].y) if self.roster else (4, 6)

    def handle_input(self, action: Action) -> GameState | None:
        if self.phase == "play":
            return self._handle_play(action)
        elif self.phase == "reward":
            return self._handle_reward(action)
        elif self.phase == "game_over":
            if action == Action.CONFIRM:
                return GameState.MENU
            return None
        return None

    def _handle_play(self, action: Action) -> GameState | None:
        cx, cy = self.cursor

        if action == Action.CANCEL:
            if self.selected_piece:
                self.selected_piece = None
                self.valid_moves = []
                self.message = ""
            else:
                return GameState.MENU
            return None

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
            return None

        if action == Action.CONFIRM:
            if self.selected_piece is None:
                # Select a player piece
                piece = self.board.get_piece_at(cx, cy)
                if piece and piece.team == Team.PLAYER:
                    self.selected_piece = piece
                    self.valid_moves = piece.get_valid_moves(self.board)
                    if self.valid_moves:
                        self.message = f"Selected {piece.piece_type.value}. Choose destination."
                    else:
                        self.message = "No valid moves for this piece!"
                        self.selected_piece = None
                else:
                    self.message = "Select one of your pieces (blue)."
            else:
                # Try to move to cursor
                if (cx, cy) in self.valid_moves:
                    captured = self.board.move_piece(self.selected_piece, cx, cy)
                    self.moves_left -= 1
                    self.total_moves += 1
                    if captured:
                        pts = captured.value * 10
                        self.score += pts
                        self.message = f"Captured {captured.piece_type.value}! +{pts} pts"
                    else:
                        self.message = "Moved."

                    self.selected_piece = None
                    self.valid_moves = []

                    # Check win/lose
                    if self.board.count_alive(Team.ENEMY) == 0:
                        bonus = self.moves_left * 20
                        self.score += bonus
                        self.message = f"Victory! Bonus: +{bonus}pts for {self.moves_left} moves left"
                        self.phase = "reward"
                        self._generate_rewards()
                    elif self.moves_left <= 0:
                        remaining = self.board.count_alive(Team.ENEMY)
                        if remaining > 0:
                            self.message = f"Out of moves! {remaining} enemies remain. Game Over!"
                            self.phase = "game_over"
                        else:
                            self.phase = "reward"
                            self._generate_rewards()
                else:
                    self.message = "Invalid move. Try again."
            return None

        return None

    def _generate_rewards(self) -> None:
        """Generate reward options between encounters."""
        self.reward_options = []
        self.reward_selection = 0

        # Option 1: New piece
        pool = [PieceType.KNIGHT, PieceType.BISHOP, PieceType.ROOK]
        if self.difficulty >= 4:
            pool.append(PieceType.QUEEN)
        pt = random.choice(pool)
        self.reward_options.append({
            "type": "new_piece",
            "piece_type": pt,
            "desc": f"Add a {pt.value} to your roster",
        })

        # Option 2: Upgrade existing piece
        if self.roster:
            target = random.choice([p for p in self.roster if p.alive])
            mod_key = random.choice(list(MODIFIERS.keys()))
            mod = MODIFIERS[mod_key]
            self.reward_options.append({
                "type": "upgrade",
                "target": target,
                "modifier": mod,
                "desc": f"Give {target.piece_type.value} '{mod.name}' ({mod.description})",
            })

        # Option 3: Skip for points
        self.reward_options.append({
            "type": "points",
            "amount": 50,
            "desc": "Skip reward, gain 50 bonus points",
        })

    def _handle_reward(self, action: Action) -> GameState | None:
        if action == Action.UP:
            self.reward_selection = (self.reward_selection - 1) % len(self.reward_options)
        elif action == Action.DOWN:
            self.reward_selection = (self.reward_selection + 1) % len(self.reward_options)
        elif action == Action.CONFIRM:
            reward = self.reward_options[self.reward_selection]
            if reward["type"] == "new_piece":
                new_piece = Piece(reward["piece_type"], Team.PLAYER)
                self.roster.append(new_piece)
            elif reward["type"] == "upgrade":
                reward["target"].modifiers.append(reward["modifier"])
            elif reward["type"] == "points":
                self.score += reward["amount"]

            self.difficulty += 1
            self._start_encounter()
        elif action == Action.CANCEL:
            return GameState.MENU
        return None

    def render(self, console: tcod.console.Console) -> None:
        if self.phase == "play":
            self._render_play(console)
        elif self.phase == "reward":
            self._render_reward(console)
        elif self.phase == "game_over":
            self._render_game_over(console)

    def _render_play(self, console: tcod.console.Console) -> None:
        # Build highlights
        highlights: dict[tuple[int, int], tuple[int, int, int]] = {}
        for mx, my in self.valid_moves:
            target = self.board.get_piece_at(mx, my)
            if target and target.team == Team.ENEMY:
                highlights[(mx, my)] = renderer.HIGHLIGHT_CAPTURE
            else:
                highlights[(mx, my)] = renderer.HIGHLIGHT_MOVE

        selected_pos = None
        if self.selected_piece:
            selected_pos = (self.selected_piece.x, self.selected_piece.y)

        renderer.draw_board_border(console, self.board, ox=2, oy=2)
        renderer.draw_board(
            console, self.board,
            ox=2, oy=2,
            highlights=highlights,
            cursor=self.cursor,
            selected=selected_pos,
        )

        # Info panel
        panel_x = 20
        panel_y = 1
        lines = [
            f"Encounter: {self.encounter}",
            f"Difficulty: {self.difficulty}",
            f"Moves left: {self.moves_left}",
            f"Score: {self.score}",
            f"Enemies: {self.board.count_alive(Team.ENEMY)}",
            "",
            "Your roster:",
        ]
        for p in self.roster:
            status = "alive" if p.alive else "dead"
            mods = ", ".join(m.name for m in p.modifiers) if p.modifiers else ""
            extra = f" [{mods}]" if mods else ""
            lines.append(f"  {p.piece_type.value}{extra}")

        renderer.draw_panel(console, panel_x, panel_y, 38, 18, "Tactics Puzzler", lines)

        # Controls
        ctrl_lines = [
            "Arrows: move cursor",
            "Enter: select/confirm",
            "Esc: deselect/menu",
        ]
        renderer.draw_panel(console, panel_x, 20, 38, 5, "Controls", ctrl_lines)

        # Message
        if self.message:
            renderer.draw_message(console, self.message, console.height - 2)

    def _render_reward(self, console: tcod.console.Console) -> None:
        renderer.draw_panel(console, 5, 3, 50, 3, "Encounter Complete!", [
            f"Score: {self.score}",
        ])

        renderer.draw_menu(
            console,
            "Choose Your Reward",
            [r["desc"] for r in self.reward_options],
            self.reward_selection,
            x=5, y=7, width=50,
        )
        renderer.draw_message(console, "UP/DOWN + ENTER to choose", console.height - 2)

    def _render_game_over(self, console: tcod.console.Console) -> None:
        renderer.draw_panel(console, 10, 8, 40, 10, "Game Over!", [
            "",
            f"  Encounters cleared: {self.encounter - 1}",
            f"  Final score: {self.score}",
            f"  Difficulty reached: {self.difficulty}",
            "",
            "  Press ENTER to return to menu",
        ])
