"""Persistent save data — ELO, unlocks, stats stored as JSON."""

from __future__ import annotations

import json
import os
import tempfile
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
    unlocked_artifacts: list[str] = field(default_factory=list)
    upgrades: dict[str, int] = field(default_factory=dict)
    grandmaster_unlocked: bool = False
    discovered_synergies: list[str] = field(default_factory=list)
    unlocked_masters: list[str] = field(default_factory=lambda: ["the_strategist"])
    selected_master: str = "the_strategist"
    unlocked_achievements: list[str] = field(default_factory=list)
    settings: dict = field(default_factory=lambda: {
        "battle_speed": 400,
        "particles_enabled": True,
    })
    stats: dict = field(default_factory=lambda: {
        "tournaments_completed": 0,
        "tournaments_won": 0,
        "total_elo_earned": 0,
        "bosses_beaten": 0,
        "total_gold_earned": 0,
        "total_gold_spent": 0,
        "items_sold": 0,
        "shop_items_bought": 0,
        "max_damage_single_hit": 0,
        "max_pieces_alive": 0,
        "battles_won_no_losses": 0,
        "different_tarots_used": 0,
        "different_artifacts_collected": 0,
        "different_masters_won_with": 0,
        "total_revives": 0,
        "total_ondeath_triggers": 0,
        "times_phoenix_revived": 0,
        "fastest_tournament_seconds": 0,
        "codex_entries_viewed": 0,
        # List-type stats stored as lists
        "tarots_used_set": [],
        "artifacts_collected_set": [],
        "masters_won_with": [],
        "boss_types_beaten": [],
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
        data.unlocked_artifacts = raw.get("unlocked_artifacts", [])
        data.upgrades = raw.get("upgrades", {})
        data.grandmaster_unlocked = raw.get("grandmaster_unlocked", False)
        data.discovered_synergies = raw.get("discovered_synergies", [])
        data.unlocked_masters = raw.get("unlocked_masters", ["the_strategist"])
        data.selected_master = raw.get("selected_master", "the_strategist")
        data.unlocked_achievements = raw.get("unlocked_achievements", [])
        data.settings = raw.get("settings", {"battle_speed": 400, "particles_enabled": True})
        # Merge saved stats with defaults so new keys are always present
        default_stats = SaveData().stats
        saved_stats = raw.get("stats", {})
        default_stats.update(saved_stats)
        data.stats = default_stats
        return data
    except (json.JSONDecodeError, OSError):
        return SaveData()


def save(data: SaveData) -> None:
    """Write save data to disk as JSON."""
    payload = {
        "elo": data.elo,
        "unlocked_pieces": data.unlocked_pieces,
        "unlocked_modifiers": data.unlocked_modifiers,
        "unlocked_artifacts": data.unlocked_artifacts,
        "upgrades": data.upgrades,
        "grandmaster_unlocked": data.grandmaster_unlocked,
        "discovered_synergies": data.discovered_synergies,
        "unlocked_masters": data.unlocked_masters,
        "selected_master": data.selected_master,
        "unlocked_achievements": data.unlocked_achievements,
        "settings": data.settings,
        "stats": data.stats,
    }
    tmp_fd, tmp_path = tempfile.mkstemp(dir=_SAVE_DIR, suffix=".tmp")
    closed = False
    try:
        os.write(tmp_fd, json.dumps(payload, indent=2).encode())
        os.close(tmp_fd)
        closed = True
        os.replace(tmp_path, SAVE_PATH)
    except Exception:
        if not closed:
            os.close(tmp_fd)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def save_run(state: dict) -> None:
    """Save serialized run state to continue_run.json."""
    tmp_fd, tmp_path = tempfile.mkstemp(dir=_SAVE_DIR, suffix=".tmp")
    closed = False
    try:
        os.write(tmp_fd, json.dumps(state, indent=2).encode())
        os.close(tmp_fd)
        closed = True
        os.replace(tmp_path, RUN_SAVE_PATH)
    except Exception:
        if not closed:
            os.close(tmp_fd)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


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
    elif category == "Artifact":
        if key not in data.unlocked_artifacts:
            data.unlocked_artifacts.append(key)
    elif category == "Master":
        if key not in data.unlocked_masters:
            data.unlocked_masters.append(key)
