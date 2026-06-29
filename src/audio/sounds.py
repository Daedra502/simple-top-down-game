"""Procedural sound effects + ambient music (no external audio assets required).

Attack sounds and a looping ambient music bed are synthesized once with numpy
and handed to the pygame mixer. Sounds are built at full amplitude and their
*playback* volume is scaled at runtime via ``Sound.set_volume`` / channel volume,
so the options menu can move the SFX and Music sliders live without rebuilding
anything. Preferred volumes persist to a small JSON file between runs.

The module fails safe: if the mixer can't initialize (e.g. a headless/CI box)
every call becomes a no-op so the game never crashes for lack of an audio device.
"""
import json
import os

import numpy as np

try:
    import pygame
except Exception:  # pragma: no cover - pygame is always present in-game
    pygame = None


_SAMPLE_RATE = 44100
_MUSIC_CHANNEL = 0   # reserved mixer channel for the looping music bed
_SETTINGS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "saves", "audio_settings.json"))


# --- waveform helpers -------------------------------------------------------
def _envelope(n, attack=0.01, release=0.25):
    """A simple attack/decay amplitude envelope over n samples (0..1)."""
    env = np.ones(n)
    a = max(1, int(_SAMPLE_RATE * attack))
    r = max(1, int(_SAMPLE_RATE * release))
    env[:a] = np.linspace(0.0, 1.0, a)
    env[-r:] = np.linspace(1.0, 0.0, r)
    return env


