"""Chess Roguelike — Entry point."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import Engine


def main() -> None:
    engine = Engine()
    engine.run()


if __name__ == "__main__":
    main()
