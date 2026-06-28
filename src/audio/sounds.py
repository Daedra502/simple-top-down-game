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

# Diatonic scales (semitone offsets from the root) the generator can pick from.
_SCALES = {
    "minor":      [0, 2, 3, 5, 7, 8, 10],
    "major":      [0, 2, 4, 5, 7, 9, 11],
    "dorian":     [0, 2, 3, 5, 7, 9, 10],
    "pentatonic": [0, 3, 5, 7, 10],
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


def generate_music_loop(rng=None):
    """Compose a fresh, randomly generated loop from modular bars.

    Picks a random scale, root and 4-bar chord progression, then renders each
    bar and concatenates them. Two calls give two different tracks.
    """
    rng = rng or _random.Random()
    scale = _SCALES[rng.choice(list(_SCALES.keys()))]
    root = rng.choice([45, 48, 50, 52, 41])     # low register roots
    bars = 4
    bar_dur = rng.choice([1.4, 1.6, 1.8])
    n_bar = int(_SAMPLE_RATE * bar_dur)
    degrees = [rng.randrange(len(scale)) for _ in range(bars)]
    track = np.concatenate([_make_bar(scale, root, d, bar_dur, n_bar, rng)
                            for d in degrees])
    peak = np.max(np.abs(track)) or 1.0
    return track / peak * 0.55


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


class SoundManager:
    """Owns synthesized SFX + music and exposes live SFX/Music volume control."""

    def __init__(self):
        self.enabled = False
        self.sfx_volume = 0.6
        self.music_volume = 0.4
        self._sounds = {}
        self._death_sounds = []     # retro enemy-death cues (random per kill)
        self._boss_death = None
        self._music = None
        self._music_channel = None
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

    def _build_music(self):
        try:
            self._music = self._to_sound(generate_music_loop(self._rng))
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

    def regenerate_music(self):
        """Compose and switch to a freshly randomized music loop."""
        if not self.enabled:
            return
        try:
            self._music = self._to_sound(generate_music_loop(self._rng))
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
