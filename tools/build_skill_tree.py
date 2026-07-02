"""Generate data/skill_tree.json: a PoE2-style radial passive tree (~270 nodes).

Layout language (deterministic, no RNG):
  - Root at CENTER; eight spokes leave it at fixed angles, grouped into six
    themed regions (Fire, Lightning, Sorcery owns the mana/dmg/speed spokes,
    Summoner, Defense/Blood, Cold).
  - Each spoke is a chain of travel nodes usually ending in a rim notable +
    keystone; wheels of minors around a notable hang off the chain (staggered
    at an inner and an outer radius so neighbouring regions don't collide);
    a small utility cluster sits in the gap between adjacent spokes.
  - Ring roads (arcs of travel minors with an occasional notable) connect
    adjacent spokes at an inner and an outer radius so builds can travel
    between regions.
  - A final relaxation pass nudges any two nodes closer than MIN_DIST apart,
    then the whole graph is validated (ids, edges, connectivity, spacing,
    legacy contract).

Legacy contract (tests + keystones.KEYSTONE_NODES depend on these ids and
adjacencies -- do not break):
  root-adjacent: fire_1, mana_1, dmg_1, lightning_1, speed_1
  chains:        fire_1-fire_2-fire_3-fire_key, mana_1-mana_2-mana_3,
                 dmg_1-dmg_2-dmg_3, speed_1-atk_1-atk_2-atk_notable,
                 speed_1-move_1-move_2-move_notable (move_1 NOT adj root)
  bridge:        hybrid_ld adjacent to lightning_1 and dmg_1
  exists:        hpregen_notable
  keystone ids:  fire_key, mana_3, dmg_3, hybrid_ld (mechanical; see
                 src/spells/keystones.py) -- the rest are stat keystones.

Run:  python tools/build_skill_tree.py   (rewrites data/skill_tree.json and
data/skill_tree_regions.json, then validates the result).
"""
import json
import math
import os
import sys
from collections import defaultdict

CENTER = (600.0, 400.0)
MIN_DIST = 34          # relaxation target / validation floor (px)
WHEEL_R = 58

COL = {
    "fire":      (235, 95, 60),
    "lightning": (250, 220, 90),
    "sorcery":   (175, 120, 250),
    "speed":     (110, 235, 170),
    "summoner":  (150, 210, 120),
    "blood":     (215, 85, 85),
    "cold":      (115, 190, 240),
    "travel":    (150, 150, 150),
}


def _pos(angle_deg, radius):
    a = math.radians(angle_deg)
    return [round(CENTER[0] + math.cos(a) * radius, 1),
            round(CENTER[1] + math.sin(a) * radius, 1)]


class Builder:
    def __init__(self):
        self.nodes = {}

    def add(self, nid, name, pos, tier, bonuses, color, edges=()):
        assert nid not in self.nodes, f"duplicate id {nid}"
        self.nodes[nid] = {
            "name": name, "pos": list(pos), "tier": tier,
            "cost": 0 if nid == "root" else 1,
            "color": list(color), "bonuses": dict(bonuses),
            "edges": list(edges),
        }
        return nid

    def link(self, a, b):
        if b not in self.nodes[a]["edges"] and a not in self.nodes[b]["edges"]:
            self.nodes[a]["edges"].append(b)


B = Builder()
B.add("root", "Life Force", CENTER, "minor",
      {"max_health": 50, "max_mana": 20}, (100, 255, 100))


def chain(spec, color):
    ids = []
    for nid, name, ang, rad, tier, bon in spec:
        B.add(nid, name, _pos(ang, rad), tier, bon, color)
        if ids:
            B.link(ids[-1], nid)
        ids.append(nid)
    return ids


