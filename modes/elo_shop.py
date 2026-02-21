"""ELO Shop — permanent unlock screen that spends ELO currency."""

from __future__ import annotations

import tcod.console

from engine import Action, GameState
import renderer
import save_data as sd

SHOP_CATALOG = [
    # Pieces
    {"key": "rook",     "category": "Piece",    "name": "Rook",          "cost": 200,  "desc": "Unlock Rook for starting roster"},
    {"key": "queen",    "category": "Piece",    "name": "Queen",         "cost": 500,  "desc": "Unlock Queen for starting roster"},
    {"key": "king",     "category": "Piece",    "name": "King",          "cost": 1000, "desc": "Unlock King for starting roster"},
    # Modifiers
    {"key": "piercing", "category": "Modifier", "name": "Piercing",      "cost": 150,  "desc": "Piercing appears in battle shop"},
    {"key": "royal",    "category": "Modifier", "name": "Royal",         "cost": 300,  "desc": "Royal appears in battle shop"},
    # Upgrades (repeatable)
    {"key": "extra_piece", "category": "Upgrade", "name": "+1 Roster Slot", "cost": 400, "desc": "Start with 1 extra piece"},
    {"key": "start_gold",  "category": "Upgrade", "name": "+5 Gold",        "cost": 250, "desc": "Start battles with +5 gold"},
    {"key": "extra_life",  "category": "Upgrade", "name": "+1 Life",        "cost": 800, "desc": "Gain an extra life in tournaments"},
    {"key": "tarot_slot",  "category": "Upgrade", "name": "+1 Tarot Slot",  "cost": 500, "desc": "Hold an additional Tarot card"},
    {"key": "artifact_slot", "category": "Upgrade", "name": "+1 Artifact Slot", "cost": 600, "desc": "Hold an additional Artifact"},
]

CATEGORY_COLORS = {
    "Piece":    (80, 130, 255),
    "Modifier": (255, 180, 60),
    "Upgrade":  (100, 220, 100),
}