def _tone(freq, dur, kind="sine", sweep=0.0):
    """Render a mono waveform. ``sweep`` bends the pitch over the duration."""
    n = int(_SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    f = freq * (1.0 + sweep * (t / dur))
    phase = 2 * np.pi * np.cumsum(f) / _SAMPLE_RATE
    if kind == "square":
        wave = np.sign(np.sin(phase))
    elif kind == "saw":
        wave = 2.0 * (t * freq - np.floor(0.5 + t * freq))
    elif kind == "noise":
        wave = np.random.uniform(-1.0, 1.0, n)
    else:  # sine
        wave = np.sin(phase)
    return wave * _envelope(n, release=min(0.3, dur * 0.6))


def _mix(*waves):
    """Sum waves (truncating to the shortest) and normalize to unit peak."""
    m = min(len(w) for w in waves)
    out = sum(w[:m] for w in waves)
    peak = np.max(np.abs(out)) or 1.0
    return out / peak


def _layer(*waves):
    """Sum waves padded to the *longest* length (no normalization).

    Unlike ``_mix`` this keeps absolute levels so callers can balance an
    arrangement themselves, and tolerates layers of different durations (a long
    drone under short stabs). Used by the music engine.
    """
    m = max(len(w) for w in waves)
    out = np.zeros(m)
    for w in waves:
        out[:len(w)] += w
    return out


# --- richer instruments (additive synthesis voices) -------------------------
# These expand the palette beyond the three primitive waveforms above so the
# music engine can arrange dark-fantasy textures (choir, strings, bells, drums,
# sub drones) in the spirit of Diablo III/IV and Path of Exile 1/2.
def _adsr(n, attack, decay, sustain, release):
    """A full attack/decay/sustain/release amplitude envelope over n samples."""
    a = max(1, int(_SAMPLE_RATE * attack))
    d = max(1, int(_SAMPLE_RATE * decay))
    r = max(1, int(_SAMPLE_RATE * release))
    a = min(a, n)
    d = min(d, max(0, n - a))
    r = min(r, max(0, n - a - d))
    s = max(0, n - a - d - r)
    env = np.concatenate([
        np.linspace(0.0, 1.0, a, endpoint=False),
        np.linspace(1.0, sustain, d, endpoint=False),
        np.full(s, sustain),
        np.linspace(sustain, 0.0, r),
    ])
    return env[:n] if len(env) >= n else np.pad(env, (0, n - len(env)))


def _voice_pad(freq, dur, detune=0.006, vibrato=4.5):
    """A breathy choir/vocal-pad voice: a few detuned harmonic partials with a
    slow swell and gentle vibrato -- the haunting wordless choir that defines
    Diablo's cathedral ambience."""
    n = int(_SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    vib = 1.0 + 0.004 * np.sin(2 * np.pi * vibrato * t)
    wave = np.zeros(n)
    # Formant-ish partial weights give the pad a vowel-like, vocal colour.
    for mult, amp in ((1.0, 1.0), (2.0, 0.5), (3.0, 0.28), (4.0, 0.14)):
        for d in (-detune, detune):
            wave += amp * np.sin(2 * np.pi * freq * mult * (1.0 + d) * t * vib)
    env = _adsr(n, attack=dur * 0.35, decay=dur * 0.2, sustain=0.8,
                release=dur * 0.4)
    return wave * env


def _bowed_string(freq, dur, detune=0.004):
    """A sustained bowed-string section: detuned saws (the classic 'supersaw'
    ensemble) with a soft attack -- the cello/viola beds under ARPG dungeons."""
    n = int(_SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    wave = np.zeros(n)
    for d in (-detune * 2, -detune, 0.0, detune, detune * 2):
        f = freq * (1.0 + d)
        wave += 2.0 * (t * f - np.floor(0.5 + t * f))
    env = _adsr(n, attack=dur * 0.22, decay=dur * 0.15, sustain=0.85,
                release=dur * 0.3)
    return wave * env


def _fm_bell(freq, dur, ratio=2.01, index=4.0):
    """An FM bell/glass tone with an inharmonic modulator and exponential decay
    -- the cold, glassy plucks PoE uses for arcane/menu accents."""
    n = int(_SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    decay = np.exp(-t / (dur * 0.35))
    mod = index * decay * np.sin(2 * np.pi * freq * ratio * t)
    wave = np.sin(2 * np.pi * freq * t + mod)
    return wave * decay


def _sub_drone(freq, dur, beat=0.6):
    """A deep sub-bass drone with a slow binaural beat for unease -- the
    foundational rumble of a brooding fantasy soundtrack."""
    n = int(_SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    wave = (np.sin(2 * np.pi * freq * t)
            + 0.6 * np.sin(2 * np.pi * (freq + beat) * t)
            + 0.3 * np.sin(2 * np.pi * freq * 0.5 * t))   # sub octave
    env = _adsr(n, attack=dur * 0.25, decay=0.0, sustain=1.0, release=dur * 0.25)
    return wave * env


def _taiko(dur=0.5, pitch=90.0):
    """A deep ritual war-drum: a pitch-dropping sine body plus a noise transient
    -- the tribal percussion driving boss and rift encounters."""
    n = int(_SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    body = np.sin(2 * np.pi * pitch * np.exp(-t * 6.0) * t * 4.0)
    transient = np.random.uniform(-1, 1, n) * np.exp(-t * 45.0)
    env = np.exp(-t / (dur * 0.4))
    return (body * 0.9 + transient * 0.5) * env


# Recipe per element -> a function returning a normalized mono waveform.
def _fire():
    return _mix(_tone(220, 0.32, "saw", sweep=-0.5),
                _tone(110, 0.32, "noise") * 0.6)


def _cold():
    return _mix(_tone(880, 0.30, "sine", sweep=0.4),
                _tone(1320, 0.30, "sine", sweep=0.3) * 0.5)


def _lightning():
    return _mix(_tone(140, 0.18, "square", sweep=2.5),
                _tone(90, 0.18, "noise") * 0.4)


def _physical():
    return _mix(_tone(120, 0.16, "sine", sweep=-0.6),
                _tone(80, 0.16, "noise") * 0.7)


def _chaos():
    return _mix(_tone(300, 0.34, "saw", sweep=-0.2),
                _tone(317, 0.34, "square", sweep=0.1) * 0.5)


_RECIPES = {
    "fire": _fire,
    "cold": _cold,
    "lightning": _lightning,
    "physical": _physical,
    "chaos": _chaos,
}


# --- modular, randomly generated music --------------------------------------
import random as _random

# Diatonic / modal scales (semitone offsets from the root). The darker modes
# (phrygian, harmonic minor, phrygian-dominant) give the exotic, dread-laden
# colour heard across Diablo and Path of Exile.
_SCALES = {
    "minor":             [0, 2, 3, 5, 7, 8, 10],   # aeolian
    "major":             [0, 2, 4, 5, 7, 9, 11],
    "dorian":            [0, 2, 3, 5, 7, 9, 10],
    "phrygian":          [0, 1, 3, 5, 7, 8, 10],    # brooding, "evil" semitone
    "harmonic_minor":    [0, 2, 3, 5, 7, 8, 11],    # augmented-2nd tension
    "phrygian_dominant": [0, 1, 4, 5, 7, 8, 10],    # exotic, ritualistic
    "pentatonic":        [0, 3, 5, 7, 10],
}

# Four-chord progressions as scale-degree roots (0 = tonic). Chosen for the
# minor-key cadences that underpin dark-fantasy scores; the engine builds
# diatonic triads (and optional 7ths) on each degree with simple voice leading.
_PROGRESSIONS = {
    "field":   [[0, 5, 3, 4],   # i - VI - iv - v  (wandering, melancholic)
                [0, 4, 5, 3],
                [0, 2, 5, 4]],
    "dungeon": [[0, 1, 0, 6],   # i - II - i - VII (oppressive, looming)
                [0, 6, 5, 0],
                [0, 4, 1, 0]],
    "town":    [[0, 3, 4, 0],   # i - iv - v - i   (settled, hopeful)
                [0, 5, 3, 4],
                [0, 4, 0, 3]],
    "boss":    [[0, 6, 5, 6],   # i - VII - VI - VII (driving, heroic-dread)
                [0, 1, 6, 0],
                [0, 5, 6, 4]],
}

# Per-theme arrangement recipes: scale pool, register, tempo, instrumentation.
# This is the dial the music engine turns to evoke a place's mood.
_THEMES = {
    "field": {
        "scales": ["dorian", "minor"], "roots": [45, 48, 50],
        "bar_dur": (1.6, 1.8), "bars": 4,
        "drone": 0.18, "strings": 0.5, "choir": 0.25, "bell": 0.3,
        "melody": 0.35, "drum": 0.0, "drum_div": 4,
    },
    "dungeon": {
        "scales": ["phrygian", "harmonic_minor", "minor"], "roots": [41, 43, 45],
        "bar_dur": (2.0, 2.4), "bars": 4,
        "drone": 0.32, "strings": 0.42, "choir": 0.4, "bell": 0.18,
        "melody": 0.16, "drum": 0.12, "drum_div": 2,
    },
    "town": {
        "scales": ["dorian", "major"], "roots": [48, 50, 52],
        "bar_dur": (1.4, 1.6), "bars": 4,
        "drone": 0.12, "strings": 0.45, "choir": 0.2, "bell": 0.45,
        "melody": 0.4, "drum": 0.0, "drum_div": 4,
    },
    "boss": {
        "scales": ["harmonic_minor", "phrygian_dominant", "phrygian"],
        "roots": [40, 43, 45],
        "bar_dur": (1.1, 1.3), "bars": 4,
        "drone": 0.28, "strings": 0.5, "choir": 0.35, "bell": 0.12,
        "melody": 0.3, "drum": 0.5, "drum_div": 8,
    },
}


def _midi_to_freq(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def _make_bar(scale, root, degree, dur, n, rng):
    """Render one self-enveloped musical bar: a chord pad, a bass note, and a
    short melodic arpeggio. Each bar fades in/out, so concatenating bars (and
    looping the whole track) is click-free."""
    t = np.linspace(0, dur, n, endpoint=False)
    env = _envelope(n, attack=0.06, release=0.30)
    sig = np.zeros(n)

    def note(deg, octave=0):
        idx = deg % len(scale)
        octs = deg // len(scale) + octave
        return _midi_to_freq(root + scale[idx] + 12 * octs)

    # Chord pad: triad (root, third, fifth of the scale degree).
    for cd in (degree, degree + 2, degree + 4):
        sig += 0.5 * np.sin(2 * np.pi * note(cd) * t)
    # Bass: scale degree an octave down.
    sig += 0.6 * np.sin(2 * np.pi * note(degree, octave=-1) * t)
    sig *= env

    # Melody arpeggio: a handful of short, enveloped notes across the bar.
    steps = rng.choice([4, 6, 8])
    seg = max(1, n // steps)
    melody = np.zeros(n)
    for s in range(steps):
        deg = degree + rng.choice([0, 1, 2, 4, 6, -1])
        st = s * seg
        en = min(n, st + seg)
        if en <= st:
            continue
        m = en - st
        tt = np.linspace(0, m / _SAMPLE_RATE, m, endpoint=False)
        ne = _envelope(m, attack=0.01, release=0.06)
        melody[st:en] += 0.35 * np.sin(2 * np.pi * note(deg, octave=1) * tt) * ne
    return sig + melody


def _scale_note(scale, root, degree, octave=0):
    """MIDI->Hz for a scale degree (degrees wrap across octaves)."""
    idx = degree % len(scale)
    octs = degree // len(scale) + octave
    return _midi_to_freq(root + scale[idx] + 12 * octs)


def _compose_bar(theme, scale, root, chord_root, dur, rng, prev_top):
    """Render one richly orchestrated bar for a theme.

    Builds a diatonic triad on ``chord_root`` (voiced as a string/choir pad),
    lays a sub-drone and bass under it, optionally sprinkles a bell/melody line,
    and -- for driving themes -- a war-drum pulse. ``prev_top`` carries the
    previous bar's melody-top degree so the line moves by small steps (basic
    voice leading) instead of leaping randomly.
    """
    n = int(_SAMPLE_RATE * dur)
    layers = []

    # Chord pad: triad (1-3-5) plus an occasional 7th for tension, rendered as a
    # blend of bowed strings and choir so the harmony has body and air.
    chord_degrees = [chord_root, chord_root + 2, chord_root + 4]
    if rng.random() < 0.4:
        chord_degrees.append(chord_root + 6)
    for cd in chord_degrees:
        f = _scale_note(scale, root, cd, octave=0)
        if theme["strings"]:
            layers.append(_bowed_string(f, dur) * (theme["strings"] / len(chord_degrees)))
        if theme["choir"]:
            layers.append(_voice_pad(f, dur) * (theme["choir"] / len(chord_degrees)))

    # Sub-drone on the tonic: the ever-present dread bed.
    if theme["drone"]:
        layers.append(_sub_drone(_scale_note(scale, root, 0, octave=-2), dur)
                      * theme["drone"])
    # Bass: chord root one octave down, plucked-ish sine.
    bass_f = _scale_note(scale, root, chord_root, octave=-1)
    bt = np.linspace(0, dur, n, endpoint=False)
    layers.append(0.5 * np.sin(2 * np.pi * bass_f * bt)
                  * _adsr(n, 0.01, dur * 0.3, 0.5, dur * 0.3))

    # Melody / bell arpeggio: stepwise motion from the previous bar's top note.
    top = prev_top
    if theme["melody"] or theme["bell"]:
        steps = rng.choice([3, 4, 6])
        seg = max(1, n // steps)
        melody = np.zeros(n)
        for s in range(steps):
            top += rng.choice([-2, -1, -1, 1, 1, 2])      # mostly steps
            top = max(chord_root, min(chord_root + 7, top))
            st, en = s * seg, min(n, (s + 1) * seg)
            if en <= st:
                continue
            f = _scale_note(scale, root, top, octave=1)
            if theme["bell"] and rng.random() < 0.5:
                voice = _fm_bell(f, (en - st) / _SAMPLE_RATE) * theme["bell"]
            else:
                m = en - st
                tt = np.linspace(0, m / _SAMPLE_RATE, m, endpoint=False)
                voice = (np.sin(2 * np.pi * f * tt)
                         * _adsr(m, 0.01, 0.05, 0.6, 0.08) * theme["melody"])
            melody[st:st + len(voice)] += voice[:n - st]
        layers.append(melody)

    # War-drum pulse for driving themes (boss/rift).
    if theme["drum"]:
        div = theme["drum_div"]
        hit = max(1, n // div)
        drum = np.zeros(n)
        for d in range(div):
            st = d * hit
            accent = 1.0 if d % 2 == 0 else 0.6
            tk = _taiko(min(0.5, hit / _SAMPLE_RATE)) * theme["drum"] * accent
            drum[st:st + len(tk)] += tk[:n - st]
        layers.append(drum)

    bar = _layer(*layers)
    env = _envelope(len(bar), attack=0.04, release=0.12)   # click-free seams
    return bar[:n] * env[:n] if len(bar) >= n else np.pad(bar, (0, n - len(bar))) * env, top


def compose_theme(theme_name="field", rng=None):
    """Compose a fresh, randomly-generated, themed music loop.

    ``theme_name`` selects an arrangement preset (field/dungeon/town/boss) that
    fixes the mode pool, register, tempo and instrumentation; within that the
    scale, root, chord progression and melody are randomized so two loops of the
    same theme never sound identical while sharing a consistent mood.
    """
    rng = rng or _random.Random()
    theme = _THEMES.get(theme_name, _THEMES["field"])
    scale = _SCALES[rng.choice(theme["scales"])]
    root = rng.choice(theme["roots"])
    progression = rng.choice(_PROGRESSIONS.get(theme_name, _PROGRESSIONS["field"]))
    bar_dur = rng.uniform(*theme["bar_dur"])

    bars, top = [], 0
    for chord_root in progression[:theme["bars"]]:
        bar, top = _compose_bar(theme, scale, root, chord_root, bar_dur, rng, top)
        bars.append(bar)
    track = np.concatenate(bars)
    peak = np.max(np.abs(track)) or 1.0
    return track / peak * 0.6


def generate_music_loop(rng=None, theme="field"):
    """Compose a themed loop (kept for backward compatibility).

    Delegates to :func:`compose_theme`; the legacy single-argument call still
    works and now produces the richer, orchestrated arrangement.
    """
    return compose_theme(theme, rng)


# --- retro (NES / Atari 2600) enemy death cues ------------------------------
def _death_blip(rng):
    """A descending square-wave arpeggio -- classic 8-bit 'defeat' chirp."""
    notes = rng.choice([3, 4])
    start = rng.choice([720, 820, 960])
    seg = 0.06
    parts = [_tone(start * (0.72 ** i), seg, "square") for i in range(notes)]
    return _mix(np.concatenate(parts))


def _death_explosion(rng):
    """A noisy downward burst -- Atari-style blast."""
    return _mix(_tone(220, 0.28, "noise", sweep=-0.7),
                _tone(130, 0.28, "square", sweep=-0.6) * 0.5)


def _death_zap(rng):
    """A short pitch-dropping square zap."""
    return _mix(_tone(rng.choice([520, 600, 680]), 0.16, "square", sweep=-0.85))


def _boss_death(rng):
    """A bigger, longer multi-stage explosion for rift bosses."""
    return _mix(_tone(180, 0.6, "noise", sweep=-0.6),
                _tone(90, 0.6, "square", sweep=-0.5) * 0.6,
                _tone(300, 0.6, "square", sweep=-0.8) * 0.3)


_DEATH_RECIPES = (_death_blip, _death_explosion, _death_zap)


# --- eerie, "alive" monster voices ------------------------------------------
# A single parametric creature synth voiced from per-monster profiles, so the
# palette scales to new monsters by adding one profile row. Each voice blends a
# pitched source, formant resonances (vowel-like body), a guttural amplitude
# "growl", and breath noise -- the organic, unsettling layering used for ARPG
# demons, undead and beasts. ``kind`` shapes the same throat into an idle
# rumble, an aggressive attack, or a pained hurt cry.
def _creature_voice(base, dur, rng, *, timbre="saw", rough=26.0, noise=0.25,
                    formants=((1.0, 1.0), (2.6, 0.45)), sweep=-0.08,
                    vibrato=5.0, attack=0.04, release=0.3):
    n = int(_SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    # Wobble + drift make it feel breathing/alive rather than a static tone.
    wob = 1.0 + 0.03 * np.sin(2 * np.pi * vibrato * t + rng.random() * 6.28)
    f = base * (1.0 + sweep * (t / dur)) * wob
    phase = 2 * np.pi * np.cumsum(f) / _SAMPLE_RATE
    if timbre == "square":
        src = np.sign(np.sin(phase))
    elif timbre == "sine":
        src = np.sin(phase)
    else:  # saw -- buzzy, brassy, good for roars/snarls
        ph = phase / (2 * np.pi)
        src = 2.0 * (ph - np.floor(0.5 + ph))
    voice = np.zeros(n)
    for mult, amp in formants:
        voice += amp * np.sin(phase * mult)
    body = 0.55 * src + 0.6 * voice
    growl = 1.0 + 0.6 * np.sin(2 * np.pi * rough * t)          # guttural AM
    breath = np.random.uniform(-1, 1, n) * noise * _envelope(n, 0.02, release)
    env = _adsr(n, attack, dur * 0.2, 0.75, release)
    return _mix((body * growl + breath) * env)


def _bone_rattle(dur, rng, density=22):
    """Dry skeletal clatter: a burst of short noise transients -- the rattling
    bones of risen undead."""
    n = int(_SAMPLE_RATE * dur)
    out = np.zeros(n)
    for _ in range(density):
        st = rng.randrange(0, n)
        ln = int(_SAMPLE_RATE * rng.uniform(0.004, 0.02))
        seg = np.random.uniform(-1, 1, ln) * np.linspace(1, 0, ln)
        out[st:st + len(seg)] += seg[:n - st]
    return _mix(out * _envelope(n, 0.01, dur * 0.4))


# Per-monster timbral profiles keyed by the enemy data key (enemy.py).
_MONSTER_PROFILES = {
    "goblin":      dict(base=300, timbre="square", rough=34, noise=0.3,
                        formants=((1.0, 1.0), (3.2, 0.5)), vibrato=8.0),
    "orc":         dict(base=150, timbre="saw", rough=22, noise=0.35,
                        formants=((1.0, 1.0), (2.2, 0.5))),
    "skeleton":    dict(base=180, timbre="square", rough=40, noise=0.5,
                        formants=((1.0, 0.7), (4.0, 0.4))),   # + rattle overlay
    "necromancer": dict(base=120, timbre="sine", rough=14, noise=0.4,
                        formants=((1.0, 0.8), (2.5, 0.6), (5.0, 0.3)),
                        vibrato=3.0),
    "demon":       dict(base=80, timbre="saw", rough=18, noise=0.4,
                        formants=((1.0, 1.0), (1.5, 0.5), (2.7, 0.3))),
    "dragon":      dict(base=70, timbre="saw", rough=12, noise=0.55,
                        formants=((1.0, 1.0), (2.0, 0.4)), vibrato=2.0),
    "vampire":     dict(base=260, timbre="saw", rough=30, noise=0.45,
                        formants=((1.0, 0.8), (3.5, 0.5)), vibrato=7.0),
    "lich":        dict(base=110, timbre="sine", rough=10, noise=0.35,
                        formants=((1.0, 0.7), (2.49, 0.6), (3.97, 0.4)),
                        vibrato=2.5),
}

# How each vocalization kind reshapes a profile's base throat.
_MONSTER_KINDS = {
    "idle":   dict(dur=0.7, sweep=-0.12, attack=0.08, release=0.4, pitch=1.0),
    "attack": dict(dur=0.45, sweep=0.25, attack=0.01, release=0.2, pitch=1.15),
    "hurt":   dict(dur=0.3, sweep=-0.5, attack=0.005, release=0.18, pitch=1.25),
}


def make_monster_sound(key, kind, rng):
    """Synthesize one eerie creature vocalization for a monster type + kind."""
    profile = dict(_MONSTER_PROFILES.get(key, _MONSTER_PROFILES["orc"]))
    km = _MONSTER_KINDS.get(kind, _MONSTER_KINDS["idle"])
    base = profile.pop("base") * km["pitch"]
    voice = _creature_voice(base, km["dur"], rng, sweep=km["sweep"],
                            attack=km["attack"], release=km["release"],
                            **profile)
    if key == "skeleton":     # overlay bone clatter for the undead
        voice = _mix(voice + _bone_rattle(km["dur"], rng) * 0.6)
    return voice


# --- player minion voices ---------------------------------------------------
# Minions (raised skeletons / conjured allies) get their own lighter, friendlier
# cues so the player can tell their summons apart from enemies.
def _minion_summon(rng):
    """A rising, airy conjuration shimmer -- something arrives to serve you."""
    return _mix(_voice_pad(220, 0.5, vibrato=6.0) * 0.7,
                _fm_bell(660, 0.5, ratio=1.5, index=3.0) * 0.5,
                _tone(330, 0.5, "sine", sweep=0.6) * 0.3)


def _minion_attack(rng):
    """A small, dry bone-strike + hiss -- the minion lashing out."""
    return _mix(_bone_rattle(0.18, rng, density=8) * 0.8,
                _tone(rng.choice([180, 220, 260]), 0.14, "square", sweep=-0.4) * 0.5)


def _minion_expire(rng):
    """A soft descending sigh as a summon crumbles back to dust."""
    return _mix(_voice_pad(180, 0.4, vibrato=4.0) * 0.6,
                _tone(160, 0.4, "sine", sweep=-0.5) * 0.4)


_MINION_RECIPES = {
    "summon": _minion_summon,
    "attack": _minion_attack,
    "expire": _minion_expire,
}


# --- treasure chest cue -----------------------------------------------------
def _chest_open(rng):
    """A bright unlatch-and-reward flourish: a creak, then an ascending bell
    arpeggio -- the satisfying 'you found loot' sting."""
    creak = _tone(140, 0.18, "saw", sweep=0.5) * 0.4
    arp = np.concatenate([_fm_bell(f, 0.16, ratio=2.0, index=3.0)
                          for f in (523, 659, 784, 1047)])   # C-E-G-C major
    return _mix(np.concatenate([creak, arp * 0.7]))


class SoundManager:
    """Owns synthesized SFX + music and exposes live SFX/Music volume control."""

    def __init__(self):
        self.enabled = False
        self.sfx_volume = 0.6
        self.music_volume = 0.4
        self._sounds = {}
        self._death_sounds = []     # retro enemy-death cues (random per kill)
        self._boss_death = None
        self._monster_sounds = {}   # (key, kind) -> Sound  (eerie creature cues)
        self._minion_sounds = {}    # kind -> Sound          (player summons)
        self._chest_sound = None    # treasure-chest open flourish
        self._music = None
        self._music_channel = None
        self._theme = "field"       # active music theme (field/dungeon/town/boss)
        self._rng = _random.Random()
        self._load_settings()
        self._init_mixer()
        if self.enabled:
            self._build_sounds()
            self._build_music()

    # --- setup ------------------------------------------------------------
    def _init_mixer(self):
        if pygame is None:
            return
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=_SAMPLE_RATE, size=-16, channels=2)
            pygame.mixer.set_num_channels(16)   # plenty of overlap for rapid casts
            pygame.mixer.set_reserved(1)        # keep channel 0 for music only
            self.enabled = True
        except Exception:
            self.enabled = False

    def _to_sound(self, mono):
        """Convert a float mono waveform into a stereo pygame Sound (full scale)."""
        audio = np.int16(np.clip(mono, -1, 1) * 32767)
        stereo = np.column_stack((audio, audio))
        return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))

    def _build_sounds(self):
        try:
            for element, recipe in _RECIPES.items():
                snd = self._to_sound(recipe())
                snd.set_volume(self.sfx_volume)
                self._sounds[element] = snd
            # Retro enemy-death cues (a few variants) + a beefier boss cue.
            self._death_sounds = [self._to_sound(r(self._rng)) for r in _DEATH_RECIPES]
            self._boss_death = self._to_sound(_boss_death(self._rng))
            # Eerie per-monster creature voices (idle/attack/hurt per type).
            for key in _MONSTER_PROFILES:
                for kind in _MONSTER_KINDS:
                    self._monster_sounds[(key, kind)] = self._to_sound(
                        make_monster_sound(key, kind, self._rng))
            # Player minion cues + treasure-chest flourish.
            for kind, recipe in _MINION_RECIPES.items():
                self._minion_sounds[kind] = self._to_sound(recipe(self._rng))
            self._chest_sound = self._to_sound(_chest_open(self._rng))
            for snd in self._all_sfx():
                snd.set_volume(self.sfx_volume)
        except Exception:
            self.enabled = False

    def _all_sfx(self):
        """Every non-music Sound, for blanket volume changes."""
        yield from self._sounds.values()
        yield from self._death_sounds
        if self._boss_death is not None:
            yield self._boss_death
        yield from self._monster_sounds.values()
        yield from self._minion_sounds.values()
        if self._chest_sound is not None:
            yield self._chest_sound

    def _build_music(self):
        try:
            self._music = self._to_sound(generate_music_loop(self._rng, self._theme))
        except Exception:
            self._music = None

    # --- playback ---------------------------------------------------------
    def play_element(self, element):
        """Play the attack cue for an elemental type (no-op if unavailable)."""
        if not self.enabled:
            return
        snd = self._sounds.get(element) or self._sounds.get("physical")
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def play_skill(self, skill):
        """Play the cue for a Skill based on its element."""
        self.play_element(getattr(skill, "element", "physical"))

    def play_enemy_death(self, boss=False):
        """Play a retro death cue: a random 8-bit blip for trash, a bigger
        explosion for bosses (no-op if audio is unavailable)."""
        if not self.enabled:
            return
        snd = self._boss_death if boss else (
            self._rng.choice(self._death_sounds) if self._death_sounds else None)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def play_monster(self, key, kind="idle"):
        """Play an eerie creature cue for a monster type.

        ``key`` is the enemy data key (e.g. "demon", "lich"); ``kind`` is one of
        "idle" / "attack" / "hurt". Falls back gracefully for unknown types so
        callers (including future monster-attack code) can call it freely.
        """
        if not self.enabled:
            return
        snd = (self._monster_sounds.get((key, kind))
               or self._monster_sounds.get(("orc", kind))
               or self._monster_sounds.get((key, "idle")))
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def play_minion(self, kind="attack"):
        """Play a player-minion cue ("summon" / "attack" / "expire")."""
        if not self.enabled:
            return
        snd = self._minion_sounds.get(kind)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def play_chest_open(self):
        """Play the treasure-chest reward flourish."""
        if not self.enabled or self._chest_sound is None:
            return
        try:
            self._chest_sound.play()
        except Exception:
            pass

    def set_theme(self, theme):
        """Switch the music theme (field/dungeon/town/boss) and recompose.

        No-op if the theme is already active, so callers can call it freely on
        every state change (entering town, starting a rift, spawning a boss).
        """
        if theme == self._theme:
            return
        self._theme = theme if theme in _THEMES else "field"
        self.regenerate_music()

    def regenerate_music(self, theme=None):
        """Compose and switch to a freshly randomized loop in the active theme."""
        if not self.enabled:
            return
        if theme is not None and theme in _THEMES:
            self._theme = theme
        try:
            self._music = self._to_sound(generate_music_loop(self._rng, self._theme))
            self.start_music()
        except Exception:
            pass

    def start_music(self):
        """Begin (or restart) the looping ambient bed on its reserved channel."""
        if not self.enabled or self._music is None:
            return
        try:
            self._music_channel = pygame.mixer.Channel(_MUSIC_CHANNEL)
            self._music_channel.play(self._music, loops=-1)
            self._music_channel.set_volume(self.music_volume)
        except Exception:
            self._music_channel = None

    def stop_music(self):
        if self._music_channel is not None:
            try:
                self._music_channel.stop()
            except Exception:
                pass

    # --- live volume control ---------------------------------------------
    def set_sfx_volume(self, value):
        """Apply the SFX volume live. Call ``save_settings`` to persist it."""
        self.sfx_volume = max(0.0, min(1.0, float(value)))
        for snd in self._all_sfx():
            try:
                snd.set_volume(self.sfx_volume)
            except Exception:
                pass

    def set_music_volume(self, value):
        """Apply the music volume live. Call ``save_settings`` to persist it."""
        self.music_volume = max(0.0, min(1.0, float(value)))
        if self._music_channel is not None:
            try:
                self._music_channel.set_volume(self.music_volume)
            except Exception:
                pass

    def save_settings(self):
        """Persist the current volumes (call once when a drag/adjust finishes)."""
        self._save_settings()

    # --- persistence ------------------------------------------------------
    def _load_settings(self):
        try:
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.sfx_volume = max(0.0, min(1.0, float(d.get("sfx_volume", self.sfx_volume))))
            self.music_volume = max(0.0, min(1.0, float(d.get("music_volume", self.music_volume))))
        except Exception:
            pass  # first run / unreadable -> keep defaults

    def _save_settings(self):
        try:
            os.makedirs(os.path.dirname(_SETTINGS_PATH), exist_ok=True)
            with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump({"sfx_volume": self.sfx_volume,
                           "music_volume": self.music_volume}, f, indent=2)
        except Exception:
            pass


_INSTANCE = None


def get_sound_manager():
    """Lazily build a single shared SoundManager."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = SoundManager()
    return _INSTANCE
