"""Central rarity registry — enum, assignments for ALL item types, weight/cost helpers."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import random


class Rarity(Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


RARITY_PROPS = {
    Rarity.COMMON:    {"color": (180, 180, 180), "weight": 50, "cost_mult": 1.0, "sell_mult": 1.0, "label": "Common"},
    Rarity.RARE:      {"color": (80, 140, 255),  "weight": 30, "cost_mult": 1.5, "sell_mult": 1.5, "label": "Rare"},
    Rarity.EPIC:      {"color": (180, 60, 255),  "weight": 15, "cost_mult": 2.5, "sell_mult": 2.0, "label": "Epic"},
    Rarity.LEGENDARY: {"color": (255, 200, 50),  "weight": 5,  "cost_mult": 4.0, "sell_mult": 3.0, "label": "Legendary"},
}

# ------------------------------------------------------------------ Piece rarity (40 pieces)
PIECE_RARITY: dict[str, Rarity] = {
    # COMMON (12)
    "pawn": Rarity.COMMON, "knight": Rarity.COMMON, "bishop": Rarity.COMMON,
    "rook": Rarity.COMMON, "decoy": Rarity.COMMON, "wall": Rarity.COMMON,
    "lancer": Rarity.COMMON, "bard": Rarity.COMMON, "imp": Rarity.COMMON,
    "cannon": Rarity.COMMON, "totem": Rarity.COMMON, "duelist": Rarity.COMMON,
    # RARE (12)
    "queen": Rarity.RARE, "king": Rarity.RARE, "bomb": Rarity.RARE,
    "leech": Rarity.RARE, "berserker_piece": Rarity.RARE, "charger": Rarity.RARE,
    "sentinel": Rarity.RARE, "healer": Rarity.RARE, "trickster": Rarity.RARE,
    "alchemist_piece": Rarity.RARE, "golem": Rarity.RARE, "witch": Rarity.RARE,
    # EPIC (10)
    "mimic": Rarity.EPIC, "summoner": Rarity.EPIC, "ghost": Rarity.EPIC,
    "parasite": Rarity.EPIC, "phoenix": Rarity.EPIC, "assassin": Rarity.EPIC,
    "reaper": Rarity.EPIC, "wyvern": Rarity.EPIC, "shapeshifter": Rarity.EPIC,
    "king_rat": Rarity.EPIC,
    # LEGENDARY (6)
    "gambler": Rarity.LEGENDARY, "anchor_piece": Rarity.LEGENDARY,
    "mirror_piece": Rarity.LEGENDARY, "void": Rarity.LEGENDARY,
    "poltergeist": Rarity.LEGENDARY, "time_mage": Rarity.LEGENDARY,
}

# ------------------------------------------------------------------ Piece modifier rarity (20 mods)
PIECE_MOD_RARITY: dict[str, Rarity] = {
    # COMMON (5)
    "flaming": Rarity.COMMON, "armored": Rarity.COMMON, "swift": Rarity.COMMON,
    "frozen": Rarity.COMMON, "thorned": Rarity.COMMON,
    # RARE (6)
    "piercing": Rarity.RARE, "royal": Rarity.RARE, "toxic": Rarity.RARE,
    "lucky": Rarity.RARE, "gilded": Rarity.RARE, "blazing": Rarity.RARE,
    # EPIC (6)
    "vampiric": Rarity.EPIC, "explosive": Rarity.EPIC, "magnetic": Rarity.EPIC,
    "splitting": Rarity.EPIC, "reflective": Rarity.EPIC, "unstable": Rarity.EPIC,
    # LEGENDARY (3)
    "ethereal": Rarity.LEGENDARY, "titan": Rarity.LEGENDARY, "haunted": Rarity.LEGENDARY,
}

# ------------------------------------------------------------------ Tarot rarity (27 tarots)
TAROT_RARITY: dict[str, Rarity] = {
    # COMMON (7)
    "the_flame": Rarity.COMMON, "the_fortress": Rarity.COMMON,
    "the_pawn": Rarity.COMMON, "the_shepherd": Rarity.COMMON,
    "the_architect": Rarity.COMMON, "the_swarm": Rarity.COMMON,
    "the_web": Rarity.COMMON,
    # RARE (9)
    "the_phantom": Rarity.RARE, "the_tide": Rarity.RARE,
    "the_merchant": Rarity.RARE, "the_tactician": Rarity.RARE,
    "the_glacier": Rarity.RARE, "the_titan": Rarity.RARE,
    "the_hourglass": Rarity.RARE, "the_sacrifice_tarot": Rarity.RARE,
    "the_crown": Rarity.RARE,
    # EPIC (8)
    "the_necromancer": Rarity.EPIC, "the_jester": Rarity.EPIC,
    "the_mirror": Rarity.EPIC, "the_executioner": Rarity.EPIC,
    "the_inferno": Rarity.EPIC, "the_plague": Rarity.EPIC,
    "the_vampire": Rarity.EPIC, "the_saboteur": Rarity.EPIC,
    # LEGENDARY (3)
    "the_gambit": Rarity.LEGENDARY, "the_chaos": Rarity.LEGENDARY,
    "the_echo": Rarity.LEGENDARY,
}

# ------------------------------------------------------------------ Artifact rarity (41 artifacts)
# Maps existing 3-tier (common/uncommon/rare) to 4-tier
ARTIFACT_RARITY: dict[str, Rarity] = {
    # COMMON (13)
    "gold_tooth": Rarity.COMMON, "war_drum": Rarity.COMMON,
    "iron_crown": Rarity.COMMON, "lucky_coin": Rarity.COMMON,
    "ember_stone": Rarity.COMMON, "frost_shard": Rarity.COMMON,
    "venom_gland": Rarity.COMMON, "scouts_map": Rarity.COMMON,
    "training_dummy": Rarity.COMMON, "loaded_dice": Rarity.COMMON,
    "battle_standard": Rarity.COMMON, "salvage_kit": Rarity.COMMON,
    "tempo_ring": Rarity.COMMON,
    # RARE (13)
    "blood_pact": Rarity.RARE, "mirror_shard": Rarity.RARE,
    "chaos_orb": Rarity.RARE, "anchor_chain": Rarity.RARE,
    "whetstone": Rarity.RARE, "soul_jar": Rarity.RARE,
    "chain_mail": Rarity.RARE, "berserkers_torc": Rarity.RARE,
    "phase_cloak": Rarity.RARE, "plague_doctor": Rarity.RARE,
    "trophy_rack": Rarity.RARE, "resonance_crystal": Rarity.RARE,
    "echo_chamber": Rarity.RARE,
    # EPIC (9)
    "forge_hammer": Rarity.EPIC, "pandemonium": Rarity.EPIC,
    "necrotome": Rarity.EPIC, "heretics_tome": Rarity.EPIC,
    "blood_altar": Rarity.EPIC, "doomsday_clock": Rarity.EPIC,
    "philosophers_stone": Rarity.EPIC, "generals_baton": Rarity.EPIC,
    "arsenal": Rarity.EPIC,
    # LEGENDARY (6)
    "crown_jewel": Rarity.LEGENDARY, "pandoras_box": Rarity.LEGENDARY,
    "grimoire": Rarity.LEGENDARY, "infinity_loop": Rarity.LEGENDARY,
    "dragons_hoard": Rarity.LEGENDARY, "chaos_engine": Rarity.LEGENDARY,
}

# ------------------------------------------------------------------ Cell modifier rarity (16 cells)
CELL_MOD_RARITY: dict[str, Rarity] = {
    # COMMON (4)
    "rage": Rarity.COMMON, "shield": Rarity.COMMON,
    "haste": Rarity.COMMON, "ice": Rarity.COMMON,
    # RARE (6)
    "phase": Rarity.RARE, "inferno": Rarity.RARE,
    "sanctuary": Rarity.RARE, "quicksand": Rarity.RARE,
    "gold_mine": Rarity.RARE, "beacon": Rarity.RARE,
    # EPIC (6)
    "vortex": Rarity.EPIC, "mirror_cell": Rarity.EPIC,
    "curse": Rarity.EPIC, "amplifier": Rarity.EPIC,
    "volcano": Rarity.EPIC, "graveyard": Rarity.EPIC,
}

# ------------------------------------------------------------------ Border modifier rarity (11 borders)
BORDER_MOD_RARITY: dict[str, Rarity] = {
    # COMMON (3)
    "fortified": Rarity.COMMON, "thorns": Rarity.COMMON, "anchor": Rarity.COMMON,
    # RARE (4)
    "firewall": Rarity.RARE, "healing_aura": Rarity.RARE,
    "speed_gate": Rarity.RARE, "tax_border": Rarity.RARE,
    # EPIC (4)
    "mirror_border": Rarity.EPIC, "gravity_well": Rarity.EPIC,
    "death_zone": Rarity.EPIC, "swap_gate": Rarity.EPIC,
}

# ------------------------------------------------------------------ Unified lookup tables
_RARITY_MAPS: dict[str, dict[str, Rarity]] = {
    "piece": PIECE_RARITY,
    "piece_mod": PIECE_MOD_RARITY,
    "tarot": TAROT_RARITY,
    "artifact": ARTIFACT_RARITY,
    "cell_mod": CELL_MOD_RARITY,
    "border_mod": BORDER_MOD_RARITY,
}


# ------------------------------------------------------------------ Helper functions

def get_rarity(item_type: str, key: str) -> Rarity:
    """Lookup any item's rarity. Returns COMMON if not found."""
    table = _RARITY_MAPS.get(item_type)
    if table:
        return table.get(key, Rarity.COMMON)
    return Rarity.COMMON


