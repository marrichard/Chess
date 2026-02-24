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
    # --- Expansion fields ---
    required_master: str | None = None      # master key required (None = any)
    required_artifacts: list[str] = field(default_factory=list)   # artifact effect keys needed
    required_tarots: list[str] = field(default_factory=list)      # tarot effect keys needed
    required_cell_mods: list[str] = field(default_factory=list)   # cell mod keys needed
    required_border_mods: list[str] = field(default_factory=list) # border mod keys needed
    min_modifier_count: int = 0  # need N+ pieces with any of required_modifiers


SYNERGIES: list[Synergy] = [
    # === Original synergies ===
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

    # === Fire Synergies ===
    Synergy(
        name="Firestorm",
        description="All fire damage chains: spreads fire to adjacent enemies",
        icon="\u2668", color=(255, 100, 30),
        required_pieces=[],
        min_counts={},
        required_modifiers=["flaming"],
        required_artifacts=["ember_stone"],
        required_cell_mods=["inferno"],
        effect_key="firestorm",
    ),
    Synergy(
        name="Scorched Earth",
        description="Killed enemies leave permanent Inferno cells on death squares",
        icon="\u2668", color=(255, 80, 0),
        required_pieces=[],
        min_counts={},
        required_modifiers=["blazing"],
        required_tarots=["the_inferno"],
        effect_key="scorched_earth",
    ),
    Synergy(
        name="Pyromancer",
        description="Fire splash range increased to 5x5",
        icon="\u2668", color=(255, 140, 30),
        required_pieces=[],
        min_counts={},
        required_modifiers=["flaming"],
        min_modifier_count=3,
        required_artifacts=["ember_stone"],
        effect_key="pyromancer",
    ),

    # === Ice / Control Synergies ===
    Synergy(
        name="Permafrost",
        description="Chilled enemies take 2 damage/turn while frozen",
        icon="\u2744", color=(100, 200, 255),
        required_pieces=[],
        min_counts={},
        required_modifiers=["frozen"],
        required_artifacts=["frost_shard"],
        effect_key="permafrost",
    ),
    Synergy(
        name="Absolute Zero",
        description="Frozen enemies shatter (instant kill) if hit while chilled",
        icon="\u2744", color=(150, 220, 255),
        required_pieces=[],
        min_counts={},
        required_modifiers=["frozen"],
        min_modifier_count=3,
        required_artifacts=["frost_shard"],
        effect_key="absolute_zero",
    ),

    # === Poison Synergies ===
    Synergy(
        name="Pandemic",
        description="Poison spreads to adjacent enemies when a poisoned enemy dies",
        icon="\u2623", color=(80, 200, 50),
        required_pieces=[],
        min_counts={},
        required_modifiers=["toxic"],
        required_artifacts=["venom_gland"],
        effect_key="pandemic",
    ),
    Synergy(
        name="Blight",
        description="Poison stacks uncapped; each stack increases damage by 1",
        icon="\u2623", color=(60, 180, 30),
        required_pieces=[PieceType.WITCH],
        min_counts={},
        required_modifiers=["toxic"],
        min_modifier_count=3,
        effect_key="blight",
    ),

    # === Death / Sacrifice Synergies ===
    Synergy(
        name="Martyrdom",
        description="Sacrificed pieces explode like a Bomb",
        icon="\u2720", color=(200, 50, 50),
        required_pieces=[PieceType.BOMB],
        min_counts={},
        required_modifiers=[],
        required_tarots=["the_sacrifice_tarot"],
        required_artifacts=["blood_altar"],
        effect_key="martyrdom",
    ),
    Synergy(
        name="Undying Legion",
        description="Revived pieces return at full HP with +2 ATK",
        icon="\u2620", color=(100, 200, 100),
        required_pieces=[PieceType.PHOENIX],
        min_counts={},
        required_modifiers=["haunted"],
        required_artifacts=["soul_jar"],
        effect_key="undying_legion",
    ),
    Synergy(
        name="Death's Harvest",
        description="Reaper executes below 50% HP. +2 gold per Reaper kill.",
        icon="\u2620", color=(150, 50, 50),
        required_pieces=[PieceType.REAPER],
        min_counts={},
        required_modifiers=[],
        required_tarots=["the_sacrifice_tarot"],
        required_artifacts=["salvage_kit"],
        effect_key="deaths_harvest",
    ),

    # === Formation / Defensive Synergies ===
    Synergy(
        name="Iron Phalanx",
        description="All pieces in 2-cell radius of Wall take -5 damage",
        icon="\u2616", color=(180, 180, 200),
        required_pieces=[PieceType.SENTINEL, PieceType.WALL],
        min_counts={},
        required_modifiers=["armored"],
        min_modifier_count=2,
        effect_key="iron_phalanx",
    ),
    Synergy(
        name="Sacred Ground",
        description="Healing doubled. Full HP pieces gain +1 ATK.",
        icon="\u2695", color=(150, 220, 150),
        required_pieces=[PieceType.TOTEM],
        min_counts={},
        required_modifiers=[],
        required_cell_mods=["sanctuary"],
        required_border_mods=["healing_aura"],
        effect_key="sacred_ground",
    ),
    Synergy(
        name="Fortress Protocol",
        description="Armored reduces damage by 4 instead of 2",
        icon="\u2656", color=(180, 180, 200),
        required_pieces=[],
        min_counts={},
        required_modifiers=["armored"],
        min_modifier_count=2,
        required_master="the_warden",
        required_border_mods=["fortified"],
        effect_key="fortress_protocol",
    ),

    # === Buff / ATK Synergies ===
    Synergy(
        name="War Machine",
        description="Berserker gains +2 ATK per damage instead of +1. No cap.",
        icon="\u2694", color=(200, 50, 50),
        required_pieces=[PieceType.BERSERKER_PIECE],
        min_counts={},
        required_modifiers=["unstable"],
        required_artifacts=["berserkers_torc"],
        effect_key="war_machine",
    ),
    Synergy(
        name="Alpha Strike",
        description="First attack each wave is guaranteed kill (ignores HP)",
        icon="\u2620", color=(255, 100, 30),
        required_pieces=[PieceType.ASSASSIN],
        min_counts={},
        required_modifiers=["swift"],
        required_artifacts=["tempo_ring"],
        effect_key="alpha_strike",
    ),
    Synergy(
        name="Battle Hymn",
        description="All ATK buffs provide double their value",
        icon="\u266A", color=(255, 200, 80),
        required_pieces=[PieceType.BARD],
        min_counts={},
        required_modifiers=[],
        required_artifacts=["battle_standard"],
        required_cell_mods=["beacon"],
        effect_key="battle_hymn",
    ),

    # === Economy Synergies ===
    Synergy(
        name="Midas Touch",
        description="Every capture gives +3 gold. Shop prices -20%.",
        icon="$", color=(255, 215, 0),
        required_pieces=[],
        min_counts={},
        required_modifiers=["gilded"],
        required_artifacts=["gold_tooth"],
        required_cell_mods=["gold_mine"],
        effect_key="midas_touch",
    ),
    Synergy(
        name="Trade Empire",
        description="Shop offers 4 extra items. One random item free.",
        icon="$", color=(255, 220, 100),
        required_pieces=[],
        min_counts={},
        required_modifiers=[],
        required_master="the_merchant",
        required_artifacts=["dragons_hoard"],
        effect_key="trade_empire",
    ),

    # === Chaos Synergies ===
    Synergy(
        name="Entropy",
        description="Random events always benefit you and harm enemies",
        icon="\u2604", color=(255, 100, 200),
        required_pieces=[],
        min_counts={},
        required_modifiers=[],
        required_master="the_anarchist",
        required_artifacts=["chaos_engine"],
        effect_key="entropy",
    ),
    Synergy(
        name="Madness",
        description="Enemy positions shuffle every 3 turns. Yours are immune.",
        icon="\u2622", color=(200, 50, 200),
        required_pieces=[PieceType.POLTERGEIST, PieceType.IMP],
        min_counts={},
        required_modifiers=[],
        required_tarots=["the_chaos"],
        effect_key="madness",
    ),

    # === Swarm Synergies ===
    Synergy(
        name="Endless Horde",
        description="Pawns that die spawn 2 Pawns. Those also have Splitting.",
        icon="\u2689", color=(200, 180, 100),
        required_pieces=[],
        min_counts={},
        required_modifiers=["splitting"],
        required_master="the_pauper",
        required_tarots=["the_swarm"],
        effect_key="endless_horde",
    ),
    Synergy(
        name="Pack Hunters",
        description="King Rats gain +1 ATK and +1 HP per King Rat alive",
        icon="\u2689", color=(180, 150, 100),
        required_pieces=[PieceType.KING_RAT],
        min_counts={PieceType.KING_RAT: 4},
        required_modifiers=[],
        effect_key="pack_hunters",
    ),

    # === Cross-Element Synergies ===
    Synergy(
        name="Elemental Fury",
        description="All elemental effects trigger simultaneously on every attack",
        icon="\u2668", color=(255, 150, 100),
        required_pieces=[],
        min_counts={},
        required_modifiers=["flaming", "frozen", "toxic"],
        effect_key="elemental_fury",
    ),
    Synergy(
        name="Thermal Shock",
        description="Frozen enemies hit with fire take 3x damage",
        icon="\u2744", color=(200, 150, 255),
        required_pieces=[],
        min_counts={},
        required_modifiers=["frozen", "flaming"],
        required_artifacts=["ember_stone"],
        effect_key="thermal_shock",
    ),

    # === Master-Specific Synergies ===
    Synergy(
        name="Master Forger",
        description="Pieces hold 4 mods. Modifier costs reduced to 1 gold.",
        icon="\u2692", color=(255, 140, 50),
        required_pieces=[],
        min_counts={},
        required_modifiers=[],
        required_master="the_blacksmith",
        required_artifacts=["philosophers_stone", "forge_hammer"],
        effect_key="master_forger",
    ),
    Synergy(
        name="Phantom Army",
        description="All pieces gain Ethereal. Ghost pieces deal +3 damage.",
        icon="\u2601", color=(180, 50, 255),
        required_pieces=[PieceType.PHOENIX],
        min_counts={},
        required_modifiers=["haunted"],
        required_master="the_phantom",
        effect_key="phantom_army",
    ),
    Synergy(
        name="The Collection",
        description="All item effects are +100% stronger",
        icon="\u2605", color=(255, 215, 0),
        required_pieces=[],
        min_counts={},
        required_modifiers=[],
        required_master="the_collector",
        required_artifacts=["grimoire", "arsenal"],
        effect_key="the_collection",
    ),
    Synergy(
        name="Blood Economy",
        description="Berserker HP drain heals 2 HP/kill. ATK gains permanent across waves.",
        icon="\u2665", color=(200, 50, 50),
        required_pieces=[],
        min_counts={},
        required_modifiers=["vampiric"],
        required_master="the_berserker",
        required_artifacts=["blood_altar"],
        effect_key="blood_economy",
    ),
]


