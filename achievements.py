"""Achievement system — definitions, condition checking, unlock rewards."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import save_data as sd

# ------------------------------------------------------------------ Data


@dataclass
class Achievement:
    key: str
    name: str
    description: str
    icon: str
    category: str               # "milestone", "combat", "economy", "discovery", "challenge", "hidden"
    condition_type: str          # "stat", "win_condition", "in_run", "collection"
    condition: dict              # type-specific params
    unlocks: list[dict]          # [{"type": "piece", "key": "assassin"}, ...]
    hidden: bool = False         # hidden until earned


# ------------------------------------------------------------------ All achievements (~55)

ACHIEVEMENTS: list[Achievement] = [
    # ===== MILESTONE (10) =====
    Achievement(
        key="first_blood", name="First Blood",
        description="Win 1 tournament",
        icon="\u2694", category="milestone",
        condition_type="stat", condition={"stat": "tournaments_won", "threshold": 1},
        unlocks=[{"type": "master", "key": "the_arsonist"}],
    ),
    Achievement(
        key="veteran", name="Veteran",
        description="Win 5 tournaments",
        icon="\u2694", category="milestone",
        condition_type="stat", condition={"stat": "tournaments_won", "threshold": 5},
        unlocks=[{"type": "master", "key": "the_tactician"}],
    ),
    Achievement(
        key="warlord", name="Warlord",
        description="Win 10 tournaments",
        icon="\u2694", category="milestone",
        condition_type="stat", condition={"stat": "tournaments_won", "threshold": 10},
        unlocks=[{"type": "master", "key": "the_berserker"}],
    ),
    Achievement(
        key="endurance", name="Endurance",
        description="Complete 25 runs",
        icon="\u231B", category="milestone",
        condition_type="stat", condition={"stat": "tournaments_completed", "threshold": 25},
        unlocks=[{"type": "master", "key": "the_warden"}],
    ),
    Achievement(
        key="hoarder", name="Hoarder",
        description="Earn 500 total ELO",
        icon="$", category="milestone",
        condition_type="stat", condition={"stat": "total_elo_earned", "threshold": 500},
        unlocks=[{"type": "master", "key": "the_merchant"}],
    ),
    Achievement(
        key="mogul", name="Mogul",
        description="Earn 2000 total ELO",
        icon="$", category="milestone",
        condition_type="stat", condition={"stat": "total_elo_earned", "threshold": 2000},
        unlocks=[{"type": "master", "key": "the_collector"}],
    ),
    Achievement(
        key="boss_slayer", name="Boss Slayer",
        description="Beat 10 bosses",
        icon="\u2620", category="milestone",
        condition_type="stat", condition={"stat": "bosses_beaten", "threshold": 10},
        unlocks=[{"type": "master", "key": "the_necromancer"}],
    ),
    Achievement(
        key="executioner_ach", name="Executioner",
        description="Beat 25 bosses",
        icon="\u2620", category="milestone",
        condition_type="stat", condition={"stat": "bosses_beaten", "threshold": 25},
        unlocks=[{"type": "master", "key": "the_phantom"}],
    ),
    Achievement(
        key="clutch", name="Clutch",
        description="Win a tournament with 0 lives remaining",
        icon="\u2665", category="milestone",
        condition_type="win_condition", condition={"check": "clutch_win"},
        unlocks=[{"type": "master", "key": "the_gambler"}],
    ),
    Achievement(
        key="perfectionist", name="Perfectionist",
        description="Win on Grandmaster difficulty",
        icon="\u2654", category="milestone",
        condition_type="win_condition", condition={"check": "grandmaster_win"},
        unlocks=[{"type": "master", "key": "the_mirror_master"}],
    ),

    # ===== COMBAT (10) =====
    Achievement(
        key="heavy_hitter", name="Heavy Hitter",
        description="Deal 30+ damage in one hit",
        icon="!", category="combat",
        condition_type="in_run", condition={"check": "max_damage_hit", "threshold": 30},
        unlocks=[{"type": "modifier", "key": "explosive"}],
    ),
    Achievement(
        key="army_builder", name="Army Builder",
        description="Have 10+ pieces alive at once",
        icon="\u2726", category="combat",
        condition_type="in_run", condition={"check": "max_pieces_alive", "threshold": 10},
        unlocks=[{"type": "master", "key": "the_hivemind"}],
    ),
    Achievement(
        key="last_stand", name="Last Stand",
        description="Win a battle with only 1 piece surviving",
        icon="\u2694", category="combat",
        condition_type="in_run", condition={"check": "win_with_one_piece"},
        unlocks=[{"type": "piece", "key": "berserker_piece"}],
    ),
    Achievement(
        key="untouchable", name="Untouchable",
        description="Win a battle without losing a piece",
        icon="\u2616", category="combat",
        condition_type="in_run", condition={"check": "flawless_battle"},
        unlocks=[{"type": "modifier", "key": "ethereal"}],
    ),
    Achievement(
        key="overkill", name="Overkill",
        description="Kill an enemy with 3x its max HP in damage",
        icon="\u2738", category="combat",
        condition_type="in_run", condition={"check": "overkill_3x"},
        unlocks=[{"type": "modifier", "key": "titan"}],
    ),
    Achievement(
        key="blitz", name="Blitz",
        description="Win a battle in under 5 turns",
        icon=">", category="combat",
        condition_type="in_run", condition={"check": "fast_battle", "threshold": 5},
        unlocks=[],  # visual unlock for swift
    ),
    Achievement(
        key="combo_master", name="Combo Master",
        description="Trigger 3+ on-death effects in one turn",
        icon="\u2604", category="combat",
        condition_type="in_run", condition={"check": "ondeath_combo", "threshold": 3},
        unlocks=[{"type": "modifier", "key": "haunted"}],
    ),
    Achievement(
        key="elemental", name="Elemental",
        description="Have fire, ice, and poison active at once",
        icon="\u2668", category="combat",
        condition_type="in_run", condition={"check": "elemental_trio"},
        unlocks=[{"type": "modifier", "key": "blazing"}],
    ),
    Achievement(
        key="assassins_creed", name="Assassin's Creed",
        description="Kill 3 enemies with one piece in one battle",
        icon="\u2620", category="combat",
        condition_type="in_run", condition={"check": "triple_kill_piece"},
        unlocks=[{"type": "piece", "key": "assassin"}],
    ),
    Achievement(
        key="necromancy", name="Necromancy",
        description="Revive 5 pieces total across runs",
        icon="\u2622", category="combat",
        condition_type="stat", condition={"stat": "total_revives", "threshold": 5},
        unlocks=[{"type": "piece", "key": "poltergeist"}],
    ),

    # ===== ECONOMY (8) =====
    Achievement(
        key="penny_pincher", name="Penny Pincher",
        description="End a run with 30+ unspent gold",
        icon="$", category="economy",
        condition_type="in_run", condition={"check": "end_run_gold", "threshold": 30},
        unlocks=[{"type": "artifact", "key": "dragons_hoard"}],
    ),
    Achievement(
        key="bargain_hunter", name="Bargain Hunter",
        description="Buy 20 shop items total",
        icon="\u2605", category="economy",
        condition_type="stat", condition={"stat": "shop_items_bought", "threshold": 20},
        unlocks=[{"type": "artifact", "key": "loaded_dice"}],
    ),
    Achievement(
        key="collector", name="Collector",
        description="Own 8+ artifacts at once",
        icon="\u2726", category="economy",
        condition_type="in_run", condition={"check": "artifacts_held", "threshold": 8},
        unlocks=[{"type": "artifact", "key": "arsenal"}],
    ),
    Achievement(
        key="bibliophile", name="Bibliophile",
        description="Hold 6+ tarots at once",
        icon="\u2605", category="economy",
        condition_type="in_run", condition={"check": "tarots_held", "threshold": 6},
        unlocks=[{"type": "artifact", "key": "grimoire"}],
    ),
    Achievement(
        key="recycler", name="Recycler",
        description="Sell 10 items total",
        icon="\u2692", category="economy",
        condition_type="stat", condition={"stat": "items_sold", "threshold": 10},
        unlocks=[{"type": "artifact", "key": "salvage_kit"}],
    ),
    Achievement(
        key="investor", name="Investor",
        description="Spend 100 gold in shops total",
        icon="$", category="economy",
        condition_type="stat", condition={"stat": "total_gold_spent", "threshold": 100},
        unlocks=[{"type": "artifact", "key": "philosophers_stone"}],
    ),
    Achievement(
        key="golden_age", name="Golden Age",
        description="Earn 50+ gold in a single run",
        icon="\u2666", category="economy",
        condition_type="in_run", condition={"check": "run_gold_earned", "threshold": 50},
        unlocks=[{"type": "artifact", "key": "crown_jewel"}],
    ),
    Achievement(
        key="war_profiteer", name="War Profiteer",
        description="Win 3 battles in a row with gilded pieces",
        icon="\u2606", category="economy",
        condition_type="in_run", condition={"check": "gilded_streak", "threshold": 3},
        unlocks=[{"type": "artifact", "key": "trophy_rack"}],
    ),

    # ===== DISCOVERY (10) =====
    Achievement(
        key="synergist", name="Synergist",
        description="Activate 3 synergies in one run",
        icon="\u25C6", category="discovery",
        condition_type="in_run", condition={"check": "synergies_active", "threshold": 3},
        unlocks=[{"type": "artifact", "key": "resonance_crystal"}],
    ),
    Achievement(
        key="scholar", name="Scholar",
        description="Discover 15 synergies",
        icon="\u25C6", category="discovery",
        condition_type="stat", condition={"stat": "synergies_discovered", "threshold": 15},
        unlocks=[{"type": "artifact", "key": "infinity_loop"}],
    ),
    Achievement(
        key="encyclopedia", name="Encyclopedia",
        description="Discover all synergies",
        icon="\u25C6", category="discovery",
        condition_type="stat", condition={"stat": "synergies_discovered", "threshold": 99},  # checked dynamically
        unlocks=[{"type": "artifact", "key": "chaos_engine"}],
    ),
    Achievement(
        key="variety_pack", name="Variety Pack",
        description="Use 10 different piece types in one run",
        icon="\u221E", category="discovery",
        condition_type="in_run", condition={"check": "unique_piece_types", "threshold": 10},
        unlocks=[{"type": "piece", "key": "shapeshifter"}],
    ),
    Achievement(
        key="mad_scientist", name="Mad Scientist",
        description="Apply 5 mods to one piece across a run",
        icon="\u2697", category="discovery",
        condition_type="in_run", condition={"check": "mods_on_one_piece", "threshold": 5},
        unlocks=[{"type": "modifier", "key": "splitting"}],
    ),
    Achievement(
        key="alchemist", name="Alchemist",
        description="Use 15 different tarots across runs",
        icon="\u2605", category="discovery",
        condition_type="stat", condition={"stat": "different_tarots_used", "threshold": 15},
        unlocks=[{"type": "tarot", "key": "the_echo"}],
    ),
    Achievement(
        key="curator", name="Curator",
        description="Collect 15 different artifacts across runs",
        icon="\u2726", category="discovery",
        condition_type="stat", condition={"stat": "different_artifacts_collected", "threshold": 15},
        unlocks=[{"type": "artifact", "key": "pandoras_box"}],
    ),
    Achievement(
        key="strategist", name="Strategist",
        description="Win with 5 different masters",
        icon="\u2654", category="discovery",
        condition_type="stat", condition={"stat": "different_masters_won_with", "threshold": 5},
        unlocks=[{"type": "artifact", "key": "generals_baton"}],
    ),
    Achievement(
        key="completionist", name="Completionist",
        description="Win with every master",
        icon="\u2654", category="discovery",
        condition_type="stat", condition={"stat": "different_masters_won_with", "threshold": 99},  # checked dynamically
        unlocks=[{"type": "piece", "key": "time_mage"}],
    ),
    Achievement(
        key="all_seeing", name="All-Seeing",
        description="View every Chessticon entry",
        icon="\u2609", category="discovery",
        condition_type="stat", condition={"stat": "codex_entries_viewed", "threshold": 99},
        unlocks=[{"type": "artifact", "key": "echo_chamber"}],
    ),

    # ===== CHALLENGE (8) =====
    Achievement(
        key="pacifist", name="Pacifist",
        description="Win a battle where King deals no damage",
        icon="\u2654", category="challenge",
        condition_type="in_run", condition={"check": "pacifist_king"},
        unlocks=[{"type": "piece", "key": "mirror_piece"}],
    ),
    Achievement(
        key="pawn_star", name="Pawn Star",
        description="Win a tournament using only Pawns + King",
        icon="\u2659", category="challenge",
        condition_type="win_condition", condition={"check": "pawns_only_win"},
        unlocks=[{"type": "master", "key": "the_pauper"}],
    ),
    Achievement(
        key="chaos_run", name="Chaos Run",
        description="Win with 5+ random events in one run",
        icon="\u2604", category="challenge",
        condition_type="in_run", condition={"check": "random_events", "threshold": 5},
        unlocks=[{"type": "master", "key": "the_anarchist"}],
    ),
    Achievement(
        key="speedrunner", name="Speedrunner",
        description="Win a tournament in under 20 minutes",
        icon="\u231A", category="challenge",
        condition_type="win_condition", condition={"check": "speed_win", "threshold": 1200},
        unlocks=[{"type": "master", "key": "the_alchemist"}],
    ),
    Achievement(
        key="deathless", name="Deathless",
        description="Win a tournament without losing a life",
        icon="\u2665", category="challenge",
        condition_type="win_condition", condition={"check": "deathless_win"},
        unlocks=[{"type": "piece", "key": "void"}],
    ),
    Achievement(
        key="minimalist", name="Minimalist",
        description="Win with 4 or fewer pieces",
        icon="\u25CB", category="challenge",
        condition_type="win_condition", condition={"check": "minimalist_win", "threshold": 4},
        unlocks=[{"type": "piece", "key": "anchor_piece"}],
    ),
    Achievement(
        key="ironman", name="Ironman",
        description="Win on Extreme+ with no shop purchases",
        icon="\u2692", category="challenge",
        condition_type="win_condition", condition={"check": "ironman_win"},
        unlocks=[{"type": "master", "key": "the_blacksmith"}],
    ),
    Achievement(
        key="true_master", name="True Master",
        description="Beat every boss type",
        icon="\u2654", category="challenge",
        condition_type="stat", condition={"stat": "boss_types_beaten_count", "threshold": 6},
        unlocks=[{"type": "piece", "key": "gambler"}],
    ),

    # ===== HIDDEN (5) =====
    Achievement(
        key="lucky_7", name="Lucky 7",
        description="Win with exactly 7 gold, 7 HP, on wave 7",
        icon="7", category="hidden",
        condition_type="in_run", condition={"check": "lucky_seven"},
        unlocks=[{"type": "modifier", "key": "lucky"}],
        hidden=True,
    ),
    Achievement(
        key="mirror_match", name="Mirror Match",
        description="Fight an enemy with identical composition",
        icon="\u25C7", category="hidden",
        condition_type="in_run", condition={"check": "mirror_match"},
        unlocks=[{"type": "border_mod", "key": "mirror_border"}],
        hidden=True,
    ),
    Achievement(
        key="phoenix_down", name="Phoenix Down",
        description="Have Phoenix revive 3 times in one battle",
        icon="\u2600", category="hidden",
        condition_type="in_run", condition={"check": "phoenix_triple_revive"},
        unlocks=[],  # Phoenix auto-gilded
        hidden=True,
    ),
    Achievement(
        key="domination", name="Domination",
        description="Win with 8+ pieces alive, all above 50% HP",
        icon="\u2605", category="hidden",
        condition_type="in_run", condition={"check": "domination_win"},
        unlocks=[{"type": "artifact", "key": "battle_standard"}],
        hidden=True,
    ),
    Achievement(
        key="ouroboros", name="Ouroboros",
        description="Loop back to wave 1 via Infinity Loop synergy",
        icon="\u221E", category="hidden",
        condition_type="in_run", condition={"check": "infinity_loop_trigger"},
        unlocks=[{"type": "artifact", "key": "doomsday_clock"}],
        hidden=True,
    ),
]

# Quick lookup by key
ACHIEVEMENT_MAP: dict[str, Achievement] = {a.key: a for a in ACHIEVEMENTS}

# Category groupings
ACHIEVEMENT_CATEGORIES = ["milestone", "combat", "economy", "discovery", "challenge", "hidden"]


# ------------------------------------------------------------------ Checker


class AchievementChecker:
    """Checks achievement conditions and returns newly unlocked achievement keys."""

    def check_end_of_battle(self, run_state: dict, battle_stats: dict,
                            save_data: sd.SaveData) -> list[str]:
        """Check achievements after a battle ends. Returns newly unlocked keys."""
        unlocked = save_data.unlocked_achievements
        newly = []

        for ach in ACHIEVEMENTS:
            if ach.key in unlocked:
                continue

            if ach.condition_type == "in_run":
                check = ach.condition.get("check", "")
                threshold = ach.condition.get("threshold", 0)

                if check == "max_damage_hit":
                    if battle_stats.get("max_damage_hit", 0) >= threshold:
                        newly.append(ach.key)
                elif check == "max_pieces_alive":
                    if battle_stats.get("max_pieces_alive", 0) >= threshold:
                        newly.append(ach.key)
                elif check == "win_with_one_piece":
                    if battle_stats.get("player_survived", 0) == 1 and battle_stats.get("won"):
                        newly.append(ach.key)
                elif check == "flawless_battle":
                    if battle_stats.get("won") and battle_stats.get("pieces_lost", 0) == 0:
                        newly.append(ach.key)
                elif check == "overkill_3x":
                    if battle_stats.get("overkill_3x"):
                        newly.append(ach.key)
                elif check == "fast_battle":
                    if battle_stats.get("won") and battle_stats.get("battle_turns", 99) < threshold:
                        newly.append(ach.key)
                elif check == "ondeath_combo":
                    if battle_stats.get("max_ondeath_in_turn", 0) >= threshold:
                        newly.append(ach.key)
                elif check == "elemental_trio":
                    if battle_stats.get("elemental_trio"):
                        newly.append(ach.key)
                elif check == "triple_kill_piece":
                    if battle_stats.get("max_kills_one_piece", 0) >= 3:
                        newly.append(ach.key)
                elif check == "domination_win":
                    if (battle_stats.get("won")
                            and battle_stats.get("player_survived", 0) >= 8
                            and battle_stats.get("all_above_half_hp")):
                        newly.append(ach.key)
                elif check == "pacifist_king":
                    if battle_stats.get("won") and battle_stats.get("king_damage_dealt", 0) == 0:
                        newly.append(ach.key)
                elif check == "mirror_match":
                    if battle_stats.get("mirror_match"):
                        newly.append(ach.key)
                elif check == "phoenix_triple_revive":
                    if battle_stats.get("phoenix_revives_this_battle", 0) >= 3:
                        newly.append(ach.key)

                # Run-scoped checks that can trigger after any battle
                elif check == "synergies_active":
                    if run_state.get("active_synergy_count", 0) >= threshold:
                        newly.append(ach.key)
                elif check == "artifacts_held":
                    if run_state.get("artifact_count", 0) >= threshold:
                        newly.append(ach.key)
                elif check == "tarots_held":
                    if run_state.get("tarot_count", 0) >= threshold:
                        newly.append(ach.key)
                elif check == "unique_piece_types":
                    if run_state.get("unique_piece_types_used", 0) >= threshold:
                        newly.append(ach.key)
                elif check == "mods_on_one_piece":
                    if run_state.get("max_mods_on_piece", 0) >= threshold:
                        newly.append(ach.key)
                elif check == "gilded_streak":
                    if run_state.get("gilded_win_streak", 0) >= threshold:
                        newly.append(ach.key)
                elif check == "run_gold_earned":
                    if run_state.get("total_gold_earned_run", 0) >= threshold:
                        newly.append(ach.key)
                elif check == "random_events":
                    if run_state.get("random_events_count", 0) >= threshold:
                        newly.append(ach.key)

        return newly

    def check_end_of_run(self, run_state: dict, save_data: sd.SaveData,
                         won: bool) -> list[str]:
        """Check achievements after a run ends. Returns newly unlocked keys."""
        unlocked = save_data.unlocked_achievements
        newly = []

        for ach in ACHIEVEMENTS:
            if ach.key in unlocked:
                continue

            if ach.condition_type == "win_condition" and won:
                check = ach.condition.get("check", "")
                threshold = ach.condition.get("threshold", 0)

                if check == "clutch_win":
                    # Won on last life: losses == max_lives - 1
                    max_lives = run_state.get("max_lives", 3)
                    losses = run_state.get("losses", 0)
                    if losses >= max_lives - 1:
                        newly.append(ach.key)
                elif check == "grandmaster_win":
                    if run_state.get("difficulty") == "grandmaster":
                        newly.append(ach.key)
                elif check == "pawns_only_win":
                    if run_state.get("pawns_only"):
                        newly.append(ach.key)
                elif check == "speed_win":
                    elapsed = run_state.get("elapsed_seconds", 99999)
                    if elapsed <= threshold:
                        newly.append(ach.key)
                elif check == "deathless_win":
                    if run_state.get("losses", 1) == 0:
                        newly.append(ach.key)
                elif check == "minimalist_win":
                    if run_state.get("max_roster_size", 99) <= threshold:
                        newly.append(ach.key)
                elif check == "ironman_win":
                    diff = run_state.get("difficulty", "basic")
                    if diff in ("extreme", "grandmaster") and run_state.get("shop_purchases", 0) == 0:
                        newly.append(ach.key)

            elif ach.condition_type == "in_run":
                check = ach.condition.get("check", "")
                threshold = ach.condition.get("threshold", 0)

                if check == "end_run_gold":
                    if run_state.get("gold", 0) >= threshold:
                        newly.append(ach.key)
                elif check == "lucky_seven":
                    if (run_state.get("gold") == 7
                            and run_state.get("total_hp") == 7
                            and run_state.get("wave") == 7
                            and won):
                        newly.append(ach.key)
                elif check == "infinity_loop_trigger":
                    if run_state.get("infinity_loop_triggered"):
                        newly.append(ach.key)

        return newly

    def check_stats(self, save_data: sd.SaveData) -> list[str]:
        """Check stat-threshold achievements. Returns newly unlocked keys."""
        unlocked = save_data.unlocked_achievements
        stats = save_data.stats
        newly = []

        for ach in ACHIEVEMENTS:
            if ach.key in unlocked:
                continue
            if ach.condition_type != "stat":
                continue

            stat_key = ach.condition.get("stat", "")
            threshold = ach.condition.get("threshold", 0)

            # Dynamic thresholds
            if stat_key == "synergies_discovered":
                from synergies import SYNERGIES
                if ach.key == "encyclopedia":
                    threshold = len(SYNERGIES)
                actual = len(save_data.discovered_synergies)
            elif stat_key == "different_masters_won_with":
                from masters import MASTERS
                if ach.key == "completionist":
                    threshold = len(MASTERS)
                actual = len(stats.get("masters_won_with", []))
            elif stat_key == "boss_types_beaten_count":
                actual = len(stats.get("boss_types_beaten", []))
            elif stat_key == "codex_entries_viewed":
                from pieces import PIECE_STATS
                from modifiers import CELL_MODIFIERS, BORDER_MODIFIERS, TAROT_CARDS, ARTIFACTS
                threshold = len(PIECE_STATS) + len(CELL_MODIFIERS) + len(BORDER_MODIFIERS) + len(TAROT_CARDS) + len(ARTIFACTS) + len(SYNERGIES) + len(MASTERS)
                actual = stats.get("codex_entries_viewed", 0)
            else:
                actual = stats.get(stat_key, 0)

            if actual >= threshold:
                newly.append(ach.key)

        return newly


def process_unlocks(newly_unlocked: list[str], save_data: sd.SaveData) -> list[dict]:
    """Process achievement unlock rewards. Returns list of reward descriptions."""
    import save_data as sd_module

    rewards = []
    for key in newly_unlocked:
        if key in save_data.unlocked_achievements:
            continue
        save_data.unlocked_achievements.append(key)

        ach = ACHIEVEMENT_MAP.get(key)
        if not ach:
            continue

        for unlock in ach.unlocks:
            utype = unlock["type"]
            ukey = unlock["key"]
            if utype == "piece":
                sd_module.unlock_item(save_data, "Piece", ukey)
                rewards.append({"achievement": ach.name, "type": "piece", "key": ukey})
            elif utype == "modifier":
                sd_module.unlock_item(save_data, "Modifier", ukey)
                rewards.append({"achievement": ach.name, "type": "modifier", "key": ukey})
            elif utype == "master":
                sd_module.unlock_item(save_data, "Master", ukey)
                rewards.append({"achievement": ach.name, "type": "master", "key": ukey})
            elif utype in ("artifact", "tarot", "border_mod"):
                # These are run-available items, just record them
                rewards.append({"achievement": ach.name, "type": utype, "key": ukey})

    sd_module.save(save_data)
    return rewards
