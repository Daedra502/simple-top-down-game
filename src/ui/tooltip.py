"""Item tooltips (Diablo 3 / Path of Exile 2 inspired).

Hovering an item -- in the backpack, an equipped slot, or a dropped item on the
ground -- pops a readable panel listing exactly the bonuses that item grants the
player. The numbers shown here match what the stat pipeline actually applies
(legacy ``item.stats`` + rolled ``item.affixes``, each scaled by the item's
purchased upgrade multiplier), so the tooltip is accurate, not decorative.
"""
import pygame

from src.items.item import slot_display_name

# Per-element accent colors for resistance / elemental lines.
_ELEMENT_COLORS = {
    "fire": (255, 130, 70),
    "cold": (120, 200, 255),
    "lightning": (255, 235, 95),
    "chaos": (190, 120, 225),
    "physical": (210, 210, 210),
}

# Stat-group accent colors (Diablo-style: life red, mana blue, offense orange).
_LIFE = (255, 110, 110)
_MANA = (110, 160, 255)
_OFFENSE = (255, 160, 95)
_DEFENSE = (150, 200, 255)
_UTILITY = (130, 230, 165)
_NEUTRAL = (220, 220, 220)

# Friendly labels + grouping for the legacy flat ``item.stats`` block.
# (kind: how to format the value; group color for readability.)
_LEGACY_STATS = {
    "health":      ("Maximum Life", "int", _LIFE),
    "mana":        ("Maximum Mana", "int", _MANA),
    "damage":      ("Attack Damage", "int", _OFFENSE),
    "armor":       ("Armor", "int", _DEFENSE),
    "attack_speed": ("Attack Speed", "pct_add", _OFFENSE),
    "elemental_damage": ("Elemental (Spell) Damage", "pct_points", _OFFENSE),
}

# Stats that read as percentage-point increases even though they are stored int.
_PCT_POINT_STATS = {
    "spell_damage", "fire_damage", "cold_damage", "lightning_damage",
    "physical_damage", "chaos_damage", "fireball_damage", "frostbolt_damage",
}


def _stat_color(stat):
    """Pick an accent color for an affix based on its stat key."""
    if stat.endswith("_resistance"):
        return _ELEMENT_COLORS.get(stat[: -len("_resistance")], _DEFENSE)
    if stat in ("max_health", "health_regen", "physical_resistance"):
        return _LIFE
    if stat in ("max_mana", "mana_regen"):
        return _MANA
    if stat in _PCT_POINT_STATS or stat in ("damage", "crit_chance", "crit_damage",
                                            "attack_speed", "burn_damage_increase",
                                            "increased_vulnerable_damage", "attack_radius"):
        return _OFFENSE
    if stat in ("armor",):
        return _DEFENSE
    return _UTILITY


def _fmt_affix(af, mult):
    """Return (text, color) for one rolled affix, scaled by upgrade multiplier."""
    stat = af["stat"]
    label = af.get("label", stat.replace("_", " ").title())
    val = af["value"] * mult
    color = _stat_color(stat)

    if stat.endswith("_resistance") or stat in _PCT_POINT_STATS:
        text = f"+{int(round(val))}% {label}"
    elif af.get("is_percent"):
        text = f"+{val * 100:.1f}% {label}"
    else:
        text = f"+{int(round(val))} {label}"
    return text, color


def build_item_lines(item, player_level=None):
    """Build the tooltip body as a list of (text, color) tuples.

    Order: header (name) -> meta (rarity/type/slot/level) -> stat lines ->
    footer (upgrade, sell value, level warning).
    """
    lines = []
    rarity_color = item.get_color()
    mult = item.upgrade_multiplier() if hasattr(item, "upgrade_multiplier") else 1.0

    # Header
    name = item.name
    if getattr(item, "upgrade_level", 0):
        name += f"  +{item.upgrade_level}"
    lines.append((name, rarity_color))

    # Meta line
    type_str = getattr(item, "item_type", "item").title()
    slot_str = slot_display_name(item.slot)
    lines.append((f"{item.rarity.name.title()} {type_str}  -  {slot_str}", (170, 170, 185)))
    ilvl = getattr(item, "ilvl", item.level_requirement)
    lines.append((f"Item Level {ilvl}", (140, 140, 155)))
    lines.append(("__rule__", None))

    # --- Stat block --------------------------------------------------------
    had_stat = False

    # Legacy flat stats
    for stat, (label, kind, color) in _LEGACY_STATS.items():
        value = item.stats.get(stat, 0)
        if not value:
            continue
        had_stat = True
        v = value * mult
        if kind == "int":
            lines.append((f"+{int(round(v))} {label}", color))
        elif kind == "pct_add":          # 0.10 -> "+10% Attack Speed"
            lines.append((f"+{v * 100:.0f}% {label}", color))
        elif kind == "pct_points":       # already a % amount
            lines.append((f"+{int(round(v))}% {label}", color))

    # Legacy resistances dict
    for elem, value in item.stats.get("resistances", {}).items():
        if value:
            had_stat = True
            color = _ELEMENT_COLORS.get(elem, _DEFENSE)
            lines.append((f"+{int(round(value * mult))}% {elem.title()} Resistance", color))

    # Rolled affixes
    for af in getattr(item, "affixes", []):
        had_stat = True
        text, color = _fmt_affix(af, mult)
        lines.append((text, color))

    if not had_stat:
        lines.append(("No bonuses", (140, 140, 140)))

    # --- Footer ------------------------------------------------------------
    lines.append(("__rule__", None))
    if hasattr(item, "can_upgrade") and item.can_upgrade():
        lines.append((f"Upgrade: {item.upgrade_cost()}c  (L-click when equipped)", (200, 180, 110)))
    if hasattr(item, "get_sell_value"):
        lines.append((f"Sell value: {item.get_sell_value()}c", (200, 180, 110)))
    if player_level is not None and player_level < item.level_requirement:
        lines.append((f"Requires Level {item.level_requirement}", (255, 90, 90)))

    return lines


