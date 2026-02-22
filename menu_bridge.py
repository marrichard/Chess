"""Pywebview JS API bridge for the main menu."""

from __future__ import annotations

import save_data as sd


class MenuAPI:
    """Exposed to JavaScript via pywebview.api.*"""

    def __init__(self) -> None:
        self.result: dict | None = None
        self._window = None

    def set_window(self, window) -> None:
        self._window = window

    def get_save_data(self) -> dict:
        """Load fresh save data from disk and return menu-relevant fields."""
        data = sd.load()
        run_state = sd.load_run()
        has_continue = run_state is not None
        continue_wave = run_state.get("wave", "?") if run_state else 0
        return {
            "elo": data.elo,
            "grandmaster_unlocked": data.grandmaster_unlocked,
            "has_continue": has_continue,
            "continue_wave": continue_wave,
            "stats": data.stats,
        }

    def select_mode(self, action: str, difficulty: str = "") -> None:
        """Called by JS when user picks a menu option."""
        self.result = {"action": action, "difficulty": difficulty}
        if self._window:
            self._window.destroy()

    def quit_game(self) -> None:
        """Called by JS when user clicks Quit or presses Escape at root."""
        self.result = {"action": "quit"}
        if self._window:
            self._window.destroy()
