"""Unified pywebview JS API bridge — menu + game + navigation."""

from __future__ import annotations

import os

from engine import Action, GameState
import save_data as sd


class GameBridge:
    """Exposed to JavaScript via pywebview.api.* — handles menu, game, and navigation."""

    def __init__(self) -> None:
        self._window = None
        self._mode = None  # AutoBattler or EloShop instance
        self._save_data: sd.SaveData = sd.load()
        self._last_action: str = ""
        self._last_difficulty: str = ""

    def set_window(self, window) -> None:
        self._window = window

    # ------------------------------------------------------------------ Menu API

    def get_save_data(self) -> dict:
        """Return menu-relevant fields from persistent save data."""
        self._save_data = sd.load()
        run_state = sd.load_run()
        has_continue = run_state is not None
        continue_wave = run_state.get("wave", "?") if run_state else 0
        return {
            "elo": self._save_data.elo,
            "grandmaster_unlocked": self._save_data.grandmaster_unlocked,
            "has_continue": has_continue,
            "continue_wave": continue_wave,
            "stats": self._save_data.stats,
        }

    def quit_game(self) -> None:
        """Destroy the window (exits the app)."""
        if self._window:
            self._window.destroy()

    # ------------------------------------------------------------------ Navigation

    def start_game(self, action: str, difficulty: str = "") -> None:
        """Called by menu JS to launch a game mode. Navigates to game.html."""
        self._last_action = action
        self._last_difficulty = difficulty
        self._save_data = sd.load()

        if action == "tournament":
            sd.clear_run()
            from modes.autobattler import AutoBattler
            self._mode = AutoBattler(
                tournament=True, difficulty=difficulty, save_data=self._save_data,
            )
            self._mode.on_enter()
        elif action == "free_play":
            sd.clear_run()
            from modes.autobattler import AutoBattler
            self._mode = AutoBattler(save_data=self._save_data)
            self._mode.on_enter()
        elif action == "continue":
            state = sd.load_run()
            if not state:
                return
            from modes.autobattler import AutoBattler
            self._mode = AutoBattler(
                tournament=state.get("tournament", False),
                difficulty=state.get("difficulty", "basic"),
                save_data=self._save_data,
            )
            self._mode.restore_from_run_state(state, self._save_data)
        elif action == "elo_shop":
            from modes.elo_shop import EloShop
            self._mode = EloShop(save_data=self._save_data)
            self._mode.on_enter()

        if self._window:
            game_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "web", "game.html",
            )
            self._window.load_url(game_path)

    def return_to_menu(self) -> None:
        """Navigate back to the menu page."""
        self._mode = None
        self._save_data = sd.load()
        if self._window:
            menu_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "web", "menu.html",
            )
            self._window.load_url(menu_path)

    # ------------------------------------------------------------------ Game API

    def get_game_state(self) -> dict:
        """Return the current render state for JS."""
        if self._mode is None:
            return {"phase": "none"}
        return self._mode.to_render_state()

    def send_action(self, action_name: str, board_x: int = -1, board_y: int = -1) -> dict:
        """Process a player action and return the new state.

        action_name: string matching Action enum name (e.g. "CONFIRM", "UP")
        board_x, board_y: board-space coords for mouse actions
        """
        if self._mode is None:
            return {"navigate": "menu"}

        # Map string to Action enum
        try:
            action = Action[action_name]
        except KeyError:
            return self._mode.to_render_state()

        # Update cursor from board coords if provided
        if board_x >= 0 and board_y >= 0:
            if hasattr(self._mode, '_update_cursor_from_board'):
                self._mode._update_cursor_from_board(board_x, board_y)

        # MOUSE_MOVE only updates cursor, no game logic
        if action == Action.MOUSE_MOVE:
            return self._mode.to_render_state()

        # Process the action
        result = self._mode.handle_input(action)

        if result == GameState.MENU:
            # Check play-again flag
            if hasattr(self._mode, 'play_again') and self._mode.play_again:
                # Restart the game without going to menu
                tournament = getattr(self._mode, 'tournament', False)
                difficulty = getattr(self._mode, 'difficulty', 'basic')
                return {
                    "navigate": "play_again",
                    "tournament": tournament,
                    "difficulty": difficulty,
                }
            return {"navigate": "menu"}

        return self._mode.to_render_state()

    def play_again(self, tournament: bool, difficulty: str = "basic") -> None:
        """Restart a game without returning to the menu."""
        self._save_data = sd.load()
        sd.clear_run()
        if tournament:
            from modes.autobattler import AutoBattler
            self._mode = AutoBattler(
                tournament=True, difficulty=difficulty, save_data=self._save_data,
            )
        else:
            from modes.autobattler import AutoBattler
            self._mode = AutoBattler(save_data=self._save_data)
        self._mode.on_enter()
