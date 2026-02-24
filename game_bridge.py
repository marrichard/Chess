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
        from achievements import ACHIEVEMENTS
        total_achievements = len(ACHIEVEMENTS)
        unlocked_count = len(self._save_data.unlocked_achievements)
        return {
            "elo": self._save_data.elo,
            "grandmaster_unlocked": self._save_data.grandmaster_unlocked,
            "has_continue": has_continue,
            "continue_wave": continue_wave,
            "stats": self._save_data.stats,
            "settings": self._save_data.settings,
            "achievement_count": unlocked_count,
            "achievement_total": total_achievements,
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
        from pieces import PIECE_STATS, PieceType, PIECE_INFO, MODIFIERS
        from modifiers import CELL_MODIFIERS, BORDER_MODIFIERS, TAROT_CARDS, ARTIFACTS, PIECE_MODIFIER_VISUALS
        from synergies import SYNERGIES
        from masters import MASTERS
        from achievements import ACHIEVEMENTS, ACHIEVEMENT_CATEGORIES
        from rarity import (
            PIECE_RARITY, PIECE_MOD_RARITY, TAROT_RARITY, ARTIFACT_RARITY,
            CELL_MOD_RARITY, BORDER_MOD_RARITY, RARITY_PROPS, Rarity,
        )
        from taglines import TAGLINES, PIECE_FACTIONS, FACTION_ORDER, FACTION_ICONS

        pieces = []
        for pt, (hp, atk) in PIECE_STATS.items():
            r = PIECE_RARITY.get(pt.value, Rarity.COMMON)
            info = PIECE_INFO.get(pt, {})
            pieces.append({
                "key": pt.value,
                "name": pt.value.replace("_", " ").title(),
                "hp": hp,
                "attack": atk,
                "unlocked": pt.value in self._save_data.unlocked_pieces,
                "rarity": r.value,
                "rarityColor": list(RARITY_PROPS[r]["color"]),
                "tagline": TAGLINES.get("piece:" + pt.value, ""),
                "faction": PIECE_FACTIONS.get(pt.value, "Unknown"),
                "move": info.get("move", ""),
                "ability": info.get("ability", ""),
            })

        cell_mods = []
        for key, m in CELL_MODIFIERS.items():
            r = CELL_MOD_RARITY.get(key, Rarity.COMMON)
            cell_mods.append({
                "key": key,
                "name": m["name"],
                "icon": m.get("icon", "?"),
                "color": list(m["color"]),
                "description": m["description"],
                "rarity": r.value,
                "rarityColor": list(RARITY_PROPS[r]["color"]),
                "tagline": TAGLINES.get("cell_mod:" + key, ""),
            })

        border_mods = []
        for key, m in BORDER_MODIFIERS.items():
            r = BORDER_MOD_RARITY.get(key, Rarity.COMMON)
            border_mods.append({
                "key": key,
                "name": m["name"],
                "icon": "\u25A3",
                "color": list(m["border_color"]),
                "description": m["description"],
                "rarity": r.value,
                "rarityColor": list(RARITY_PROPS[r]["color"]),
                "tagline": TAGLINES.get("border_mod:" + key, ""),
            })

        piece_mods = []
        for key, mod in MODIFIERS.items():
            r = PIECE_MOD_RARITY.get(key, Rarity.COMMON)
            vis = PIECE_MODIFIER_VISUALS.get(key, {})
            piece_mods.append({
                "key": key,
                "name": mod.name,
                "description": mod.description,
                "rarity": r.value,
                "rarityColor": list(RARITY_PROPS[r]["color"]),
                "color": list(vis.get("color", (200, 200, 200))),
                "tagline": TAGLINES.get("piece_mod:" + key, ""),
            })

        tarots = []
        for key, t in TAROT_CARDS.items():
            r = TAROT_RARITY.get(key, Rarity.COMMON)
            tarots.append({
                "key": key,
                "name": t["name"],
                "icon": t.get("icon", "\u2605"),
                "color": list(t["color"]),
                "cost": t["cost"],
                "description": t["description"],
                "rarity": r.value,
                "rarityColor": list(RARITY_PROPS[r]["color"]),
                "tagline": TAGLINES.get("tarot:" + key, ""),
            })

        artifacts = []
        for key, a in ARTIFACTS.items():
            r = ARTIFACT_RARITY.get(key, Rarity.COMMON)
            artifacts.append({
                "key": key,
                "name": a["name"],
                "icon": a.get("icon", "\u2726"),
                "color": list(a["color"]),
                "cost": a["cost"],
                "rarity": r.value,
                "rarityColor": list(RARITY_PROPS[r]["color"]),
                "description": a["description"],
                "tagline": TAGLINES.get("artifact:" + key, ""),
            })

        synergies = []
        discovered = set(self._save_data.discovered_synergies)
        for s in SYNERGIES:
            synergies.append({
                "key": s.effect_key,
                "name": s.name,
                "icon": s.icon,
                "color": list(s.color),
                "description": s.description,
                "required_pieces": [p.value for p in s.required_pieces],
                "discovered": s.effect_key in discovered,
                "tagline": TAGLINES.get("synergy:" + s.effect_key, ""),
            })

        masters_list = []
        for key, m in MASTERS.items():
            masters_list.append({
                "key": m.key,
                "name": m.name,
                "description": m.description,
                "passive": m.passive_desc,
                "drawback": m.drawback_desc,
                "icon": m.icon,
                "color": list(m.color),
                "unlocked": key in self._save_data.unlocked_masters,
                "tagline": TAGLINES.get("master:" + key, ""),
            })

        unlocked_ach = set(self._save_data.unlocked_achievements)
        achievements = []
        for ach in ACHIEVEMENTS:
            earned = ach.key in unlocked_ach
            achievements.append({
                "key": ach.key,
                "name": ach.name if (earned or not ach.hidden) else "???",
                "description": ach.description if (earned or not ach.hidden) else "Hidden achievement",
                "icon": ach.icon if (earned or not ach.hidden) else "?",
                "category": ach.category,
                "hidden": ach.hidden,
                "earned": earned,
                "unlocks": ach.unlocks if (earned or not ach.hidden) else [],
                "tagline": TAGLINES.get("achievement:" + ach.key, "") if (earned or not ach.hidden) else "",
            })

        return {
            "pieces": pieces,
            "piece_modifiers": piece_mods,
            "cell_modifiers": cell_mods,
            "border_modifiers": border_mods,
            "tarots": tarots,
            "artifacts": artifacts,
            "synergies": synergies,
            "masters": masters_list,
            "achievements": achievements,
            "achievement_categories": ACHIEVEMENT_CATEGORIES,
            "faction_order": FACTION_ORDER,
            "faction_icons": FACTION_ICONS,
        }

    def mark_codex_viewed(self, tab: str) -> None:
        """Called from chessticon.js when user views a codex tab. Increments unique entries viewed."""
        from pieces import PIECE_STATS, MODIFIERS
        from modifiers import CELL_MODIFIERS, BORDER_MODIFIERS, TAROT_CARDS, ARTIFACTS
        from synergies import SYNERGIES
        from masters import MASTERS
        from achievements import ACHIEVEMENTS

        # Count items for this tab
        tab_counts = {
            "pieces": len(PIECE_STATS),
            "modifiers": len(MODIFIERS) + len(CELL_MODIFIERS) + len(BORDER_MODIFIERS),
            "tarots": len(TAROT_CARDS),
            "artifacts": len(ARTIFACTS),
            "synergies": len(SYNERGIES),
            "masters": len(MASTERS),
            "achievements": len(ACHIEVEMENTS),
        }
        count = tab_counts.get(tab, 0)
        if count <= 0:
            return

        self._save_data = sd.load()
        viewed_tabs = set(self._save_data.stats.get("codex_tabs_viewed", []))
        if tab not in viewed_tabs:
            viewed_tabs.add(tab)
            self._save_data.stats["codex_tabs_viewed"] = list(viewed_tabs)
            # Count total unique entries viewed based on tabs visited
            total_viewed = sum(tab_counts.get(t, 0) for t in viewed_tabs)
            self._save_data.stats["codex_entries_viewed"] = total_viewed
            sd.save(self._save_data)

    def get_achievements(self) -> dict:
        """Return all achievement data for the gallery UI."""
        from achievements import ACHIEVEMENTS, ACHIEVEMENT_CATEGORIES
        self._save_data = sd.load()
        unlocked = set(self._save_data.unlocked_achievements)

        achievements = []
        for ach in ACHIEVEMENTS:
            earned = ach.key in unlocked
            achievements.append({
                "key": ach.key,
                "name": ach.name if (earned or not ach.hidden) else "???",
                "description": ach.description if (earned or not ach.hidden) else "Hidden achievement",
                "icon": ach.icon if (earned or not ach.hidden) else "?",
                "category": ach.category,
                "hidden": ach.hidden,
                "earned": earned,
                "unlocks": ach.unlocks if (earned or not ach.hidden) else [],
            })

        return {
            "achievements": achievements,
            "categories": ACHIEVEMENT_CATEGORIES,
            "unlocked_count": len(unlocked),
            "total_count": len(ACHIEVEMENTS),
        }

    def get_achievement_progress(self) -> list[dict]:
        """Return progress data for stat-based achievements."""
        from achievements import ACHIEVEMENTS
        self._save_data = sd.load()
        stats = self._save_data.stats
        unlocked = set(self._save_data.unlocked_achievements)

        progress = []
        for ach in ACHIEVEMENTS:
            if ach.condition_type != "stat":
                continue
            earned = ach.key in unlocked
            stat_key = ach.condition.get("stat", "")
            threshold = ach.condition.get("threshold", 0)

            # Dynamic thresholds
            if stat_key == "synergies_discovered":
                from synergies import SYNERGIES
                if ach.key == "encyclopedia":
                    threshold = len(SYNERGIES)
                actual = len(self._save_data.discovered_synergies)
            elif stat_key == "different_masters_won_with":
                from masters import MASTERS
                if ach.key == "completionist":
                    threshold = len(MASTERS)
                actual = len(stats.get("masters_won_with", []))
            elif stat_key == "codex_entries_viewed":
                from pieces import PIECE_STATS
                from modifiers import CELL_MODIFIERS, BORDER_MODIFIERS, TAROT_CARDS, ARTIFACTS
                total = len(PIECE_STATS) + len(CELL_MODIFIERS) + len(BORDER_MODIFIERS) + len(TAROT_CARDS) + len(ARTIFACTS) + len(SYNERGIES) + len(MASTERS)
                threshold = total
                actual = stats.get("codex_entries_viewed", 0)
            elif stat_key == "boss_types_beaten_count":
                actual = len(stats.get("boss_types_beaten", []))
            else:
                actual = stats.get(stat_key, 0)

            progress.append({
                "key": ach.key,
                "name": ach.name if (earned or not ach.hidden) else "???",
                "current": min(actual, threshold),
                "target": threshold,
                "earned": earned,
            })

        return progress

    def quit_game(self) -> None:
        """Destroy the window (exits the app)."""
        if self._window:
            self._window.destroy()

    # ------------------------------------------------------------------ Master API

    def get_masters(self) -> list[dict]:
        """Return list of master data for selection UI."""
        from masters import MASTERS
        result = []
        for key, m in MASTERS.items():
            result.append({
                "key": m.key,
                "name": m.name,
                "description": m.description,
                "passive": m.passive_desc,
                "drawback": m.drawback_desc,
                "icon": m.icon,
                "color": list(m.color),
                "unlocked": key in self._save_data.unlocked_masters,
                "selected": key == self._save_data.selected_master,
            })
        return result

    def select_master(self, key: str) -> dict:
        """Store master selection in save data."""
        from masters import MASTERS
        if key in MASTERS and key in self._save_data.unlocked_masters:
            self._save_data.selected_master = key
            sd.save(self._save_data)
            return {"success": True, "selected": key}
        return {"success": False}

    # ------------------------------------------------------------------ Navigation

    def start_game(self, action: str, difficulty: str = "") -> None:
        """Called by menu JS to launch a game mode. Navigates to game.html."""
        self._last_action = action
        self._last_difficulty = difficulty
        self._save_data = sd.load()

        master_key = self._save_data.selected_master

        if action == "tournament":
            sd.clear_run()
            from modes.autobattler import AutoBattler
            self._mode = AutoBattler(
                tournament=True, difficulty=difficulty, save_data=self._save_data,
                master_key=master_key,
            )
            self._mode.on_enter()
        elif action == "free_play":
            sd.clear_run()
            from modes.autobattler import AutoBattler
            self._mode = AutoBattler(save_data=self._save_data, master_key=master_key)
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
        elif phase == "map":
            floor = mode.encounter_map[mode.current_floor] if mode.current_floor < len(mode.encounter_map) else []
            if row < len(floor):
                mode.map_selection = row
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
        master_key = self._save_data.selected_master
        if tournament:
            from modes.autobattler import AutoBattler
            self._mode = AutoBattler(
                tournament=True, difficulty=difficulty, save_data=self._save_data,
                master_key=master_key,
            )
        else:
            from modes.autobattler import AutoBattler
            self._mode = AutoBattler(save_data=self._save_data, master_key=master_key)
        self._mode.on_enter()
