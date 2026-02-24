"""Chess piece definitions, movement rules, and modifier system."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from board import Board


class PieceType(Enum):
    PAWN = "pawn"
    KNIGHT = "knight"
    BISHOP = "bishop"
    ROOK = "rook"
    QUEEN = "queen"
    KING = "king"
    BOMB = "bomb"
    MIMIC = "mimic"
    LEECH = "leech"
    SUMMONER = "summoner"
    GHOST = "ghost"
    GAMBLER = "gambler"
    ANCHOR_PIECE = "anchor_piece"
    PARASITE = "parasite"
    MIRROR_PIECE = "mirror_piece"
    VOID = "void"
    PHOENIX = "phoenix"
    KING_RAT = "king_rat"
    # --- Expansion pieces ---
    ASSASSIN = "assassin"
    BERSERKER_PIECE = "berserker_piece"
    CANNON = "cannon"
    LANCER = "lancer"
    DUELIST = "duelist"
    REAPER = "reaper"
    WYVERN = "wyvern"
    CHARGER = "charger"
    SENTINEL = "sentinel"
    HEALER = "healer"
    BARD = "bard"
    WALL = "wall"
    TOTEM = "totem"
    DECOY = "decoy"
    SHAPESHIFTER = "shapeshifter"
    TIME_MAGE = "time_mage"
    IMP = "imp"
    POLTERGEIST = "poltergeist"
    ALCHEMIST_PIECE = "alchemist_piece"
    GOLEM = "golem"
    WITCH = "witch"
    TRICKSTER = "trickster"


class Team(Enum):
    PLAYER = "player"
    ENEMY = "enemy"


# Display characters
PIECE_CHARS = {
    (PieceType.KING, Team.PLAYER): "\u2654",
    (PieceType.QUEEN, Team.PLAYER): "\u2655",
    (PieceType.ROOK, Team.PLAYER): "\u2656",
    (PieceType.BISHOP, Team.PLAYER): "\u2657",
    (PieceType.KNIGHT, Team.PLAYER): "\u2658",
    (PieceType.PAWN, Team.PLAYER): "\u2659",
    (PieceType.KING, Team.ENEMY): "\u265A",
    (PieceType.QUEEN, Team.ENEMY): "\u265B",
    (PieceType.ROOK, Team.ENEMY): "\u265C",
    (PieceType.BISHOP, Team.ENEMY): "\u265D",
    (PieceType.KNIGHT, Team.ENEMY): "\u265E",
    (PieceType.PAWN, Team.ENEMY): "\u265F",
    # New abstract pieces (same char for both teams)
    (PieceType.BOMB, Team.PLAYER): "\u2738",
    (PieceType.BOMB, Team.ENEMY): "\u2738",
    (PieceType.MIMIC, Team.PLAYER): "?",
    (PieceType.MIMIC, Team.ENEMY): "?",
    (PieceType.LEECH, Team.PLAYER): "\u2687",
    (PieceType.LEECH, Team.ENEMY): "\u2687",
    (PieceType.SUMMONER, Team.PLAYER): "\u2726",
    (PieceType.SUMMONER, Team.ENEMY): "\u2726",
    (PieceType.GHOST, Team.PLAYER): "\u2601",
    (PieceType.GHOST, Team.ENEMY): "\u2601",
    (PieceType.GAMBLER, Team.PLAYER): "\u2660",
    (PieceType.GAMBLER, Team.ENEMY): "\u2660",
    (PieceType.ANCHOR_PIECE, Team.PLAYER): "\u2693",
    (PieceType.ANCHOR_PIECE, Team.ENEMY): "\u2693",
    (PieceType.PARASITE, Team.PLAYER): "\u2623",
    (PieceType.PARASITE, Team.ENEMY): "\u2623",
    (PieceType.MIRROR_PIECE, Team.PLAYER): "\u25C8",
    (PieceType.MIRROR_PIECE, Team.ENEMY): "\u25C8",
    (PieceType.VOID, Team.PLAYER): "\u25C9",
    (PieceType.VOID, Team.ENEMY): "\u25C9",
    (PieceType.PHOENIX, Team.PLAYER): "\u2600",
    (PieceType.PHOENIX, Team.ENEMY): "\u2600",
    (PieceType.KING_RAT, Team.PLAYER): "\u2689",
    (PieceType.KING_RAT, Team.ENEMY): "\u2689",
    # --- Expansion pieces ---
    (PieceType.ASSASSIN, Team.PLAYER): "\u2620",
    (PieceType.ASSASSIN, Team.ENEMY): "\u2620",
    (PieceType.BERSERKER_PIECE, Team.PLAYER): "\u2694",
    (PieceType.BERSERKER_PIECE, Team.ENEMY): "\u2694",
    (PieceType.CANNON, Team.PLAYER): "\u25CE",
    (PieceType.CANNON, Team.ENEMY): "\u25CE",
    (PieceType.LANCER, Team.PLAYER): "\u2191",
    (PieceType.LANCER, Team.ENEMY): "\u2191",
    (PieceType.DUELIST, Team.PLAYER): "\u2694",
    (PieceType.DUELIST, Team.ENEMY): "\u2694",
    (PieceType.REAPER, Team.PLAYER): "\u2620",
    (PieceType.REAPER, Team.ENEMY): "\u2620",
    (PieceType.WYVERN, Team.PLAYER): "\u2682",
    (PieceType.WYVERN, Team.ENEMY): "\u2682",
    (PieceType.CHARGER, Team.PLAYER): "\u25B6",
    (PieceType.CHARGER, Team.ENEMY): "\u25B6",
    (PieceType.SENTINEL, Team.PLAYER): "\u2616",
    (PieceType.SENTINEL, Team.ENEMY): "\u2616",
    (PieceType.HEALER, Team.PLAYER): "\u2695",
    (PieceType.HEALER, Team.ENEMY): "\u2695",
    (PieceType.BARD, Team.PLAYER): "\u266A",
    (PieceType.BARD, Team.ENEMY): "\u266A",
    (PieceType.WALL, Team.PLAYER): "\u2588",
    (PieceType.WALL, Team.ENEMY): "\u2588",
    (PieceType.TOTEM, Team.PLAYER): "\u2641",
    (PieceType.TOTEM, Team.ENEMY): "\u2641",
    (PieceType.DECOY, Team.PLAYER): "\u2302",
    (PieceType.DECOY, Team.ENEMY): "\u2302",
    (PieceType.SHAPESHIFTER, Team.PLAYER): "\u221E",
    (PieceType.SHAPESHIFTER, Team.ENEMY): "\u221E",
    (PieceType.TIME_MAGE, Team.PLAYER): "\u231A",
    (PieceType.TIME_MAGE, Team.ENEMY): "\u231A",
    (PieceType.IMP, Team.PLAYER): "\u2666",
    (PieceType.IMP, Team.ENEMY): "\u2666",
    (PieceType.POLTERGEIST, Team.PLAYER): "\u2622",
    (PieceType.POLTERGEIST, Team.ENEMY): "\u2622",
    (PieceType.ALCHEMIST_PIECE, Team.PLAYER): "\u2697",
    (PieceType.ALCHEMIST_PIECE, Team.ENEMY): "\u2697",
    (PieceType.GOLEM, Team.PLAYER): "\u25A0",
    (PieceType.GOLEM, Team.ENEMY): "\u25A0",
    (PieceType.WITCH, Team.PLAYER): "\u2605",
    (PieceType.WITCH, Team.ENEMY): "\u2605",
    (PieceType.TRICKSTER, Team.PLAYER): "\u2740",
    (PieceType.TRICKSTER, Team.ENEMY): "\u2740",
}

# Fallback single-letter display
PIECE_LETTERS = {
    (PieceType.KING, Team.PLAYER): "K",
    (PieceType.QUEEN, Team.PLAYER): "Q",
    (PieceType.ROOK, Team.PLAYER): "R",
    (PieceType.BISHOP, Team.PLAYER): "B",
    (PieceType.KNIGHT, Team.PLAYER): "N",
    (PieceType.PAWN, Team.PLAYER): "P",
    (PieceType.KING, Team.ENEMY): "k",
    (PieceType.QUEEN, Team.ENEMY): "q",
    (PieceType.ROOK, Team.ENEMY): "r",
    (PieceType.BISHOP, Team.ENEMY): "b",
    (PieceType.KNIGHT, Team.ENEMY): "n",
    (PieceType.PAWN, Team.ENEMY): "p",
    (PieceType.BOMB, Team.PLAYER): "X", (PieceType.BOMB, Team.ENEMY): "x",
    (PieceType.MIMIC, Team.PLAYER): "M", (PieceType.MIMIC, Team.ENEMY): "m",
    (PieceType.LEECH, Team.PLAYER): "L", (PieceType.LEECH, Team.ENEMY): "l",
    (PieceType.SUMMONER, Team.PLAYER): "S", (PieceType.SUMMONER, Team.ENEMY): "s",
    (PieceType.GHOST, Team.PLAYER): "G", (PieceType.GHOST, Team.ENEMY): "g",
    (PieceType.GAMBLER, Team.PLAYER): "A", (PieceType.GAMBLER, Team.ENEMY): "a",
    (PieceType.ANCHOR_PIECE, Team.PLAYER): "C", (PieceType.ANCHOR_PIECE, Team.ENEMY): "c",
    (PieceType.PARASITE, Team.PLAYER): "T", (PieceType.PARASITE, Team.ENEMY): "t",
    (PieceType.MIRROR_PIECE, Team.PLAYER): "I", (PieceType.MIRROR_PIECE, Team.ENEMY): "i",
    (PieceType.VOID, Team.PLAYER): "V", (PieceType.VOID, Team.ENEMY): "v",
    (PieceType.PHOENIX, Team.PLAYER): "H", (PieceType.PHOENIX, Team.ENEMY): "h",
    (PieceType.KING_RAT, Team.PLAYER): "Z", (PieceType.KING_RAT, Team.ENEMY): "z",
    # --- Expansion pieces ---
    (PieceType.ASSASSIN, Team.PLAYER): "As", (PieceType.ASSASSIN, Team.ENEMY): "as",
    (PieceType.BERSERKER_PIECE, Team.PLAYER): "Bk", (PieceType.BERSERKER_PIECE, Team.ENEMY): "bk",
    (PieceType.CANNON, Team.PLAYER): "Cn", (PieceType.CANNON, Team.ENEMY): "cn",
    (PieceType.LANCER, Team.PLAYER): "Ln", (PieceType.LANCER, Team.ENEMY): "ln",
    (PieceType.DUELIST, Team.PLAYER): "Du", (PieceType.DUELIST, Team.ENEMY): "du",
    (PieceType.REAPER, Team.PLAYER): "Rp", (PieceType.REAPER, Team.ENEMY): "rp",
    (PieceType.WYVERN, Team.PLAYER): "Wy", (PieceType.WYVERN, Team.ENEMY): "wy",
    (PieceType.CHARGER, Team.PLAYER): "Ch", (PieceType.CHARGER, Team.ENEMY): "ch",
    (PieceType.SENTINEL, Team.PLAYER): "Sn", (PieceType.SENTINEL, Team.ENEMY): "sn",
    (PieceType.HEALER, Team.PLAYER): "He", (PieceType.HEALER, Team.ENEMY): "he",
    (PieceType.BARD, Team.PLAYER): "Bd", (PieceType.BARD, Team.ENEMY): "bd",
    (PieceType.WALL, Team.PLAYER): "Wl", (PieceType.WALL, Team.ENEMY): "wl",
    (PieceType.TOTEM, Team.PLAYER): "To", (PieceType.TOTEM, Team.ENEMY): "to",
    (PieceType.DECOY, Team.PLAYER): "Dc", (PieceType.DECOY, Team.ENEMY): "dc",
    (PieceType.SHAPESHIFTER, Team.PLAYER): "Sh", (PieceType.SHAPESHIFTER, Team.ENEMY): "sh",
    (PieceType.TIME_MAGE, Team.PLAYER): "Tm", (PieceType.TIME_MAGE, Team.ENEMY): "tm",
    (PieceType.IMP, Team.PLAYER): "Im", (PieceType.IMP, Team.ENEMY): "im",
    (PieceType.POLTERGEIST, Team.PLAYER): "Po", (PieceType.POLTERGEIST, Team.ENEMY): "po",
    (PieceType.ALCHEMIST_PIECE, Team.PLAYER): "Al", (PieceType.ALCHEMIST_PIECE, Team.ENEMY): "al",
    (PieceType.GOLEM, Team.PLAYER): "Go", (PieceType.GOLEM, Team.ENEMY): "go",
    (PieceType.WITCH, Team.PLAYER): "Wi", (PieceType.WITCH, Team.ENEMY): "wi",
    (PieceType.TRICKSTER, Team.PLAYER): "Tr", (PieceType.TRICKSTER, Team.ENEMY): "tr",
}

# Piece value for scoring/AI
PIECE_VALUES = {
    PieceType.PAWN: 1,
    PieceType.KNIGHT: 3,
    PieceType.BISHOP: 3,
    PieceType.ROOK: 5,
    PieceType.QUEEN: 9,
    PieceType.KING: 100,
    PieceType.BOMB: 2,
    PieceType.MIMIC: 3,
    PieceType.LEECH: 4,
    PieceType.SUMMONER: 5,
    PieceType.GHOST: 4,
    PieceType.GAMBLER: 3,
    PieceType.ANCHOR_PIECE: 4,
    PieceType.PARASITE: 3,
    PieceType.MIRROR_PIECE: 4,
    PieceType.VOID: 5,
    PieceType.PHOENIX: 5,
    PieceType.KING_RAT: 2,
    # --- Expansion pieces ---
    PieceType.ASSASSIN: 4,
    PieceType.BERSERKER_PIECE: 4,
    PieceType.CANNON: 4,
    PieceType.LANCER: 3,
    PieceType.DUELIST: 3,
    PieceType.REAPER: 4,
    PieceType.WYVERN: 4,
    PieceType.CHARGER: 3,
    PieceType.SENTINEL: 5,
    PieceType.HEALER: 3,
    PieceType.BARD: 3,
    PieceType.WALL: 3,
    PieceType.TOTEM: 3,
    PieceType.DECOY: 1,
    PieceType.SHAPESHIFTER: 3,
    PieceType.TIME_MAGE: 4,
    PieceType.IMP: 2,
    PieceType.POLTERGEIST: 2,
    PieceType.ALCHEMIST_PIECE: 3,
    PieceType.GOLEM: 5,
    PieceType.WITCH: 4,
    PieceType.TRICKSTER: 2,
}

# (max_hp, attack) per piece type
PIECE_STATS: dict[PieceType, tuple[int, int]] = {
    PieceType.PAWN: (4, 2), PieceType.KNIGHT: (7, 5), PieceType.BISHOP: (6, 3),
    PieceType.ROOK: (14, 4), PieceType.QUEEN: (14, 6), PieceType.KING: (20, 3),
    PieceType.BOMB: (1, 0), PieceType.MIMIC: (3, 1), PieceType.LEECH: (6, 2),
    PieceType.SUMMONER: (5, 0), PieceType.GHOST: (3, 3), PieceType.GAMBLER: (5, 12),
    PieceType.ANCHOR_PIECE: (20, 0), PieceType.PARASITE: (4, 0),
    PieceType.MIRROR_PIECE: (5, 3), PieceType.VOID: (8, 4),
    PieceType.PHOENIX: (6, 4), PieceType.KING_RAT: (4, 2),
    # --- Expansion pieces ---
    PieceType.ASSASSIN: (3, 8), PieceType.BERSERKER_PIECE: (10, 2),
    PieceType.CANNON: (8, 6), PieceType.LANCER: (5, 5),
    PieceType.DUELIST: (7, 4), PieceType.REAPER: (4, 3),
    PieceType.WYVERN: (6, 5), PieceType.CHARGER: (8, 3),
    PieceType.SENTINEL: (15, 1), PieceType.HEALER: (5, 0),
    PieceType.BARD: (4, 2), PieceType.WALL: (25, 0),
    PieceType.TOTEM: (8, 0), PieceType.DECOY: (1, 0),
    PieceType.SHAPESHIFTER: (5, 3), PieceType.TIME_MAGE: (4, 2),
    PieceType.IMP: (2, 1), PieceType.POLTERGEIST: (3, 2),
    PieceType.ALCHEMIST_PIECE: (5, 1), PieceType.GOLEM: (20, 7),
    PieceType.WITCH: (4, 0), PieceType.TRICKSTER: (3, 3),
}

# Player-facing descriptions for tooltips
PIECE_INFO: dict[PieceType, dict[str, str | None]] = {
    PieceType.PAWN: {
        "move": "Moves forward, captures diagonally",
        "ability": "Double move on first turn",
    },
    PieceType.KNIGHT: {
        "move": "Leaps in an L-shape",
        "ability": "Jumps over other pieces",
    },
    PieceType.BISHOP: {
        "move": "Slides diagonally",
        "ability": None,
    },
    PieceType.ROOK: {
        "move": "Slides in straight lines",
        "ability": None,
    },
    PieceType.QUEEN: {
        "move": "Slides in any direction",
        "ability": None,
    },
    PieceType.KING: {
        "move": "Moves one square any direction",
        "ability": None,
    },
    PieceType.BOMB: {
        "move": "Cannot move",
        "ability": "Explodes on death, damaging nearby pieces",
    },
    PieceType.MIMIC: {
        "move": "Moves one square any direction",
        "ability": "Transforms when damaged",
    },
    PieceType.LEECH: {
        "move": "Moves one square any direction",
        "ability": "Steals from enemies",
    },
    PieceType.SUMMONER: {
        "move": "Moves one square (empty cells only)",
        "ability": "Spawns pawns on empty cells",
    },
    PieceType.GHOST: {
        "move": "Slides in any direction",
        "ability": "Passes through all pieces",
    },
    PieceType.GAMBLER: {
        "move": "Teleports anywhere on the board",
        "ability": "High risk, high reward",
    },
    PieceType.ANCHOR_PIECE: {
        "move": "Cannot move",
        "ability": "Immovable wall",
    },
    PieceType.PARASITE: {
        "move": "Moves one square any direction",
        "ability": "Infests enemies",
    },
    PieceType.MIRROR_PIECE: {
        "move": "Moves one square any direction",
        "ability": "Reflects enemy effects",
    },
    PieceType.VOID: {
        "move": "Slides in any direction",
        "ability": "Warps the battlefield",
    },
    PieceType.PHOENIX: {
        "move": "Slides diagonally",
        "ability": "Revives after death",
    },
    PieceType.KING_RAT: {
        "move": "Range grows with more rats",
        "ability": "Swarm — more rats, more power",
    },
    # --- Expansion pieces ---
    PieceType.ASSASSIN: {
        "move": "Leaps in an L-shape",
        "ability": "Triple damage to full-HP targets. Dies after 3 captures.",
    },
    PieceType.BERSERKER_PIECE: {
        "move": "Moves one square any direction",
        "ability": "Gains +1 ATK each time it takes damage. ATK resets on kill.",
    },
    PieceType.CANNON: {
        "move": "Cannot move",
        "ability": "Attacks nearest enemy in any straight line (range 8).",
    },
    PieceType.LANCER: {
        "move": "Slides in straight lines",
        "ability": "Damage scales with distance moved: +1 per square.",
    },
    PieceType.DUELIST: {
        "move": "Moves one square any direction",
        "ability": "Both pieces deal ATK simultaneously. Survives if HP > 0.",
    },
    PieceType.REAPER: {
        "move": "Slides diagonally",
        "ability": "Executes enemies below 25% HP regardless of ATK.",
    },
    PieceType.WYVERN: {
        "move": "Knight L-shape + diagonal slide",
        "ability": "Ignores ground-based cell and border modifiers.",
    },
    PieceType.CHARGER: {
        "move": "Straight lines (min 2 squares)",
        "ability": "+2 ATK for each square moved.",
    },
    PieceType.SENTINEL: {
        "move": "Moves one square any direction",
        "ability": "Adjacent friendlies take 50% damage (Sentinel absorbs rest).",
    },
    PieceType.HEALER: {
        "move": "Slides diagonally",
        "ability": "Heals target friendly for 3 HP instead of attacking.",
    },
    PieceType.BARD: {
        "move": "Moves one square any direction",
        "ability": "Adjacent friendlies gain +2 ATK. Removed when Bard moves/dies.",
    },
    PieceType.WALL: {
        "move": "Cannot move",
        "ability": "Blocks all movement. Takes -3 from all sources.",
    },
    PieceType.TOTEM: {
        "move": "Cannot move",
        "ability": "Friendly pieces within 2 cells regenerate 1 HP/turn.",
    },
    PieceType.DECOY: {
        "move": "Cannot move",
        "ability": "Enemies prioritize Decoy. Spawns 2 Pawns on death.",
    },
    PieceType.SHAPESHIFTER: {
        "move": "Moves one square any direction",
        "ability": "Changes piece type each turn (cycles roster types).",
    },
    PieceType.TIME_MAGE: {
        "move": "Moves one square any direction",
        "ability": "On death, rewinds board state by 1 turn (one-time).",
    },
    PieceType.IMP: {
        "move": "Teleports to any empty cell",
        "ability": "After moving, swaps 2 random enemy positions.",
    },
    PieceType.POLTERGEIST: {
        "move": "Teleports to any empty cell",
        "ability": "On death, shuffles all remaining enemy positions.",
    },
    PieceType.ALCHEMIST_PIECE: {
        "move": "Moves one square any direction",
        "ability": "Converts current cell into a random cell modifier each turn.",
    },
    PieceType.GOLEM: {
        "move": "Moves one square any direction",
        "ability": "Loses 1 max HP permanently each turn. Cannot be healed.",
    },
    PieceType.WITCH: {
        "move": "Slides diagonally",
        "ability": "Curses target: -2 ATK and -2 HP/turn for 3 turns.",
    },
    PieceType.TRICKSTER: {
        "move": "Leaps in an L-shape",
        "ability": "After attacking, teleports to a random empty cell.",
    },
}


@dataclass
class Modifier:
    """A roguelike upgrade applied to a piece."""
    name: str
    description: str
    # Effect callbacks are checked by game logic
    effect: str  # e.g. "flaming", "armored", "swift", "piercing"


@dataclass
class Piece:
    """A chess piece with position and optional modifiers."""
    piece_type: PieceType
    team: Team
    x: int = 0
    y: int = 0
    modifiers: list[Modifier] = field(default_factory=list)
    has_moved: bool = False
    alive: bool = True
    cell_modifier: object | None = None  # CellModifier absorbed from a cell
    hp: int = 0
    max_hp: int = 0
    attack: int = 0
    ability_flags: dict = field(default_factory=dict)
    status_effects: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.hp == 0 and self.piece_type in PIECE_STATS:
            mhp, atk = PIECE_STATS[self.piece_type]
            self.hp = mhp
            self.max_hp = mhp
            self.attack = atk

    @property
    def char(self) -> str:
        return PIECE_LETTERS.get((self.piece_type, self.team), "?")

    @property
    def value(self) -> int:
        return PIECE_VALUES.get(self.piece_type, 0)

    def get_raw_moves(self, board_w: int, board_h: int) -> list[tuple[int, int]]:
        """Get all potential move destinations ignoring other pieces."""
        moves = []
        x, y = self.x, self.y

        if self.piece_type == PieceType.PAWN:
            direction = -1 if self.team == Team.PLAYER else 1
            # Forward move
            ny = y + direction
            if 0 <= ny < board_h:
                moves.append((x, ny))
            # Double move from starting position
            if not self.has_moved:
                ny2 = y + 2 * direction
                if 0 <= ny2 < board_h:
                    moves.append((x, ny2))
            # Diagonal captures
            for dx in [-1, 1]:
                nx = x + dx
                ny = y + direction
                if 0 <= nx < board_w and 0 <= ny < board_h:
                    moves.append((nx, ny))

        elif self.piece_type == PieceType.KNIGHT:
            for dx, dy in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < board_w and 0 <= ny < board_h:
                    moves.append((nx, ny))

        elif self.piece_type == PieceType.BISHOP:
            for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        elif self.piece_type == PieceType.ROOK:
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        elif self.piece_type == PieceType.QUEEN:
            for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        elif self.piece_type == PieceType.KING:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))

        # --- New abstract pieces ---
        elif self.piece_type in (PieceType.BOMB, PieceType.ANCHOR_PIECE, PieceType.PARASITE):
            pass  # Cannot move

        elif self.piece_type in (PieceType.MIMIC, PieceType.LEECH, PieceType.MIRROR_PIECE):
            # King-style: 1 square any direction
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))

        elif self.piece_type == PieceType.SUMMONER:
            # King-style but only empty cells (handled in get_valid_moves)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))

        elif self.piece_type == PieceType.GHOST:
            # Queen-style (passes through pieces — handled in get_valid_moves)
            for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        elif self.piece_type == PieceType.GAMBLER:
            # Anywhere on board
            for gx in range(board_w):
                for gy in range(board_h):
                    if gx != x or gy != y:
                        moves.append((gx, gy))

        elif self.piece_type == PieceType.PHOENIX:
            # Bishop-style
            for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        elif self.piece_type == PieceType.VOID:
            # Queen-style
            for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        elif self.piece_type == PieceType.KING_RAT:
            # King-style with extended range based on other living king rats
            # (range handled in get_valid_moves via board reference)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))

        # --- Expansion pieces ---

        # Immobile pieces
        elif self.piece_type in (PieceType.CANNON, PieceType.WALL, PieceType.TOTEM, PieceType.DECOY):
            pass  # Cannot move

        # Knight L-shape: Assassin, Trickster
        elif self.piece_type in (PieceType.ASSASSIN, PieceType.TRICKSTER):
            for dx, dy in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < board_w and 0 <= ny < board_h:
                    moves.append((nx, ny))

        # Wyvern: Knight L-shape + diagonal slide
        elif self.piece_type == PieceType.WYVERN:
            for dx, dy in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < board_w and 0 <= ny < board_h:
                    moves.append((nx, ny))
            for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        # Rook straight: Lancer, Charger
        elif self.piece_type in (PieceType.LANCER, PieceType.CHARGER):
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        # Bishop diagonal: Healer, Witch, Reaper
        elif self.piece_type in (PieceType.HEALER, PieceType.WITCH, PieceType.REAPER):
            for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                for dist in range(1, max(board_w, board_h)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))
                    else:
                        break

        # Queen-style: Golem
        elif self.piece_type == PieceType.GOLEM:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))

        # Teleport anywhere: Imp, Poltergeist
        elif self.piece_type in (PieceType.IMP, PieceType.POLTERGEIST):
            for gx in range(board_w):
                for gy in range(board_h):
                    if gx != x or gy != y:
                        moves.append((gx, gy))

        # King-style (1 square any): Berserker, Sentinel, Bard, Alchemist, Shapeshifter, Time Mage, Duelist
        elif self.piece_type in (
            PieceType.BERSERKER_PIECE, PieceType.SENTINEL, PieceType.BARD,
            PieceType.ALCHEMIST_PIECE, PieceType.SHAPESHIFTER, PieceType.TIME_MAGE,
            PieceType.DUELIST,
        ):
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < board_w and 0 <= ny < board_h:
                        moves.append((nx, ny))

        return moves

    def get_valid_moves(self, board: Board) -> list[tuple[int, int]]:
        """Get valid moves considering the board state."""
        valid = []
        x, y = self.x, self.y

        if self.piece_type == PieceType.PAWN:
            direction = -1 if self.team == Team.PLAYER else 1
            # Forward (must be empty)
            ny = y + direction
            if board.in_bounds(x, ny):
                if board.is_empty(x, ny):
                    valid.append((x, ny))
                    # Double move
                    if not self.has_moved:
                        ny2 = y + 2 * direction
                        if board.in_bounds(x, ny2) and board.is_empty(x, ny2):
                            valid.append((x, ny2))
            # Diagonal captures (must have enemy)
            for dx in [-1, 1]:
                nx = x + dx
                ny = y + direction
                if board.in_bounds(nx, ny):
                    target = board.get_piece_at(nx, ny)
                    if target and target.team != self.team:
                        valid.append((nx, ny))

        elif self.piece_type == PieceType.KNIGHT:
            for dx, dy in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                nx, ny = x + dx, y + dy
                if board.in_bounds(nx, ny) and not board.is_blocked(nx, ny):
                    target = board.get_piece_at(nx, ny)
                    if not target or target.team != self.team:
                        valid.append((nx, ny))

        elif self.piece_type in (PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN):
            dirs = []
            if self.piece_type in (PieceType.BISHOP, PieceType.QUEEN):
                dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
            if self.piece_type in (PieceType.ROOK, PieceType.QUEEN):
                dirs += [(-1,0),(1,0),(0,-1),(0,1)]
            has_piercing = any(m.effect == "piercing" for m in self.modifiers)
            has_phase = (self.cell_modifier and self.cell_modifier.effect == "phase")
            has_ethereal = (any(m.effect == "ethereal" for m in self.modifiers)
                            or (self.team == Team.PLAYER and hasattr(board, 'master_effects')
                                and "phantom_passive" in board.master_effects))
            for dx, dy in dirs:
                skipped = False
                for dist in range(1, max(board.width, board.height)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if not board.in_bounds(nx, ny):
                        break
                    if board.is_blocked(nx, ny):
                        break
                    target = board.get_piece_at(nx, ny)
                    if target:
                        if has_ethereal:
                            # Ethereal: pass through all pieces, can capture enemies
                            if target.team != self.team:
                                valid.append((nx, ny))
                            continue
                        if target.team == self.team:
                            # Phase: can pass through friendly pieces
                            if has_phase:
                                continue
                            # Piercing: skip one blocker (friend or foe)
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                        else:
                            valid.append((nx, ny))
                            # Piercing: can skip one blocker and still capture behind
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                    valid.append((nx, ny))

        elif self.piece_type == PieceType.KING:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if board.in_bounds(nx, ny) and not board.is_blocked(nx, ny):
                        target = board.get_piece_at(nx, ny)
                        if not target or target.team != self.team:
                            valid.append((nx, ny))

        # --- New abstract pieces ---
        elif self.piece_type in (PieceType.BOMB, PieceType.ANCHOR_PIECE, PieceType.PARASITE):
            pass  # Cannot move

        elif self.piece_type in (PieceType.MIMIC, PieceType.LEECH, PieceType.MIRROR_PIECE):
            # King-style: 1 square any direction
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if board.in_bounds(nx, ny) and not board.is_blocked(nx, ny):
                        target = board.get_piece_at(nx, ny)
                        if not target or target.team != self.team:
                            valid.append((nx, ny))

        elif self.piece_type == PieceType.SUMMONER:
            # King-style but only empty cells (cannot attack)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if board.in_bounds(nx, ny) and board.is_empty(nx, ny):
                        valid.append((nx, ny))

        elif self.piece_type == PieceType.GHOST:
            # Queen-style but passes through ALL pieces
            for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                for dist in range(1, max(board.width, board.height)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if not board.in_bounds(nx, ny):
                        break
                    if board.is_blocked(nx, ny):
                        break
                    target = board.get_piece_at(nx, ny)
                    if target:
                        if target.team != self.team:
                            valid.append((nx, ny))
                        # Ghost passes through all pieces — don't break
                        continue
                    valid.append((nx, ny))

        elif self.piece_type == PieceType.GAMBLER:
            # Anywhere on board (that's empty or has enemy)
            for gx in range(board.width):
                for gy in range(board.height):
                    if gx == x and gy == y:
                        continue
                    if not board.in_bounds(gx, gy) or board.is_blocked(gx, gy):
                        continue
                    target = board.get_piece_at(gx, gy)
                    if not target or target.team != self.team:
                        valid.append((gx, gy))

        elif self.piece_type == PieceType.PHOENIX:
            # Bishop-style (standard sliding with blocking)
            has_ethereal = (any(m.effect == "ethereal" for m in self.modifiers)
                            or (self.team == Team.PLAYER and hasattr(board, 'master_effects')
                                and "phantom_passive" in board.master_effects))
            for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                has_piercing = any(m.effect == "piercing" for m in self.modifiers)
                skipped = False
                for dist in range(1, max(board.width, board.height)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if not board.in_bounds(nx, ny):
                        break
                    if board.is_blocked(nx, ny):
                        break
                    target = board.get_piece_at(nx, ny)
                    if target:
                        if has_ethereal:
                            if target.team != self.team:
                                valid.append((nx, ny))
                            continue
                        if target.team == self.team:
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                        else:
                            valid.append((nx, ny))
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                    valid.append((nx, ny))

        elif self.piece_type == PieceType.VOID:
            # Queen-style (standard sliding)
            has_ethereal = (any(m.effect == "ethereal" for m in self.modifiers)
                            or (self.team == Team.PLAYER and hasattr(board, 'master_effects')
                                and "phantom_passive" in board.master_effects))
            for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
                has_piercing = any(m.effect == "piercing" for m in self.modifiers)
                skipped = False
                for dist in range(1, max(board.width, board.height)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if not board.in_bounds(nx, ny):
                        break
                    if board.is_blocked(nx, ny):
                        break
                    target = board.get_piece_at(nx, ny)
                    if target:
                        if has_ethereal:
                            if target.team != self.team:
                                valid.append((nx, ny))
                            continue
                        if target.team == self.team:
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                        else:
                            valid.append((nx, ny))
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                    valid.append((nx, ny))

        elif self.piece_type == PieceType.KING_RAT:
            # King-style with range = 1 + other_living_king_rats
            other_rats = sum(
                1 for p in board.get_team_pieces(self.team)
                if p.piece_type == PieceType.KING_RAT and p is not self
            )
            move_range = 1 + other_rats
            for dx in range(-move_range, move_range + 1):
                for dy in range(-move_range, move_range + 1):
                    if dx == 0 and dy == 0:
                        continue
                    if abs(dx) > move_range or abs(dy) > move_range:
                        continue
                    nx, ny = x + dx, y + dy
                    if board.in_bounds(nx, ny) and not board.is_blocked(nx, ny):
                        target = board.get_piece_at(nx, ny)
                        if not target or target.team != self.team:
                            valid.append((nx, ny))

        # --- Expansion pieces ---

        # Immobile pieces
        elif self.piece_type in (PieceType.CANNON, PieceType.WALL, PieceType.TOTEM, PieceType.DECOY):
            pass  # Cannot move

        # Knight L-shape: Assassin, Trickster
        elif self.piece_type in (PieceType.ASSASSIN, PieceType.TRICKSTER):
            for dx, dy in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                nx, ny = x + dx, y + dy
                if board.in_bounds(nx, ny) and not board.is_blocked(nx, ny):
                    target = board.get_piece_at(nx, ny)
                    if not target or target.team != self.team:
                        valid.append((nx, ny))

        # Wyvern: Knight L-shape + diagonal slide
        elif self.piece_type == PieceType.WYVERN:
            has_ethereal = (any(m.effect == "ethereal" for m in self.modifiers)
                            or (self.team == Team.PLAYER and hasattr(board, 'master_effects')
                                and "phantom_passive" in board.master_effects))
            for dx, dy in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
                nx, ny = x + dx, y + dy
                if board.in_bounds(nx, ny) and not board.is_blocked(nx, ny):
                    target = board.get_piece_at(nx, ny)
                    if not target or target.team != self.team:
                        valid.append((nx, ny))
            # Diagonal slide
            for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                for dist in range(1, max(board.width, board.height)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if not board.in_bounds(nx, ny) or board.is_blocked(nx, ny):
                        break
                    target = board.get_piece_at(nx, ny)
                    if target:
                        if has_ethereal:
                            if target.team != self.team:
                                valid.append((nx, ny))
                            continue
                        if target.team != self.team:
                            valid.append((nx, ny))
                        break
                    valid.append((nx, ny))

        # Rook-style sliders: Lancer, Charger
        elif self.piece_type in (PieceType.LANCER, PieceType.CHARGER):
            has_piercing = any(m.effect == "piercing" for m in self.modifiers)
            has_ethereal = (any(m.effect == "ethereal" for m in self.modifiers)
                            or (self.team == Team.PLAYER and hasattr(board, 'master_effects')
                                and "phantom_passive" in board.master_effects))
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                skipped = False
                for dist in range(1, max(board.width, board.height)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if not board.in_bounds(nx, ny) or board.is_blocked(nx, ny):
                        break
                    # Charger: must move at least 2 squares
                    if self.piece_type == PieceType.CHARGER and dist < 2:
                        target = board.get_piece_at(nx, ny)
                        if target:
                            if has_ethereal:
                                continue
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                        continue  # skip distance 1, don't add to valid
                    target = board.get_piece_at(nx, ny)
                    if target:
                        if has_ethereal:
                            if target.team != self.team:
                                valid.append((nx, ny))
                            continue
                        if target.team == self.team:
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                        else:
                            valid.append((nx, ny))
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                    valid.append((nx, ny))

        # Bishop-style sliders: Healer, Witch, Reaper
        elif self.piece_type in (PieceType.HEALER, PieceType.WITCH, PieceType.REAPER):
            has_piercing = any(m.effect == "piercing" for m in self.modifiers)
            has_ethereal = (any(m.effect == "ethereal" for m in self.modifiers)
                            or (self.team == Team.PLAYER and hasattr(board, 'master_effects')
                                and "phantom_passive" in board.master_effects))
            for dx, dy in [(-1,-1),(-1,1),(1,-1),(1,1)]:
                skipped = False
                for dist in range(1, max(board.width, board.height)):
                    nx, ny = x + dx * dist, y + dy * dist
                    if not board.in_bounds(nx, ny) or board.is_blocked(nx, ny):
                        break
                    target = board.get_piece_at(nx, ny)
                    if target:
                        if has_ethereal:
                            if target.team != self.team:
                                valid.append((nx, ny))
                            elif self.piece_type == PieceType.HEALER:
                                valid.append((nx, ny))
                            continue
                        if target.team == self.team:
                            # Healer can target friendlies
                            if self.piece_type == PieceType.HEALER:
                                valid.append((nx, ny))
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                        else:
                            valid.append((nx, ny))
                            if has_piercing and not skipped:
                                skipped = True
                                continue
                            break
                    valid.append((nx, ny))

        # King-style: Golem, Berserker, Sentinel, Bard, Alchemist, Shapeshifter, Time Mage, Duelist
        elif self.piece_type in (
            PieceType.GOLEM, PieceType.BERSERKER_PIECE, PieceType.SENTINEL,
            PieceType.BARD, PieceType.ALCHEMIST_PIECE, PieceType.SHAPESHIFTER,
            PieceType.TIME_MAGE, PieceType.DUELIST,
        ):
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if board.in_bounds(nx, ny) and not board.is_blocked(nx, ny):
                        target = board.get_piece_at(nx, ny)
                        if not target or target.team != self.team:
                            valid.append((nx, ny))

        # Teleport anywhere: Imp (empty cells only), Poltergeist (empty cells only)
        elif self.piece_type in (PieceType.IMP, PieceType.POLTERGEIST):
            for gx in range(board.width):
                for gy in range(board.height):
                    if gx == x and gy == y:
                        continue
                    if not board.in_bounds(gx, gy) or board.is_blocked(gx, gy):
                        continue
                    if board.is_empty(gx, gy):
                        valid.append((gx, gy))

        # Ethereal modifier: allow passing through all pieces (re-calculate for sliders)
        # This is handled by the ghost-style logic if the piece has ethereal
        # For now, the standard movement already handles most cases via piercing/phase

        # Swift modifier: king-style moves in addition to normal moves
        has_extra_move = any(m.effect == "swift" for m in self.modifiers)
        # Haste cell modifier: same as swift but temporary
        if self.cell_modifier and self.cell_modifier.effect == "haste":
            has_extra_move = True
        if has_extra_move:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x + dx, y + dy
                    if board.in_bounds(nx, ny) and not board.is_blocked(nx, ny):
                        target = board.get_piece_at(nx, ny)
                        if not target or target.team != self.team:
                            if (nx, ny) not in valid:
                                valid.append((nx, ny))

        # Warden drawback: max 2 square movement range
        if (self.team == Team.PLAYER and hasattr(board, 'master_effects')
                and "warden_drawback" in board.master_effects):
            valid = [(mx, my) for mx, my in valid
                     if abs(mx - x) <= 2 and abs(my - y) <= 2]

        # Speed gate border modifier: +2 extra range (king-style moves at range 2)
        if hasattr(board, 'border_modifiers') and (x, y) in board.border_modifiers:
            if board.border_modifiers[(x, y)].effect == "speed_gate":
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if board.in_bounds(nx, ny) and not board.is_blocked(nx, ny):
                            target = board.get_piece_at(nx, ny)
                            if not target or target.team != self.team:
                                if (nx, ny) not in valid:
                                    valid.append((nx, ny))

        return valid

    def get_capture_moves(self, board: Board) -> list[tuple[int, int]]:
        """Get only moves that result in a capture."""
        return [
            (mx, my) for mx, my in self.get_valid_moves(board)
            if board.get_piece_at(mx, my) and board.get_piece_at(mx, my).team != self.team
        ]

    def copy(self) -> Piece:
        p = Piece(
            piece_type=self.piece_type,
            team=self.team,
            x=self.x,
            y=self.y,
            modifiers=list(self.modifiers),
            has_moved=self.has_moved,
            alive=self.alive,
            hp=self.hp,
            max_hp=self.max_hp,
            attack=self.attack,
            ability_flags=dict(self.ability_flags),
            status_effects=[dict(se) for se in self.status_effects],
        )
        if self.cell_modifier and hasattr(self.cell_modifier, 'copy'):
            p.cell_modifier = self.cell_modifier.copy()
        else:
            p.cell_modifier = self.cell_modifier
        return p


# Predefined modifiers
MODIFIERS = {
    "flaming": Modifier("Flaming", "On kill, deal 2 splash damage to adjacent enemies", "flaming"),
    "armored": Modifier("Armored", "-2 incoming damage (persistent)", "armored"),
    "swift": Modifier("Swift", "Can also move one square in any direction", "swift"),
    "piercing": Modifier("Piercing", "Sliding pieces can attack through one piece", "piercing"),
    "royal": Modifier("Royal", "Worth double points when scoring", "royal"),
    # --- Expansion modifiers ---
    "vampiric": Modifier("Vampiric", "On capture, heals for 50% of damage dealt", "vampiric"),
    "explosive": Modifier("Explosive", "On death, deals 5 damage in 3x3", "explosive"),
    "frozen": Modifier("Frozen", "Attacks apply Chill: target skips next move", "frozen"),
    "toxic": Modifier("Toxic", "On hit, applies 1 poison/turn for 3 turns", "toxic"),
    "ethereal": Modifier("Ethereal", "Can move through all pieces", "ethereal"),
    "thorned": Modifier("Thorned", "Attackers take 3 retaliation damage", "thorned"),
    "lucky": Modifier("Lucky", "20% chance to dodge attacks", "lucky"),
    "magnetic": Modifier("Magnetic", "Pulls nearest enemy 1 cell closer at turn start", "magnetic"),
    "splitting": Modifier("Splitting", "On death, spawns 2 Pawns with this piece's mods", "splitting"),
    "reflective": Modifier("Reflective", "30% of damage taken is reflected to attacker", "reflective"),
    "gilded": Modifier("Gilded", "Earn +1 gold per capture with this piece", "gilded"),
    "titan": Modifier("Titan", "+5 HP, +2 ATK, but moves every other turn", "titan"),
    "unstable": Modifier("Unstable", "+4 ATK but takes 1 self-damage per turn", "unstable"),
    "haunted": Modifier("Haunted", "On death, becomes Ghost at 50% HP for 2 turns", "haunted"),
    "blazing": Modifier("Blazing", "Leaves fire trail: 1 damage to enemies entering", "blazing"),
}