class EloShop:
    """Permanent unlock shop mode — spend ELO on pieces, modifiers, upgrades."""

    def __init__(self, save_data: sd.SaveData) -> None:
        self.save_data = save_data
        self.selection = 0
        self.message = ""
        # Show 4 items at a time, scroll offset
        self.scroll = 0
        self.visible_count = 4

    def on_enter(self) -> None:
        self.selection = 0
        self.scroll = 0
        self.message = ""

    def _is_owned(self, item: dict) -> bool:
        """Check if a catalog item is already owned (non-upgrade)."""
        if item["category"] == "Piece":
            return item["key"] in self.save_data.unlocked_pieces
        elif item["category"] == "Modifier":
            return item["key"] in self.save_data.unlocked_modifiers
        return False  # upgrades are always purchasable

    def _effective_cost(self, item: dict) -> int:
        """Return effective cost — upgrades double each level."""
        if item["category"] == "Upgrade":
            level = self.save_data.upgrades.get(item["key"], 0)
            return item["cost"] * (2 ** level)
        return item["cost"]

    def _upgrade_level(self, item: dict) -> int:
        if item["category"] == "Upgrade":
            return self.save_data.upgrades.get(item["key"], 0)
        return 0

    def handle_input(self, action: Action) -> GameState | None:
        if action == Action.LEFT:
            self.selection = max(0, self.selection - 1)
            self._update_scroll()
        elif action == Action.RIGHT:
            self.selection = min(len(SHOP_CATALOG) - 1, self.selection + 1)
            self._update_scroll()
        elif action == Action.CONFIRM:
            self._purchase()
        elif action == Action.CANCEL:
            return GameState.MENU
        elif action == Action.MOUSE_CLICK:
            self._purchase()
        return None

    def _update_scroll(self) -> None:
        if self.selection < self.scroll:
            self.scroll = self.selection
        elif self.selection >= self.scroll + self.visible_count:
            self.scroll = self.selection - self.visible_count + 1

    def _purchase(self) -> None:
        item = SHOP_CATALOG[self.selection]
        owned = self._is_owned(item)
        cost = self._effective_cost(item)

        if owned and item["category"] != "Upgrade":
            self.message = f"{item['name']} already owned!"
            return

        if self.save_data.elo < cost:
            self.message = "Not enough ELO!"
            return

        self.save_data.elo -= cost
        sd.unlock_item(self.save_data, item["category"], item["key"])
        sd.save(self.save_data)

        if item["category"] == "Upgrade":
            level = self.save_data.upgrades.get(item["key"], 0)
            self.message = f"Purchased {item['name']} (Lv.{level})!"
        else:
            self.message = f"Unlocked {item['name']}!"

    def _update_cursor_from_board(self, bx: int, by: int) -> None:
        """No-op for ELO shop (no board)."""
        pass

    def to_render_state(self) -> dict:
        """Serialize state for JS rendering."""
        items = []
        for item in SHOP_CATALOG:
            owned = self._is_owned(item) and item["category"] != "Upgrade"
            cost = self._effective_cost(item)
            level = self._upgrade_level(item)
            items.append({
                "key": item["key"],
                "category": item["category"],
                "name": item["name"],
                "cost": cost,
                "desc": item["desc"],
                "owned": owned,
                "level": level,
                "affordable": self.save_data.elo >= cost and not owned,
                "icon": self._get_icon(item),
                "color": list(CATEGORY_COLORS.get(item["category"], (200, 200, 200))),
            })
        return {
            "phase": "elo_shop",
            "elo": self.save_data.elo,
            "items": items,
            "selection": self.selection,
            "message": self.message,
        }

    def render(self, console: tcod.console.Console) -> None:
        cw, ch = console.width, console.height

        # Felt background
        console.draw_rect(0, 0, cw, ch, ch=ord(' '), bg=renderer.BG_FELT)

        # Header
        header = "ELO SHOP"
        hx = (cw - len(header)) // 2
        console.print(hx, 2, header, fg=(255, 220, 100), bg=renderer.BG_FELT)

        # ELO balance
        renderer.draw_elo_display(console, (cw - 16) // 2, 4, self.save_data.elo)

        # Separator
        sep = "\u2550" * min(60, cw - 4)
        sx = (cw - len(sep)) // 2
        console.print(sx, 5, sep, fg=(80, 80, 60), bg=renderer.BG_FELT)

        # Card grid — show `visible_count` items starting from scroll
        visible_items = SHOP_CATALOG[self.scroll:self.scroll + self.visible_count]
        num_vis = len(visible_items)
        card_w = min(18, max(14, (cw - 8 - 3 * (num_vis - 1)) // max(1, num_vis)))
        gap = 3
        total_w = card_w * num_vis + gap * max(0, num_vis - 1)
        start_x = (cw - total_w) // 2
        card_h = 12
        cards_y = 7

        for i, item in enumerate(visible_items):
            abs_idx = self.scroll + i
            cx = start_x + i * (card_w + gap)
            selected = (abs_idx == self.selection)
            owned = self._is_owned(item) and item["category"] != "Upgrade"
            cost = self._effective_cost(item)
            affordable = self.save_data.elo >= cost and not owned

            color = CATEGORY_COLORS.get(item["category"], renderer.FG_TEXT)

            # Build description
            desc = item["desc"]
            if item["category"] == "Upgrade":
                level = self._upgrade_level(item)
                desc = f"{item['desc']} (Lv.{level})"

            # Draw card
            if owned:
                # Grayed out owned card
                renderer.draw_shop_card(
                    console, cx, cards_y, card_w, card_h,
                    icon="\u2713",
                    name=item["name"],
                    description="OWNED",
                    category=item["category"],
                    color=(80, 80, 80),
                    selected=selected,
                    affordable=False,
                )
            else:
                icon = self._get_icon(item)
                renderer.draw_shop_card(
                    console, cx, cards_y, card_w, card_h,
                    icon=icon,
                    name=item["name"],
                    description=desc,
                    category=item["category"],
                    color=color,
                    selected=selected,
                    affordable=affordable,
                )

            # Price tag
            if not owned:
                renderer.draw_shop_price_tag(
                    console, cx, cards_y + card_h + 1, card_w,
                    cost=cost, affordable=affordable,
                )
            else:
                # Show "OWNED" text below
                owned_str = "OWNED"
                ox = cx + (card_w - len(owned_str)) // 2
                console.print(ox, cards_y + card_h + 1, owned_str,
                              fg=(80, 80, 80), bg=renderer.BG_FELT)

        # Scroll indicators
        if self.scroll > 0:
            console.print(start_x - 2, cards_y + card_h // 2, "\u25c0",
                          fg=(200, 200, 200), bg=renderer.BG_FELT)
        if self.scroll + self.visible_count < len(SHOP_CATALOG):
            end_x = start_x + total_w + 1
            console.print(min(end_x, cw - 1), cards_y + card_h // 2, "\u25b6",
                          fg=(200, 200, 200), bg=renderer.BG_FELT)

        # Page indicator
        page_str = f"{self.selection + 1}/{len(SHOP_CATALOG)}"
        px = (cw - len(page_str)) // 2
        console.print(px, cards_y + card_h + 3, page_str,
                      fg=renderer.FG_DIM, bg=renderer.BG_FELT)

        # Back button
        btn_y = cards_y + card_h + 5
        renderer.draw_felt_button(
            console, btn_y, width=total_w, start_x=start_x,
            label="Back to Menu",
            selected=False,
            fg_normal=(180, 180, 180),
            bg_selected=(60, 60, 80),
        )

        # Controls
        controls = "L/R: browse | Enter: buy | Esc: back"
        if len(controls) > cw - 2:
            controls = controls[:cw - 2]
        ccx = (cw - len(controls)) // 2
        console.print(max(0, ccx), ch - 2, controls, fg=renderer.FG_DIM, bg=renderer.BG_FELT)

        # Message
        if self.message:
            msg = self.message[:cw - 2] if len(self.message) > cw - 2 else self.message
            mx = (cw - len(msg)) // 2
            console.print(max(0, mx), ch - 1, msg,
                          fg=renderer.FG_TEXT, bg=renderer.BG_FELT)

    def _get_icon(self, item: dict) -> str:
        """Return an icon character for a shop item."""
        icons = {
            "rook": "\u265c", "queen": "\u265b", "king": "\u265a",
            "piercing": "\u2694", "royal": "\u2654",
            "extra_piece": "+", "start_gold": "$", "extra_life": "\u2665",
            "tarot_slot": "\u2605", "artifact_slot": "\u2726",
        }
        return icons.get(item["key"], "?")
