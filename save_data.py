"""Persistent save data — ELO, unlocks, stats stored as JSON."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

# Save file lives next to this module
_SAVE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(_SAVE_DIR, "save_data.json")
RUN_SAVE_PATH = os.path.join(_SAVE_DIR, "continue_run.json")

DEFAULT_PIECES = ["pawn", "knight", "bishop"]
DEFAULT_MODIFIERS = ["flaming", "armored", "swift"]


@dataclass
class SaveData:
    elo: int = 0
    unlocked_pieces: list[str] = field(default_factory=lambda: list(DEFAULT_PIECES))
    unlocked_modifiers: list[str] = field(default_factory=lambda: list(DEFAULT_MODIFIERS))
    upgrades: dict[str, int] = field(default_factory=dict)
    grandmaster_unlocked: bool = False
    stats: dict[str, int] = field(default_factory=lambda: {
        "tournaments_completed": 0,
        "tournaments_won": 0,
        "total_elo_earned": 0,
        "bosses_beaten": 0,
    })


def load() -> SaveData:
    """Load save data from disk, returning defaults if missing or corrupt."""
    if not os.path.exists(SAVE_PATH):
        return SaveData()
    try:
        with open(SAVE_PATH, "r") as f:
            raw = json.load(f)
        data = SaveData()
        data.elo = raw.get("elo", 0)
        data.unlocked_pieces = raw.get("unlocked_pieces", list(DEFAULT_PIECES))
        data.unlocked_modifiers = raw.get("unlocked_modifiers", list(DEFAULT_MODIFIERS))
        data.upgrades = raw.get("upgrades", {})
        data.grandmaster_unlocked = raw.get("grandmaster_unlocked", False)
        data.stats = raw.get("stats", data.stats)
        return data
    except (json.JSONDecodeError, OSError):
        return SaveData()


def save(data: SaveData) -> None:
    """Write save data to disk as JSON."""
    payload = {
        "elo": data.elo,
        "unlocked_pieces": data.unlocked_pieces,
        "unlocked_modifiers": data.unlocked_modifiers,
        "upgrades": data.upgrades,
        "grandmaster_unlocked": data.grandmaster_unlocked,
        "stats": data.stats,
    }
    with open(SAVE_PATH, "w") as f:
        json.dump(payload, f, indent=2)


def save_run(state: dict) -> None:
    """Save serialized run state to continue_run.json."""
    with open(RUN_SAVE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def load_run() -> dict | None:
    """Load run state from disk, or None if no save."""
    if not os.path.exists(RUN_SAVE_PATH):
        return None
    try:
        with open(RUN_SAVE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def clear_run() -> None:
    """Delete the continue save file."""
    if os.path.exists(RUN_SAVE_PATH):
        os.remove(RUN_SAVE_PATH)


def unlock_item(data: SaveData, category: str, key: str) -> None:
    """Add an item to the appropriate unlock list (idempotent)."""
    if category == "Piece":
        if key not in data.unlocked_pieces:
            data.unlocked_pieces.append(key)
    elif category == "Modifier":
        if key not in data.unlocked_modifiers:
            data.unlocked_modifiers.append(key)
    elif category == "Upgrade":
        data.upgrades[key] = data.upgrades.get(key, 0) + 1
