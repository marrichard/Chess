"""Master system — selectable characters that define run rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Master:
    key: str
    name: str
    description: str
    passive_desc: str
    drawback_desc: str
    icon: str
    color: tuple[int, int, int]
    # Effect keys checked by game logic
    passive: str       # passive effect identifier
    drawback: str      # drawback effect identifier


DEFAULT_MASTER = "the_strategist"

MASTERS: dict[str, Master] = {
    "the_strategist": Master(
        key="the_strategist",
        name="The Strategist",
        description="Start with 1 extra roster slot",
        passive_desc="Pieces gain +1 HP per wave survived",
        drawback_desc="No drawback (default master)",
        icon="\u2654",
        color=(100, 180, 255),
        passive="strategist_passive",
        drawback="",
    ),
    "the_arsonist": Master(
        key="the_arsonist",
        name="The Arsonist",
        description="All starting pieces gain Flaming",
        passive_desc="Fire effects deal +1 damage",
        drawback_desc="Non-fire damage dealt by your pieces is halved",
        icon="\u2668",
        color=(255, 100, 30),
        passive="arsonist_passive",
        drawback="arsonist_drawback",
    ),
    "the_blacksmith": Master(
        key="the_blacksmith",
        name="The Blacksmith",
        description="Start with Forge Hammer artifact",
        passive_desc="Piece modifiers cost 2 less gold",
        drawback_desc="Pieces without a modifier take +2 damage",
        icon="\u2692",
        color=(255, 140, 50),
        passive="blacksmith_passive",
        drawback="blacksmith_drawback",
    ),
    "the_gambler": Master(
        key="the_gambler",
        name="The Gambler",
        description="Start with 15 gold, Lucky Coin",
        passive_desc="Shop offers 2 extra items",
        drawback_desc="All prices randomized (0.5x to 2x cost)",
        icon="\u2660",
        color=(255, 215, 0),
        passive="gambler_passive",
        drawback="gambler_drawback",
    ),
    "the_necromancer": Master(
        key="the_necromancer",
        name="The Necromancer",
        description="Start with a Phoenix and a Bomb",
        passive_desc="Dead pieces fight as ghosts for 1 extra turn",
        drawback_desc="Your pieces have -2 max HP",
        icon="\u2620",
        color=(100, 200, 100),
        passive="necromancer_passive",
        drawback="necromancer_drawback",
    ),
    "the_tactician": Master(
        key="the_tactician",
        name="The Tactician",
        description="Start with The Tactician tarot",
        passive_desc="Move 2 pieces per turn in manual mode",
        drawback_desc="Enemy pieces also move twice per turn",
        icon="\u2694",
        color=(60, 200, 255),
        passive="tactician_passive",
        drawback="tactician_drawback",
    ),
    "the_pauper": Master(
        key="the_pauper",
        name="The Pauper",
        description="Start with 0 gold, 4 extra Pawns",
        passive_desc="Pawns have +3 HP and promote after 1 capture",
        drawback_desc="Non-Pawn pieces cost double in shop",
        icon="\u2659",
        color=(220, 180, 120),
        passive="pauper_passive",
        drawback="pauper_drawback",
    ),
    "the_collector": Master(
        key="the_collector",
        name="The Collector",
        description="Start with +1 tarot slot, +1 artifact slot",
        passive_desc="Gain 1 gold whenever you acquire any item",
        drawback_desc="Pieces have -1 ATK",
        icon="\u2605",
        color=(200, 100, 255),
        passive="collector_passive",
        drawback="collector_drawback",
    ),
    "the_berserker": Master(
        key="the_berserker",
        name="The Berserker",
        description="All pieces start with +3 ATK",
        passive_desc="Pieces that capture gain +1 ATK permanently",
        drawback_desc="Pieces lose 1 HP at start of each turn",
        icon="\u2694",
        color=(200, 50, 50),
        passive="berserker_passive",
        drawback="berserker_drawback",
    ),
    "the_warden": Master(
        key="the_warden",
        name="The Warden",
        description="Start with 2 Anchor Pieces",
        passive_desc="Pieces on border cells gain Armored",
        drawback_desc="Your pieces cannot move more than 2 squares",
        icon="\u2693",
        color=(50, 200, 120),
        passive="warden_passive",
        drawback="warden_drawback",
    ),
    "the_alchemist": Master(
        key="the_alchemist",
        name="The Alchemist",
        description="Start with 3 random cell mods pre-placed",
        passive_desc="Cell mod effects are doubled",
        drawback_desc="Cell mods disappear after 3 turns",
        icon="\u2697",
        color=(80, 200, 50),
        passive="alchemist_passive",
        drawback="alchemist_drawback",
    ),
    "the_hivemind": Master(
        key="the_hivemind",
        name="The Hivemind",
        description="Start with 3 King Rats",
        passive_desc="All same-type pieces share damage equally",
        drawback_desc="You can never have more than 3 piece types",
        icon="\u2689",
        color=(180, 150, 100),
        passive="hivemind_passive",
        drawback="hivemind_drawback",
    ),
    "the_phantom": Master(
        key="the_phantom",
        name="The Phantom",
        description="Start with 2 Ghosts",
        passive_desc="Your pieces can pass through enemies",
        drawback_desc="Your pieces have -3 max HP",
        icon="\u2601",
        color=(180, 50, 255),
        passive="phantom_passive",
        drawback="phantom_drawback",
    ),
    "the_merchant": Master(
        key="the_merchant",
        name="The Merchant",
        description="Start with 20 gold and The Merchant tarot",
        passive_desc="Can sell items back at 50% price",
        drawback_desc="Waves give 50% less gold",
        icon="$",
        color=(255, 215, 0),
        passive="merchant_passive",
        drawback="merchant_drawback",
    ),
    "the_anarchist": Master(
        key="the_anarchist",
        name="The Anarchist",
        description="Start with Chaos Orb artifact",
        passive_desc="Each wave, 1 random board rule changes",
        drawback_desc="You cannot buy tarot cards",
        icon="\u2604",
        color=(255, 100, 200),
        passive="anarchist_passive",
        drawback="anarchist_drawback",
    ),
    "the_mirror_master": Master(
        key="the_mirror_master",
        name="The Mirror",
        description="No starting roster — copy enemy's first wave",
        passive_desc="After each wave, gain a copy of the strongest enemy killed",
        drawback_desc="Your copied pieces have -2 ATK",
        icon="\u25C7",
        color=(200, 200, 220),
        passive="mirror_master_passive",
        drawback="mirror_master_drawback",
    ),
}
