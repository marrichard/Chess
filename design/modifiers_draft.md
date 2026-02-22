# Modifier & Synergy Draft

## Current System
- 5 piece mods: flaming, armored, swift, piercing, royal
- 4 cell mods: rage, shield, haste, phase
- 3 border mods: fortified, thorns, anchor

---

## New Piece Modifiers

### Offensive
| Name | Effect | Description |
|------|--------|-------------|
| **Vampiric** | `vampiric` | On capture, heal one dead roster piece back to alive for next wave |
| **Explosive** | `explosive` | On death, damages all adjacent pieces (friend or foe) |
| **Venomous** | `venomous` | Pieces you attack but don't kill (armored saves) are poisoned — they die at end of round |
| **Rallying** | `rallying` | After this piece captures, one random friendly piece gets +1 move range for the rest of the battle |
| **Magnetic** | `magnetic` | Pulls the nearest enemy 1 square closer at the start of each turn (before moving) |

### Defensive
| Name | Effect | Description |
|------|--------|-------------|
| **Regenerating** | `regenerating` | Survives first capture (like armored), but the armor comes back after 3 turns |
| **Ghostly** | `ghostly` | 50% chance to dodge any capture (coin flip) |
| **Guardian** | `guardian` | Adjacent friendly pieces can't be captured |

### Utility
| Name | Effect | Description |
|------|--------|-------------|
| **Tactical** | `tactical` | This piece can move twice per turn |
| **Mimic** | `mimic` | Copies the movement pattern of the piece it captures (Pawn captures Knight -> moves like Knight) |
| **Hexing** | `hexing` | On capture, removes one random modifier from the nearest enemy piece |

## New Cell Modifiers
| Name | Effect | Color | Description |
|------|--------|-------|-------------|
| **Trap** | `trap` | (200, 80, 80) | First enemy to step here is instantly killed |
| **Rally Point** | `rally_point` | (255, 180, 50) | Pieces starting on this cell get +1 move range for the wave |
| **Void** | `void` | (80, 0, 120) | Pieces on this cell can't be targeted by ranged effects (flaming splash, rage, explosive) |

## New Border Modifiers
| Name | Effect | Border Color | Description |
|------|--------|--------------|-------------|
| **Launcher** | `launcher` | (100, 200, 255) | Piece here gets teleported to a random empty square after each move |
| **Crown** | `crown` | (255, 215, 0) | Piece standing here earns 2x gold when the wave is won |

---

## Synergies

### Piece + Piece Synergies

| Combo | Name | Effect |
|-------|------|--------|
| **Flaming + Piercing** | *Fire Lance* | Flaming splash damage also fires along the piercing line (damages the whole row/diagonal, not just adjacent) |
| **Flaming + Explosive** | *Inferno* | Explosive death radius increases from adjacent (1) to radius 2, and the blast applies flaming to surviving pieces |
| **Swift + Piercing** | *Lancer* | Piece can charge: move in a straight line up to 3 squares, capturing the first enemy hit and continuing through |
| **Armored + Venomous** | *Toxic Shell* | When armor absorbs a hit, the attacker gets poisoned (dies end of round) |
| **Vampiric + Flaming** | *Soul Fire* | Splash damage kills also count as captures for vampiric healing |
| **Royal + Guardian** | *Sovereign* | Guardian protection extends to all friendly pieces within radius 2 (not just adjacent) |
| **Ghostly + Swift** | *Phantom* | When dodge triggers, piece teleports to a random empty square instead of staying in place |
| **Tactical + Magnetic** | *Commander* | Instead of pulling 1 enemy, pulls ALL enemies within range 2 one square closer |
| **Rallying + Royal** | *Warlord* | The rally buff is permanent for the rest of the run (not just the battle) |
| **Explosive + Armored** | *Martyr* | Survives its own explosion, essentially becoming a reusable bomb |
| **Venomous + Piercing** | *Plague* | Poison spreads — when a poisoned piece dies, pieces adjacent to it also get poisoned |
| **Mimic + Swift** | *Shapeshifter* | Keeps BOTH the original and copied movement pattern |
| **Hexing + Vampiric** | *Witch* | Stolen modifiers are applied to a random friendly piece instead of being destroyed |

### Piece + Cell Synergies

| Combo | Name | Effect |
|-------|------|--------|
| **Flaming + Rage cell** | *Berserker* | Splash damage hits ALL adjacent enemies (not random 1), and splash range extends to 2 |
| **Armored + Shield cell** | *Fortress* | Piece gets 3 total capture-survivals instead of 1+1 |
| **Ghostly + Phase cell** | *Wraith* | Dodge chance increases to 75%, and piece can move through enemy pieces too |
| **Vampiric + Rally Point cell** | *War Medic* | On capture, heals TWO dead roster pieces and gives both +1 move range |

