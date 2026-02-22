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
            "settings": self._save_data.settings,
        }

    def get_settings(self) -> dict:
        """Return current settings."""
        return dict(self._save_data.settings)

    def update_settings(self, settings: dict) -> dict:
        """Merge keys into save_data.settings, persist, return updated."""
        self._save_data.settings.update(settings)
        sd.save(self._save_data)
        return dict(self._save_data.settings)

    def get_codex_data(self) -> dict:
        """Collect all static definitions plus discovery state for codex."""
        from pieces import PIECE_STATS, PieceType
        from modifiers import CELL_MODIFIERS, BORDER_MODIFIERS, TAROT_CARDS, ARTIFACTS
        from synergies import SYNERGIES

        pieces = []
        for pt, (hp, atk) in PIECE_STATS.items():
            pieces.append({
                "key": pt.value,
                "name": pt.value.replace("_", " ").title(),
                "hp": hp,
                "attack": atk,
                "unlocked": pt.value in self._save_data.unlocked_pieces,
            })

        cell_mods = []
        for key, m in CELL_MODIFIERS.items():
            cell_mods.append({
                "key": key,
                "name": m["name"],
                "icon": m.get("icon", "?"),
                "color": list(m["color"]),
                "description": m["description"],
            })

        border_mods = []
        for key, m in BORDER_MODIFIERS.items():
            border_mods.append({
                "key": key,
                "name": m["name"],
                "color": list(m["border_color"]),
                "description": m["description"],
            })

        tarots = []
        for key, t in TAROT_CARDS.items():
            tarots.append({
                "key": key,
                "name": t["name"],
                "icon": t.get("icon", "\u2605"),
                "color": list(t["color"]),
                "cost": t["cost"],
                "description": t["description"],
            })

        artifacts = []
        for key, a in ARTIFACTS.items():
            artifacts.append({
                "key": key,
                "name": a["name"],
                "icon": a.get("icon", "\u2726"),
                "color": list(a["color"]),
                "cost": a["cost"],
                "rarity": a.get("rarity", "common"),
                "description": a["description"],
            })

        synergies = []
        discovered = set(self._save_data.discovered_synergies)
        for s in SYNERGIES:
            synergies.append({
                "name": s.name,
                "icon": s.icon,
                "color": list(s.color),
                "description": s.description,
                "required_pieces": [p.value for p in s.required_pieces],
                "discovered": s.effect_key in discovered,
            })

        return {
            "pieces": pieces,
            "cell_modifiers": cell_mods,
            "border_modifiers": border_mods,
            "tarots": tarots,
            "artifacts": artifacts,
            "synergies": synergies,
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

    def cash_out(self) -> dict:
        """Cash out of the current tournament for 1/3 ELO instead of 1/4."""
        if self._mode is None:
            return {"navigate": "menu"}
        from modes.autobattler import AutoBattler
        if not isinstance(self._mode, AutoBattler) or not self._mode.tournament:
            return {"navigate": "menu"}
        self._mode._cash_out()
        return self._mode.to_render_state()

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

    def set_selection(self, row: int, col: int = 0) -> dict:
        """Directly set cursor/selection for current phase. Returns new state."""
        if self._mode is None:
            return {"phase": "none"}
        mode = self._mode
        phase = getattr(mode, 'phase', '')

        if phase == "shop":
            rows = mode._get_shop_rows()
            if row < len(rows):
                mode.shop_row = row
                mode.shop_col = min(col, len(rows[row]["items"]) - 1)
            else:
                mode.shop_row = len(rows)  # done button
                mode.shop_col = 0
        elif phase == "draft":
            if hasattr(mode, 'draft_options') and row < len(mode.draft_options):
                mode.draft_selection = row
        elif phase == "place_piece_mod":
            mode.roster_selection = row
        elif phase == "swap_tarot":
            mode.roster_selection = row
        elif phase == "elo_shop":
            from modes.elo_shop import SHOP_CATALOG
            if row < len(SHOP_CATALOG):
                mode.selection = row
                mode._update_scroll()

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
