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
    # --- Expansion modifiers ---
    "vampiric": {"color": (180, 30, 30), "animation": "pulse"},
    "explosive": {"color": (255, 80, 0), "animation": "pulse"},
    "frozen": {"color": (100, 200, 255), "animation": "slow_pulse"},
    "toxic": {"color": (80, 200, 50), "animation": "shimmer"},
    "ethereal": {"color": (200, 200, 255), "animation": "shimmer"},
    "thorned": {"color": (200, 50, 50), "animation": "slow_pulse"},
    "lucky": {"color": (255, 220, 100), "animation": "shimmer"},
    "magnetic": {"color": (150, 100, 255), "animation": "pulse"},
    "splitting": {"color": (200, 150, 50), "animation": "pulse"},
    "reflective": {"color": (220, 220, 240), "animation": "shimmer"},
    "gilded": {"color": (255, 200, 50), "animation": "pulse"},
    "titan": {"color": (160, 100, 50), "animation": "slow_pulse"},
    "unstable": {"color": (255, 50, 50), "animation": "pulse"},
    "haunted": {"color": (100, 50, 200), "animation": "shimmer"},
    "blazing": {"color": (255, 150, 30), "animation": "pulse"},
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
    # --- Expansion cell modifiers ---
    "inferno": {
        "name": "Inferno",
        "effect": "inferno",
        "color": (255, 140, 30),
        "overlay_alpha": 0.35,
        "icon": "F",
        "description": "Piece gains +3 ATK but takes 1 damage/turn",
    },
    "sanctuary": {
        "name": "Sanctuary",
        "effect": "sanctuary",
        "color": (240, 240, 255),
        "overlay_alpha": 0.3,
        "icon": "+",
        "description": "Piece heals 2 HP per turn",
    },
    "quicksand": {
        "name": "Quicksand",
        "effect": "quicksand",
        "color": (160, 120, 60),
        "overlay_alpha": 0.35,
        "icon": "Q",
        "description": "Piece cannot move (stuck for 1 turn)",
    },
    "vortex": {
        "name": "Vortex",
        "effect": "vortex",
        "color": (150, 50, 200),
        "overlay_alpha": 0.35,
        "icon": "@",
        "description": "Pulls all adjacent pieces 1 cell toward center at turn start",
    },
    "gold_mine": {
        "name": "Gold Mine",
        "effect": "gold_mine",
        "color": (255, 215, 0),
        "overlay_alpha": 0.3,
        "icon": "$",
        "description": "Piece standing here earns +1 gold per turn survived",
    },
    "mirror_cell": {
        "name": "Mirror Cell",
        "effect": "mirror_cell",
        "color": (100, 220, 255),
        "overlay_alpha": 0.3,
        "icon": "M",
        "description": "Piece creates a 1HP mirror image on opposite cell",
    },
    "curse": {
        "name": "Curse",
        "effect": "curse",
        "color": (150, 30, 30),
        "overlay_alpha": 0.35,
        "icon": "X",
        "description": "Enemy piece takes 2 damage/turn and has -2 ATK",
    },
    "amplifier": {
        "name": "Amplifier",
        "effect": "amplifier",
        "color": (200, 50, 255),
        "overlay_alpha": 0.35,
        "icon": "A",
        "description": "Piece modifier effects on this cell are doubled",
    },
    "ice": {
        "name": "Ice",
        "effect": "ice",
        "color": (150, 220, 255),
        "overlay_alpha": 0.3,
        "icon": "/",
        "description": "Piece slides through (continues in same direction)",
    },
    "volcano": {
        "name": "Volcano",
        "effect": "volcano",
        "color": (255, 80, 30),
        "overlay_alpha": 0.35,
        "icon": "V",
        "description": "Every 3 turns, deals 3 damage to all pieces within 2 cells",
    },
    "beacon": {
        "name": "Beacon",
        "effect": "beacon",
        "color": (255, 200, 80),
        "overlay_alpha": 0.3,
        "icon": "B",
        "description": "Friendly pieces within 2 cells have +1 ATK",
    },
    "graveyard": {
        "name": "Graveyard",
        "effect": "graveyard",
        "color": (120, 140, 100),
        "overlay_alpha": 0.3,
        "icon": "G",
        "description": "When a piece dies here, spawn a Pawn for the killer's team",
    },
    "cursed_ground": {
        "name": "Cursed Ground",
        "effect": "cursed_ground",
        "color": (100, 50, 200),
        "overlay_alpha": 0.25,
        "icon": "C",
        "description": "Enemy stepping here takes 1 damage",
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
    # --- Expansion border modifiers ---
    "firewall": {
        "name": "Firewall",
        "effect": "firewall",
        "border_color": (255, 140, 30),
        "description": "Pieces moving through take 3 fire damage",
    },
    "mirror_border": {
        "name": "Mirror Border",
        "effect": "mirror_border",
        "border_color": (200, 200, 220),
        "description": "Attacks across this border hit attacker instead",
    },
    "gravity_well": {
        "name": "Gravity Well",
        "effect": "gravity_well",
        "border_color": (100, 50, 180),
        "description": "Adjacent pieces are pulled 1 cell toward it each turn",
    },
    "healing_aura": {
        "name": "Healing Aura",
        "effect": "healing_aura",
        "border_color": (50, 200, 80),
        "description": "Adjacent pieces heal 1 HP per turn",
    },
    "speed_gate": {
        "name": "Speed Gate",
        "effect": "speed_gate",
        "border_color": (60, 200, 255),
        "description": "Pieces crossing get +2 move range for that turn",
    },
    "death_zone": {
        "name": "Death Zone",
        "effect": "death_zone",
        "border_color": (180, 30, 30),
        "description": "Pieces ending turn adjacent take 2 damage",
    },
    "swap_gate": {
        "name": "Swap Gate",
        "effect": "swap_gate",
        "border_color": (255, 200, 50),
        "description": "Pieces crossing swap HP with first enemy touched",
    },
    "tax_border": {
        "name": "Tax Border",
        "effect": "tax_border",
        "border_color": (255, 215, 0),
        "description": "Enemy crossing gives you 2 gold",
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
    # --- Expansion tarot cards ---
    "the_inferno": {
        "name": "The Inferno",
        "effect": "the_inferno",
        "cost": 10,
        "color": (255, 100, 30),
        "icon": "\u2668",
        "description": "All damage triggers 1 fire splash to adjacent cells.",
    },
    "the_glacier": {
        "name": "The Glacier",
        "effect": "the_glacier",
        "cost": 10,
        "color": (100, 200, 255),
        "icon": "\u2744",
        "description": "All your attacks apply Chill (target skips next move).",
    },
    "the_plague": {
        "name": "The Plague",
        "effect": "the_plague",
        "cost": 11,
        "color": (80, 200, 50),
        "icon": "\u2623",
        "description": "Enemies that die spread 2 poison to adjacent enemies.",
    },
    "the_architect": {
        "name": "The Architect",
        "effect": "the_architect",
        "cost": 9,
        "color": (200, 150, 100),
        "icon": "\u2302",
        "description": "Start each wave with 2 random cell mods on your half.",
    },
    "the_vampire": {
        "name": "The Vampire",
        "effect": "the_vampire",
        "cost": 11,
        "color": (180, 30, 30),
        "icon": "\u2665",
        "description": "All pieces heal 1 HP per capture (any piece's capture).",
    },
    "the_titan": {
        "name": "The Titan",
        "effect": "the_titan",
        "cost": 12,
        "color": (160, 100, 50),
        "icon": "\u25A0",
        "description": "All pieces gain +5 HP. Pieces cannot be one-shot.",
    },
    "the_swarm": {
        "name": "The Swarm",
        "effect": "the_swarm",
        "cost": 9,
        "color": (200, 180, 100),
        "icon": "\u2689",
        "description": "Start each wave with 2 extra Pawns. Pawns scale ATK.",
    },
    "the_saboteur": {
        "name": "The Saboteur",
        "effect": "the_saboteur",
        "cost": 10,
        "color": (180, 50, 100),
        "icon": "\u2622",
        "description": "Enemy modifiers have 30% chance to backfire each turn.",
    },
    "the_gambit": {
        "name": "The Gambit",
        "effect": "the_gambit",
        "cost": 8,
        "color": (255, 100, 100),
        "icon": "\u2660",
        "description": "Sacrifice 1 random piece at wave start. Others gain its ATK.",
    },
    "the_hourglass": {
        "name": "The Hourglass",
        "effect": "the_hourglass",
        "cost": 11,
        "color": (200, 180, 120),
        "icon": "\u231B",
        "description": "Sudden death is delayed by 10 turns.",
    },
    "the_chaos": {
        "name": "The Chaos",
        "effect": "the_chaos",
        "cost": 9,
        "color": (255, 100, 200),
        "icon": "\u2604",
        "description": "Every 3 turns, trigger a random event.",
    },
    "the_sacrifice_tarot": {
        "name": "The Sacrifice",
        "effect": "the_sacrifice_tarot",
        "cost": 10,
        "color": (200, 50, 50),
        "icon": "\u2720",
        "description": "When a friendly piece dies, all others gain +1 ATK permanently.",
    },
    "the_crown": {
        "name": "The Crown",
        "effect": "the_crown",
        "cost": 12,
        "color": (255, 215, 0),
        "icon": "\u2654",
        "description": "Strongest piece gains +3 ATK and Armored at wave start.",
    },
    "the_echo": {
        "name": "The Echo",
        "effect": "the_echo",
        "cost": 11,
        "color": (150, 200, 255),
        "icon": "\u21BB",
        "description": "Every capture triggers on-death ability twice.",
    },
    "the_web": {
        "name": "The Web",
        "effect": "the_web",
        "cost": 9,
        "color": (200, 200, 200),
        "icon": "\u2022",
        "description": "Enemies moving adjacent to your pieces lose 1 move range.",
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
    # --- Expansion artifacts: Common ---
    "ember_stone": {
        "name": "Ember Stone",
        "effect": "ember_stone",
        "cost": 7,
        "rarity": "common",
        "color": (255, 100, 30),
        "icon": "\u2668",
        "description": "Fire effects deal +1 damage",
    },
    "frost_shard": {
        "name": "Frost Shard",
        "effect": "frost_shard",
        "cost": 7,
        "rarity": "common",
        "color": (100, 200, 255),
        "icon": "\u2744",
        "description": "Chill effects last 1 extra turn",
    },
    "venom_gland": {
        "name": "Venom Gland",
        "effect": "venom_gland",
        "cost": 7,
        "rarity": "common",
        "color": (80, 200, 50),
        "icon": "\u2623",
        "description": "Poison damage ticks twice per turn",
    },
    "scouts_map": {
        "name": "Scout's Map",
        "effect": "scouts_map",
        "cost": 6,
        "rarity": "common",
        "color": (200, 180, 120),
        "icon": "\u2691",
        "description": "See enemy composition during setup phase",
    },
    "training_dummy": {
        "name": "Training Dummy",
        "effect": "training_dummy",
        "cost": 8,
        "rarity": "common",
        "color": (200, 150, 100),
        "icon": "\u2302",
        "description": "Surviving pieces gain +1 HP per wave survived",
    },
    "loaded_dice": {
        "name": "Loaded Dice",
        "effect": "loaded_dice",
        "cost": 8,
        "rarity": "common",
        "color": (255, 220, 100),
        "icon": "\u2680",
        "description": "Reroll shop once per wave for free",
    },
    "battle_standard": {
        "name": "Battle Standard",
        "effect": "battle_standard",
        "cost": 8,
        "rarity": "common",
        "color": (255, 100, 50),
        "icon": "\u2691",
        "description": "Pieces within 2 cells of your King gain +1 ATK",
    },
    "salvage_kit": {
        "name": "Salvage Kit",
        "effect": "salvage_kit",
        "cost": 7,
        "rarity": "common",
        "color": (180, 150, 100),
        "icon": "\u2692",
        "description": "Gain 1 gold for each of your pieces that dies",
    },
    "tempo_ring": {
        "name": "Tempo Ring",
        "effect": "tempo_ring",
        "cost": 8,
        "rarity": "common",
        "color": (100, 180, 255),
        "icon": "\u25CB",
        "description": "First piece to move each turn gets +2 ATK for that attack",
    },
    # --- Expansion artifacts: Uncommon ---
    "soul_jar": {
        "name": "Soul Jar",
        "effect": "soul_jar",
        "cost": 10,
        "rarity": "uncommon",
        "color": (150, 100, 200),
        "icon": "\u2620",
        "description": "Store up to 3 dead pieces. Revive at wave start 50% HP",
    },
    "chain_mail": {
        "name": "Chain Mail",
        "effect": "chain_mail",
        "cost": 10,
        "rarity": "uncommon",
        "color": (180, 180, 200),
        "icon": "\u2693",
        "description": "Armored reduces by 3 instead of 2",
    },
    "berserkers_torc": {
        "name": "Berserker's Torc",
        "effect": "berserkers_torc",
        "cost": 11,
        "rarity": "uncommon",
        "color": (200, 50, 50),
        "icon": "\u2694",
        "description": "Pieces below 50% HP gain +3 ATK",
    },
    "phase_cloak": {
        "name": "Phase Cloak",
        "effect": "phase_cloak",
        "cost": 10,
        "rarity": "uncommon",
        "color": (180, 50, 255),
        "icon": "\u25C8",
        "description": "Once per wave, piece at 0 HP teleports to 1 HP instead",
    },
    "plague_doctor": {
        "name": "Plague Doctor's Mask",
        "effect": "plague_doctor",
        "cost": 11,
        "rarity": "uncommon",
        "color": (80, 200, 50),
        "icon": "\u2695",
        "description": "Your pieces are immune to poison and curse effects",
    },
    "trophy_rack": {
        "name": "Trophy Rack",
        "effect": "trophy_rack",
        "cost": 10,
        "rarity": "uncommon",
        "color": (255, 180, 50),
        "icon": "\u2606",
        "description": "+1 gold per unique enemy type killed this run",
    },
    "resonance_crystal": {
        "name": "Resonance Crystal",
        "effect": "resonance_crystal",
        "cost": 12,
        "rarity": "uncommon",
        "color": (200, 100, 255),
        "icon": "\u25C6",
        "description": "Synergy effects are +50% stronger",
    },
    "echo_chamber": {
        "name": "Echo Chamber",
        "effect": "echo_chamber",
        "cost": 11,
        "rarity": "uncommon",
        "color": (150, 200, 255),
        "icon": "\u21BB",
        "description": "Cell modifier effects trigger twice",
    },
    "blood_altar": {
        "name": "Blood Altar",
        "effect": "blood_altar",
        "cost": 10,
        "rarity": "uncommon",
        "color": (180, 30, 30),
        "icon": "\u2720",
        "description": "Sacrifice piece at wave start: all others +2 ATK for wave",
    },
    # --- Expansion artifacts: Rare ---
    "doomsday_clock": {
        "name": "Doomsday Clock",
        "effect": "doomsday_clock",
        "cost": 14,
        "rarity": "rare",
        "color": (200, 50, 50),
        "icon": "\u231B",
        "description": "Sudden death 2x faster, but you deal +50% damage",
    },
    "philosophers_stone": {
        "name": "Philosopher's Stone",
        "effect": "philosophers_stone",
        "cost": 16,
        "rarity": "rare",
        "color": (255, 215, 0),
        "icon": "\u2666",
        "description": "All piece modifiers can stack (double effect)",
    },
    "pandoras_box": {
        "name": "Pandora's Box",
        "effect": "pandoras_box",
        "cost": 13,
        "rarity": "rare",
        "color": (180, 50, 255),
        "icon": "\u2604",
        "description": "Start each wave with 3 random mods on random pieces",
    },
    "grimoire": {
        "name": "Grimoire",
        "effect": "grimoire",
        "cost": 14,
        "rarity": "rare",
        "color": (100, 50, 200),
        "icon": "\u2605",
        "description": "+2 tarot slots",
    },
    "arsenal": {
        "name": "Arsenal",
        "effect": "arsenal",
        "cost": 14,
        "rarity": "rare",
        "color": (200, 100, 50),
        "icon": "\u2694",
        "description": "+2 artifact slots",
    },
    "generals_baton": {
        "name": "General's Baton",
        "effect": "generals_baton",
        "cost": 15,
        "rarity": "rare",
        "color": (255, 215, 0),
        "icon": "\u2726",
        "description": "Manual: move 3 pieces/turn. Auto: AI depth +1",
    },
    "infinity_loop": {
        "name": "Infinity Loop",
        "effect": "infinity_loop",
        "cost": 16,
        "rarity": "rare",
        "color": (200, 200, 255),
        "icon": "\u221E",
        "description": "Synergy requirements reduced by 1 piece/item",
    },
    "dragons_hoard": {
        "name": "Dragon's Hoard",
        "effect": "dragons_hoard",
        "cost": 13,
        "rarity": "rare",
        "color": (255, 180, 0),
        "icon": "\u2666",
        "description": "+3 gold per wave. Random shop item costs 0.",
    },
    "chaos_engine": {
        "name": "Chaos Engine",
        "effect": "chaos_engine",
        "cost": 14,
        "rarity": "rare",
        "color": (255, 100, 200),
        "icon": "\u2604",
        "description": "Random game rule changes each wave",
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
