"""Active skill framework (DESIGN.md Phase 13).

PoE-inspired: each skill is data-driven (data/skills.json), levels up on its own
XP track (gained from casting, dealing damage, and kills), and grows stronger
with level. Each skill also has its own mastery path (data/skill_mastery.json);
a mastery point is earned every few levels. Phase 14 (runes) layers on top.
"""
from src.core.data_loader import load_json

MASTERY_EVERY = 3   # one mastery point per N skill levels

# XP awarded per event type.
XP_ON_CAST = 10
XP_ON_KILL = 30
XP_PER_DAMAGE = 0.08


class Skill:
    def __init__(self, skill_id, defn):
        self.id = skill_id
        self.defn = defn
        self.name = defn["name"]
        self.element = defn["element"]
        self.kind = defn["kind"]
        self.mana_cost = defn["mana_cost"]
        self.cooldown = defn["cooldown"]
        self.max_level = defn["max_level"]
        self.color = tuple(defn.get("color", [255, 255, 255]))
        self.mastery_key = defn.get("mastery", skill_id)

        self.level = 1
        self.xp = 0.0
        self.cd_remaining = 0.0
        self.allocated_mastery = []
        self.runes = []   # equipped rune ids (Phase 14)

    # --- runes (Phase 14) -------------------------------------------------
    def equip_rune(self, rune_id):
        from src.spells.runes import MAX_RUNE_SLOTS, load_runes
        if len(self.runes) >= MAX_RUNE_SLOTS or rune_id in self.runes:
            return False
        if rune_id not in load_runes():
            return False
        self.runes.append(rune_id)
        return True

    def unequip_rune(self, rune_id):
        if rune_id in self.runes:
            self.runes.remove(rune_id)
            return True
        return False

    # --- XP / leveling ----------------------------------------------------
    def xp_to_next(self):
        c = self.defn["xp_curve"]
        if self.level >= self.max_level:
            return 0
        return int(c["base"] * (self.level ** c["exp"]))

    def gain_xp(self, amount):
        if self.level >= self.max_level:
            return 0
        self.xp += amount
        gained = 0
        need = self.xp_to_next()
        while need > 0 and self.xp >= need:
            self.xp -= need
            self.level += 1
            gained += 1
            need = self.xp_to_next()
        return gained

    # --- mastery ----------------------------------------------------------
    def _mastery_nodes(self):
        return load_json("skill_mastery.json").get(self.mastery_key, [])

    def mastery_points_available(self):
        return self.level // MASTERY_EVERY - len(self.allocated_mastery)

    def allocate_mastery(self, node_id):
        if self.mastery_points_available() <= 0:
            return False
        if node_id in self.allocated_mastery:
            return False
        if not any(n["id"] == node_id for n in self._mastery_nodes()):
            return False
        self.allocated_mastery.append(node_id)
        return True

    def deallocate_mastery(self, node_id):
        """Refund an allocated mastery node (frees the point for re-spend)."""
        if node_id in self.allocated_mastery:
            self.allocated_mastery.remove(node_id)
            return True
        return False

    def _mastery_effect(self, node_id):
        for n in self._mastery_nodes():
            if n["id"] == node_id:
                return n.get("effect", {})
        return {}

    # --- computed stats ---------------------------------------------------
    def stats(self):
        s = dict(self.defn["base"])
        lvl = self.level - 1
        for key, per in self.defn.get("per_level", {}).items():
            s[key] = s.get(key, 0) + per * lvl

        flags = {}
        damage_mult = 1.0
        speed_mult = 1.0
        for node_id in self.allocated_mastery:
            for ek, ev in self._mastery_effect(node_id).items():
                if ek == "count":
                    s["count"] = s.get("count", 1) + ev
                elif ek == "aoe_radius_add":
                    s["aoe_radius"] = s.get("aoe_radius", 0) + ev
                elif ek == "range_add":
                    s["range"] = s.get("range", 0) + ev
                elif ek == "radius_add":
                    s["radius"] = s.get("radius", 0) + ev
                elif ek == "damage_mult":
                    damage_mult += ev
                elif ek == "speed_mult":
                    speed_mult += ev
                elif ek in ("explosion", "explosion_radius", "freeze_explosion",
                            "burn_bonus", "pierce", "fork"):
                    # Accumulating projectile sub-mechanics (radii / burn / pierce / fork).
                    flags[ek] = flags.get(ek, 0) + ev
                else:
                    flags[ek] = ev
        s["damage"] = s.get("damage", 0) * damage_mult
        s["speed"] = s.get("speed", 0) * speed_mult
        s["flags"] = flags
        return s

    # --- casting bookkeeping ---------------------------------------------
    def update(self, dt):
        if self.cd_remaining > 0:
            self.cd_remaining -= dt

    def can_cast(self, player):
        return self.cd_remaining <= 0 and player.mana >= self.mana_cost

    def start_cooldown(self, player):
        cdr = getattr(player, "cooldown_reduction", 0.0)
        self.cd_remaining = self.cooldown * max(0.2, 1.0 - cdr)

    def cast_plan(self, player, tx, ty):
        """Return a description of the cast, transformed by equipped runes."""
        from src.spells.runes import apply_runes
        s = self.stats()
        radius_mult = 1.0 + getattr(player, "attack_radius_increase", 0.0)
        if self.kind == "projectile":
            # Passive tree adds projectiles and projectile speed on top of the
            # skill's own (per-spell mastery) count/speed.
            count = int(s.get("count", 1)) + int(getattr(player, "extra_projectiles", 0))
            speed = s.get("speed", 7) * (1.0 + getattr(player, "projectile_speed_increase", 0.0))
            # Forking: innate (skills.json base, e.g. Lightning Spark) + mastery.
            fork = int(s.get("fork", 0)) + int(s["flags"].get("fork", 0))
            plan = {"kind": "projectile", "count": max(1, count),
                    "speed": speed, "radius": int(s.get("radius", 6) * radius_mult),
                    "damage": player.get_spell_damage(s["damage"], self.element, self.id),
                    "element": self.element, "color": self.color,
                    "tx": tx, "ty": ty, "flags": s["flags"], "fork": fork,
                    "homing": bool(s["flags"].get("homing"))}
        elif self.kind == "aoe":
            plan = {"kind": "aoe", "at": self.defn.get("aoe_at", "player"),
                    "aoe_radius": s.get("aoe_radius", 80) * radius_mult,
                    "damage": player.get_spell_damage(s["damage"], self.element, self.id),
                    "element": self.element, "color": self.color,
                    "tx": tx, "ty": ty, "flags": s["flags"]}
        elif self.kind == "blink":
            plan = {"kind": "blink", "range": s.get("range", 300), "tx": tx, "ty": ty}
        elif self.kind == "summon":
            plan = {"kind": "summon", "count": int(s.get("count", 1)),
                    "damage": s["damage"], "duration": s.get("duration", 12),
                    "color": self.color}
        else:
            plan = {"kind": "none"}
        return apply_runes(plan, self.runes)

    # --- save -------------------------------------------------------------
    def to_dict(self):
        return {"id": self.id, "level": self.level, "xp": self.xp,
                "mastery": list(self.allocated_mastery), "runes": list(self.runes)}

    def load_dict(self, d):
        self.level = d.get("level", 1)
        self.xp = d.get("xp", 0.0)
        self.allocated_mastery = list(d.get("mastery", []))
        self.runes = list(d.get("runes", []))


class SkillManager:
    def __init__(self):
        defs = load_json("skills.json")
        self.skills = {sid: Skill(sid, defn) for sid, defn in defs.items()}
        self.slots = list(self.skills.keys())   # all skills usable; selectable 1..N

    def get(self, skill_id):
        return self.skills.get(skill_id)

    def slot(self, index):
        if 0 <= index < len(self.slots):
            return self.skills[self.slots[index]]
        return None

    def update(self, dt):
        for s in self.skills.values():
            s.update(dt)

    # XP awards (return levels gained, for cue purposes)
    def award_cast(self, skill_id):
        return self.skills[skill_id].gain_xp(XP_ON_CAST)

    def award_damage(self, skill_id, damage):
        if skill_id in self.skills:
            return self.skills[skill_id].gain_xp(damage * XP_PER_DAMAGE)
        return 0

    def award_kill(self, skill_id):
        if skill_id in self.skills:
            return self.skills[skill_id].gain_xp(XP_ON_KILL)
        return 0

    def to_dict(self):
        return [s.to_dict() for s in self.skills.values()]

    def load_list(self, data):
        for entry in data or []:
            sk = self.skills.get(entry.get("id"))
            if sk:
                sk.load_dict(entry)