def wheel(prefix, minor_name, color, center_angle, center_radius, attach_id,
          notable_id, notable_name, notable_bonuses, minor_bonuses):
    """A PoE-style wheel: 7 minors + 1 notable ring-connected on a circle,
    attached to the tree at the wheel node nearest to the attach node."""
    cx, cy = _pos(center_angle, center_radius)
    count = 8
    ids = []
    ax, ay = B.nodes[attach_id]["pos"]
    base = math.degrees(math.atan2(ay - cy, ax - cx))
    for k in range(count):
        a = math.radians(base + k * 360.0 / count)
        pos = [round(cx + math.cos(a) * WHEEL_R, 1),
               round(cy + math.sin(a) * WHEEL_R, 1)]
        if k == count // 2:   # farthest from the entry: the notable
            ids.append(B.add(notable_id, notable_name, pos, "notable",
                             notable_bonuses, color))
        else:
            ids.append(B.add(f"{prefix}_m{k}", minor_name, pos, "minor",
                             minor_bonuses, color))
    for k in range(count):
        B.link(ids[k], ids[(k + 1) % count])
    B.link(attach_id, ids[0])


def cluster(prefix, name, color, angle, attach_id, bonuses, radii=(155, 200, 245)):
    prev = attach_id
    for k, r in enumerate(radii):
        nid = B.add(f"{prefix}_c{k}", name, _pos(angle, r), "minor", bonuses, color)
        B.link(prev, nid)
        prev = nid


# --- spokes -------------------------------------------------------------------
A_FIRE, A_LIGHT, A_DMG, A_MANA = 270, 315, 355, 35
A_ATK, A_SPEED, A_MOVE = 61, 75, 89
A_MINION, A_BLOOD, A_COLD = 120, 175, 225

# FIRE: legacy chain runs straight to its keystone; rim lord beyond it.
chain([
    ("fire_1", "Ember", A_FIRE, 110, "minor", {"fire_damage": 5}),
    ("fire_2", "Kindling", A_FIRE, 210, "minor", {"fire_damage": 5, "burn_damage_increase": 0.05}),
    ("fire_3", "Blaze", A_FIRE, 310, "minor", {"fire_damage": 6, "spell_damage": 3}),
    ("fire_key", "Elemental Focus", A_FIRE, 470, "keystone",
     {"spell_damage": 12, "fire_damage": 10, "max_mana": 20}),
    ("fire_lord", "Infernal Lord", A_FIRE, 550, "notable",
     {"fire_damage": 18, "fireball_damage": 15, "burn_damage_increase": 0.15}),
], COL["fire"])
B.link("root", "fire_1")
wheel("fire_wa", "Fire", COL["fire"], A_FIRE - 14, 360, "fire_3",
      "fire_wa_nb", "Pyromancer",
      {"fire_damage": 14, "fireball_damage": 10, "spell_damage": 5},
      {"fire_damage": 5})
wheel("fire_wb", "Fire", COL["fire"], A_FIRE + 14, 490, "fire_lord",
      "fire_wb_nb", "Wildfire",
      {"burn_damage_increase": 0.18, "fire_damage": 8, "status_radius": 0.1},
      {"burn_damage_increase": 0.05, "fire_damage": 3})

# LIGHTNING: full-length spoke.
chain([
    ("lightning_1", "Spark", A_LIGHT, 110, "minor", {"lightning_damage": 5}),
    ("ln_t1", "Static", A_LIGHT, 200, "minor", {"lightning_damage": 5, "crit_chance": 0.005}),
    ("ln_t2", "Charge", A_LIGHT, 270, "minor", {"lightning_damage": 6}),
    ("ln_t3", "Ion Trail", A_LIGHT, 380, "minor", {"lightning_damage": 6, "crit_chance": 0.005}),
    ("ln_rt", "Conduction", A_LIGHT, 470, "minor", {"lightning_damage": 7, "shock_range_bonus": 0.05}),
    ("storm_rim", "Thunderhead", A_LIGHT, 550, "notable",
     {"lightning_damage": 16, "shock_chain_bonus": 1, "crit_chance": 0.02}),
    ("ks_storm", "Stormcaller", A_LIGHT, 625, "keystone",
     {"lightning_damage": 20, "shock_chain_bonus": 2, "shock_range_bonus": 0.25}),
], COL["lightning"])
B.link("root", "lightning_1")
wheel("ln_wa", "Lightning", COL["lightning"], A_LIGHT - 14, 360, "ln_t2",
      "ln_wa_nb", "Overload",
      {"lightning_damage": 14, "shock_range_bonus": 0.1, "crit_damage": 0.15},
      {"lightning_damage": 5})