def check_synergies(
    roster: list[Piece],
    team: Team,
    master_key: str | None = None,
    held_artifacts: list[dict] | None = None,
    held_tarots: list[dict] | None = None,
    board_cell_mods: list[str] | None = None,
    board_border_mods: list[str] | None = None,
    has_infinity_loop: bool = False,
) -> list[str]:
    """Evaluate roster against all synergies, returns list of active effect_keys.

    Extended to check master, artifact, tarot, cell mod, and border mod requirements.
    """
    # Count pieces by type
    counts: dict[PieceType, int] = {}
    all_mods: set[str] = set()
    mod_counts: dict[str, int] = {}
    for p in roster:
        if p.team == team:
            counts[p.piece_type] = counts.get(p.piece_type, 0) + 1
            for m in p.modifiers:
                all_mods.add(m.effect)
                mod_counts[m.effect] = mod_counts.get(m.effect, 0) + 1

    artifact_effects = {a["effect"] for a in (held_artifacts or [])}
    tarot_effects = {t["effect"] for t in (held_tarots or [])}
    cell_mod_keys = set(board_cell_mods or [])
    border_mod_keys = set(board_border_mods or [])

    reduction = 1 if has_infinity_loop else 0

    active = []
    for syn in SYNERGIES:
        # Check required master
        if syn.required_master and master_key != syn.required_master:
            continue

        # Check required pieces (need 1+ of each)
        pieces_ok = True
        for pt in syn.required_pieces:
            needed = max(1 - reduction, 0)
            if counts.get(pt, 0) < needed:
                pieces_ok = False
                break
        if not pieces_ok:
            continue

        # Check min_counts
        counts_ok = True
        for pt, n in syn.min_counts.items():
            needed = max(n - reduction, 1)
            if counts.get(pt, 0) < needed:
                counts_ok = False
                break
        if not counts_ok:
            continue

        # Check required_modifiers (any piece has at least one of these)
        if syn.required_modifiers:
            if syn.min_modifier_count > 0:
                # Need N+ pieces with any of these mods
                total = sum(mod_counts.get(m, 0) for m in syn.required_modifiers)
                needed = max(syn.min_modifier_count - reduction, 1)
                if total < needed:
                    continue
            else:
                if not any(m in all_mods for m in syn.required_modifiers):
                    continue

        # Check required artifacts
        if syn.required_artifacts:
            needed_count = max(len(syn.required_artifacts) - reduction, 1)
            found = sum(1 for a in syn.required_artifacts if a in artifact_effects)
            if found < needed_count:
                continue

        # Check required tarots
        if syn.required_tarots:
            needed_count = max(len(syn.required_tarots) - reduction, 1)
            found = sum(1 for t in syn.required_tarots if t in tarot_effects)
            if found < needed_count:
                continue

        # Check required cell mods (on the board)
        if syn.required_cell_mods:
            needed = max(len(syn.required_cell_mods) - reduction, 0)
            found = sum(1 for c in syn.required_cell_mods if c in cell_mod_keys)
            if found < needed:
                continue

        # Check required border mods (on the board)
        if syn.required_border_mods:
            needed = max(len(syn.required_border_mods) - reduction, 0)
            found = sum(1 for b in syn.required_border_mods if b in border_mod_keys)
            if found < needed:
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