# --- stat comparison --------------------------------------------------------
# Map legacy ``item.stats`` keys onto the canonical stat keys used by affixes,
# so an item's whole contribution can be reduced to one comparable dict.
_COMPARE_LEGACY = {
    "health": "max_health", "mana": "max_mana", "damage": "damage",
    "armor": "armor", "attack_speed": "attack_speed",
    "elemental_damage": "spell_damage",
}

# label + value format per canonical stat key (for delta lines).
_STAT_LABEL = {
    "max_health": ("Maximum Life", "flat"),
    "max_mana": ("Maximum Mana", "flat"),
    "armor": ("Armor", "flat"),
    "damage": ("Attack Damage", "flat"),
    "health_regen": ("Life Regen", "flat"),
    "mana_regen": ("Mana Regen", "flat"),
    "attack_speed": ("Attack Speed", "pct_frac"),
    "crit_chance": ("Critical Chance", "pct_frac"),
    "crit_damage": ("Critical Damage", "pct_frac"),
    "cooldown_reduction": ("Cooldown Reduction", "pct_frac"),
    "move_speed_increase": ("Movement Speed", "pct_frac"),
    "status_radius": ("Status Radius", "pct_frac"),
    "attack_radius": ("Attack Radius", "pct_frac"),
    "increased_vulnerable_damage": ("Vulnerable Damage", "pct_frac"),
    "burn_damage_increase": ("Burn Damage", "pct_frac"),
    "freeze_duration_bonus": ("Freeze Duration", "pct_frac"),
    "spell_damage": ("Spell Damage", "pct_points"),
    "shock_chain_bonus": ("Shock Chains", "flat"),
}


def compute_item_stats(item):
    """Reduce an item to a flat {canonical_stat: value} dict (upgrade-scaled).

    Mirrors what the gear pipeline actually applies, so deltas between two items
    are accurate.
    """
    mult = item.upgrade_multiplier() if hasattr(item, "upgrade_multiplier") else 1.0
    out = {}
    for stat, val in item.stats.items():
        if stat == "resistances":
            for elem, v in (val or {}).items():
                if v:
                    key = f"{elem}_resistance"
                    out[key] = out.get(key, 0) + v * mult
            continue
        key = _COMPARE_LEGACY.get(stat)
        if key and val:
            out[key] = out.get(key, 0) + val * mult
    for af in getattr(item, "affixes", []):
        out[af["stat"]] = out.get(af["stat"], 0) + af["value"] * mult
    return out


def _stat_label_fmt(key):
    if key in _STAT_LABEL:
        return _STAT_LABEL[key]
    if key.endswith("_resistance"):
        return (key[: -len("_resistance")].title() + " Resistance", "pct_points")
    if key.endswith("_damage"):
        return (key.replace("_", " ").title(), "pct_points")
    return (key.replace("_", " ").title(), "flat")


def _fmt_delta(key, delta):
    label, fmt = _stat_label_fmt(key)
    sign = "+" if delta > 0 else "-"
    a = abs(delta)
    if fmt == "pct_frac":
        num = f"{a * 100:.1f}%"
    elif fmt == "pct_points":
        num = f"{a:.0f}%"
    else:
        num = f"{a:.0f}" if a >= 1 else f"{a:.1f}"
    return f"{sign}{num} {label}"


