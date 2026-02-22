# Chess Roguelike — Item Expansion & Master System Design

> Massive item pool with layered synergies. Items should be useful alone but **transform** when combined.
> Inspired by Balatro's joker stacking, TBoI's item combos, and Hades' boon duos.

---

## TABLE OF CONTENTS
1. [Masters (New System)](#masters)
2. [New Pieces](#new-pieces)
3. [New Piece Modifiers](#new-piece-modifiers)
4. [New Cell Modifiers](#new-cell-modifiers)
5. [New Border Modifiers](#new-border-modifiers)
6. [New Tarot Cards](#new-tarot-cards)
7. [New Artifacts](#new-artifacts)
8. [Official Synergies](#official-synergies)
9. [Unofficial Synergy Map](#unofficial-synergy-map)

---

## MASTERS

Masters are the character you play as. Selected before a run begins. Each Master changes the fundamental rules of your run — similar to Balatro's decks or TBoI's characters. A Master defines your starting conditions, a passive effect that lasts the entire run, and a drawback that forces you to adapt.

### Existing-compatible Masters

| # | Name | Starting Bonus | Passive | Drawback |
|---|------|---------------|---------|----------|
| 1 | **The Strategist** | Start with 1 extra roster slot | Pieces gain +1 HP per wave survived | No drawback (default/tutorial master) |
| 2 | **The Arsonist** | All starting pieces gain Flaming | Fire effects deal +1 damage | Non-fire damage dealt by your pieces is halved |
| 3 | **The Blacksmith** | Start with Forge Hammer artifact | Piece modifiers cost 2 less gold | Pieces without a modifier take +2 damage |
| 4 | **The Gambler** | Start with 15 gold, Lucky Coin | Shop offers 2 extra items | All prices are randomized (0.5x to 2x cost) |
| 5 | **The Necromancer** | Start with a Phoenix and a Bomb | Dead pieces fight as ghosts for 1 extra turn | Your pieces have -2 max HP |
| 6 | **The Tactician** | Start with The Tactician tarot | Move 2 pieces per turn in manual mode | Enemy pieces also move twice per turn |
| 7 | **The Pauper** | Start with 0 gold, 4 extra Pawns | Pawns have +3 HP and promote after 1 capture | Non-Pawn pieces cost double in shop |
| 8 | **The Collector** | Start with +1 tarot slot, +1 artifact slot | Gain 1 gold whenever you acquire any item | Pieces have -1 ATK |
| 9 | **The Berserker** | All pieces start with +3 ATK | Pieces that capture gain +1 ATK permanently | Pieces lose 1 HP at the start of each turn |
| 10 | **The Warden** | Start with 2 Anchor Pieces | Pieces on border cells gain Armored | Your pieces cannot move more than 2 squares |
| 11 | **The Alchemist** | Start with 3 random cell mods pre-placed | Cell mod effects are doubled | Cell mods disappear after 3 turns |
| 12 | **The Hivemind** | Start with 3 King Rats | All same-type pieces share damage equally | You can never have more than 3 piece types |
| 13 | **The Phantom** | Start with 2 Ghosts | Your pieces can pass through enemies | Your pieces have -3 max HP |
| 14 | **The Merchant** | Start with 20 gold and The Merchant tarot | Can sell items back at 50% price | Waves give 50% less gold |
| 15 | **The Anarchist** | Start with Chaos Orb artifact | Each wave, 1 random board rule changes | You cannot buy tarot cards |
| 16 | **The Mirror** | No starting roster — copy the enemy's first wave | After each wave, gain a copy of the strongest enemy piece killed | Your copied pieces have -2 ATK |

### Master Unlock Conditions (ELO shop or achievements)
- The Strategist: Free (default)
- The Arsonist: Win a run with 3+ Flaming pieces
- The Blacksmith: Apply 10 piece modifiers in a single run
- The Gambler: Spend 100 gold in shops across runs
- The Necromancer: Have 3+ pieces revive in a single wave
- The Pauper: Win a run using only Pawns
- The Berserker: Kill 5 enemies in a single turn
- The Mirror: Win a run without buying any pieces
- (etc.)

---

## NEW PIECES

### Offensive

| # | Name | HP | ATK | Movement | Ability |
|---|------|----|-----|----------|---------|
| 1 | **Assassin** | 3 | 8 | Knight-style L-shape | Deals triple damage to full-HP targets. Dies after 2 captures. |
| 2 | **Berserker** | 10 | 2 | King (1 any) | Gains +1 ATK each time it takes damage. ATK resets on kill. |
| 3 | **Cannon** | 8 | 6 | Cannot move | Attacks the nearest enemy in any straight line (range 8). Cannot capture, only damages. |
| 4 | **Lancer** | 5 | 5 | Rook (straight lines) | Damage scales with distance moved: +1 per square traveled. |
| 5 | **Duelist** | 7 | 4 | King (1 any) | When attacking, both pieces deal their ATK simultaneously. Survives if HP > 0. |
| 6 | **Reaper** | 4 | 3 | Bishop (diagonal) | Executes enemies below 25% HP regardless of ATK. |
| 7 | **Wyvern** | 6 | 5 | Knight L-shape, +diagonal slide | Ignores ground-based cell modifiers and border mods. |
| 8 | **Charger** | 8 | 3 | Rook (straight only) | Must move at least 2 squares. +2 ATK for each square moved. |

### Defensive / Utility

| # | Name | HP | ATK | Movement | Ability |
|---|------|----|-----|----------|---------|
| 9 | **Sentinel** | 15 | 1 | King (1 any) | Adjacent friendly pieces take 50% damage (Sentinel absorbs the rest). |
| 10 | **Healer** | 5 | 0 | Bishop (diagonal) | Instead of attacking, heals target friendly for 3 HP. |
| 11 | **Bard** | 4 | 2 | King (1 any) | Adjacent friendly pieces gain +2 ATK. Buff is removed when Bard moves or dies. |
| 12 | **Wall** | 25 | 0 | Cannot move | Blocks all movement through its cell. Cannot attack. Takes -3 from all sources. |
| 13 | **Totem** | 8 | 0 | Cannot move | All friendly pieces within 2 cells regenerate 1 HP per turn. |
| 14 | **Decoy** | 1 | 0 | Cannot move | Enemies always prioritize attacking Decoy. On death, spawns 2 Pawns. |

### Weird / Chaotic

| # | Name | HP | ATK | Movement | Ability |
|---|------|----|-----|----------|---------|
| 15 | **Shapeshifter** | 5 | 3 | King (1 any) | Changes piece type each turn (cycles through your roster's types). Keeps HP. |
| 16 | **Time Mage** | 4 | 2 | King (1 any) | On death, rewinds board state by 1 turn (one-time). |
| 17 | **Imp** | 2 | 1 | Teleport to any empty cell | After moving, swaps positions of 2 random enemy pieces. |
| 18 | **Poltergeist** | 3 | 2 | Teleport to any empty cell | On death, randomly shuffles all remaining enemy positions. |
| 19 | **Alchemist** | 5 | 1 | King (1 any) | Converts the cell it stands on into a random cell modifier each turn. |
| 20 | **Golem** | 20 | 7 | King (1 any) | Loses 1 max HP permanently each turn. Cannot be healed. |
| 21 | **Witch** | 4 | 0 | Bishop (diagonal) | Curses target enemy: -2 ATK and -2 HP per turn for 3 turns. |
| 22 | **Trickster** | 3 | 3 | Knight L-shape | After attacking (hit or bounce), teleports to a random empty cell. |

---

## NEW PIECE MODIFIERS

| # | Name | Effect | Unofficial Synergizes With |
|---|------|--------|---------------------------|
| 1 | **Vampiric** | On capture, heals this piece for 50% of damage dealt | Berserker piece, Leech, Life Drain synergy |
| 2 | **Explosive** | On death, deals 5 damage in 3x3. Stacks with Bomb. | Bomb, Decoy, Flaming, Minefield synergy |
| 3 | **Frozen** | Attacks apply Chill: target can't move next turn | Witch, Parasite, Charger (frozen = easy target) |
| 4 | **Toxic** | On hit (even bounce), applies 1 poison/turn for 3 turns | Piercing (spread poison), Parasite, Leech |
| 5 | **Ethereal** | Can move through all pieces (friend and foe) | Ghost, Phantom master, Lancer (long charge through) |
| 6 | **Thorned** | Attackers take 3 retaliation damage | Armored, Sentinel, Wall, Anchor Piece |
| 7 | **Lucky** | 20% chance to dodge attacks completely | Gambler, Lucky Coin artifact, Glass Cannon |
| 8 | **Magnetic** | Pulls nearest enemy 1 cell closer at turn start | Bomb (pull into blast), Parasite, Frozen |
| 9 | **Splitting** | On death, spawns 2 Pawns with this piece's modifiers | Explosive (chain), Summoner, Decoy |
| 10 | **Reflective** | 30% of damage taken is reflected back to attacker | Thorned, Armored, Sentinel |
| 11 | **Gilded** | Earn +1 gold per capture with this piece | Gold Tooth, Merchant tarot, Collector master |
| 12 | **Titan** | +5 HP, +2 ATK, but can only move every other turn | Golem, Wall, Frozen (self-freeze irrelevant) |
| 13 | **Unstable** | +4 ATK but takes 1 self-damage per turn | Berserker piece (feeds ATK), Vampiric (offset), Healer |
| 14 | **Haunted** | On death, becomes a Ghost at 50% HP for 2 turns | Phoenix, Necromancer master, Necrotome artifact |
| 15 | **Blazing** | Leaves a fire trail: cells this piece moves through deal 1 damage to enemies that enter | Flaming, Arsonist master, Charger/Lancer |

---

## NEW CELL MODIFIERS

| # | Name | Effect | Color | Icon | Unofficial Synergizes With |
|---|------|--------|-------|------|---------------------------|
| 1 | **Inferno** | Piece on this cell gains +3 ATK but takes 1 damage/turn | Orange | "F" | Flaming, Arsonist, Armored (offset dmg) |
| 2 | **Sanctuary** | Piece on this cell heals 2 HP per turn | White | "+" | Totem, Healer, Sentinel, defensive builds |
| 3 | **Quicksand** | Piece on this cell cannot move (stuck for 1 turn) | Brown | "Q" | Cannon (doesn't move anyway), Magnetic |
| 4 | **Vortex** | At turn start, pulls all adjacent pieces 1 cell toward center | Purple | "@" | Bomb (cluster enemies), Parasite, Flaming |
| 5 | **Gold Mine** | Piece standing here earns +1 gold per turn it survives | Gold | "$" | Gilded mod, Merchant, Collector master |
| 6 | **Mirror Cell** | Piece on this cell creates a mirror image (1HP clone) on opposite cell | Cyan | "M" | Mirror Piece, Decoy strategy, Splitting |
| 7 | **Curse** | Enemy piece on this cell takes 2 damage/turn and has -2 ATK | Dark red | "X" | Witch, Toxic mod, Magnetic (pull onto curse) |
| 8 | **Amplifier** | Piece modifiers on this cell have doubled effects | Bright purple | "A" | Any piece modifier, Forge Hammer, Blacksmith |
| 9 | **Ice** | Piece slides through this cell (continues in same direction) | Light blue | "/" | Charger, Lancer (extra distance), Frozen |
| 10 | **Volcano** | Every 3 turns, deals 3 damage to all pieces within 2 cells | Red-orange | "V" | Armored, Fortified border, defensive placement |
| 11 | **Beacon** | Friendly pieces within 2 cells have +1 ATK | Warm yellow | "B" | Bard, Totem, Anchor Piece, formation play |
| 12 | **Graveyard** | When a piece dies here, spawn a Pawn (for the killer's team) | Grey-green | "G" | Assassin (kills feed army), Necromancer |

---

## NEW BORDER MODIFIERS

| # | Name | Effect | Border Color | Unofficial Synergizes With |
|---|------|--------|-------------|---------------------------|
| 1 | **Firewall** | Pieces moving through this border take 3 fire damage | Orange | Arsonist, Armored (ignore), Flaming |
| 2 | **Mirror Border** | Attacks across this border are reflected (hits attacker instead) | Silver | Defensive formations, Reflective mod |
| 3 | **Gravity Well** | Pieces adjacent to this border are pulled 1 cell toward it each turn | Dark purple | Bomb placement, Quicksand, Vortex |
| 4 | **Healing Aura** | Pieces adjacent to this border heal 1 HP per turn | Green | Sanctuary, Totem, defensive builds |
| 5 | **Speed Gate** | Pieces crossing this border get +2 move range for that turn | Cyan | Swift, Lancer, Charger |
| 6 | **Death Zone** | Pieces ending turn adjacent to this border take 2 damage | Dark red | Magnetic (push enemies in), Frozen |
| 7 | **Swap Gate** | Pieces crossing this border swap HP with the first enemy they touch | Yellow | Low-HP high-ATK pieces, Assassin |
| 8 | **Tax Border** | Enemy crossing this border gives you 2 gold | Gold | Merchant, Collector, Magnetic |

---

## NEW TAROT CARDS

| # | Name | Cost | Effect | Unofficial Synergizes With |
|---|------|------|--------|---------------------------|
| 1 | **The Inferno** | 10 | All damage triggers 1 fire splash to adjacent cells | Flaming, Arsonist master, Toxic (spread both) |
| 2 | **The Glacier** | 10 | All your attacks apply Chill (target skips next move) | Frozen mod, Charger, Lancer, assassin setups |
| 3 | **The Plague** | 11 | Enemies that die spread 2 poison stacks to adjacent enemies | Toxic mod, Reaper, AoE builds |
| 4 | **The Architect** | 9 | Start each wave with 2 random cell mods pre-placed on your half | Alchemist master, cell mod builds |
| 5 | **The Vampire** | 11 | All your pieces heal 1 HP per capture (any piece's capture) | Vampiric mod, Leech, Life Drain, sustain builds |
| 6 | **The Titan** | 12 | All pieces gain +5 HP. Pieces cannot be one-shot. | Titan mod, Golem, Wall, defensive stacking |
| 7 | **The Swarm** | 9 | Start each wave with 2 extra Pawns. Pawns gain +1 ATK for each other Pawn alive. | Pauper master, Pawn armies, Swarm Intelligence |
| 8 | **The Saboteur** | 10 | Enemy modifiers have a 30% chance to backfire each turn | Anti-modifier, combos with stealing (Leech, Mirror Shard) |
| 9 | **The Gambit** | 8 | At wave start, sacrifice 1 random piece. All others gain its ATK. | Decoy (sacrifice fodder), Splitting, Bomb |
| 10 | **The Hourglass** | 11 | Sudden death is delayed by 10 turns | Defensive/stall builds, Totem, Healer, Parasite |
| 11 | **The Chaos** | 9 | Every 3 turns, trigger a random event (heal all, damage all, shuffle, spawn piece, etc.) | Anarchist master, chaotic builds |
| 12 | **The Sacrifice** | 10 | Whenever a friendly piece dies, all other friendlies gain +1 ATK permanently | Bomb, Decoy, Splitting, expendable pieces |
| 13 | **The Crown** | 12 | Your strongest piece gains +3 ATK and Armored at wave start | Berserker, Golem, Queen, boss-killer focus |
| 14 | **The Echo** | 11 | Every capture triggers the captured piece's on-death ability twice | Bomb (double explosion), Phoenix (double revive), Mimic |
| 15 | **The Web** | 9 | Enemies that move adjacent to your pieces lose 1 move range permanently | Defensive formations, Sentinel, Wall, Bard |

---

## NEW ARTIFACTS

### Common (cost: 6-8)

| # | Name | Cost | Effect | Unofficial Synergizes With |
|---|------|------|--------|---------------------------|
| 1 | **Ember Stone** | 7 | Fire effects deal +1 damage | Flaming, Inferno cell, Arsonist, The Inferno tarot |
| 2 | **Frost Shard** | 7 | Chill effects last 1 extra turn | Frozen mod, The Glacier tarot |
| 3 | **Venom Gland** | 7 | Poison damage ticks twice per turn instead of once | Toxic mod, The Plague tarot |
| 4 | **Scout's Map** | 6 | See enemy composition during setup phase | Strategic placement, any build |
| 5 | **Training Dummy** | 8 | Your pieces gain +1 HP for each wave they survive | Long runs, sustain builds, The Titan tarot |
| 6 | **Loaded Dice** | 8 | Reroll shop once per wave for free | Merchant, Collector, finding combos |
| 7 | **Battle Standard** | 8 | Pieces within 2 cells of your King gain +1 ATK | King-centric builds, formation play |
| 8 | **Salvage Kit** | 7 | Gain 1 gold for each of your pieces that dies | Expendable builds, Bomb, Decoy, Splitting |
| 9 | **Tempo Ring** | 8 | Your first piece to move each turn gets +2 ATK for that attack | Assassin, Charger, alpha-strike builds |

### Uncommon (cost: 9-12)

| # | Name | Cost | Effect | Unofficial Synergizes With |
|---|------|------|--------|---------------------------|
| 10 | **Soul Jar** | 10 | Store up to 3 dead pieces. They revive at wave start with 50% HP | Phoenix, Necromancer master, Haunted mod |
| 11 | **Chain Mail** | 10 | Armored effect increased to -3 damage (from -2) | Armored mod, Fortress tarot, Warden master |
| 12 | **Berserker's Torc** | 11 | Pieces below 50% HP gain +3 ATK | Berserker piece, Unstable mod, risky plays |
| 13 | **Phase Cloak** | 10 | Once per wave, a piece that would die instead teleports to random empty cell at 1 HP | Anchor Chain (2 saves), survival builds |
| 14 | **Plague Doctor's Mask** | 11 | Your pieces are immune to poison and curse effects | Anti-debuff, pairs with Toxic/Witch on your side |
| 15 | **Trophy Rack** | 10 | +1 gold for each different piece type you've killed this run | Long runs, diverse enemy kills |
| 16 | **Resonance Crystal** | 12 | When any synergy activates, all synergy effects are +50% stronger | Multi-synergy builds, synergy stacking |
| 17 | **Echo Chamber** | 11 | Cell modifier effects trigger twice | Alchemist master, cell mod builds, Amplifier |
| 18 | **Blood Altar** | 10 | Sacrifice a piece at wave start: all others gain +2 ATK for the wave | Decoy, Splitting, expendable units, The Sacrifice |

### Rare (cost: 12-16)

| # | Name | Cost | Effect | Unofficial Synergizes With |
|---|------|------|--------|---------------------------|
| 19 | **Doomsday Clock** | 14 | Sudden death deals double damage and closes 2x faster, but you deal +50% damage | Aggressive builds, Berserker master |
| 20 | **Philosopher's Stone** | 16 | All piece modifiers can stack (same mod applied twice = double effect) | Forge Hammer, Blacksmith master, mod stacking |
| 21 | **Pandora's Box** | 13 | Start each wave with 3 random modifiers applied to random pieces (can be bad) | Chaotic builds, Anarchist master |
| 22 | **Grimoire** | 14 | +2 tarot slots | Collector master, tarot-heavy builds |
| 23 | **Arsenal** | 14 | +2 artifact slots | Collector master, artifact-heavy builds |
| 24 | **General's Baton** | 15 | In manual mode, move 3 pieces per turn. In auto mode, AI considers 2 moves ahead. | Tactician master, manual mode play |
| 25 | **Infinity Loop** | 16 | Synergy requirements are reduced by 1 piece/item | Multi-synergy, easier activation |
| 26 | **Dragon's Hoard** | 13 | +3 gold per wave. Each wave, a random shop item costs 0. | Economy builds, Merchant, Collector |
| 27 | **Chaos Engine** | 14 | At the start of each wave, a random game rule changes (ally/enemy ATK swap, gravity reversal, etc.) | Anarchist master, adapting on the fly |

---

## OFFICIAL SYNERGIES

Official synergies appear in the Chessticon codex. They provide a named bonus when all required items are present.

### Fire Synergies

| # | Name | Requirements | Bonus |
|---|------|-------------|-------|
| 1 | **Firestorm** | Flaming mod + Inferno cell + Ember Stone artifact | All fire damage chains: hitting an enemy spreads fire to adjacent enemies |
| 2 | **Scorched Earth** | Arsonist master + Blazing mod + The Inferno tarot | Killed enemies leave permanent Inferno cells on their death squares |
| 3 | **Pyromancer** | 3+ pieces with Flaming + Ember Stone | Fire splash range increased to 5x5 |

### Ice / Control Synergies

| # | Name | Requirements | Bonus |
|---|------|-------------|-------|
| 4 | **Permafrost** | Frozen mod + Frost Shard artifact + The Glacier tarot | Chilled enemies also take 2 damage per turn while frozen |
| 5 | **Absolute Zero** | 3+ pieces with Frozen + Frost Shard | Frozen enemies shatter (instant kill) if hit while chilled |

### Poison Synergies

| # | Name | Requirements | Bonus |
|---|------|-------------|-------|
| 6 | **Pandemic** | Toxic mod + Venom Gland + The Plague tarot | Poison spreads to adjacent enemies when a poisoned enemy dies |
| 7 | **Blight** | 3+ pieces with Toxic + Witch piece | Poison stacks are uncapped and each stack increases damage by 1 |

### Death / Sacrifice Synergies

| # | Name | Requirements | Bonus |
|---|------|-------------|-------|
| 8 | **Martyrdom** | The Sacrifice tarot + Blood Altar artifact + Bomb | When a piece is sacrificed, it explodes like a Bomb |
| 9 | **Undying Legion** | Phoenix + Soul Jar + Haunted mod | Revived pieces return at full HP with +2 ATK |
| 10 | **Death's Harvest** | Reaper piece + The Sacrifice tarot + Salvage Kit | Reaper executes below 50% HP instead of 25%. +2 gold per Reaper kill. |

### Formation / Defensive Synergies

| # | Name | Requirements | Bonus |
|---|------|-------------|-------|
| 11 | **Iron Phalanx** | Sentinel + Wall + Armored mod on 2+ pieces | All pieces in a 2-cell radius of Wall take -5 damage |
| 12 | **Sacred Ground** | Totem + Sanctuary cell + Healing Aura border | Healing effects doubled. Pieces at full HP gain +1 ATK. |
| 13 | **Fortress Protocol** | Warden master + Fortified border + Armored mod on 3+ pieces | Armored reduces damage by 4 instead of 2 |

### Buff / ATK Synergies

| # | Name | Requirements | Bonus |
|---|------|-------------|-------|
| 14 | **War Machine** | Berserker piece + Berserker's Torc artifact + Unstable mod | Berserker gains +2 ATK per damage taken instead of +1. No ATK cap. |
| 15 | **Alpha Strike** | Assassin + Tempo Ring artifact + Swift mod | First attack each wave is guaranteed kill (ignores HP) |
| 16 | **Battle Hymn** | Bard + Battle Standard artifact + Beacon cell | All ATK buffs provide double their value |

### Economy Synergies

| # | Name | Requirements | Bonus |
|---|------|-------------|-------|
| 17 | **Midas Touch** | Gilded mod + Gold Mine cell + Gold Tooth artifact | Every capture gives +3 gold. Shop prices reduced by 20%. |
| 18 | **Trade Empire** | Merchant master + Dragon's Hoard + Lucky Coin | Shop offers 4 extra items. One random item per shop is free. |

### Chaos Synergies

| # | Name | Requirements | Bonus |
|---|------|-------------|-------|
| 19 | **Entropy** | Anarchist master + Chaos Engine artifact + The Chaos tarot | Random events always benefit you (heal, buff, gold) and harm enemies |
| 20 | **Madness** | Poltergeist + Imp + The Chaos tarot | Enemy positions shuffle every 3 turns. Your pieces are immune to shuffle. |

### Swarm Synergies

| # | Name | Requirements | Bonus |
|---|------|-------------|-------|
| 21 | **Endless Horde** | Pauper master + The Swarm tarot + Splitting mod | Pawns that die spawn 2 Pawns. Those Pawns also have Splitting. |
| 22 | **Pack Hunters** | 4+ King Rats + Rat King synergy | King Rats gain +1 ATK and +1 HP for EACH King Rat alive (exponential scaling) |

### Cross-Element Synergies

| # | Name | Requirements | Bonus |
|---|------|-------------|-------|
| 23 | **Elemental Fury** | Flaming + Frozen + Toxic on 3 different pieces | All elemental effects trigger simultaneously on every attack |
| 24 | **Thermal Shock** | Frozen mod + Flaming mod (on different pieces) + any fire artifact | Frozen enemies hit with fire take 3x damage |

### Master-Specific Synergies

| # | Name | Requirements | Bonus |
|---|------|-------------|-------|
| 25 | **Master Forger** | Blacksmith master + Philosopher's Stone + Forge Hammer | Pieces can hold 4 modifiers. Modifier costs reduced to 1 gold. |
| 26 | **Phantom Army** | Phantom master + Necromancer master's piece (Phoenix) + Haunted mod | All your pieces gain Ethereal. Ghost pieces deal +3 damage. |
| 27 | **The Collection** | Collector master + Grimoire + Arsenal + 3+ artifacts + 2+ tarots | All item effects are +100% stronger |
| 28 | **Blood Economy** | Berserker master + Vampiric mod + Blood Altar | Berserker HP drain now heals 2 HP per kill instead. ATK gains are permanent across waves. |

---

## UNOFFICIAL SYNERGY MAP

These are NOT marked in the Chessticon. Players discover them naturally. Items buff each other indirectly.

### Fire Web
```
Flaming mod ──── Ember Stone artifact ──── The Inferno tarot
    │                    │                        │
    ├── Arsonist master  ├── Blazing mod          ├── Inferno cell mod
    │                    │                        │
    └── Explosive mod    └── Firewall border      └── Volcano cell mod
```
Any combination amplifies fire damage even without the official synergy.

### Poison Web
```
Toxic mod ──── Venom Gland artifact ──── The Plague tarot
    │                  │                       │
    ├── Witch piece    ├── Parasite piece       ├── Curse cell mod
    │                                          │
    └── Leech piece (spread via steal)         └── Death Zone border
```

### Sustain / Healing Web
```
Vampiric mod ──── The Vampire tarot ──── Healer piece
    │                    │                    │
    ├── Leech piece      ├── Sanctuary cell   ├── Totem piece
    │                    │                    │
    └── Life Drain syn.  └── Healing Aura     └── Training Dummy artifact
```

### Economy Web
```
Gilded mod ──── Gold Tooth artifact ──── Merchant tarot
    │                  │                      │
    ├── Gold Mine cell ├── Trophy Rack        ├── Dragon's Hoard
    │                  │                      │
    └── Salvage Kit    └── Tax Border         └── Lucky Coin
```

### ATK Stacking Web
```
Berserker piece ──── Berserker's Torc ──── Unstable mod
    │                      │                     │
    ├── Bard piece         ├── Inferno cell      ├── The Sacrifice tarot
    │                      │                     │
    └── Battle Standard    └── Beacon cell       └── Blood Altar
```

### Death Cascade Web
```
Bomb ──── Explosive mod ──── Splitting mod
 │              │                  │
 ├── Decoy     ├── Minefield syn. ├── The Sacrifice tarot
 │              │                  │
 └── Martyrdom └── The Echo tarot └── Salvage Kit (profit from deaths)
```

### Control / Lockdown Web
```
Frozen mod ──── Frost Shard ──── The Glacier tarot
    │                │                  │
    ├── Quicksand    ├── Ice cell       ├── Witch piece
    │                │                  │
    └── Magnetic mod └── Gravity Well   └── The Web tarot
```

### Piece Multiplication Web
```
Summoner ──── Splitting mod ──── Decoy piece
    │               │                 │
    ├── The Swarm   ├── Pauper master ├── Graveyard cell
    │               │                 │
    └── Swarm Intel └── Necromancer   └── Soul Jar
```

---

## DESIGN PHILOSOPHY

### Standalone Viability
Every item should be worth buying even if you have zero other items in its web. A Frozen mod is useful on its own (skip enemy turns). Ember Stone is useful even without Flaming (it buffs Inferno cells, Firewall borders, etc.).

### Discovery Layers
1. **Obvious**: Flaming + Ember Stone = more fire damage
2. **Clever**: Magnetic mod + Bomb = pull enemies into explosion range
3. **Galaxy brain**: Decoy (enemies focus it) + Explosive mod (it explodes on death) + Splitting (spawns 2 explosive Pawns) + The Sacrifice tarot (team gets +ATK from each death) + Salvage Kit (earn gold from each death) = a death cascade engine that funds itself

### Power Scaling
- **1 item**: Functional, slight edge
- **2 items in same web**: Noticeable combo, feels good
- **3+ items in same web**: Build-defining, run warping
- **Official synergy complete**: Dramatically alters gameplay, win condition enabler

### Balatro-style "Break the Game" Moments
The system should allow for runs where the math breaks in your favor:
- Berserker at low HP + Berserker's Torc + Unstable = ATK climbing every turn from both self-damage AND enemy hits
- Midas Touch synergy + Gilded on all pieces = drowning in gold, buying everything
- Endless Horde = screen filling with Pawns that each spawn more Pawns on death
- Elemental Fury = every attack procs fire + ice + poison simultaneously

### Anti-Synergies (Intentional Tension)
Some items create interesting tradeoffs:
- Armored (-2 damage taken) vs Berserker piece (wants to take damage for ATK)
- Healer (can't attack) vs The Sacrifice tarot (wants pieces to die)
- Frozen mod (control) vs Berserker's Torc (wants enemies hitting you)
- Wall (can't move) vs Swift mod (extra movement is wasted)

Players should feel clever when they identify which items conflict and which transform each other.
