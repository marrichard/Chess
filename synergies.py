"""Synergy system — Enter the Gungeon-style named synergies from piece combinations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pieces import PieceType, Piece, Team


@dataclass
class Synergy:
    name: str
    description: str
    icon: str
    color: tuple[int, int, int]
    required_pieces: list[PieceType]  # need 1+ of each
    min_counts: dict[PieceType, int]  # need N+ of these (override required_pieces count)
    required_modifiers: list[str]     # any piece has one of these
    effect_key: str                   # unique identifier


SYNERGIES: list[Synergy] = [
    Synergy(
        name="Minefield",
        description="Bomb explosions chain to other bombs within 2 cells",
        icon="\u2738", color=(255, 100, 30),
        required_pieces=[PieceType.BOMB],
        min_counts={PieceType.BOMB: 2},
        required_modifiers=[],
        effect_key="minefield",
    ),
    Synergy(
        name="Identity Theft",
        description="Mimic transforms on any damage; Leech steals 2 mods",
        icon="?", color=(200, 50, 200),
        required_pieces=[PieceType.MIMIC, PieceType.LEECH],
        min_counts={},
        required_modifiers=[],
        effect_key="identity_theft",
    ),
    Synergy(
        name="Necromancer",
        description="Summoner-spawned pawns revive once",
        icon="\u2620", color=(100, 200, 100),
        required_pieces=[PieceType.SUMMONER, PieceType.PHOENIX],
        min_counts={},
        required_modifiers=[],
        effect_key="necromancer",
    ),
    Synergy(
        name="Rat King",
        description="Merge 3+ King Rats into a mega rat with combined HP",
        icon="\u2689", color=(180, 150, 100),
        required_pieces=[PieceType.KING_RAT],
        min_counts={PieceType.KING_RAT: 3},
        required_modifiers=[],
        effect_key="rat_king",
    ),
    Synergy(
        name="Haunted Board",
        description="Ghost leaves 1-damage cursed cells when moving",
        icon="\u2601", color=(100, 50, 200),
        required_pieces=[PieceType.GHOST, PieceType.VOID],
        min_counts={},
        required_modifiers=[],
        effect_key="haunted_board",
    ),
    Synergy(
        name="Sacrifice",
        description="Bomb explosion converts enemies instead of damaging",
        icon="\u2623", color=(200, 50, 50),
        required_pieces=[PieceType.BOMB, PieceType.PARASITE],
        min_counts={},
        required_modifiers=[],
        effect_key="sacrifice",
    ),
    Synergy(
        name="Swarm Intelligence",
        description="Summoner spawns Knights instead of Pawns",
        icon="\u2726", color=(60, 200, 255),
        required_pieces=[PieceType.SUMMONER],
        min_counts={PieceType.PAWN: 4},
        required_modifiers=[],
        effect_key="swarm_intelligence",
    ),
    Synergy(
        name="Infinite Recursion",
        description="Mirrors teleport randomly, deal 1 damage on arrival",
        icon="\u25C8", color=(200, 200, 220),
        required_pieces=[PieceType.MIRROR_PIECE],
        min_counts={PieceType.MIRROR_PIECE: 2},
        required_modifiers=[],
        effect_key="infinite_recursion",
    ),
    Synergy(
        name="Life Drain",
        description="Parasite also heals adjacent friendlies",
        icon="\u2665", color=(180, 30, 30),
        required_pieces=[PieceType.LEECH, PieceType.PARASITE],
        min_counts={},
        required_modifiers=[],
        effect_key="life_drain",
    ),
    Synergy(
        name="Glass Cannon",
        description="Gambler never misses but takes double damage",
        icon="\u2660", color=(255, 215, 0),
        required_pieces=[PieceType.GAMBLER],
        min_counts={},
        required_modifiers=["flaming", "piercing", "swift"],
        effect_key="glass_cannon",
    ),
]


def check_synergies(roster: list[Piece], team: Team) -> list[str]:
    """Evaluate roster against all synergies, returns list of active effect_keys."""
    # Count pieces by type
    counts: dict[PieceType, int] = {}
    all_mods: set[str] = set()
    for p in roster:
        if p.team == team:
            counts[p.piece_type] = counts.get(p.piece_type, 0) + 1
            for m in p.modifiers:
                all_mods.add(m.effect)

    active = []
    for syn in SYNERGIES:
        # Check required pieces (need 1+ of each)
        if not all(counts.get(pt, 0) >= 1 for pt in syn.required_pieces):
            continue

        # Check min_counts
        if not all(counts.get(pt, 0) >= n for pt, n in syn.min_counts.items()):
            continue

        # Check required_modifiers (any piece has at least one of these)
        if syn.required_modifiers:
            if not any(m in all_mods for m in syn.required_modifiers):
                continue

        active.append(syn.effect_key)

    return active


def get_synergy_display_data(active_keys: list[str]) -> list[dict]:
    """Returns serializable display data for active synergies."""
    result = []
    for syn in SYNERGIES:
        if syn.effect_key in active_keys:
            result.append({
                "name": syn.name,
                "description": syn.description,
                "icon": syn.icon,
                "color": list(syn.color),
                "effectKey": syn.effect_key,
            })
    return result