wheel("ln_wb", "Lightning", COL["lightning"], A_LIGHT + 14, 490, "ln_rt",
      "ln_wb_nb", "Tempest",
      {"lightning_damage": 10, "attack_speed": 0.06, "crit_chance": 0.02},
      {"lightning_damage": 3, "crit_chance": 0.004})

# DMG (arcane/blood spoke of Sorcery): short legacy chain ending in Omnivamp.
chain([
    ("dmg_1", "Arcane Bite", A_DMG, 110, "minor", {"spell_damage": 4, "damage": 2}),
    ("dmg_2", "Arcane Hunger", A_DMG, 240, "minor", {"spell_damage": 5, "damage": 3}),
    ("dmg_3", "Omnivamp", A_DMG, 380, "keystone",
     {"spell_damage": 10, "max_health": 40, "life_leech": 0.05}),
], COL["sorcery"])
B.link("root", "dmg_1")
wheel("dmg_wa", "Arcana", COL["sorcery"], A_DMG - 14, 360, "dmg_2",
      "dmg_wa_nb", "Battle Mage",
      {"spell_damage": 12, "damage": 8, "crit_damage": 0.2},
      {"spell_damage": 4, "damage": 2})
wheel("dmg_wb", "Arcana", COL["sorcery"], A_DMG + 14, 490, "dmg_2",
      "dmg_wb_nb", "Blood Scholar",
      {"spell_damage": 10, "life_leech": 0.03, "max_health": 25},
      {"spell_damage": 3, "max_health": 8})

# Bridge keystone between Lightning and the dmg spoke (legacy hybrid_ld).
B.add("hybrid_ld", "Voltage Surge", _pos(335, 190), "keystone",
      {"lightning_damage": 10, "spell_damage": 8, "projectile_speed": 0.15},
      COL["lightning"])
B.link("hybrid_ld", "lightning_1")
B.link("hybrid_ld", "dmg_1")

# MANA spoke of Sorcery: short legacy chain ending in Spell Echo.
chain([
    ("mana_1", "Clarity", A_MANA, 110, "minor", {"max_mana": 25, "mana_regen": 0.3}),
    ("mana_2", "Meditation", A_MANA, 240, "minor", {"max_mana": 35, "mana_regen": 0.5}),
    ("mana_3", "Spell Echo", A_MANA, 380, "keystone",
     {"max_mana": 60, "mana_regen": 1.0, "cooldown_reduction": 0.05}),
], COL["sorcery"])
B.link("root", "mana_1")
wheel("mana_wa", "Sorcery", COL["sorcery"], A_MANA - 14, 360, "mana_2",
      "mana_wa_nb", "Archmage",
      {"max_mana": 50, "spell_damage": 10, "mana_regen": 1.0},
      {"max_mana": 15, "mana_regen": 0.3})
wheel("mana_wb", "Sorcery", COL["sorcery"], A_MANA + 14, 490, "mana_2",
      "mana_wb_nb", "Prism Weaver",
      {"projectile_count": 1, "projectile_speed": 0.1, "spell_damage": 6},
      {"projectile_speed": 0.04, "spell_damage": 2})

# SPEED spoke of Sorcery: legacy twin branches (attack / movement).
B.add("speed_1", "Momentum", _pos(A_SPEED, 110), "minor",
      {"attack_speed": 0.04, "move_speed_increase": 0.02}, COL["speed"])