def build_comparison_lines(new_item, base_item):
    """Delta lines comparing ``new_item`` to the currently-equipped ``base_item``.

    Green = upgrade, red = downgrade. Only changed stats are listed.
    """
    a = compute_item_stats(new_item)
    b = compute_item_stats(base_item)
    green, red = (120, 230, 130), (235, 110, 110)
    lines = [("If equipped (vs current):", (205, 205, 215))]
    any_diff = False
    for k in sorted(set(a) | set(b)):
        d = a.get(k, 0) - b.get(k, 0)
        if abs(d) < 1e-6:
            continue
        any_diff = True
        lines.append((_fmt_delta(k, d), green if d > 0 else red))
    if not any_diff:
        lines.append(("No stat change", (160, 160, 160)))
    return lines


class ItemTooltip:
    """Renders item hover tooltips, optionally side-by-side for comparison."""

    def __init__(self):
        self.title_font = pygame.font.Font(None, 22)
        self.font = pygame.font.Font(None, 18)
        self.pad = 10
        self.line_h = 19

    # --- low-level panel helpers -----------------------------------------
    def _measure(self, lines):
        """Render lines to surfaces; return (width, height, [surf|None])."""
        rendered = []
        max_w = 0
        for i, (text, color) in enumerate(lines):
            if text == "__rule__":
                rendered.append(None)
                continue
            font = self.title_font if i == 0 else self.font
            surf = font.render(text, True, color or (220, 220, 220))
            rendered.append(surf)
            max_w = max(max_w, surf.get_width())
        width = max_w + self.pad * 2
        height = self.pad * 2 + sum(self.line_h if r is None else r.get_height() + 2
                                    for r in rendered)
        return width, height, rendered

    def _blit_panel(self, surface, x, y, width, height, rendered, border):
        bg = pygame.Surface((width, height), pygame.SRCALPHA)
        bg.fill((12, 14, 22, 240))
        surface.blit(bg, (x, y))
        pygame.draw.rect(surface, border, pygame.Rect(x, y, width, height), 2, border_radius=4)
        cy = y + self.pad
        for r in rendered:
            if r is None:
                pygame.draw.line(surface, (70, 74, 92),
                                 (x + self.pad, cy + self.line_h // 2),
                                 (x + width - self.pad, cy + self.line_h // 2), 1)
                cy += self.line_h
            else:
                surface.blit(r, (x + self.pad, cy))
                cy += r.get_height() + 2

    # --- public API -------------------------------------------------------
    def draw(self, surface, item, pos, screen_w, screen_h, player_level=None):
        if item is None:
            return
        w, h, rendered = self._measure(build_item_lines(item, player_level))
        mx, my = pos
        x = mx + 18
        y = my + 12
        if x + w > screen_w:
            x = mx - w - 18
        if x < 0:
            x = 4
        if y + h > screen_h:
            y = max(4, screen_h - h - 4)
        self._blit_panel(surface, x, y, w, h, rendered, item.get_color())

    def draw_with_comparison(self, surface, item, compare_items, pos,
                             screen_w, screen_h, player_level=None):
        """Draw the hovered item plus the currently-equipped item(s) it would
        compare against, with a stat-delta block on the hovered panel."""
        if item is None:
            return
        compare_items = [c for c in (compare_items or []) if c is not None]
        if not compare_items:
            return self.draw(surface, item, pos, screen_w, screen_h, player_level)

        # Hovered panel = item tooltip + delta block vs the primary equipped.
        hov_lines = build_item_lines(item, player_level)
        hov_lines.append(("__rule__", None))
        hov_lines += build_comparison_lines(item, compare_items[0])
        hw, hh, hr = self._measure(hov_lines)

        # Equipped reference panel(s).
        comp_sized = [self._measure([("Currently Equipped", (185, 185, 195))]
                                    + build_item_lines(it, player_level)) for it in compare_items]
        cw = max((w for w, _, _ in comp_sized), default=0)
        gap = 12
        ch = sum(h for _, h, _ in comp_sized) + gap * (len(comp_sized) - 1)

        total_w = hw + gap + cw
        block_h = max(hh, ch)
        mx, my = pos
        x = mx + 18
        if x + total_w > screen_w:
            x = max(4, mx - total_w - 18)
        y = my + 12
        if y + block_h > screen_h:
            y = max(4, screen_h - block_h - 4)

        # Hovered panel on the left of the block, equipped stacked on the right.
        self._blit_panel(surface, x, y, hw, hh, hr, item.get_color())
        cx = x + hw + gap
        cy = y
        for (it, (w, h, r)) in zip(compare_items, comp_sized):
            self._blit_panel(surface, cx, cy, w, h, r, it.get_color())
            cy += h + gap
