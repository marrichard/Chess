"""Shared game loop, input handling, state machine."""

from __future__ import annotations

import sys
import os
from enum import Enum, auto
from typing import Protocol

import tcod.event
import tcod.console
import tcod.context

import numpy as np

import renderer
import save_data as sd


def make_square_tileset(path: str, tile_height: int = 20) -> tcod.tileset.Tileset:
    """Load a TrueType font and pad glyphs into square cells."""
    font = tcod.tileset.load_truetype_font(path, tile_width=0, tile_height=tile_height)
    fw, fh = font.tile_width, font.tile_height

    if fw == fh:
        return font  # already square

    size = max(fw, fh)
    square = tcod.tileset.Tileset(size, size)

    ox = (size - fw) // 2
    oy = (size - fh) // 2

    for cp in range(32, 512):
        try:
            glyph = font.get_tile(cp)
            new_glyph = np.zeros((size, size, 4), dtype=np.uint8)
            new_glyph[oy:oy + fh, ox:ox + fw] = glyph
            square.set_tile(cp, new_glyph)
        except Exception:
            pass

    return square


class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    ENCOUNTER_END = auto()
    SHOP = auto()
    GAME_OVER = auto()


class Action(Enum):
    NONE = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    CONFIRM = auto()
    CANCEL = auto()
    SPACE = auto()
    NUM_1 = auto()
    NUM_2 = auto()
    NUM_3 = auto()
    NUM_4 = auto()
    NUM_5 = auto()
    NUM_6 = auto()
    NUM_7 = auto()
    NUM_8 = auto()
    NUM_9 = auto()
    MOUSE_MOVE = auto()
    MOUSE_CLICK = auto()
    MOUSE_UP = auto()
    QUIT = auto()
    TOGGLE_FULLSCREEN = auto()
    SCREENSHOT = auto()
    TAB = auto()


# Map tcod keysyms to our actions
KEY_MAP = {
    tcod.event.KeySym.UP: Action.UP,
    tcod.event.KeySym.DOWN: Action.DOWN,
    tcod.event.KeySym.LEFT: Action.LEFT,
    tcod.event.KeySym.RIGHT: Action.RIGHT,
    tcod.event.KeySym.w: Action.UP,
    tcod.event.KeySym.a: Action.LEFT,
    tcod.event.KeySym.s: Action.DOWN,
    tcod.event.KeySym.d: Action.RIGHT,
    tcod.event.KeySym.RETURN: Action.CONFIRM,
    tcod.event.KeySym.KP_ENTER: Action.CONFIRM,
    tcod.event.KeySym.ESCAPE: Action.CANCEL,
    tcod.event.KeySym.SPACE: Action.SPACE,
    tcod.event.KeySym.TAB: Action.TAB,
    tcod.event.KeySym.N1: Action.NUM_1,
    tcod.event.KeySym.N2: Action.NUM_2,
    tcod.event.KeySym.N3: Action.NUM_3,
    tcod.event.KeySym.N4: Action.NUM_4,
    tcod.event.KeySym.N5: Action.NUM_5,
    tcod.event.KeySym.N6: Action.NUM_6,
    tcod.event.KeySym.N7: Action.NUM_7,
    tcod.event.KeySym.N8: Action.NUM_8,
    tcod.event.KeySym.N9: Action.NUM_9,
    tcod.event.KeySym.q: Action.QUIT,
    tcod.event.KeySym.F11: Action.TOGGLE_FULLSCREEN,
    tcod.event.KeySym.f: Action.TOGGLE_FULLSCREEN,
    tcod.event.KeySym.F12: Action.SCREENSHOT,
}


class Mode(Protocol):
    """Protocol for game modes."""
    def on_enter(self) -> None: ...
    def handle_input(self, action: Action) -> GameState | None: ...
    def render(self, console: tcod.console.Console) -> None: ...


TITLE = "Chess Roguelike"

# Base menu options (Continue Run is inserted dynamically)
BASE_MENU_OPTIONS = [
    ("Tournament", "Structured campaign with bosses"),
    ("Free Play", "Endless waves (classic mode)"),
    ("ELO Shop", "Spend ELO on permanent unlocks"),
]

DIFFICULTY_OPTIONS = [
    ("Basic", "Standard challenge"),
    ("Extreme", "Tougher enemies, +mods"),
    ("Grandmaster", "Ultimate challenge"),
]


