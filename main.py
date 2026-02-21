"""Chess Roguelike — Entry point."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    try:
        import webview  # noqa: F401
    except ImportError:
        # Fallback: run the old tcod-only menu
        from engine import Engine
        engine = Engine()
        engine.run()
        return

    from game_bridge import GameBridge

    api = GameBridge()
    menu_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "menu.html")
    window = webview.create_window(
        "Chess Roguelike",
        url=menu_path,
        js_api=api,
        width=1024,
        height=768,
        resizable=True,
        frameless=False,
    )
    api.set_window(window)
    webview.start()  # blocks until window closed


if __name__ == "__main__":
    main()