def weighted_choice(items: list[str], item_type: str, rng: random.Random,
                    wave_bonus: float = 0.0) -> str:
    """Pick from a list of item keys using rarity weights.

    wave_bonus: multiplier added to RARE+ weights per wave (e.g. wave * 0.1).
    Higher wave_bonus makes rare items more likely.
    """
    table = _RARITY_MAPS.get(item_type, {})
    weights = []
    for key in items:
        rarity = table.get(key, Rarity.COMMON)
        base_weight = RARITY_PROPS[rarity]["weight"]
        if rarity != Rarity.COMMON and wave_bonus > 0:
            base_weight = base_weight * (1 + wave_bonus)
        weights.append(base_weight)
    return rng.choices(items, weights=weights, k=1)[0]


def get_shop_cost(base_cost: int, rarity: Rarity) -> int:
    """Apply rarity cost multiplier to a base cost."""
    return max(1, int(base_cost * RARITY_PROPS[rarity]["cost_mult"]))


def get_sell_value(base_value: int, rarity: Rarity) -> int:
    """Calculate salvage/sell price based on rarity."""
    return max(1, int(base_value * RARITY_PROPS[rarity]["sell_mult"]))


# Flat sell values by rarity for pieces
PIECE_SELL_VALUES = {
    Rarity.COMMON: 1,
    Rarity.RARE: 2,
    Rarity.EPIC: 4,
    Rarity.LEGENDARY: 6,
}
