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
        "description": "On kill, deal 2 damage to random adjacent enemy",
    },
    "shield": {
        "name": "Shield",
        "effect": "shield",
        "color": (50, 120, 255),
        "overlay_alpha": 0.3,
        "icon": "+",
        "description": "-3 incoming damage (consumed on hit)",
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
        "description": "Piece on this cell cannot be attacked",
    },
    "thorns": {
        "name": "Thorns",
        "effect": "thorns",
        "border_color": (200, 50, 50),
        "description": "Attacker takes 2 retaliation damage",
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


# --- Layer 4: Tarot Cards (run-long build-defining passives) ---

TAROT_CARDS: dict[str, dict] = {
    "the_flame": {
        "name": "The Flame",
        "effect": "the_flame",
        "cost": 12,
        "color": (255, 100, 30),
        "icon": "\u2668",  # hot springs / flame
        "description": "All pieces gain flaming. Splash hits in a cross pattern.",
    },
    "the_fortress": {
        "name": "The Fortress",
        "effect": "the_fortress",
        "cost": 12,
        "color": (180, 180, 200),
        "icon": "\u2656",  # rook
        "description": "All pieces gain armored. Pieces can't move more than 2 squares.",
    },
    "the_phantom": {
        "name": "The Phantom",
        "effect": "the_phantom",
        "cost": 10,
        "color": (180, 50, 255),
        "icon": "\u2623",  # phantom
        "description": "Pieces can move through enemies. Captures happen by passing through.",
    },
    "the_tide": {
        "name": "The Tide",
        "effect": "the_tide",
        "cost": 10,
        "color": (50, 150, 255),
        "icon": "\u224b",  # waves
        "description": "Each turn, all pieces shift 1 square toward the nearest enemy.",
    },
    "the_merchant": {
        "name": "The Merchant",
        "effect": "the_merchant",
        "cost": 8,
        "color": (255, 215, 0),
        "icon": "$",
        "description": "Shop has 2 extra items, costs -2g. +3 gold per wave.",
    },
    "the_necromancer": {
        "name": "The Necromancer",
        "effect": "the_necromancer",
        "cost": 12,
        "color": (100, 200, 100),
        "icon": "\u2620",  # skull
        "description": "Dead roster pieces return as ghosts for 1 turn after 2 turns.",
    },
    "the_jester": {
        "name": "The Jester",
        "effect": "the_jester",
        "cost": 10,
        "color": (255, 100, 200),
        "icon": "\u2663",  # club
        "description": "Every modifier effect is randomized each wave. Chaos run.",
    },
    "the_tactician": {
        "name": "The Tactician",
        "effect": "the_tactician",
        "cost": 11,
        "color": (60, 200, 255),
        "icon": "\u2694",  # crossed swords
        "description": "Move 2 pieces per turn instead of 1.",
    },
    "the_mirror": {
        "name": "The Mirror",
        "effect": "the_mirror",
        "cost": 10,
        "color": (200, 200, 220),
        "icon": "\u25c7",  # diamond
        "description": "Your roster copies enemy piece types each wave. Keep your modifiers.",
    },
    "the_pawn": {
        "name": "The Pawn",
        "effect": "the_pawn",
        "cost": 8,
        "color": (220, 180, 120),
        "icon": "\u2659",  # pawn
        "description": "Start each wave with 3 extra pawns. Pawns that capture promote.",
    },
    "the_executioner": {
        "name": "The Executioner",
        "effect": "the_executioner",
        "cost": 11,
        "color": (200, 50, 50),
        "icon": "\u2620",  # skull
        "description": "First capture each turn ignores armor, fortified, and all defenses.",
    },
    "the_shepherd": {
        "name": "The Shepherd",
        "effect": "the_shepherd",
        "cost": 10,
        "color": (150, 220, 150),
        "icon": "\u2618",  # shamrock
        "description": "Adjacent friendly pieces can't be captured. Rewards tight formations.",
    },
}


# --- Layer 5: Artifacts (stackable run-long passives) ---

ARTIFACTS: dict[str, dict] = {
    "gold_tooth": {
        "name": "Gold Tooth",
        "effect": "gold_tooth",
        "cost": 8,
        "rarity": "common",
        "color": (255, 215, 0),
        "icon": "$",
        "description": "+2 gold per wave won",
    },
    "war_drum": {
        "name": "War Drum",
        "effect": "war_drum",
        "cost": 8,
        "rarity": "common",
        "color": (200, 100, 50),
        "icon": "!",
        "description": "All pieces get +1 move range on first turn",
    },
    "iron_crown": {
        "name": "Iron Crown",
        "effect": "iron_crown",
        "cost": 10,
        "rarity": "common",
        "color": (255, 215, 0),
        "icon": "\u2654",
        "description": "Royal pieces earn 3x instead of 2x",
    },
    "lucky_coin": {
        "name": "Lucky Coin",
        "effect": "lucky_coin",
        "cost": 8,
        "rarity": "common",
        "color": (255, 220, 100),
        "icon": "\u25cb",
        "description": "Shop offers +1 extra item each time",
    },
    "blood_pact": {
        "name": "Blood Pact",
        "effect": "blood_pact",
        "cost": 10,
        "rarity": "uncommon",
        "color": (180, 30, 30),
        "icon": "\u2665",
        "description": "Each capture heals a random dead roster piece",
    },
    "mirror_shard": {
        "name": "Mirror Shard",
        "effect": "mirror_shard",
        "cost": 10,
        "rarity": "uncommon",
        "color": (200, 200, 220),
        "icon": "\u25c7",
        "description": "25% chance to steal enemy modifier on capture",
    },
    "chaos_orb": {
        "name": "Chaos Orb",
        "effect": "chaos_orb",
        "cost": 10,
        "rarity": "uncommon",
        "color": (255, 100, 200),
        "icon": "\u2739",
        "description": "One random enemy switches sides at wave start",
    },
    "anchor_chain": {
        "name": "Anchor Chain",
        "effect": "anchor_chain",
        "cost": 10,
        "rarity": "uncommon",
        "color": (100, 150, 200),
        "icon": "\u2693",
        "description": "First piece to die each wave survives instead",
    },
    "whetstone": {
        "name": "Whetstone",
        "effect": "whetstone",
        "cost": 10,
        "rarity": "uncommon",
        "color": (180, 180, 200),
        "icon": "\u2726",
        "description": "All modifier effects enhanced (+1 range/damage)",
    },
    "forge_hammer": {
        "name": "Forge Hammer",
        "effect": "forge_hammer",
        "cost": 12,
        "rarity": "rare",
        "color": (255, 140, 50),
        "icon": "\u2692",
        "description": "Pieces can hold 2 modifiers instead of 1",
    },
    "pandemonium": {
        "name": "Pandemonium",
        "effect": "pandemonium",
        "cost": 12,
        "rarity": "rare",
        "color": (180, 50, 255),
        "icon": "\u2604",
        "description": "Random cell modifier spawns on the board each wave",
    },
    "necrotome": {
        "name": "Necrotome",
        "effect": "necrotome",
        "cost": 14,
        "rarity": "rare",
        "color": (100, 200, 100),
        "icon": "\u2620",
        "description": "Dead pieces get one ghost turn before dying permanently",
    },
    "heretics_tome": {
        "name": "Heretic's Tome",
        "effect": "heretics_tome",
        "cost": 12,
        "rarity": "rare",
        "color": (200, 50, 200),
        "icon": "\u2622",
        "description": "+1 Tarot card slot for this run",
    },
    "crown_jewel": {
        "name": "Crown Jewel",
        "effect": "crown_jewel",
        "cost": 14,
        "rarity": "rare",
        "color": (255, 215, 0),
        "icon": "\u2666",
        "description": "Earn +1 ELO per wave won during the run",
    },
}


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
