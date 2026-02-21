"""Cell and border modifier definitions for the three-layer modifier system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from board import Board
    from pieces import Piece


# --- Piece modifier colors & animations ---

PIECE_MODIFIER_VISUALS: dict[str, dict] = {
    "flaming": {"color": (255, 100, 30), "animation": "pulse"},
    "armored": {"color": (180, 180, 200), "animation": "slow_pulse"},
    "swift": {"color": (60, 200, 255), "animation": "shimmer"},
    "piercing": {"color": (180, 60, 255), "animation": "shimmer"},
    "royal": {"color": (255, 215, 0), "animation": "pulse"},
}


# --- Layer 2: Cell Modifiers ---

@dataclass
class CellModifier:
    """A modifier placed on a board cell that transfers to pieces on contact."""
    name: str
    effect: str
    color: tuple[int, int, int]
    overlay_alpha: float
    origin_x: int = 0
    origin_y: int = 0

    def copy(self) -> CellModifier:
        return CellModifier(
            name=self.name, effect=self.effect, color=self.color,
            overlay_alpha=self.overlay_alpha,
            origin_x=self.origin_x, origin_y=self.origin_y,
        )


CELL_MODIFIERS: dict[str, dict] = {
    "rage": {
        "name": "Rage",
        "effect": "rage",
        "color": (255, 50, 50),
        "overlay_alpha": 0.3,
        "icon": "!",
        "description": "Captures also kill one random adjacent enemy",
    },
    "shield": {
        "name": "Shield",
        "effect": "shield",
        "color": (50, 120, 255),
        "overlay_alpha": 0.3,
        "icon": "+",
        "description": "Survives one capture this round",
    },
    "haste": {
        "name": "Haste",
        "effect": "haste",
        "color": (255, 220, 50),
        "overlay_alpha": 0.3,
        "icon": ">",
        "description": "+1 square movement any direction",
    },
    "phase": {
        "name": "Phase",
        "effect": "phase",
        "color": (180, 50, 255),
        "overlay_alpha": 0.3,
        "icon": "~",
        "description": "Can move through friendly pieces",
    },
}


# --- Layer 3: Border Modifiers ---

@dataclass
class BorderModifier:
    """A modifier placed on a board cell that affects pieces while standing on it."""
    name: str
    effect: str
    border_color: tuple[int, int, int]
    x: int = 0
    y: int = 0

    def copy(self) -> BorderModifier:
        return BorderModifier(
            name=self.name, effect=self.effect,
            border_color=self.border_color, x=self.x, y=self.y,
        )


BORDER_MODIFIERS: dict[str, dict] = {
    "fortified": {
        "name": "Fortified",
        "effect": "fortified",
        "border_color": (255, 200, 50),
        "description": "Piece on this cell cannot be captured",
    },
    "thorns": {
        "name": "Thorns",
        "effect": "thorns",
        "border_color": (200, 50, 50),
        "description": "If piece here is captured, attacker also dies",
    },
    "anchor": {
        "name": "Anchor",
        "effect": "anchor",
        "border_color": (50, 200, 120),
        "description": "Piece can't be moved by enemy effects",
    },
}


def make_cell_modifier(key: str, x: int, y: int) -> CellModifier:
    """Create a CellModifier from registry template and place it at (x, y)."""
    t = CELL_MODIFIERS[key]
    return CellModifier(
        name=t["name"], effect=t["effect"], color=t["color"],
        overlay_alpha=t["overlay_alpha"], origin_x=x, origin_y=y,
    )


def make_border_modifier(key: str, x: int, y: int) -> BorderModifier:
    """Create a BorderModifier from registry template and place it at (x, y)."""
    t = BORDER_MODIFIERS[key]
    return BorderModifier(
        name=t["name"], effect=t["effect"],
        border_color=t["border_color"], x=x, y=y,
    )


def apply_cell_modifier(piece: Piece, cell_mod: CellModifier) -> None:
    """Transfer a cell modifier onto a piece."""
    piece.cell_modifier = cell_mod.copy()


def reset_cell_modifiers(
    board: Board,
    cell_mods: dict[tuple[int, int], CellModifier],
) -> None:
    """Return all cell modifiers to their original cells, strip from pieces."""
    # Collect absorbed cell mods from pieces before stripping
    all_mods: list[CellModifier] = list(cell_mods.values())
    for p in board.pieces:
        if p.cell_modifier is not None:
            all_mods.append(p.cell_modifier)
            p.cell_modifier = None

    # Restore all cell mods to their origin positions
    cell_mods.clear()
    for cm in all_mods:
        cell_mods[(cm.origin_x, cm.origin_y)] = cm