### Piece + Border Synergies

| Combo | Name | Effect |
|-------|------|--------|
| **Explosive + Thorns border** | *Minefield* | When this piece dies to thorns, the explosion radius is doubled |
| **Guardian + Fortified border** | *Bastion* | The fortified effect extends to all adjacent cells too |
| **Royal + Crown border** | *Emperor* | All friendly pieces on the board earn 2x gold (not just this one) |

### Triple Synergies (rare, build-defining)

| Combo | Name | Effect |
|-------|------|--------|
| **Flaming + Explosive + Rage cell** | *Apocalypse* | On death, entire board erupts — all enemy pieces take damage, armored lose armor |
| **Swift + Tactical + Haste cell** | *Blitz* | Piece moves 3 times per turn with king+original movement on each |
| **Armored + Regenerating + Shield cell** | *Immortal* | Piece literally cannot die — always regenerates (but can only attack once per 2 turns as penalty) |
| **Vampiric + Venomous + Hexing** | *Lich* | Poison kills trigger vampiric healing AND steal a modifier, creating a snowball engine |

---

## Build Archetypes

| Archetype | Core Mods | Strategy |
|-----------|-----------|----------|
| **Pyromancer** | Flaming + Explosive + Rage | Maximum area damage, clear whole board with chain reactions |
| **Assassin** | Swift + Piercing + Tactical | Extreme mobility, hit-and-run, pick off key targets |
| **Necromancer** | Vampiric + Venomous + Hexing | Kill chain — each kill makes the next easier, recover dead pieces |
| **Fortress** | Armored + Guardian + Fortified | Create an unkillable zone, win by attrition |
| **Warlord** | Royal + Rallying + Crown | Economy focus — survive and maximize gold per wave |
| **Chaos** | Explosive + Ghostly + Mimic | Unpredictable, high-variance, can swing any fight |

---

## HP System Proposal

Small numbers, keeps chess feel for pawns:

```
Pawn:   1 HP    (still dies in one hit)
Knight: 2 HP
Bishop: 2 HP
Rook:   3 HP
Queen:  4 HP
King:   5 HP
```

All captures deal 1 damage by default. Modifiers can add +damage, healing, poison, etc.

### How Existing Modifiers Map With HP

| Current Modifier | New Behavior |
|-----------------|-------------|
| **Armored** | +2 max HP |
| **Flaming** | Captures deal 1 splash damage to adjacent enemies |
| **Piercing** | Captures deal +1 bonus damage to the target |
| **Swift** | Unchanged (movement) |
| **Royal** | Unchanged (scoring) |
| **Shield (cell)** | +1 temporary HP for the round |
| **Rage (cell)** | Captures deal 1 damage to a random adjacent enemy |
| **Thorns (border)** | Attacker takes 1 damage when capturing piece on this cell |
| **Fortified (border)** | Piece on this cell takes 1 less damage (min 0) |

### New Modifiers HP Enables

| Name | Effect | Description |
|------|--------|-------------|
| **Venomous** | `venomous` | Target takes 1 additional damage at end of next turn |
| **Lifesteal** | `lifesteal` | Heal 1 HP on capture |
| **Heavy** | `heavy` | Captures deal +1 damage, but piece loses swift/haste |
| **Fragile** | `fragile` | -1 max HP, but +1 move range (curse/blessing) |
| **Rallying** | `rallying` | Adjacent friendlies heal 1 HP when this piece captures |
| **Explosive** | `explosive` | On death, deal 1 damage to ALL adjacent (friend and foe) |

### HP Synergies

- **Venomous + Piercing** = *Plague*: poison spreads to adjacent when target dies
- **Lifesteal + Flaming** = *Soul Fire*: splash kills also heal
- **Heavy + Explosive** = *Martyr*: explosion deals 2 damage instead of 1

---

## Implementation Notes

### Synergy Detection
```python
def has_synergy(piece, *effects):
    piece_effects = {m.effect for m in piece.modifiers}
    if piece.cell_modifier:
        piece_effects.add(piece.cell_modifier.effect)
    return all(e in piece_effects for e in effects)
```

### Multi-Modifier Slots
Currently pieces can only hold one modifier (shop checks `not p.modifiers`).
Allowing 2-3 modifiers per piece unlocks the synergy system.
- 1 slot default
- 2nd slot unlocked via ELO shop
- 3rd from a rare draft option

### Synergy Discovery UI
When a synergy activates for the first time, flash a named banner ("FIRE LANCE!").
This is the Balatro moment where players discover combos and want to chase them again.
