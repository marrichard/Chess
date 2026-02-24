"""Grid/board logic — placement, validation, capture detection."""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pieces import Piece, Team, PieceType

if TYPE_CHECKING:
    from modifiers import CellModifier, BorderModifier


@dataclass
class Board:
    """A chess-like grid that holds pieces and obstacles."""
    width: int = 8
    height: int = 8
    pieces: list[Piece] = field(default_factory=list)
    blocked_tiles: set[tuple[int, int]] = field(default_factory=set)
    cell_modifiers: dict[tuple[int, int], CellModifier] = field(default_factory=dict)
    border_modifiers: dict[tuple[int, int], BorderModifier] = field(default_factory=dict)
    dead_zone: set[tuple[int, int]] = field(default_factory=set)
    _grid: dict[tuple[int, int], Piece] = field(default_factory=dict, repr=False)
    _grid_dirty: bool = field(default=True, repr=False)
    master_effects: list[str] = field(default_factory=list)

    def _ensure_grid(self) -> None:
        """Rebuild spatial lookup if dirty."""
        if not self._grid_dirty:
            return
        self._grid.clear()
        for p in self.pieces:
            if p.alive:
                self._grid[(p.x, p.y)] = p
        self._grid_dirty = False

    def invalidate_grid(self) -> None:
        """Mark grid as needing rebuild. Call after any piece mutation."""
        self._grid_dirty = True

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height and (x, y) not in self.dead_zone

    def is_empty(self, x: int, y: int) -> bool:
        if (x, y) in self.blocked_tiles:
            return False
        self._ensure_grid()
        return (x, y) not in self._grid

    def is_blocked(self, x: int, y: int) -> bool:
        return (x, y) in self.blocked_tiles

    def get_piece_at(self, x: int, y: int) -> Piece | None:
        self._ensure_grid()
        return self._grid.get((x, y))

    def get_team_pieces(self, team: Team) -> list[Piece]:
        return [p for p in self.pieces if p.alive and p.team == team]

    def place_piece(self, piece: Piece, x: int, y: int) -> bool:
        """Place a piece on the board. Returns False if position is invalid."""
        if not self.in_bounds(x, y):
            return False
        if self.is_blocked(x, y):
            return False
        if self.get_piece_at(x, y) is not None:
            return False
        piece.x = x
        piece.y = y
        piece.alive = True
        if piece not in self.pieces:
            self.pieces.append(piece)
        self._grid_dirty = True
        return True

    def move_piece(self, piece: Piece, nx: int, ny: int, rng: random.Random | None = None,
                   active_synergies: list[str] | None = None,
                   master_effects: list[str] | None = None) -> Piece | None:
        """Move a piece to (nx, ny). Returns captured piece or None.

        HP combat: attacker deals damage to target. If target survives, attacker
        bounces back to origin. If target dies, attacker moves to cell.
        """
        import random as _random_mod
        _rng = rng or _random_mod
        _synergies = active_synergies or []
        _masters = master_effects or []

        old_x, old_y = piece.x, piece.y
        captured = None
        target = self.get_piece_at(nx, ny)
        # Invalidate grid upfront — positions/alive will change during combat
        self._grid_dirty = True

        # Healer: heal friendly target instead of attacking
        if target and target.team == piece.team and piece.piece_type == PieceType.HEALER:
            if self._can_heal(target):
                heal_amount = 3
                target.hp = min(target.max_hp, target.hp + heal_amount)
            piece.has_moved = True
            return None

        if target and target.team != piece.team:
            # Border modifier checks on target cell
            target_bm = self.border_modifiers.get((target.x, target.y))

            # Fortified border modifier: piece on this cell cannot be captured
            if target_bm and target_bm.effect == "fortified":
                return None

            # Mirror border: all damage reflected back to attacker instead
            if target_bm and target_bm.effect == "mirror_border":
                reflected_dmg = piece.attack
                piece.hp -= reflected_dmg
                if piece.hp <= 0:
                    piece.alive = False
                piece.has_moved = True
                return None

            # Firewall: attacker crossing into firewall takes 3 fire damage before combat
            if target_bm and target_bm.effect == "firewall":
                piece.hp -= 3
                if piece.hp <= 0:
                    piece.alive = False
                    piece.has_moved = True
                    return None

            # Swap gate: swap HP values between attacker and defender
            if target_bm and target_bm.effect == "swap_gate":
                piece.hp, target.hp = target.hp, piece.hp
                piece.has_moved = True
                return None

            # Tax border: enemy crossing onto this cell grants player gold
            if target_bm and target_bm.effect == "tax_border" and piece.team == Team.ENEMY:
                piece.ability_flags["tax_gold_earned"] = piece.ability_flags.get("tax_gold_earned", 0) + 2

            # --- Calculate damage ---
            damage = piece.attack

            # Arsonist master: fire attacks +1, non-fire attacks halved
            if "arsonist_passive" in _masters and piece.team == Team.PLAYER:
                if any(m.effect == "flaming" for m in piece.modifiers):
                    damage += 1
            if "arsonist_drawback" in _masters and piece.team == Team.PLAYER:
                if not any(m.effect == "flaming" for m in piece.modifiers):
                    damage = damage // 2

            # Alpha Strike synergy: first attack each wave is guaranteed kill
            if "alpha_strike" in _synergies and not piece.ability_flags.get("alpha_strike_used"):
                piece.ability_flags["alpha_strike_used"] = True
                damage = target.hp  # guaranteed kill

            # Phantom Army synergy: Ghost pieces deal +3 damage
            if "phantom_army" in _synergies and piece.piece_type == PieceType.GHOST:
                damage += 3

            # Assassin: triple damage to full-HP targets
            if piece.piece_type == PieceType.ASSASSIN and target.hp == target.max_hp:
                damage *= 3

            # Lancer: +1 damage per square moved
            if piece.piece_type == PieceType.LANCER:
                dist = abs(nx - old_x) + abs(ny - old_y)
                damage += dist

            # Charger: +2 ATK per square moved (Manhattan distance)
            if piece.piece_type == PieceType.CHARGER:
                dist = abs(nx - old_x) + abs(ny - old_y)
                damage += dist * 2

            # Gambler: 50% chance damage = 0 (unless glass_cannon synergy)
            if piece.piece_type == PieceType.GAMBLER:
                if "glass_cannon" in _synergies:
                    pass  # never misses
                elif _rng.random() < 0.5:
                    damage = 0

            # Lucky modifier on target: 20% dodge chance
            if any(m.effect == "lucky" for m in target.modifiers):
                if _rng.random() < 0.2:
                    damage = 0

            # Absolute Zero synergy: chilled enemies shatter (instant kill) if hit
            if "absolute_zero" in _synergies and target.ability_flags.get("chilled") and damage > 0:
                damage = target.hp

            # Thermal Shock synergy: frozen+fire hit = 3x damage
            if ("thermal_shock" in _synergies and target.ability_flags.get("chilled")
                    and any(m.effect == "flaming" for m in piece.modifiers) and damage > 0):
                damage *= 3

            # Executioner tarot: first attack ignores all damage reduction
            is_executioner = (piece.ability_flags.get("the_executioner")
                              and not piece.ability_flags.get("executioner_used_this_turn"))
            if is_executioner:
                piece.ability_flags["executioner_used_this_turn"] = True
            else:
                # --- Damage reduction pipeline ---
                # Anchor piece aura: reduce damage if target is near an anchor
                damage = max(0, damage - self.get_anchor_damage_reduction(target.x, target.y, target.team))

                # Armored modifier: -2 incoming damage (persistent, not consumed)
                if any(m.effect == "armored" for m in target.modifiers):
                    armor_reduction = 2
                    # Chain Mail artifact: armored reduces by 3 (checked via ability_flags)
                    if target.ability_flags.get("chain_mail"):
                        armor_reduction = 3
                    # Fortress Protocol synergy: reduces by 4
                    if "fortress_protocol" in _synergies and target.team == Team.PLAYER:
                        armor_reduction = 4
                    damage = max(0, damage - armor_reduction)

                # Iron Phalanx synergy: pieces within 2 cells of Wall take -5 damage
                if "iron_phalanx" in _synergies and target.team == Team.PLAYER:
                    for wall in self.pieces:
                        if (wall.alive and wall.piece_type == PieceType.WALL
                                and wall.team == target.team
                                and abs(wall.x - target.x) <= 2 and abs(wall.y - target.y) <= 2):
                            damage = max(0, damage - 5)
                            break

                # Blacksmith drawback: unmodded pieces take +2 damage
                if "blacksmith_drawback" in _masters and target.team == Team.PLAYER and not target.modifiers:
                    damage += 2

                # Wall: takes -3 from all sources
                if target.piece_type == PieceType.WALL:
                    damage = max(0, damage - 3)

                # Shield cell modifier: -3 incoming damage (consumed)
                has_shield = (target.cell_modifier and target.cell_modifier.effect == "shield")
                if has_shield:
                    damage = max(0, damage - 3)
                    target.cell_modifier = None  # consume the shield

            # Reaper: execute enemies below 25% HP (or 50% with deaths_harvest)
            if piece.piece_type == PieceType.REAPER:
                threshold = 0.5 if "deaths_harvest" in _synergies else 0.25
                if target.hp <= target.max_hp * threshold:
                    damage = target.hp  # guaranteed kill

            # Sentinel: adjacent friendly Sentinels absorb 50% of incoming damage
            if damage > 0:
                for sp in self.pieces:
                    if (sp.alive and sp.team == target.team
                            and sp.piece_type == PieceType.SENTINEL
                            and sp is not target
                            and abs(sp.x - target.x) <= 1
                            and abs(sp.y - target.y) <= 1):
                        absorbed = damage // 2
                        sp.hp -= absorbed
                        if sp.hp <= 0:
                            sp.alive = False
                        damage -= absorbed
                        break  # only one Sentinel absorbs per hit

            # Reflective modifier: 30% of damage reflected back to attacker
            if any(m.effect == "reflective" for m in target.modifiers) and damage > 0:
                reflected = max(1, int(damage * 0.3))
                piece.hp -= reflected
                if piece.hp <= 0:
                    piece.alive = False

            # Hivemind master passive: same-type pieces share damage equally
            if "hivemind_passive" in _masters and target.team == Team.PLAYER and damage > 0:
                same_type = [p for p in self.get_team_pieces(target.team)
                             if p.alive and p.piece_type == target.piece_type]
                if len(same_type) > 1:
                    shared_dmg = max(1, damage // len(same_type))
                    for p in same_type:
                        if p is not target:
                            p.hp -= shared_dmg
                            if p.hp <= 0:
                                p.alive = False
                    damage = shared_dmg  # target takes its share

            # Apply damage
            target.hp -= damage

            # Frozen modifier on attacker: apply chill to target
            if any(m.effect == "frozen" for m in piece.modifiers) and damage > 0:
                chill_duration = 1
                if target.ability_flags.get("frost_shard"):
                    chill_duration = 2
                target.status_effects.append({"type": "chill", "duration": chill_duration})

            # Toxic modifier on attacker: apply poison to target
            if any(m.effect == "toxic" for m in piece.modifiers):
                target.status_effects.append({"type": "poison", "duration": 3, "magnitude": 1})

            # Witch: curse target (-2 ATK, -2 HP/turn for 3 turns)
            if piece.piece_type == PieceType.WITCH and target.alive:
                target.status_effects.append({"type": "curse", "duration": 3})
                target.attack = max(0, target.attack - 2)

            # Elemental Fury synergy: all elemental effects trigger on every attack
            if "elemental_fury" in _synergies and damage > 0 and target.alive:
                has_flaming = any(m.effect == "flaming" for m in piece.modifiers)
                has_frozen = any(m.effect == "frozen" for m in piece.modifiers)
                has_toxic = any(m.effect == "toxic" for m in piece.modifiers)
                # Apply missing effects
                if not has_frozen:
                    target.status_effects.append({"type": "chill", "duration": 1})
                if not has_toxic:
                    target.status_effects.append({"type": "poison", "duration": 3, "magnitude": 1})
                if not has_flaming:
                    # Apply 2 fire splash damage to target
                    target.hp -= 2
                    if target.hp <= 0:
                        target.alive = False

            # Thorns border modifier: 2 retaliation damage to attacker
            if (target.x, target.y) in self.border_modifiers:
                bm = self.border_modifiers[(target.x, target.y)]
                if bm.effect == "thorns":
                    piece.hp -= 2
                    if piece.hp <= 0:
                        piece.alive = False

            # Thorned piece modifier: 3 retaliation damage
            if any(m.effect == "thorned" for m in target.modifiers) and piece.alive:
                piece.hp -= 3
                if piece.hp <= 0:
                    piece.alive = False

            # Leech: heal attacker equal to damage dealt
            if piece.piece_type == PieceType.LEECH and damage > 0 and self._can_heal(piece):
                piece.hp = min(piece.max_hp, piece.hp + damage)

            # Vampiric modifier: heal 50% of damage dealt on capture
            if any(m.effect == "vampiric" for m in piece.modifiers) and damage > 0 and self._can_heal(piece):
                heal = max(1, damage // 2)
                piece.hp = min(piece.max_hp, piece.hp + heal)

            # Berserker piece: gains +1 ATK when damaged (target hits back on bounce)
            if target.hp > 0 and piece.piece_type == PieceType.BERSERKER_PIECE:
                # Berserker took retaliation conceptually - gain ATK
                gain = 2 if "war_machine" in _synergies else 1
                piece.attack += gain

            # Duelist: both deal ATK simultaneously
            if piece.piece_type == PieceType.DUELIST and target.alive:
                piece.hp -= target.attack
                if piece.hp <= 0:
                    piece.alive = False

            # Glass cannon synergy: gambler takes double damage from retaliation
            if piece.piece_type == PieceType.GAMBLER and "glass_cannon" in _synergies:
                if target.hp > 0 and target.attack > 0:
                    piece.hp -= target.attack * 2

            if target.hp <= 0:
                # Target dies
                target.alive = False
                captured = target

                # Attacker moves to target cell
                piece.x = nx
                piece.y = ny
                piece.has_moved = True

                # Assassin: track captures, die after 3
                if piece.piece_type == PieceType.ASSASSIN:
                    kills = piece.ability_flags.get("assassin_kills", 0) + 1
                    piece.ability_flags["assassin_kills"] = kills
                    if kills >= 3:
                        piece.hp = 0
                        piece.alive = False

                # Berserker piece: ATK resets on kill
                if piece.piece_type == PieceType.BERSERKER_PIECE:
                    from pieces import PIECE_STATS
                    _, base_atk = PIECE_STATS[PieceType.BERSERKER_PIECE]
                    piece.attack = base_atk

                # Golem: recover 2 max HP on kill (offsets erosion)
                if piece.piece_type == PieceType.GOLEM:
                    piece.max_hp += 2
                    piece.hp = min(piece.max_hp, piece.hp + 2)

                # Leech on kill: steal one random modifier from victim
                if piece.piece_type == PieceType.LEECH and target.modifiers:
                    num_steal = 2 if "identity_theft" in _synergies else 1
                    for _ in range(min(num_steal, len(target.modifiers))):
                        stolen = _rng.choice(target.modifiers)
                        if not any(m.effect == stolen.effect for m in piece.modifiers):
                            piece.modifiers.append(stolen)

                # Midas Touch synergy: captures give +3 gold
                if "midas_touch" in _synergies and piece.team == Team.PLAYER:
                    piece.ability_flags["midas_gold"] = piece.ability_flags.get("midas_gold", 0) + 3

                # Blood Economy synergy: berserker ATK gains permanent, heal 2 on kill
                if "blood_economy" in _synergies and piece.piece_type == PieceType.BERSERKER_PIECE:
                    if self._can_heal(piece):
                        piece.hp = min(piece.max_hp, piece.hp + 2)
                    # Don't reset ATK (overrides the reset above — re-add the rage)
                    piece.attack += 2

                # Berserker master passive: +1 ATK permanently on capture
                if "berserker_passive" in _masters and piece.team == Team.PLAYER:
                    piece.attack += 1

                # Pauper master passive: Pawn promotes after 1 capture
                if "pauper_passive" in _masters and piece.piece_type == PieceType.PAWN and piece.team == Team.PLAYER:
                    piece.ability_flags["pauper_promote"] = True

            else:
                # Target survives — attacker bounces back to origin
                piece.has_moved = True
                # Piece stays at old_x, old_y (already there, no position change)

                # Berserker piece: gain ATK from taking conceptual damage
                if target.piece_type == PieceType.BERSERKER_PIECE and damage > 0:
                    gain = 2 if "war_machine" in _synergies else 1
                    target.attack += gain

        else:
            # Non-capture move
            piece.x = nx
            piece.y = ny
            piece.has_moved = True

        # Void: after moving, add origin cell to blocked_tiles
        if piece.piece_type == PieceType.VOID and (piece.x != old_x or piece.y != old_y):
            self.blocked_tiles.add((old_x, old_y))

        # Haunted Board synergy: Ghost leaves cursed ground at origin
        if (piece.piece_type == PieceType.GHOST
                and "haunted_board" in _synergies
                and (piece.x != old_x or piece.y != old_y)
                and (old_x, old_y) not in self.cell_modifiers):
            from modifiers import CellModifier
            self.cell_modifiers[(old_x, old_y)] = CellModifier(
                name="Cursed Ground", effect="cursed_ground",
                color=(100, 50, 200), overlay_alpha=0.25,
                origin_x=old_x, origin_y=old_y,
            )

        # Pawn promotion
        if piece.alive:
            self.check_promotion(piece, _rng)

        # Blazing modifier: leave fire trail on origin cell
        if any(m.effect == "blazing" for m in piece.modifiers) and (piece.x != old_x or piece.y != old_y):
            # Mark traversed cell as fire trail in cell_modifiers
            from modifiers import make_cell_modifier, CELL_MODIFIERS
            if (old_x, old_y) not in self.cell_modifiers and "inferno" in CELL_MODIFIERS:
                from modifiers import CellModifier
                fire_trail = CellModifier(
                    name="Fire Trail", effect="fire_trail",
                    color=(255, 100, 30), overlay_alpha=0.25,
                    origin_x=old_x, origin_y=old_y,
                )
                self.cell_modifiers[(old_x, old_y)] = fire_trail

        # Flaming modifier: 2 flat damage to adjacent enemies on kill
        if any(m.effect == "flaming" for m in piece.modifiers) and captured:
            splash_range = 2 if "pyromancer" in _synergies else 1
            fire_bonus = 1 if piece.ability_flags.get("ember_stone") else 0
            # Arsonist master: fire effects +1 damage
            if "arsonist_passive" in _masters and piece.team == Team.PLAYER:
                fire_bonus += 1
            for dx in range(-splash_range, splash_range + 1):
                for dy in range(-splash_range, splash_range + 1):
                    if dx == 0 and dy == 0:
                        continue
                    adj = self.get_piece_at(piece.x + dx, piece.y + dy)
                    if adj and adj.team != piece.team and adj.alive:
                        adj.hp -= (2 + fire_bonus)
                        if adj.hp <= 0:
                            adj.alive = False

        # Rage cell modifier: 2 damage to random adjacent enemy on kill
        if captured and piece.cell_modifier and piece.cell_modifier.effect == "rage":
            adj_enemies = []
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    adj = self.get_piece_at(piece.x + dx, piece.y + dy)
                    if adj and adj.team != piece.team and adj.alive:
                        adj_enemies.append(adj)
            if adj_enemies:
                victim = _rng.choice(adj_enemies)
                victim.hp -= 2
                if victim.hp <= 0:
                    victim.alive = False

        # Trickster: after attacking, teleport to random empty cell
        if piece.alive and piece.piece_type == PieceType.TRICKSTER and (captured or target):
            empty_cells = [
                (ex, ey) for ex in range(self.width) for ey in range(self.height)
                if self.is_empty(ex, ey) and (ex, ey) != (piece.x, piece.y)
            ]
            if empty_cells:
                tx, ty = _rng.choice(empty_cells)
                piece.x = tx
                piece.y = ty

        # Imp: after moving, swap 2 random enemy positions (respects anchor)
        if piece.alive and piece.piece_type == PieceType.IMP and (piece.x != old_x or piece.y != old_y):
            enemy_team = Team.ENEMY if piece.team == Team.PLAYER else Team.PLAYER
            enemies = [p for p in self.get_team_pieces(enemy_team) if p.alive
                       and not ((p.x, p.y) in self.border_modifiers and self.border_modifiers[(p.x, p.y)].effect == "anchor")]
            if len(enemies) >= 2:
                e1, e2 = _rng.sample(enemies, 2)
                e1.x, e1.y, e2.x, e2.y = e2.x, e2.y, e1.x, e1.y

        # Cursed ground / fire trail: deal 1 damage on step (consumed)
        if piece.alive and (piece.x, piece.y) in self.cell_modifiers:
            cm = self.cell_modifiers[(piece.x, piece.y)]
            if cm.effect in ("cursed_ground", "fire_trail"):
                piece.hp -= 1
                if piece.hp <= 0:
                    piece.alive = False
                del self.cell_modifiers[(piece.x, piece.y)]

        # Absorb cell modifier at destination (if piece is alive and no cell mod yet)
        if piece.alive and piece.cell_modifier is None and (piece.x, piece.y) in self.cell_modifiers:
            cm_to_absorb = self.cell_modifiers[(piece.x, piece.y)]
            from modifiers import apply_cell_modifier
            apply_cell_modifier(piece, cm_to_absorb)
            del self.cell_modifiers[(piece.x, piece.y)]

            # Mirror cell: create a 1-HP copy at the mirrored position
            if cm_to_absorb.effect == "mirror_cell":
                mirror_x = self.width - 1 - piece.x
                mirror_y = self.height - 1 - piece.y
                if self.in_bounds(mirror_x, mirror_y) and self.is_empty(mirror_x, mirror_y):
                    clone = piece.copy()
                    clone.hp = 1
                    clone.max_hp = 1
                    clone.cell_modifier = None
                    clone.ability_flags = {}
                    self.place_piece(clone, mirror_x, mirror_y)

            # Amplifier: double existing modifier effects (mark as amplified)
            if cm_to_absorb.effect == "amplifier":
                piece.ability_flags["amplified"] = True

        # Ice cell: piece slides in same direction until blocked
        if piece.alive and piece.cell_modifier and piece.cell_modifier.effect == "ice":
            dx = nx - old_x
            dy = ny - old_y
            # Normalize to unit direction
            if dx != 0:
                dx = dx // abs(dx)
            if dy != 0:
                dy = dy // abs(dy)
            if dx != 0 or dy != 0:
                slide_x, slide_y = piece.x + dx, piece.y + dy
                while self.in_bounds(slide_x, slide_y) and self.is_empty(slide_x, slide_y):
                    piece.x = slide_x
                    piece.y = slide_y
                    slide_x += dx
                    slide_y += dy
                self._grid_dirty = True

        return captured

    def process_non_capture_move(self, piece: Piece, old_x: int, old_y: int,
                                rng: random.Random,
                                active_synergies: list[str] | None = None) -> list[str]:
        """Process side effects for non-capture moves (called by autobattler)."""
        _synergies = active_synergies or []
        messages = []
        self._grid_dirty = True

        # Void blocks origin
        if piece.piece_type == PieceType.VOID and (piece.x != old_x or piece.y != old_y):
            self.blocked_tiles.add((old_x, old_y))

        # Haunted Board synergy: Ghost leaves cursed ground at origin
        if (piece.piece_type == PieceType.GHOST
                and "haunted_board" in _synergies
                and (piece.x != old_x or piece.y != old_y)
                and (old_x, old_y) not in self.cell_modifiers):
            from modifiers import CellModifier
            self.cell_modifiers[(old_x, old_y)] = CellModifier(
                name="Cursed Ground", effect="cursed_ground",
                color=(100, 50, 200), overlay_alpha=0.25,
                origin_x=old_x, origin_y=old_y,
            )

        # Blazing modifier: leave fire trail on origin cell
        if any(m.effect == "blazing" for m in piece.modifiers) and (piece.x != old_x or piece.y != old_y):
            from modifiers import make_cell_modifier, CELL_MODIFIERS
            if (old_x, old_y) not in self.cell_modifiers and "inferno" in CELL_MODIFIERS:
                from modifiers import CellModifier
                fire_trail = CellModifier(
                    name="Fire Trail", effect="fire_trail",
                    color=(255, 100, 30), overlay_alpha=0.25,
                    origin_x=old_x, origin_y=old_y,
                )
                self.cell_modifiers[(old_x, old_y)] = fire_trail

        # Cursed ground / fire trail at destination: deal 1 damage on step (consumed)
        if piece.alive and (piece.x, piece.y) in self.cell_modifiers:
            cm = self.cell_modifiers[(piece.x, piece.y)]
            if cm.effect in ("cursed_ground", "fire_trail"):
                piece.hp -= 1
                if piece.hp <= 0:
                    piece.alive = False
                del self.cell_modifiers[(piece.x, piece.y)]

        # Absorb cell modifier at destination
        if piece.alive and piece.cell_modifier is None and (piece.x, piece.y) in self.cell_modifiers:
            from modifiers import apply_cell_modifier
            apply_cell_modifier(piece, self.cell_modifiers[(piece.x, piece.y)])
            del self.cell_modifiers[(piece.x, piece.y)]

        # Imp: after moving, swap 2 random enemy positions
        if piece.alive and piece.piece_type == PieceType.IMP and (piece.x != old_x or piece.y != old_y):
            enemy_team = Team.ENEMY if piece.team == Team.PLAYER else Team.PLAYER
            enemies = [p for p in self.get_team_pieces(enemy_team) if p.alive]
            if len(enemies) >= 2:
                e1, e2 = rng.sample(enemies, 2)
                e1.x, e1.y, e2.x, e2.y = e2.x, e2.y, e1.x, e1.y
                messages.append("Imp swaps enemy positions!")

        return messages

    def get_anchor_damage_reduction(self, x: int, y: int, team: Team) -> int:
        """Calculate damage reduction from friendly Anchor pieces within 2 cells."""
        reduction = 0
        for p in self.pieces:
            if p.alive and p.team == team and p.piece_type == PieceType.ANCHOR_PIECE:
                dist = abs(p.x - x) + abs(p.y - y)
                if 0 < dist <= 2:
                    reduction += 2
        return reduction

    @staticmethod
    def _can_heal(piece: Piece) -> bool:
        """Return False for pieces that cannot be healed (e.g. Golem)."""
        return piece.piece_type != PieceType.GOLEM

    # --- Ability hook methods ---

    def process_turn_start_abilities(self, team: Team, rng: random.Random,
                                     active_synergies: list[str] | None = None,
                                     master_effects: list[str] | None = None) -> list[str]:
        """Process start-of-turn abilities for a team. Returns log messages."""
        _synergies = active_synergies or []
        _masters = master_effects or []
        messages = []
        self._grid_dirty = True  # abilities may move/kill pieces

        # Reset per-turn flags
        for p in list(self.get_team_pieces(team)):
            p.ability_flags.pop("executioner_used_this_turn", None)

        # Strip old Bard buffs before re-applying
        for p in list(self.get_team_pieces(team)):
            bard_buff = p.ability_flags.get("bard_buffed")
            if bard_buff:
                p.attack -= bard_buff
                del p.ability_flags["bard_buffed"]

        # Berserker master drawback: pieces lose 1 HP at turn start
        if "berserker_drawback" in _masters and team == Team.PLAYER:
            for p in list(self.get_team_pieces(team)):
                if p.alive and p.ability_flags.get("berserker_master_drain"):
                    p.hp -= 1
                    if p.hp <= 0:
                        p.alive = False
                        messages.append(f"Berserker drain kills {p.piece_type.value}")

        for p in list(self.get_team_pieces(team)):
            if not p.alive:
                continue

            # --- Process status effects ---
            expired = []
            for i, se in enumerate(p.status_effects):
                if se["type"] == "chill":
                    p.ability_flags["chilled"] = True
                    # Permafrost synergy: chilled enemies take 2 damage/turn
                    if "permafrost" in _synergies:
                        p.hp -= 2
                        if p.hp <= 0:
                            p.alive = False
                            messages.append(f"Permafrost kills {p.piece_type.value}")
                    se["duration"] -= 1
                    if se["duration"] <= 0:
                        expired.append(i)
                elif se["type"] == "poison":
                    ticks = 2 if p.ability_flags.get("venom_gland") else 1
                    # Blight synergy: poison stacks uncapped, +1 dmg per stack
                    magnitude = se.get("magnitude", 1)
                    if "blight" in _synergies:
                        magnitude += se.get("blight_stacks", 0)
                        se["blight_stacks"] = se.get("blight_stacks", 0) + 1
                    for _ in range(ticks):
                        p.hp -= magnitude
                    se["duration"] -= 1
                    # Blight: poison never expires
                    if "blight" in _synergies:
                        se["duration"] = max(se["duration"], 1)
                    if se["duration"] <= 0:
                        expired.append(i)
                    if p.hp <= 0:
                        p.alive = False
                        messages.append(f"Poison kills {p.piece_type.value}")
                elif se["type"] == "curse":
                    p.hp -= 2
                    se["duration"] -= 1
                    if se["duration"] <= 0:
                        expired.append(i)
                    if p.hp <= 0:
                        p.alive = False
                        messages.append(f"Curse kills {p.piece_type.value}")
            for i in reversed(expired):
                p.status_effects.pop(i)
            # Clear chill flag if no chill effects remain
            if not any(se["type"] == "chill" for se in p.status_effects):
                p.ability_flags.pop("chilled", None)

            if not p.alive:
                continue

            # Haunted ghost countdown
            if p.ability_flags.get("haunted_turns"):
                p.ability_flags["haunted_turns"] -= 1
                if p.ability_flags["haunted_turns"] <= 0:
                    p.alive = False
                    messages.append(f"Haunted Ghost fades away")
                    continue

            # Titan modifier: skip every other turn (dedicated flag, not chill)
            if any(m.effect == "titan" for m in p.modifiers):
                titan_skip = p.ability_flags.get("titan_skip", False)
                p.ability_flags["titan_skip"] = not titan_skip
                if titan_skip:
                    p.has_moved = True  # skip turn without touching chilled

            # Unstable modifier: 1 self-damage per turn
            if any(m.effect == "unstable" for m in p.modifiers):
                p.hp -= 1
                if p.hp <= 0:
                    p.alive = False
                    messages.append(f"Unstable kills {p.piece_type.value}")
                    continue

            # Golem: lose 1 max HP per turn permanently
            if p.piece_type == PieceType.GOLEM:
                p.max_hp = max(1, p.max_hp - 1)
                if p.hp > p.max_hp:
                    p.hp = p.max_hp
                messages.append(f"Golem erodes (max HP:{p.max_hp})")

            # Summoner: spawn pawn on random adjacent empty cell
            if p.piece_type == PieceType.SUMMONER:
                empty_adj = []
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        sx, sy = p.x + dx, p.y + dy
                        if self.in_bounds(sx, sy) and self.is_empty(sx, sy):
                            empty_adj.append((sx, sy))
                if empty_adj:
                    sx, sy = rng.choice(empty_adj)
                    spawn_type = PieceType.KNIGHT if "swarm_intelligence" in _synergies else PieceType.PAWN
                    spawn = Piece(spawn_type, team)
                    self.place_piece(spawn, sx, sy)
                    messages.append(f"Summoner spawns {spawn_type.value} at ({sx},{sy})")

            # Parasite: deal 1 damage to all adjacent enemy pieces
            if p.piece_type == PieceType.PARASITE:
                enemy_team = Team.ENEMY if team == Team.PLAYER else Team.PLAYER
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        adj = self.get_piece_at(p.x + dx, p.y + dy)
                        if adj and adj.team == enemy_team and adj.alive:
                            adj.hp -= 1
                            if adj.hp <= 0:
                                adj.alive = False
                                messages.append(f"Parasite kills {adj.piece_type.value}")
                            else:
                                messages.append(f"Parasite drains {adj.piece_type.value} (HP:{adj.hp})")
                if "life_drain" in _synergies:
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            adj = self.get_piece_at(p.x + dx, p.y + dy)
                            if adj and adj.team == team and adj.alive and adj is not p:
                                adj.hp = min(adj.max_hp, adj.hp + 1)

            # Cannon: attack nearest enemy in any straight line
            if p.piece_type == PieceType.CANNON:
                enemy_team = Team.ENEMY if team == Team.PLAYER else Team.PLAYER
                nearest = None
                nearest_dist = float('inf')
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    for dist in range(1, max(self.width, self.height)):
                        cx, cy = p.x + dx * dist, p.y + dy * dist
                        if not self.in_bounds(cx, cy):
                            break
                        target = self.get_piece_at(cx, cy)
                        if target and target.team == enemy_team and target.alive:
                            if dist < nearest_dist:
                                nearest_dist = dist
                                nearest = target
                            break
                        if target:
                            break  # blocked by friendly
                if nearest:
                    nearest.hp -= p.attack
                    if nearest.hp <= 0:
                        nearest.alive = False
                        messages.append(f"Cannon kills {nearest.piece_type.value}!")
                    else:
                        messages.append(f"Cannon hits {nearest.piece_type.value} (HP:{nearest.hp})")

            # Totem: heal friendlies within 2 cells for 1 HP
            if p.piece_type == PieceType.TOTEM:
                totem_heal = 2 if "sacred_ground" in _synergies else 1
                for ally in self.get_team_pieces(team):
                    if ally is p or not ally.alive:
                        continue
                    if abs(ally.x - p.x) <= 2 and abs(ally.y - p.y) <= 2 and self._can_heal(ally):
                        ally.hp = min(ally.max_hp, ally.hp + totem_heal)

            # Bard: adjacent friendlies gain +2 ATK (tracked as buff)
            if p.piece_type == PieceType.BARD:
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        adj = self.get_piece_at(p.x + dx, p.y + dy)
                        if adj and adj.team == team and adj.alive and adj is not p:
                            if not adj.ability_flags.get("bard_buffed"):
                                buff_amt = 4 if "battle_hymn" in _synergies else 2
                                adj.attack += buff_amt
                                adj.ability_flags["bard_buffed"] = buff_amt

            # Alchemist piece: convert current cell to random cell modifier
            if p.piece_type == PieceType.ALCHEMIST_PIECE:
                from modifiers import CELL_MODIFIERS, make_cell_modifier
                cell_keys = list(CELL_MODIFIERS.keys())
                key = rng.choice(cell_keys)
                if (p.x, p.y) not in self.cell_modifiers:
                    cm = make_cell_modifier(key, p.x, p.y)
                    self.cell_modifiers[(p.x, p.y)] = cm
                    messages.append(f"Alchemist creates {key} cell")

            # Magnetic modifier: pull nearest enemy 1 cell closer
            if any(m.effect == "magnetic" for m in p.modifiers):
                enemy_team = Team.ENEMY if team == Team.PLAYER else Team.PLAYER
                nearest = None
                nearest_dist = float('inf')
                for e in self.get_team_pieces(enemy_team):
                    d = abs(e.x - p.x) + abs(e.y - p.y)
                    if d < nearest_dist:
                        nearest_dist = d
                        nearest = e
                if nearest and nearest_dist > 1:
                    # Check anchor protection
                    is_anchored = ((nearest.x, nearest.y) in self.border_modifiers
                                   and self.border_modifiers[(nearest.x, nearest.y)].effect == "anchor")
                    if not is_anchored:
                        # Move 1 cell closer
                        dx = 0 if nearest.x == p.x else (1 if p.x > nearest.x else -1)
                        dy = 0 if nearest.y == p.y else (1 if p.y > nearest.y else -1)
                        nx, ny = nearest.x + dx, nearest.y + dy
                        if self.in_bounds(nx, ny) and self.is_empty(nx, ny):
                            nearest.x = nx
                            nearest.y = ny
                            messages.append(f"Magnetic pulls {nearest.piece_type.value}")

            # Witch: apply curse via combat (handled in move_piece as targeting)
            # Witch's curse is applied when she "attacks" — handled in move_piece
            # Shapeshifter: cycle piece type (handled here)
            if p.piece_type == PieceType.SHAPESHIFTER:
                roster_types = list({
                    ally.piece_type for ally in self.get_team_pieces(team)
                    if ally is not p and ally.alive
                })
                if roster_types:
                    from pieces import PIECE_STATS
                    new_type = rng.choice(roster_types)
                    p.piece_type = new_type
                    if new_type in PIECE_STATS:
                        _, new_atk = PIECE_STATS[new_type]
                        p.attack = new_atk
                    messages.append(f"Shapeshifter becomes {new_type.value}")

            # --- Process absorbed cell modifier effects ---
            # Alchemist master: cell mod effects doubled
            _cm_mult = 2 if "alchemist_passive" in _masters and p.team == Team.PLAYER else 1
            if p.alive and p.cell_modifier:
                eff = p.cell_modifier.effect
                # Alchemist drawback: cell mods vanish after 3 turns
                if "alchemist_drawback" in _masters and p.team == Team.PLAYER:
                    turns = p.ability_flags.get("alchemist_cm_turns", 0) + 1
                    p.ability_flags["alchemist_cm_turns"] = turns
                    if turns >= 3:
                        p.cell_modifier = None
                        p.ability_flags.pop("alchemist_cm_turns", None)
                        messages.append(f"{p.piece_type.value} cell mod vanishes (Alchemist)")
                        # skip processing this turn since it was removed
                        eff = None
                if eff == "inferno":
                    if not p.ability_flags.get("inferno_buffed"):
                        p.attack += 3 * _cm_mult
                        p.ability_flags["inferno_buffed"] = True
                    p.hp -= 1 * _cm_mult
                    if p.hp <= 0:
                        p.alive = False
                        messages.append(f"Inferno kills {p.piece_type.value}")
                        continue
                elif eff == "sanctuary":
                    if self._can_heal(p):
                        heal_amt = (4 if "sacred_ground" in _synergies else 2) * _cm_mult
                        p.hp = min(p.max_hp, p.hp + heal_amt)
                elif eff == "quicksand":
                    p.has_moved = True
                    p.cell_modifier = None  # consumed after 1 turn
                    messages.append(f"{p.piece_type.value} stuck in quicksand!")
                elif eff == "gold_mine":
                    p.ability_flags["gold_mine_earned"] = p.ability_flags.get("gold_mine_earned", 0) + 1 * _cm_mult
                elif eff == "curse":
                    if not p.ability_flags.get("curse_debuffed"):
                        p.attack = max(0, p.attack - 2 * _cm_mult)
                        p.ability_flags["curse_debuffed"] = True
                    p.hp -= 2 * _cm_mult
                    if p.hp <= 0:
                        p.alive = False
                        messages.append(f"Curse kills {p.piece_type.value}")
                        continue
                elif eff == "beacon":
                    # Beacon grants +1 ATK to friendly pieces within 2 cells of origin
                    beacon_bonus = 1 * _cm_mult
                    ox, oy = p.cell_modifier.origin_x, p.cell_modifier.origin_y
                    for ally in self.get_team_pieces(team):
                        if ally is not p and ally.alive and abs(ally.x - ox) <= 2 and abs(ally.y - oy) <= 2:
                            if not ally.ability_flags.get("beacon_buffed"):
                                ally.attack += beacon_bonus
                                ally.ability_flags["beacon_buffed"] = beacon_bonus

        # --- Synergy turn-start effects ---

        # Pack Hunters: King Rats gain +1 ATK/HP per King Rat alive
        if "pack_hunters" in _synergies:
            king_rats = [p for p in self.get_team_pieces(team)
                         if p.alive and p.piece_type == PieceType.KING_RAT]
            rat_count = len(king_rats)
            for kr in king_rats:
                bonus = rat_count - 1  # +1 per OTHER king rat
                if bonus > 0 and not kr.ability_flags.get("pack_buffed"):
                    kr.attack += bonus
                    kr.max_hp += bonus
                    kr.hp += bonus
                    kr.ability_flags["pack_buffed"] = True

        # Madness synergy: enemy positions shuffle every 3 turns
        if "madness" in _synergies and team == Team.PLAYER:
            madness_counter = self.__dict__.get("_madness_counter", 0) + 1
            self.__dict__["_madness_counter"] = madness_counter
            if madness_counter % 3 == 0:
                enemy_team = Team.ENEMY if team == Team.PLAYER else Team.PLAYER
                enemies = [p for p in self.get_team_pieces(enemy_team) if p.alive]
                if len(enemies) >= 2:
                    positions = [(p.x, p.y) for p in enemies]
                    rng.shuffle(positions)
                    for i, p in enumerate(enemies):
                        p.x, p.y = positions[i]
                    self._grid_dirty = True
                    messages.append("Madness shuffles enemy positions!")

        # Sacred Ground synergy: healing doubled (applied via multiplier), full HP → +1 ATK
        if "sacred_ground" in _synergies:
            for p in list(self.get_team_pieces(team)):
                if p.alive and p.hp >= p.max_hp and not p.ability_flags.get("sacred_atk_buffed"):
                    p.attack += 1
                    p.ability_flags["sacred_atk_buffed"] = True

        # --- Process board-placed cell modifiers (not absorbed) ---
        # Volcano: every 3 turns, deal 3 damage in 2-cell radius
        for pos, cm in list(self.cell_modifiers.items()):
            if cm.effect == "volcano":
                counter = cm.__dict__.get("_volcano_counter", 0) + 1
                cm.__dict__["_volcano_counter"] = counter
                if counter % 3 == 0:
                    ox, oy = pos
                    for p in list(self.pieces):
                        if p.alive and abs(p.x - ox) <= 2 and abs(p.y - oy) <= 2:
                            p.hp -= 3
                            if p.hp <= 0:
                                p.alive = False
                                messages.append(f"Volcano erupts and kills {p.piece_type.value}!")
                            else:
                                messages.append(f"Volcano damages {p.piece_type.value} (HP:{p.hp})")

        # Vortex (board-placed): pull all adjacent enemy pieces 1 cell toward origin
        for pos, cm in list(self.cell_modifiers.items()):
            if cm.effect == "vortex":
                ox, oy = pos
                for p in list(self.pieces):
                    if not p.alive or p.team == team:
                        continue
                    if abs(p.x - ox) <= 1 and abs(p.y - oy) <= 1 and (p.x, p.y) != (ox, oy):
                        dx = 0 if p.x == ox else (1 if ox > p.x else -1)
                        dy = 0 if p.y == oy else (1 if oy > p.y else -1)
                        nx, ny = p.x + dx, p.y + dy
                        if self.in_bounds(nx, ny) and self.is_empty(nx, ny):
                            p.x = nx
                            p.y = ny
                            self._grid_dirty = True

        # Strip beacon buffs for pieces no longer in range (cleanup at end of turn processing)
        for p in list(self.get_team_pieces(team)):
            if p.ability_flags.get("beacon_buffed"):
                # Check if any beacon holder is still within range
                has_beacon = False
                for ally in self.get_team_pieces(team):
                    if ally.cell_modifier and ally.cell_modifier.effect == "beacon":
                        ox, oy = ally.cell_modifier.origin_x, ally.cell_modifier.origin_y
                        if abs(p.x - ox) <= 2 and abs(p.y - oy) <= 2:
                            has_beacon = True
                            break
                if not has_beacon:
                    buff_val = p.ability_flags["beacon_buffed"]
                    p.attack -= buff_val if isinstance(buff_val, int) else 1
                    del p.ability_flags["beacon_buffed"]

        # --- Process border modifier turn-start effects ---
        enemy_team = Team.ENEMY if team == Team.PLAYER else Team.PLAYER
        for pos, bm in list(self.border_modifiers.items()):
            bx, by = pos

            # Healing aura: heal all adjacent pieces +1 HP/turn
            if bm.effect == "healing_aura":
                for p in list(self.pieces):
                    if p.alive and abs(p.x - bx) <= 1 and abs(p.y - by) <= 1 and self._can_heal(p):
                        p.hp = min(p.max_hp, p.hp + 1)

            # Gravity well: pull all adjacent pieces 1 cell toward this cell at turn start
            elif bm.effect == "gravity_well":
                for p in list(self.pieces):
                    if not p.alive or (p.x == bx and p.y == by):
                        continue
                    if abs(p.x - bx) <= 1 and abs(p.y - by) <= 1:
                        # Check anchor protection
                        if (p.x, p.y) in self.border_modifiers and self.border_modifiers[(p.x, p.y)].effect == "anchor":
                            continue
                        dx = 0 if p.x == bx else (1 if bx > p.x else -1)
                        dy = 0 if p.y == by else (1 if by > p.y else -1)
                        new_x, new_y = p.x + dx, p.y + dy
                        if self.in_bounds(new_x, new_y) and self.is_empty(new_x, new_y):
                            p.x = new_x
                            p.y = new_y
                            self._grid_dirty = True

            # Death zone: deal 2 damage to all adjacent enemies at turn start
            elif bm.effect == "death_zone":
                for p in list(self.pieces):
                    if p.alive and p.team == enemy_team:
                        if abs(p.x - bx) <= 1 and abs(p.y - by) <= 1:
                            p.hp -= 2
                            if p.hp <= 0:
                                p.alive = False
                                messages.append(f"Death Zone kills {p.piece_type.value}!")

        return messages

    def process_on_death(self, dead_piece: Piece, killer: Piece | None,
                         rng: random.Random,
                         active_synergies: list[str] | None = None,
                         _depth: int = 0,
                         master_effects: list[str] | None = None) -> list[str]:
        """Process on-death abilities. Returns log messages."""
        if _depth > 10:
            return []
        _synergies = active_synergies or []
        _masters = master_effects or []
        messages = []
        self._grid_dirty = True  # on-death effects spawn/revive pieces

        # Bard death: strip buffs from adjacent allies
        if dead_piece.piece_type == PieceType.BARD:
            for p in list(self.get_team_pieces(dead_piece.team)):
                bard_buff = p.ability_flags.get("bard_buffed")
                if bard_buff:
                    p.attack -= bard_buff
                    del p.ability_flags["bard_buffed"]

        # Bomb: 10 damage to everything in 3x3 (both teams)
        if dead_piece.piece_type == PieceType.BOMB:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    adj = self.get_piece_at(dead_piece.x + dx, dead_piece.y + dy)
                    if adj and adj.alive and adj is not dead_piece:
                        if "sacrifice" in _synergies:
                            if adj.team != dead_piece.team:
                                adj.team = dead_piece.team
                                messages.append(f"Bomb converts {adj.piece_type.value}!")
                        else:
                            adj.hp -= 10
                            if adj.hp <= 0:
                                adj.alive = False
                                messages.append(f"Bomb explosion kills {adj.piece_type.value}!")
                                if adj.piece_type == PieceType.BOMB and "minefield" in _synergies:
                                    messages.extend(self.process_on_death(adj, dead_piece, rng, _synergies, _depth + 1, _masters))
                            else:
                                messages.append(f"Bomb damages {adj.piece_type.value} (HP:{adj.hp})")

        # Explosive modifier: 5 damage in 3x3 on death
        if any(m.effect == "explosive" for m in dead_piece.modifiers):
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    adj = self.get_piece_at(dead_piece.x + dx, dead_piece.y + dy)
                    if adj and adj.alive and adj is not dead_piece:
                        adj.hp -= 5
                        if adj.hp <= 0:
                            adj.alive = False
                            messages.append(f"Explosive kills {adj.piece_type.value}!")
                        else:
                            messages.append(f"Explosive damages {adj.piece_type.value} (HP:{adj.hp})")

        # Splitting modifier: spawn 2 Pawns with this piece's mods
        if any(m.effect == "splitting" for m in dead_piece.modifiers):
            from pieces import MODIFIERS
            spawn_mods = [m for m in dead_piece.modifiers]
            for _ in range(2):
                empty_cells = [
                    (ex, ey) for ex in range(self.width) for ey in range(self.height)
                    if self.is_empty(ex, ey) and not self.is_blocked(ex, ey)
                ]
                if empty_cells:
                    sx, sy = rng.choice(empty_cells)
                    spawn = Piece(PieceType.PAWN, dead_piece.team)
                    spawn.modifiers = list(spawn_mods)
                    self.place_piece(spawn, sx, sy)
                    messages.append(f"Splitting spawns Pawn at ({sx},{sy})")

        # Haunted modifier: become Ghost at 50% HP for 2 turns
        if any(m.effect == "haunted" for m in dead_piece.modifiers) and not dead_piece.ability_flags.get("haunted_used"):
            dead_piece.piece_type = PieceType.GHOST
            dead_piece.hp = max(1, dead_piece.max_hp // 2)
            dead_piece.alive = True
            dead_piece.ability_flags["haunted_used"] = True
            dead_piece.ability_flags["haunted_turns"] = 2
            messages.append(f"Haunted piece becomes Ghost!")

        # Decoy: spawn 2 Pawns for the killer's team
        if dead_piece.piece_type == PieceType.DECOY and killer:
            for _ in range(2):
                empty_cells = [
                    (ex, ey) for ex in range(self.width) for ey in range(self.height)
                    if self.is_empty(ex, ey) and not self.is_blocked(ex, ey)
                ]
                if empty_cells:
                    sx, sy = rng.choice(empty_cells)
                    spawn = Piece(PieceType.PAWN, dead_piece.team)
                    self.place_piece(spawn, sx, sy)
                    messages.append(f"Decoy spawns Pawn for {dead_piece.team.value} at ({sx},{sy})")

        # Poltergeist: shuffle all enemy positions on death (respects anchor)
        if dead_piece.piece_type == PieceType.POLTERGEIST:
            enemy_team = Team.ENEMY if dead_piece.team == Team.PLAYER else Team.PLAYER
            enemies = [p for p in self.get_team_pieces(enemy_team) if p.alive
                       and not ((p.x, p.y) in self.border_modifiers and self.border_modifiers[(p.x, p.y)].effect == "anchor")]
            if len(enemies) >= 2:
                positions = [(p.x, p.y) for p in enemies]
                rng.shuffle(positions)
                for i, p in enumerate(enemies):
                    p.x, p.y = positions[i]
                self._grid_dirty = True
                messages.append("Poltergeist shuffles all enemy positions!")

        # Mimic: transform into killer's type, revive with full HP
        if dead_piece.piece_type == PieceType.MIMIC and killer and not dead_piece.ability_flags.get("mimic_transformed"):
            from pieces import PIECE_STATS
            dead_piece.piece_type = killer.piece_type
            if dead_piece.piece_type in PIECE_STATS:
                mhp, atk = PIECE_STATS[dead_piece.piece_type]
                dead_piece.max_hp = mhp
                dead_piece.hp = mhp
                dead_piece.attack = atk
            dead_piece.alive = True
            dead_piece.ability_flags["mimic_transformed"] = True
            messages.append(f"Mimic transforms into {dead_piece.piece_type.value}!")

        # Phoenix: revive once at random empty cell with 50% HP
        if dead_piece.piece_type == PieceType.PHOENIX and not dead_piece.ability_flags.get("phoenix_revived"):
            revive_hp_mult = 1.0 if "undying_legion" in _synergies else 0.5
            revive_atk_bonus = 2 if "undying_legion" in _synergies else 0
            empty_cells = [
                (ex, ey) for ex in range(self.width) for ey in range(self.height)
                if self.is_empty(ex, ey) and not self.is_blocked(ex, ey)
            ]
            if empty_cells:
                rx, ry = rng.choice(empty_cells)
                dead_piece.alive = True
                dead_piece.x = rx
                dead_piece.y = ry
                dead_piece.hp = max(1, int(dead_piece.max_hp * revive_hp_mult))
                dead_piece.attack += revive_atk_bonus
                dead_piece.ability_flags["phoenix_revived"] = True
                messages.append(f"Phoenix revives at ({rx},{ry}) with {dead_piece.hp} HP!")

        # Time Mage: on death, set rewind flag (handled by autobattler)
        if dead_piece.piece_type == PieceType.TIME_MAGE and not dead_piece.ability_flags.get("time_mage_used"):
            dead_piece.ability_flags["time_mage_used"] = True
            dead_piece.ability_flags["time_mage_rewind"] = True
            messages.append("Time Mage triggers rewind!")

        # --- Synergy on-death effects ---

        # Scorched Earth: killed enemies leave Inferno cells
        if "scorched_earth" in _synergies and killer and killer.team == Team.PLAYER:
            from modifiers import CellModifier
            if (dead_piece.x, dead_piece.y) not in self.cell_modifiers:
                self.cell_modifiers[(dead_piece.x, dead_piece.y)] = CellModifier(
                    name="Inferno", effect="inferno",
                    color=(255, 140, 30), overlay_alpha=0.35,
                    origin_x=dead_piece.x, origin_y=dead_piece.y,
                )
                messages.append("Scorched Earth leaves Inferno!")

        # Firestorm: fire damage chains to adjacent enemies after flaming kill
        if "firestorm" in _synergies and killer and any(m.effect == "flaming" for m in killer.modifiers):
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    adj = self.get_piece_at(dead_piece.x + dx, dead_piece.y + dy)
                    if adj and adj.alive and adj.team != killer.team:
                        adj.hp -= 2
                        if adj.hp <= 0:
                            adj.alive = False
                            messages.append(f"Firestorm chains to kill {adj.piece_type.value}!")

        # Pandemic: poison spreads to adjacent enemies when poisoned enemy dies
        if "pandemic" in _synergies and any(se["type"] == "poison" for se in dead_piece.status_effects):
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    adj = self.get_piece_at(dead_piece.x + dx, dead_piece.y + dy)
                    if adj and adj.alive and adj.team == dead_piece.team:
                        if not any(se["type"] == "poison" for se in adj.status_effects):
                            adj.status_effects.append({"type": "poison", "duration": 3, "magnitude": 1})
                            messages.append(f"Pandemic spreads poison to {adj.piece_type.value}")

        # Martyrdom: sacrificed pieces explode like Bomb
        if "martyrdom" in _synergies and killer and killer.team == dead_piece.team:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    adj = self.get_piece_at(dead_piece.x + dx, dead_piece.y + dy)
                    if adj and adj.alive and adj is not dead_piece:
                        adj.hp -= 10
                        if adj.hp <= 0:
                            adj.alive = False
                            messages.append(f"Martyrdom explosion kills {adj.piece_type.value}!")

        # Endless Horde: dead Pawns spawn 2 Pawns with Splitting
        if ("endless_horde" in _synergies
                and dead_piece.piece_type == PieceType.PAWN
                and dead_piece.team == Team.PLAYER
                and not dead_piece.ability_flags.get("endless_horde_spawned")):
            from pieces import MODIFIERS
            for _ in range(2):
                empty_cells = [
                    (ex, ey) for ex in range(self.width) for ey in range(self.height)
                    if self.is_empty(ex, ey) and not self.is_blocked(ex, ey)
                ]
                if empty_cells:
                    sx, sy = rng.choice(empty_cells)
                    spawn = Piece(PieceType.PAWN, dead_piece.team)
                    spawn.modifiers.append(MODIFIERS["splitting"])
                    spawn.ability_flags["endless_horde_spawned"] = True
                    self.place_piece(spawn, sx, sy)
                    messages.append(f"Endless Horde spawns Pawn at ({sx},{sy})")

        # Necromancer: summoner-spawned pawns revive once
        if ("necromancer" in _synergies
                and dead_piece.piece_type == PieceType.PAWN
                and dead_piece.team == Team.PLAYER
                and not dead_piece.ability_flags.get("necro_revived")):
            empty_cells = [
                (ex, ey) for ex in range(self.width) for ey in range(self.height)
                if self.is_empty(ex, ey) and not self.is_blocked(ex, ey)
            ]
            if empty_cells:
                rx, ry = rng.choice(empty_cells)
                dead_piece.alive = True
                dead_piece.x = rx
                dead_piece.y = ry
                dead_piece.hp = max(1, dead_piece.max_hp // 2)
                dead_piece.ability_flags["necro_revived"] = True
                messages.append(f"Necromancer revives Pawn at ({rx},{ry})")

        # Identity Theft: Mimic transforms on any damage (not just death)
        # This is handled in move_piece already (mimic_transformed flag), just extend

        # Necromancer master passive: dead pieces fight as ghosts for 1 extra turn
        if ("necromancer_passive" in _masters
                and dead_piece.team == Team.PLAYER
                and not dead_piece.alive
                and not dead_piece.ability_flags.get("necro_ghost_used")):
            dead_piece.alive = True
            dead_piece.hp = 1
            dead_piece.ability_flags["necro_ghost_used"] = True
            dead_piece.ability_flags["haunted_turns"] = 1
            messages.append(f"{dead_piece.piece_type.value} fights as ghost (Necromancer)!")

        # Mirror Master passive: track strongest killed enemy for wave-end copying
        if ("mirror_master_passive" in _masters
                and dead_piece.team == Team.ENEMY
                and killer and killer.team == Team.PLAYER):
            # Store strongest kill info in ability_flags on killer for autobattler to collect
            prev_strongest = killer.ability_flags.get("mirror_master_kill_atk", 0)
            if dead_piece.attack > prev_strongest:
                killer.ability_flags["mirror_master_kill_type"] = dead_piece.piece_type.value
                killer.ability_flags["mirror_master_kill_atk"] = dead_piece.attack
                killer.ability_flags["mirror_master_kill_hp"] = dead_piece.max_hp

        return messages

    def process_on_damage_dealt(self, attacker: Piece, target: Piece, damage: int,
                                rng: random.Random) -> list[str]:
        """Process after-damage-dealt abilities. Returns log messages."""
        messages = []

        # Leech healing is handled inline in move_piece

        return messages

    def process_mirror_moves(self, moved_piece: Piece, old_x: int, old_y: int,
                             rng: random.Random,
                             active_synergies: list[str] | None = None) -> list[str]:
        """After any piece moves, same-team Mirror pieces make the reflected move."""
        _synergies = active_synergies or []
        messages = []
        self._grid_dirty = True
        dx = moved_piece.x - old_x
        dy = moved_piece.y - old_y
        if dx == 0 and dy == 0:
            return messages

        mirrors = [p for p in self.get_team_pieces(moved_piece.team)
                   if p.alive and p.piece_type == PieceType.MIRROR_PIECE and p is not moved_piece]

        for mirror in mirrors:
            # Infinite Recursion synergy: mirrors teleport randomly instead
            if "infinite_recursion" in _synergies:
                empty_cells = [
                    (ex, ey) for ex in range(self.width) for ey in range(self.height)
                    if self.is_empty(ex, ey)
                ]
                if empty_cells:
                    nx, ny = rng.choice(empty_cells)
                    mirror.x = nx
                    mirror.y = ny
                    self._grid_dirty = True
                    # Deal 1 damage on arrival to adjacent enemies
                    enemy_team = Team.ENEMY if mirror.team == Team.PLAYER else Team.PLAYER
                    for adx in [-1, 0, 1]:
                        for ady in [-1, 0, 1]:
                            if adx == 0 and ady == 0:
                                continue
                            adj = self.get_piece_at(nx + adx, ny + ady)
                            if adj and adj.team == enemy_team and adj.alive:
                                adj.hp -= 1
                                if adj.hp <= 0:
                                    adj.alive = False
                    messages.append(f"Mirror teleports to ({nx},{ny})!")
            else:
                # Reflected move: negate dx/dy
                nx, ny = mirror.x - dx, mirror.y - dy
                if self.in_bounds(nx, ny) and not self.is_blocked(nx, ny):
                    target = self.get_piece_at(nx, ny)
                    if target and target.team != mirror.team:
                        # Attack the target
                        self.move_piece(mirror, nx, ny, rng)
                        messages.append(f"Mirror reflects: attacks {target.piece_type.value}")
                    elif not target:
                        mirror.x = nx
                        mirror.y = ny
                        self._grid_dirty = True
                        messages.append(f"Mirror reflects to ({nx},{ny})")

        return messages

    def check_promotion(self, piece: Piece, rng: random.Random | None = None) -> bool:
        """Promote a pawn that reached the far rank. Returns True if promoted."""
        if not piece.alive or piece.piece_type != PieceType.PAWN:
            return False
        import random as _random_mod
        _rng = rng or _random_mod
        promote_rank = 0 if piece.team == Team.PLAYER else self.height - 1
        # Pauper master: promote after 1 capture
        should_promote = (piece.y == promote_rank
                          or piece.ability_flags.get("pauper_promote"))
        if should_promote:
            promo_choices = [PieceType.KNIGHT, PieceType.BISHOP, PieceType.ROOK, PieceType.QUEEN]
            piece.piece_type = _rng.choice(promo_choices)
            piece.ability_flags.pop("pauper_promote", None)
            return True
        return False

    def remove_piece(self, piece: Piece) -> None:
        piece.alive = False
        self._grid_dirty = True

    def reset_round(self) -> None:
        """Reset cell modifiers to original cells, strip absorbed cell mods from pieces."""
        from modifiers import reset_cell_modifiers
        reset_cell_modifiers(self, self.cell_modifiers)

    def clear(self) -> None:
        self.pieces.clear()
        self.blocked_tiles.clear()
        self.cell_modifiers.clear()
        self.dead_zone.clear()
        self._grid.clear()
        self._grid_dirty = False
        # Note: border_modifiers persist across rounds, not cleared here

    def add_obstacle(self, x: int, y: int) -> None:
        self.blocked_tiles.add((x, y))

    def is_square_attacked_by(self, x: int, y: int, team: Team) -> bool:
        """Check if a square is attacked by any piece of the given team."""
        for p in self.get_team_pieces(team):
            if (x, y) in p.get_valid_moves(self):
                return True
        return False

    def get_all_valid_moves(self, team: Team) -> list[tuple[Piece, int, int]]:
        """Get all valid (piece, dest_x, dest_y) for a team."""
        result = []
        for p in self.get_team_pieces(team):
            for mx, my in p.get_valid_moves(self):
                result.append((p, mx, my))
        return result

    def count_alive(self, team: Team) -> int:
        return len(self.get_team_pieces(team))

    def copy(self) -> Board:
        new_board = Board(width=self.width, height=self.height)
        new_board.pieces = [p.copy() for p in self.pieces]
        new_board.blocked_tiles = set(self.blocked_tiles)
        new_board.cell_modifiers = {k: v.copy() for k, v in self.cell_modifiers.items()}
        new_board.border_modifiers = {k: v.copy() for k, v in self.border_modifiers.items()}
        new_board.dead_zone = set(self.dead_zone)
        new_board._grid_dirty = True  # rebuilt lazily on first lookup
        return new_board

    # --- Sudden Death: ring collapse ---

    def _ring_cells(self, ring: int) -> list[tuple[int, int]]:
        """Return all cells at ring distance `ring` from the board edge.
        Ring 0 = outermost edge, ring 1 = next layer in, etc."""
        cells = []
        d = ring
        for x in range(d, self.width - d):
            for y in range(d, self.height - d):
                if x == d or x == self.width - 1 - d or y == d or y == self.height - 1 - d:
                    cells.append((x, y))
        return cells

    def get_warning_cells(self, next_ring: int) -> set[tuple[int, int]]:
        """Return cells that will be closed in the next ring closure."""
        max_ring = min(self.width, self.height) // 2
        if next_ring < 0 or next_ring >= max_ring:
            return set()
        return set(self._ring_cells(next_ring)) - self.dead_zone

    def _push_direction(self, x: int, y: int, ring: int) -> tuple[int, int]:
        """Determine push direction (dx, dy) for a piece on the given ring.
        Pushes toward the board center."""
        cx = self.width / 2.0
        cy = self.height / 2.0
        dx = 0
        dy = 0
        if x == ring:
            dx = 1
        elif x == self.width - 1 - ring:
            dx = -1
        if y == ring:
            dy = 1
        elif y == self.height - 1 - ring:
            dy = -1
        # For corners (both dx and dy set), pick the axis with more room
        if dx != 0 and dy != 0:
            room_x = abs(cx - (x + dx))
            room_y = abs(cy - (y + dy))
            if room_x >= room_y:
                dy = 0  # push horizontally
            else:
                dx = 0  # push vertically
        return (dx, dy)

    def close_ring(self, ring: int) -> tuple[list[Piece], list[Piece]]:
        """Close ring `ring` of the board. Pushes pieces inward.
        Returns (killed_by_squeeze, all_pushed) lists."""
        self._grid_dirty = True
        cells = self._ring_cells(ring)
        new_dead = set()
        for (x, y) in cells:
            if (x, y) in self.dead_zone:
                continue
            new_dead.add((x, y))

        # Collect pieces that need pushing
        to_push: list[Piece] = []
        for (x, y) in new_dead:
            piece = self.get_piece_at(x, y)
            if piece and piece.alive:
                to_push.append(piece)

        # Mark cells as dead BEFORE placing (so push destinations exclude dead cells)
        for (x, y) in new_dead:
            self.dead_zone.add((x, y))
            self.blocked_tiles.add((x, y))
            # Remove modifiers
            self.cell_modifiers.pop((x, y), None)
            self.border_modifiers.pop((x, y), None)

        # Push each piece inward
        pushed: list[Piece] = []
        squeeze_list: list[Piece] = []

        for piece in to_push:
            placed = self._try_push_piece(piece, ring)
            if placed:
                pushed.append(piece)
            else:
                squeeze_list.append(piece)

        # Squeeze mode: damage squeezed pieces until enough die to fit
        killed: list[Piece] = []
        if squeeze_list:
            killed = self._resolve_squeeze(squeeze_list, ring)

        return (killed, pushed)

    def _try_push_piece(self, piece: Piece, ring: int) -> bool:
        """Try to push a piece inward. Returns True if placed."""
        # 1) Try primary push direction (line along axis toward center)
        dx, dy = self._push_direction(piece.x, piece.y, ring)
        nx, ny = piece.x + dx, piece.y + dy
        for _ in range(max(self.width, self.height)):
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                break
            if (nx, ny) in self.dead_zone:
                break
            if self.get_piece_at(nx, ny) is None and (nx, ny) not in self.blocked_tiles:
                piece.x = nx
                piece.y = ny
                self._grid_dirty = True
                return True
            nx += dx
            ny += dy

        # 2) Try all adjacent cells (including diagonals), sorted by distance to center
        cx, cy = self.width / 2.0, self.height / 2.0
        adjacents = []
        for adx in (-1, 0, 1):
            for ady in (-1, 0, 1):
                if adx == 0 and ady == 0:
                    continue
                ax, ay = piece.x + adx, piece.y + ady
                if (0 <= ax < self.width and 0 <= ay < self.height
                        and (ax, ay) not in self.dead_zone
                        and (ax, ay) not in self.blocked_tiles
                        and self.get_piece_at(ax, ay) is None):
                    dist = abs(ax - cx) + abs(ay - cy)
                    adjacents.append((dist, ax, ay))
        adjacents.sort()
        if adjacents:
            _, ax, ay = adjacents[0]
            piece.x = ax
            piece.y = ay
            self._grid_dirty = True
            return True

        # 3) Find nearest empty cell on the entire surviving board
        best = None
        best_dist = float('inf')
        for bx in range(self.width):
            for by in range(self.height):
                if ((bx, by) not in self.dead_zone
                        and (bx, by) not in self.blocked_tiles
                        and self.get_piece_at(bx, by) is None):
                    dist = abs(bx - piece.x) + abs(by - piece.y)
                    if dist < best_dist:
                        best_dist = dist
                        best = (bx, by)
        if best:
            piece.x, piece.y = best
            self._grid_dirty = True
            return True

        return False

    def _resolve_squeeze(self, squeeze_list: list[Piece], ring: int) -> list[Piece]:
        """Damage squeezed pieces until enough die to free up space."""
        killed: list[Piece] = []
        max_iters = 50  # safety

        for _ in range(max_iters):
            # Try to place each remaining squeezed piece
            still_stuck: list[Piece] = []
            for piece in squeeze_list:
                if not piece.alive:
                    continue
                if self._try_push_piece(piece, ring):
                    pass  # placed successfully
                else:
                    still_stuck.append(piece)

            if not still_stuck:
                break

            # All still-stuck pieces take 1 damage
            for piece in still_stuck:
                piece.hp -= 1
                if piece.hp <= 0:
                    piece.alive = False
                    killed.append(piece)

            # Remove dead from squeeze list and board
            squeeze_list = [p for p in still_stuck if p.alive]
            self.pieces = [p for p in self.pieces if p.alive]

            if not squeeze_list:
                break

        # Safety: kill any pieces still stranded in dead zone after all attempts
        for piece in list(squeeze_list):
            if piece.alive and (piece.x, piece.y) in self.dead_zone:
                piece.alive = False
                killed.append(piece)
        self.pieces = [p for p in self.pieces if p.alive]
        self._grid_dirty = True

        return killed