B.link("root", "speed_1")
chain([
    ("atk_1", "Quick Hands", A_ATK, 200, "minor", {"attack_speed": 0.04, "damage": 3}),
    ("atk_2", "Fluid Casting", A_ATK, 270, "minor", {"attack_speed": 0.05, "damage": 3}),
    ("atk_notable", "Battle Tempo", A_ATK, 380, "notable",
     {"attack_speed": 0.12, "damage": 8, "crit_chance": 0.01}),
], COL["speed"])
B.link("speed_1", "atk_1")
chain([
    ("move_1", "Fleet Foot", A_MOVE, 200, "minor", {"move_speed_increase": 0.04}),
    ("move_2", "Wind Runner", A_MOVE, 270, "minor", {"move_speed_increase": 0.04}),
    ("move_notable", "Slipstream", A_MOVE, 380, "notable",
     {"move_speed_increase": 0.1, "attack_speed": 0.05}),
], COL["speed"])
B.link("speed_1", "move_1")
chain([
    ("spd_rt", "Tailwind", A_SPEED, 470, "minor",
     {"attack_speed": 0.04, "move_speed_increase": 0.02}),
    ("ks_zephyr", "Zephyr", A_SPEED, 560, "keystone",
     {"attack_speed": 0.15, "move_speed_increase": 0.1, "cooldown_reduction": 0.08}),
], COL["speed"])
B.link("atk_notable", "spd_rt")
B.link("move_notable", "spd_rt")
wheel("spd_wa", "Alacrity", COL["speed"], A_ATK - 14, 490, "atk_notable",
      "spd_wa_nb", "Frenzy",
      {"attack_speed": 0.1, "crit_chance": 0.02, "projectile_speed": 0.1},
      {"attack_speed": 0.03})
wheel("spd_wb", "Alacrity", COL["speed"], A_MOVE + 14, 490, "move_notable",
      "spd_wb_nb", "Phase Dancer",
      {"move_speed_increase": 0.08, "cooldown_reduction": 0.04, "max_mana": 20},
      {"move_speed_increase": 0.02, "cooldown_reduction": 0.005})

# SUMMONER: full-length spoke.
chain([
    ("minion_1", "Dark Pact", A_MINION, 110, "minor", {"minion_damage_increase": 0.06}),
    ("mn_t1", "Grave Call", A_MINION, 200, "minor", {"minion_damage_increase": 0.06}),
    ("mn_t2", "Bone Binding", A_MINION, 270, "minor", {"minion_damage_increase": 0.07, "max_health": 10}),
    ("mn_t3", "Soul Harvest", A_MINION, 380, "minor", {"minion_damage_increase": 0.07, "life_leech": 0.01}),
    ("mn_rt", "Death March", A_MINION, 470, "minor", {"minion_damage_increase": 0.08}),
    ("necro_rim", "Bone Sovereign", A_MINION, 550, "notable",
     {"minion_damage_increase": 0.2, "max_health": 25, "damage": 5}),
    ("ks_deadlord", "Lord of the Dead", A_MINION, 625, "keystone",
     {"minion_damage_increase": 0.4, "max_health": 40}),
], COL["summoner"])
B.link("root", "minion_1")
wheel("mn_wa", "Necromancy", COL["summoner"], A_MINION - 14, 360, "mn_t2",
      "mn_wa_nb", "Corpse Tender",
      {"minion_damage_increase": 0.15, "health_regen": 1.0},
      {"minion_damage_increase": 0.05})
wheel("mn_wb", "Necromancy", COL["summoner"], A_MINION + 14, 490, "mn_rt",
      "mn_wb_nb", "Grave Herald",
      {"minion_damage_increase": 0.12, "max_health": 20, "mana_regen": 0.5},
      {"minion_damage_increase": 0.04, "max_health": 6})