class Engine:
    """Main game engine with state machine and game loop."""

    def __init__(self) -> None:
        self.state = GameState.MENU
        self.mode: Mode | None = None
        self.running = True
        self.mouse_pixel: tuple[int, int] = (0, 0)
        self.animating: bool = False

        # Menu state
        self.menu_selection: int = 0
        self.menu_phase: str = "main"  # "main" or "difficulty"
        self.difficulty_selection: int = 0
        self.menu_options: list[tuple[str, str]] = []
        self.has_continue: bool = False

        # Persistent save data
        self.save_data: sd.SaveData = sd.load()
        self._rebuild_menu()

    def set_mode(self, mode: Mode) -> None:
        self.mode = mode

    def _rebuild_menu(self) -> None:
        """Rebuild the dynamic menu options list based on save state."""
        run_state = sd.load_run()
        self.has_continue = run_state is not None
        self.menu_options = []
        if self.has_continue:
            wave = run_state.get("wave", "?")
            self.menu_options.append(("Continue Run", f"Resume wave {wave}"))
        self.menu_options.extend(BASE_MENU_OPTIONS)
        if self.menu_selection >= len(self.menu_options):
            self.menu_selection = 0

    def run(self) -> None:
        from piece_tiles import install_piece_tiles

        # Load a monospace font
        tileset = None
        if sys.platform == "win32":
            for font in ("consola.ttf", "lucon.ttf", "cour.ttf"):
                path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", font)
                if os.path.exists(path):
                    tileset = make_square_tileset(path, tile_height=20)
                    break

        # Install custom pixel-art chess piece glyphs
        if tileset:
            install_piece_tiles(tileset)

        with tcod.context.new(
            columns=80,
            rows=40,
            tileset=tileset,
            title=TITLE,
            vsync=True,
            sdl_window_flags=tcod.context.SDL_WINDOW_RESIZABLE | tcod.context.SDL_WINDOW_FULLSCREEN,
        ) as context:
            self.fullscreen = True

            while self.running:
                # Dynamically size console to fill the window
                cols, rows = context.recommended_console_size()
                cols = max(cols, 60)
                rows = max(rows, 30)
                console = tcod.console.Console(cols, rows, order="C")

                # Render
                renderer.clear(console)
                if self.state == GameState.MENU:
                    self._render_menu(console)
                elif self.state in (
                    GameState.PLAYING,
                    GameState.ENCOUNTER_END,
                    GameState.SHOP,
                    GameState.GAME_OVER,
                ):
                    if self.mode:
                        self.mode.render(console)
                context.present(console, keep_aspect=True)

                # Check if mode has active animations
                if self.mode and hasattr(self.mode, 'has_active_animations'):
                    self.animating = self.mode.has_active_animations()
                else:
                    self.animating = False

                # Input
                action = self._wait_for_input(context)
                if action == Action.NONE:
                    continue  # re-render for animation frames
                if action == Action.TOGGLE_FULLSCREEN:
                    self.fullscreen = not self.fullscreen
                    context.sdl_window.fullscreen = self.fullscreen
                    continue
                if action == Action.SCREENSHOT:
                    context.save_screenshot("game_screenshot.png")
                    continue
                if action == Action.QUIT:
                    if self.state == GameState.MENU:
                        self.running = False
                    else:
                        self.state = GameState.MENU
                        self.menu_phase = "main"
                        # Reload save data when returning to menu
                        self.save_data = sd.load()
                        self._rebuild_menu()
                    continue
                if action == Action.MOUSE_MOVE:
                    if self.mode and hasattr(self.mode, 'on_mouse_move'):
                        self.mode.on_mouse_move(self.mouse_pixel)
                    continue
                if action in (Action.MOUSE_CLICK, Action.MOUSE_UP):
                    if self.mode and hasattr(self.mode, 'on_mouse_move'):
                        self.mode.on_mouse_move(self.mouse_pixel)
                    # fall through to _handle_input

                self._handle_input(action)

    def _wait_for_input(self, context: tcod.context.Context) -> Action:
        # Non-blocking poll when animating (vsync gives ~60fps),
        # blocking wait otherwise (saves CPU).
        events = tcod.event.get() if self.animating else tcod.event.wait()
        for event in events:
            context.convert_event(event)
            if isinstance(event, tcod.event.Quit):
                self.running = False
                return Action.QUIT
            if isinstance(event, tcod.event.MouseMotion):
                self.mouse_pixel = (int(event.tile.x), int(event.tile.y))
                return Action.MOUSE_MOVE
            if isinstance(event, tcod.event.MouseButtonDown) and event.button == tcod.event.MouseButton.LEFT:
                self.mouse_pixel = (int(event.tile.x), int(event.tile.y))
                return Action.MOUSE_CLICK
            if isinstance(event, tcod.event.MouseButtonUp) and event.button == tcod.event.MouseButton.LEFT:
                self.mouse_pixel = (int(event.tile.x), int(event.tile.y))
                return Action.MOUSE_UP
            if isinstance(event, tcod.event.KeyDown):
                action = KEY_MAP.get(event.sym, Action.NONE)
                if action != Action.NONE:
                    return action
        return Action.NONE

    def _handle_input(self, action: Action) -> None:
        if self.state == GameState.MENU:
            self._handle_menu(action)
        elif self.state in (
            GameState.PLAYING,
            GameState.ENCOUNTER_END,
            GameState.SHOP,
            GameState.GAME_OVER,
        ):
            if self.mode:
                new_state = self.mode.handle_input(action)
                if new_state:
                    if new_state == GameState.MENU:
                        # Check play-again before going to menu
                        if hasattr(self.mode, 'play_again') and self.mode.play_again:
                            if self.mode.tournament:
                                self._launch_tournament(self.mode.difficulty)
                            else:
                                self._launch_free_play()
                            return
                        # Reload save data when returning to menu
                        self.save_data = sd.load()
                        self._rebuild_menu()
                        self.menu_phase = "main"
                    self.state = new_state

    def _handle_menu(self, action: Action) -> None:
        if self.menu_phase == "main":
            self._handle_main_menu(action)
        elif self.menu_phase == "difficulty":
            self._handle_difficulty_menu(action)

    def _handle_main_menu(self, action: Action) -> None:
        if action == Action.UP:
            self.menu_selection = (self.menu_selection - 1) % len(self.menu_options)
        elif action == Action.DOWN:
            self.menu_selection = (self.menu_selection + 1) % len(self.menu_options)
        elif action == Action.CONFIRM:
            label = self.menu_options[self.menu_selection][0]
            if label == "Continue Run":
                self._launch_continue()
            elif label == "Tournament":
                self.menu_phase = "difficulty"
                self.difficulty_selection = 0
            elif label == "Free Play":
                self._launch_free_play()
            elif label == "ELO Shop":
                self._launch_elo_shop()
        elif action == Action.CANCEL:
            self.running = False

    def _handle_difficulty_menu(self, action: Action) -> None:
        if action == Action.UP:
            self.difficulty_selection = (self.difficulty_selection - 1) % len(DIFFICULTY_OPTIONS)
        elif action == Action.DOWN:
            self.difficulty_selection = (self.difficulty_selection + 1) % len(DIFFICULTY_OPTIONS)
        elif action == Action.CONFIRM:
            diff_key = ["basic", "extreme", "grandmaster"][self.difficulty_selection]
            if diff_key == "grandmaster" and not self.save_data.grandmaster_unlocked:
                return  # locked
            self._launch_tournament(diff_key)
        elif action == Action.CANCEL:
            self.menu_phase = "main"

    def _launch_tournament(self, difficulty: str) -> None:
        from modes.autobattler import AutoBattler
        sd.clear_run()
        mode = AutoBattler(tournament=True, difficulty=difficulty, save_data=self.save_data)
        self.set_mode(mode)
        self.mode.on_enter()
        self.state = GameState.PLAYING

    def _launch_free_play(self) -> None:
        from modes.autobattler import AutoBattler
        sd.clear_run()
        mode = AutoBattler()
        self.set_mode(mode)
        self.mode.on_enter()
        self.state = GameState.PLAYING

    def _launch_continue(self) -> None:
        from modes.autobattler import AutoBattler
        state = sd.load_run()
        if not state:
            return
        mode = AutoBattler(
            tournament=state.get("tournament", False),
            difficulty=state.get("difficulty", "basic"),
            save_data=self.save_data,
        )
        mode.restore_from_run_state(state, self.save_data)
        self.set_mode(mode)
        self.state = GameState.PLAYING

    def _launch_elo_shop(self) -> None:
        from modes.elo_shop import EloShop
        mode = EloShop(save_data=self.save_data)
        self.set_mode(mode)
        self.mode.on_enter()
        self.state = GameState.PLAYING

    def launch_from_menu(self, result: dict) -> None:
        """Set up a game mode based on the pywebview menu result."""
        action = result["action"]
        if action == "tournament":
            self._launch_tournament(result["difficulty"])
        elif action == "free_play":
            self._launch_free_play()
        elif action == "continue":
            self._launch_continue()
        elif action == "elo_shop":
            self._launch_elo_shop()

    def run_game(self) -> dict:
        """Run the tcod game loop without the menu.

        Returns a dict describing why the game ended:
          {"reason": "menu"}       — user pressed Q / mode returned to menu
          {"reason": "quit"}       — user closed the window
          {"reason": "play_again", "tournament": bool, "difficulty": str}
        """
        from piece_tiles import install_piece_tiles

        # Load a monospace font
        tileset = None
        if sys.platform == "win32":
            for font in ("consola.ttf", "lucon.ttf", "cour.ttf"):
                path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", font)
                if os.path.exists(path):
                    tileset = make_square_tileset(path, tile_height=20)
                    break

        if tileset:
            install_piece_tiles(tileset)

        with tcod.context.new(
            columns=80,
            rows=40,
            tileset=tileset,
            title=TITLE,
            vsync=True,
            sdl_window_flags=tcod.context.SDL_WINDOW_RESIZABLE | tcod.context.SDL_WINDOW_FULLSCREEN,
        ) as context:
            self.fullscreen = True

            while True:
                cols, rows = context.recommended_console_size()
                cols = max(cols, 60)
                rows = max(rows, 30)
                console = tcod.console.Console(cols, rows, order="C")

                renderer.clear(console)
                if self.mode:
                    self.mode.render(console)
                context.present(console, keep_aspect=True)

                if self.mode and hasattr(self.mode, 'has_active_animations'):
                    self.animating = self.mode.has_active_animations()
                else:
                    self.animating = False

                action = self._wait_for_input(context)
                if action == Action.NONE:
                    continue
                if action == Action.TOGGLE_FULLSCREEN:
                    self.fullscreen = not self.fullscreen
                    context.sdl_window.fullscreen = self.fullscreen
                    continue
                if action == Action.SCREENSHOT:
                    context.save_screenshot("game_screenshot.png")
                    continue
                if action == Action.QUIT:
                    return {"reason": "menu"}
                if action == Action.MOUSE_MOVE:
                    if self.mode and hasattr(self.mode, 'on_mouse_move'):
                        self.mode.on_mouse_move(self.mouse_pixel)
                    continue
                if action in (Action.MOUSE_CLICK, Action.MOUSE_UP):
                    if self.mode and hasattr(self.mode, 'on_mouse_move'):
                        self.mode.on_mouse_move(self.mouse_pixel)

                # Handle mode input
                if self.mode:
                    new_state = self.mode.handle_input(action)
                    if new_state and new_state == GameState.MENU:
                        # Check play-again
                        if hasattr(self.mode, 'play_again') and self.mode.play_again:
                            return {
                                "reason": "play_again",
                                "tournament": getattr(self.mode, 'tournament', False),
                                "difficulty": getattr(self.mode, 'difficulty', 'basic'),
                            }
                        return {"reason": "menu"}
                    if new_state:
                        self.state = new_state

    def _render_menu(self, console: tcod.console.Console) -> None:
        cw, ch = console.width, console.height

        art = [
            r"   _____ _                     ",
            r"  / ____| |                    ",
            r" | |    | |__   ___  ___ ___   ",
            r" | |    | '_ \ / _ \/ __/ __|  ",
            r" | |____| | | |  __/\__ \__ \  ",
            r"  \_____|_| |_|\___||___/___/  ",
            r"                               ",
            r"       R O G U E L I K E       ",
            r"                               ",
            r"       A U T O - B A T T L E   ",
        ]
        art_y = ch // 2 - 12
        for i, line in enumerate(art):
            cx = (cw - len(line)) // 2
            console.print(cx, art_y + i, line, fg=(180, 140, 255), bg=renderer.BG_BLACK)

        # ELO display in top-right corner
        renderer.draw_elo_display(console, cw - 18, 1, self.save_data.elo)

        if self.menu_phase == "main":
            menu_y = art_y + len(art) + 2
            for i, (label, desc) in enumerate(self.menu_options):
                selected = (i == self.menu_selection)
                renderer.draw_menu_option(
                    console, (cw - 40) // 2, menu_y + i * 3,
                    40, label, desc, selected,
                )

            renderer.draw_message(console, "Up/Down: select  |  Enter: confirm  |  Q: quit", ch - 2)

        elif self.menu_phase == "difficulty":
            menu_y = art_y + len(art) + 2
            title = "-- Select Difficulty --"
            tx = (cw - len(title)) // 2
            console.print(tx, menu_y - 1, title, fg=(255, 220, 100), bg=renderer.BG_BLACK)

            for i, (label, desc) in enumerate(DIFFICULTY_OPTIONS):
                selected = (i == self.difficulty_selection)
                locked = (i == 2 and not self.save_data.grandmaster_unlocked)
                renderer.draw_menu_option(
                    console, (cw - 40) // 2, menu_y + 1 + i * 3,
                    40, label, desc, selected, locked=locked,
                )

            renderer.draw_message(console, "Up/Down: select  |  Enter: confirm  |  Esc: back", ch - 2)