# DEFENSE / BLOOD: full-length spoke; hosts the legacy hpregen_notable.
chain([
    ("blood_1", "Vigor", A_BLOOD, 110, "minor", {"max_health": 15}),
    ("bl_t1", "Stone Skin", A_BLOOD, 200, "minor", {"armor": 4, "max_health": 10}),
    ("bl_t2", "Iron Will", A_BLOOD, 270, "minor", {"armor": 5, "max_health": 12}),
    ("bl_t3", "Bulwark Stance", A_BLOOD, 380, "minor", {"armor": 6, "max_health": 12}),
    ("bl_rt", "Last Bastion", A_BLOOD, 470, "minor", {"armor": 6, "health_regen": 0.5}),
    ("bl_rim", "Bulwark", A_BLOOD, 550, "notable",
     {"armor": 15, "max_health": 40, "physical_resistance": 8}),
    ("ks_juggernaut", "Juggernaut", A_BLOOD, 625, "keystone",
     {"max_health_increase": 0.15, "armor": 20, "health_regen": 2.0}),
], COL["blood"])
B.link("root", "blood_1")
wheel("bl_wa", "Blood", COL["blood"], A_BLOOD - 14, 360, "bl_t2",
      "hpregen_notable", "Font of Life",
      {"health_regen": 2.5, "max_health": 20},
      {"health_regen": 0.4, "max_health": 6})
wheel("bl_wb", "Blood", COL["blood"], A_BLOOD + 14, 490, "bl_rt",
      "bl_wb_nb", "Elements Ward",
      {"fire_resistance": 10, "cold_resistance": 10, "lightning_resistance": 10},
      {"fire_resistance": 3, "cold_resistance": 3, "lightning_resistance": 3})

# COLD: full-length spoke.
chain([
    ("cold_1", "Chill", A_COLD, 110, "minor", {"cold_damage": 5}),
    ("cd_t1", "Frostbite", A_COLD, 200, "minor", {"cold_damage": 5, "freeze_duration_bonus": 0.03}),
    ("cd_t2", "Rime", A_COLD, 270, "minor", {"cold_damage": 6}),
    ("cd_t3", "Deep Winter", A_COLD, 380, "minor", {"cold_damage": 6, "freeze_threshold_reduction": 0.03}),
    ("cd_rt", "Whiteout", A_COLD, 470, "minor", {"cold_damage": 7}),
    ("cd_rim", "Glacier", A_COLD, 550, "notable",
     {"cold_damage": 16, "frostbolt_damage": 12, "freeze_duration_bonus": 0.1}),
    ("ks_winterheart", "Winterheart", A_COLD, 625, "keystone",
     {"cold_damage": 20, "freeze_threshold_reduction": 0.2, "freeze_duration_bonus": 0.2}),
], COL["cold"])
B.link("root", "cold_1")
wheel("cd_wa", "Cold", COL["cold"], A_COLD - 14, 360, "cd_t2",
      "cd_wa_nb", "Shatter",
      {"cold_damage": 14, "frostbolt_damage": 10, "crit_damage": 0.2},
      {"cold_damage": 5})
wheel("cd_wb", "Cold", COL["cold"], A_COLD + 14, 490, "cd_rt",
      "cd_wb_nb", "Permafrost",
      {"freeze_duration_bonus": 0.15, "freeze_threshold_reduction": 0.1, "cold_damage": 8},
      {"freeze_duration_bonus": 0.04, "cold_damage": 3})

# --- gap clusters (small utility chains between adjacent spokes) ---------------
cluster("fire", "Warmth", COL["fire"], 292, "fire_1", {"max_health": 12, "fire_damage": 2})
cluster("dmg", "Focus", COL["sorcery"], 15, "dmg_1", {"spell_damage": 2, "max_mana": 8})
cluster("mana", "Insight", COL["sorcery"], 48, "mana_1", {"max_mana": 12, "cooldown_reduction": 0.005})
cluster("spd", "Agility", COL["speed"], 104, "speed_1", {"move_speed_increase": 0.015, "attack_speed": 0.015})
cluster("mn", "Ritual", COL["summoner"], 147, "minion_1", {"minion_damage_increase": 0.03, "max_mana": 6})
cluster("bl", "Toughness", COL["blood"], 200, "blood_1", {"max_health": 10, "armor": 2})
cluster("cd", "Insulation", COL["cold"], 247, "cold_1", {"max_health": 8, "cold_damage": 2})

# --- ring roads ---------------------------------------------------------------
RING_NOTABLE_BONUSES = {"max_health": 20, "max_mana": 15, "damage": 4}


def ring_road(tag, anchors, minor_bonuses, notables=False, spacing=52.0):
    """Arcs of travel minors between consecutive anchors [(angle, radius, id)].
    Interpolates both angle and radius; optional notable at each arc midpoint."""
    for i in range(len(anchors)):
        a1, r1, n1 = anchors[i]
        a2, r2, n2 = anchors[(i + 1) % len(anchors)]
        if a2 <= a1:
            a2 += 360
        arc_len = math.radians(a2 - a1) * (r1 + r2) / 2.0
        n_between = max(1, int(arc_len / spacing) - 1)
        prev = n1
        for k in range(1, n_between + 1):
            f = k / (n_between + 1)
            ang, rad = a1 + (a2 - a1) * f, r1 + (r2 - r1) * f
            mid = notables and (k == (n_between + 1) // 2) and n_between >= 3
            nid = f"{tag}_{i}_{k}"
            B.add(nid, "Crossroads" if mid else "Wayfare",
                  _pos(ang % 360, rad),
                  "notable" if mid else "minor",
                  RING_NOTABLE_BONUSES if mid else minor_bonuses,
                  COL["travel"])
            B.link(prev, nid)
            prev = nid
        B.link(prev, n2)


ring_road("ring_i", [
    (A_FIRE, 310, "fire_3"), (A_LIGHT, 270, "ln_t2"), (A_DMG, 240, "dmg_2"),
    (A_MANA, 240, "mana_2"), (A_ATK, 270, "atk_2"), (A_MOVE, 270, "move_2"),
    (A_MINION, 270, "mn_t2"), (A_BLOOD, 270, "bl_t2"), (A_COLD, 270, "cd_t2"),
], {"max_health": 8, "max_mana": 6}, notables=True)

ring_road("ring_o", [
    (A_FIRE, 550, "fire_lord"), (A_LIGHT, 470, "ln_rt"), (A_SPEED, 470, "spd_rt"),
    (A_MINION, 470, "mn_rt"), (A_BLOOD, 470, "bl_rt"), (A_COLD, 470, "cd_rt"),
], {"max_health": 10, "armor": 2}, spacing=60.0)

# --- region labels (consumed by the tree UI) ----------------------------------
REGIONS = [
    {"name": "FIRE", "angle": A_FIRE}, {"name": "LIGHTNING", "angle": A_LIGHT},
    {"name": "SORCERY", "angle": 15}, {"name": "ALACRITY", "angle": A_SPEED},
    {"name": "SUMMONING", "angle": A_MINION}, {"name": "BLOOD & IRON", "angle": A_BLOOD},
    {"name": "WINTER", "angle": A_COLD},
]
_REGION_COL = [COL["fire"], COL["lightning"], COL["sorcery"], COL["speed"],
               COL["summoner"], COL["blood"], COL["cold"]]


# --- relaxation ---------------------------------------------------------------
def relax(nodes, min_dist=MIN_DIST, passes=300):
    """Push apart any two nodes closer than min_dist (root stays pinned)."""
    ids = [nid for nid in nodes if nid != "root"]
    for _ in range(passes):
        moved = False
        pts = {nid: nodes[nid]["pos"] for nid in nodes}
        for i, na in enumerate(ids):
            xa, ya = pts[na]
            for nb in ids[i + 1:]:
                xb, yb = pts[nb]
                dx, dy = xb - xa, yb - ya
                d = math.hypot(dx, dy)
                if d >= min_dist or d == 0:
                    continue
                push = (min_dist - d) / 2.0 + 0.5
                ux, uy = dx / d, dy / d
                nodes[na]["pos"][0] -= ux * push
                nodes[na]["pos"][1] -= uy * push
                nodes[nb]["pos"][0] += ux * push
                nodes[nb]["pos"][1] += uy * push
                xa, ya = nodes[na]["pos"]
                moved = True
        if not moved:
            return True
    return False


# --- validation ---------------------------------------------------------------
def validate(nodes):
    ids = set(nodes)
    errors = []
    adj = defaultdict(set)
    for nid, row in nodes.items():
        for e in row["edges"]:
            if e not in ids:
                errors.append(f"{nid} -> missing edge target {e}")
            else:
                adj[nid].add(e)
                adj[e].add(nid)

    seen, stack = {"root"}, ["root"]
    while stack:
        for nb in adj[stack.pop()]:
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    unreachable = ids - seen
    if unreachable:
        errors.append(f"unreachable nodes: {sorted(unreachable)[:10]} ...")

    pts = list(nodes.items())
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            (na, ra), (nb, rb) = pts[i], pts[j]
            d = math.hypot(ra["pos"][0] - rb["pos"][0], ra["pos"][1] - rb["pos"][1])
            if d < MIN_DIST - 2:
                errors.append(f"nodes too close ({d:.0f}px): {na} / {nb}")

    required = ["fire_1", "fire_2", "fire_3", "fire_key", "mana_1", "mana_2",
                "mana_3", "dmg_1", "dmg_2", "dmg_3", "lightning_1", "speed_1",
                "atk_1", "atk_2", "atk_notable", "move_1", "move_2",
                "move_notable", "hpregen_notable", "hybrid_ld"]
    errors += [f"missing required legacy node {nid}" for nid in required if nid not in ids]
    for a, b in [("root", "fire_1"), ("root", "mana_1"), ("root", "dmg_1"),
                 ("root", "lightning_1"), ("root", "speed_1"),
                 ("fire_3", "fire_key"), ("mana_2", "mana_3"),
                 ("dmg_2", "dmg_3"), ("hybrid_ld", "lightning_1"),
                 ("hybrid_ld", "dmg_1"), ("speed_1", "move_1"),
                 ("move_1", "move_2"), ("speed_1", "atk_1")]:
        if b not in adj[a]:
            errors.append(f"missing required edge {a} - {b}")
    if "move_1" in adj["root"]:
        errors.append("move_1 must NOT be adjacent to root (cut-vertex test)")
    return errors


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not relax(B.nodes):
        print("WARNING: relaxation did not fully converge")
    for row in B.nodes.values():
        row["pos"] = [round(row["pos"][0], 1), round(row["pos"][1], 1)]

    errors = validate(B.nodes)
    if errors:
        for e in errors:
            print("ERROR:", e)
        sys.exit(1)

    tiers = defaultdict(int)
    for row in B.nodes.values():
        tiers[row["tier"]] += 1
    print(f"OK: {len(B.nodes)} nodes ({dict(tiers)})")

    with open(os.path.join(here, "data", "skill_tree.json"), "w") as f:
        json.dump(B.nodes, f, indent=1)
    regions = [{"name": r["name"], "pos": _pos(r["angle"], 690),
                "color": list(c)} for r, c in zip(REGIONS, _REGION_COL)]
    with open(os.path.join(here, "data", "skill_tree_regions.json"), "w") as f:
        json.dump(regions, f, indent=1)
    print("wrote data/skill_tree.json and data/skill_tree_regions.json")


if __name__ == "__main__":
    main()
