from __future__ import annotations
import random
import numpy as np
import pygame
from core.event_bus import (
    bus,
    EVT_HULL_DAMAGE, EVT_TETHER_HIT, EVT_TETHER_SNAP,
    EVT_GUN_FIRE, EVT_TERMINAL_OPEN, EVT_TERMINAL_CLOSE,
    EVT_SPORE_INVERTED, EVT_SHIP_DESTROYED, EVT_SLINGSHOT,
    EVT_CANISTER_GRAB, EVT_BARGE_NEARBY, EVT_BAX_SPEAK, EVT_COMMS_SPEAK,
    EVT_VOICE_CHAR, EVT_JUMP_READY, EVT_DEBT_DING,
    EVT_DELIVERY_STEP, EVT_DELIVERY_HIT, EVT_DELIVERY_DONE,
    EVT_SECTOR_CLEAR, EVT_RUN_START,
)
from audio.synth import (
    SAMPLE_RATE,
    engine_drone, ambient_static, gun_shot, hull_impact,
    tether_clang, tether_snap, terminal_beep, spore_sting,
    death_sting, slingshot_whoosh, canister_chime,
    barge_alert, terminal_drone, jump_ready_charge, debt_ding,
    delivery_footstep, delivery_hit_sting, delivery_door_chime,
    sector_pad, slide_blues_note,
    tape_hum_bed, slingshot_stinger, barge_motif, decanting_printer,
    npc_sig_dispatcher, npc_sig_adjuster, torch_slow_clap,
    _to_sound, _2PI,
    drum_kick, drum_snare_gated, drum_hihat, drum_clap,
    synth_bass_note,
)
from audio.blues_licks import prebuild_all, generate_lick
from audio.voices import prebuild_voices, resolve_voice_key
from audio.new_wave_pad import build_new_wave_pad, build_long_form_menu_pad
from audio.guitar_phrases import prebuild_phrases

# ---------------------------------------------------------------------------
# Channel layout
_N_TIERS  = 5
_SPEED_BP = [0.0, 120.0, 240.0, 380.0, 520.0]

_ENG_CH     = 0    # channels 0-4: engine tiers (5)
_AMB_CH     = 5    # deep-space ambient static
_LICK_CH    = 6    # blues harmonica licks
_BAX_V_CH   = 7    # Bax voice blips
_NPC_V_CH   = 8    # NPC terminal voice blips
_DRONE_CH   = 9    # terminal drone pad
_MUSIC_CH_A = 20   # sector music pad — channel A (active)
_MUSIC_CH_B = 21   # sector music pad — channel B (crossfade target)
_DRUM_CH    = 22   # 80s drum-machine loop
_BASS_CH    = 23   # walking sub-bass loop
_GTR_CH     = 24   # acoustic guitar phrases (one-shot)
_ARP_CH     = 25   # new-wave arpeggio pad
_SLIDE_CH   = 26   # mournful slide-blues notes
_HUM_CH       = 27   # tape hum bed (subliminal glue layer)
_BARGE_CH     = 28   # barge motif drone
_HUM_VOICE_CH = 29   # Bax hums (§7.4) — own channel so voice-duck doesn't grab it
_SFX_POOL     = 10   # channels 10-19: one-shot SFX pool

_BAX_CHARS_PER_SEC = 32.0

# Scene names
SCENE_MENU         = "menu"
SCENE_FLIGHT       = "flight"
SCENE_TERMINAL     = "terminal"
SCENE_DELIVERY     = "delivery"
SCENE_SHOP         = "shop"
SCENE_INTERSTITIAL = "interstitial"
SCENE_DECANTING    = "decanting"
SCENE_LOADOUT      = "loadout"
SCENE_RADIO        = "radio"

# Bluesy minor chord progression — Am, F, G, Em (Hz)
_PROGRESSION = [220.0, 174.61, 196.0, 164.81]
_DEFAULT_BPM = 96.0

# Per-chapter home keys (root frequencies in Hz).
# Am=220, Cm=261.6, F#m=185, Em=164.8 (Locrian)
_CHAPTER_ROOTS = {1: 220.0, 2: 261.6, 3: 185.0, 4: 164.81}
_CHAPTER_MODES = {1: "minor", 2: "dorian", 3: "sus2", 4: "locrian"}

# 5 BPM tiers driven by flight_pressure
_DRUM_BPMS = [84.0, 96.0, 108.0, 120.0, 128.0]

# Slingshot pad transpositions: root, +2 semitones, +5 (P5), +7 (P5+), +12 (octave)
_SLING_SEMITONES = [0, 2, 5, 7, 12]


def _sound_to_np(snd: pygame.mixer.Sound) -> np.ndarray:
    arr = pygame.sndarray.array(snd)
    if arr.ndim == 2:
        arr = arr[:, 0]
    return arr.astype(np.float32) / 32767.0


def _mix_at(buf: np.ndarray, hit: np.ndarray, pos: int, gain: float = 1.0):
    end = pos + len(hit)
    if pos >= len(buf):
        return
    if end > len(buf):
        hit = hit[: len(buf) - pos]
        end = len(buf)
    buf[pos:end] += hit * gain


def _build_drum_loop(bpm: float = 96.0, length_bars: int = 2,
                     intensity: float = 1.0) -> pygame.mixer.Sound:
    intensity = max(0.0, min(1.5, intensity))
    spb   = 60.0 / bpm
    beats = 4 * length_bars
    n     = int(SAMPLE_RATE * spb * beats)
    buf   = np.zeros(n, dtype=np.float32)

    kick_np  = _sound_to_np(drum_kick())
    snare_np = _sound_to_np(drum_snare_gated())
    hat_np   = _sound_to_np(drum_hihat())
    clap_np  = _sound_to_np(drum_clap())

    eighth = spb / 2.0
    for i in range(beats * 2):
        pos  = int(SAMPLE_RATE * i * eighth)
        gain = (0.45 if i % 2 == 0 else 0.32) * (0.7 + 0.3 * intensity)
        _mix_at(buf, hat_np, pos, gain=gain)

    for bar in range(length_bars):
        for b in (0, 2):
            _mix_at(buf, kick_np, int(SAMPLE_RATE * (bar * 4 + b) * spb), gain=0.95)
        for b in (1, 3):
            pos = int(SAMPLE_RATE * (bar * 4 + b) * spb)
            _mix_at(buf, snare_np, pos, gain=0.78)
            if intensity > 0.65:
                _mix_at(buf, clap_np, pos, gain=0.45 * min(1.0, (intensity - 0.65) / 0.5))

    if intensity > 0.85 and length_bars >= 2:
        ghost = (length_bars - 1) * 4 + 3.5
        _mix_at(buf, snare_np, int(SAMPLE_RATE * ghost * spb), gain=0.22)

    peak = float(np.max(np.abs(buf))) if len(buf) else 0.0
    if peak > 0.95:
        buf = buf / peak * 0.92
    xf = min(int(SAMPLE_RATE * 0.005), n // 32)
    if xf > 4:
        buf[:xf] *= np.linspace(0.0, 1.0, xf)
    return _to_sound(buf.clip(-1.0, 1.0))


def _build_bass_loop(progression: list[float], bpm: float = 96.0,
                     notes_per_chord: int = 4) -> pygame.mixer.Sound:
    spb      = 60.0 / bpm
    note_dur = spb
    n        = int(SAMPLE_RATE * len(progression) * notes_per_chord * note_dur)
    buf      = np.zeros(n, dtype=np.float32)
    for ci, root in enumerate(progression):
        fifth   = root * 1.4983
        pattern = [root, root, fifth, root]
        if root >= 110.0:
            pattern = [f * 0.5 for f in pattern]
        for ni, freq in enumerate(pattern[:notes_per_chord]):
            idx = ci * notes_per_chord + ni
            pos = int(SAMPLE_RATE * idx * note_dur)
            np_ = _sound_to_np(synth_bass_note(freq, duration=note_dur * 0.95))
            _mix_at(buf, np_, pos, gain=0.85)
    peak = float(np.max(np.abs(buf))) if len(buf) else 0.0
    if peak > 0.95:
        buf = buf / peak * 0.90
    return _to_sound(buf.clip(-1.0, 1.0))


def _select_drum_tier(pressure: float) -> int:
    """Map 0..1 flight_pressure to one of 5 BPM tier indices."""
    if pressure < 0.2:  return 0
    if pressure < 0.4:  return 1
    if pressure < 0.6:  return 2
    if pressure < 0.8:  return 3
    return 4


def _transpose_pad(progression: list[float], semitones: int,
                   mode: str = "minor") -> pygame.mixer.Sound:
    mul = 2.0 ** (semitones / 12.0)
    new_prog = [f * mul for f in progression]
    return build_new_wave_pad(new_prog, duration_per_chord=2.5, mode=mode,
                              with_arpeggio=True)


class AudioManager:
    """
    DEAD DRIFT soundtrack — procedural, 100% numpy/pygame. No asset files.

    Architecture (per SOUNDTRACK_PLAN.md):
    - flight_pressure (0..1) drives tempo, kit intensity, bass density, pad voicing.
    - 5 pre-built drum/bass tiers at 84/96/108/120/128 BPM; swap at bar boundaries.
    - Tape hum bed on ch.27 — subliminal glue layer, always on.
    - Barge motif drone on ch.28 — minor 2nd on harp, fades in at proximity.
    - 5-stem budget enforcer ducks lowest-priority stem when 6th wants in.
    - Master FX (hull degradation) via audio/master_fx.py.
    - Slingshot musical stinger + 5 pre-baked pad transpositions.
    - Tether snap musical resolution (snare flam + bass walk + pad open).
    """

    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(32)

        self._eng_ch:   list[pygame.mixer.Channel] = []
        self._eng_snd:  list[pygame.mixer.Sound]   = []
        self._amb_ch:   pygame.mixer.Channel | None = None
        self._lick_ch:  pygame.mixer.Channel | None = None
        self._bax_v_ch: pygame.mixer.Channel | None = None
        self._npc_v_ch: pygame.mixer.Channel | None = None
        self._drone_ch: pygame.mixer.Channel | None = None
        self._hum_ch:   pygame.mixer.Channel | None = None
        self._barge_ch: pygame.mixer.Channel | None = None
        self._hum_voice_ch: pygame.mixer.Channel | None = None
        self._bax_hums: list[pygame.mixer.Sound] = []
        self._licks:    list[pygame.mixer.Sound] = []
        self._sfx:      dict[str, pygame.mixer.Sound] = {}
        self._voices:   dict[str, list[pygame.mixer.Sound]] = {}

        self._master      = 0.70
        self._in_terminal = False
        self._lick_cd     = random.uniform(3.0, 7.0)

        # Sector music crossfade channels
        self._music_a:   pygame.mixer.Channel | None = None
        self._music_b:   pygame.mixer.Channel | None = None
        self._music_pads: list[pygame.mixer.Sound] = []
        self._music_active = 0
        self._music_xfade  = 0.0
        self._music_xfade_dur = 2.5
        self._music_target_vol = 0.34

        # Bax voice timer
        self._bax_speaking   = False
        self._bax_speak_t    = 0.0
        self._bax_speak_dur  = 0.0
        self._bax_blip_cd    = 0.0
        # Duck music/stems while Bax or NPC speech is active
        self._voice_duck         = 1.0
        self._voice_duck_target  = 1.0
        self._npc_speak_t        = 0.0
        self._VOICE_DUCK_FLOOR   = 0.52   # gentle duck — keep music audible
        self._VOICE_BLIP_VOL     = 0.52   # blips present but not overpowering

        # Bandstand channels
        self._scene: str = SCENE_MENU
        self._drum_ch:    pygame.mixer.Channel | None = None
        self._bass_ch:    pygame.mixer.Channel | None = None
        self._gtr_ch:     pygame.mixer.Channel | None = None
        self._arp_ch:     pygame.mixer.Channel | None = None
        self._slide_ch:   pygame.mixer.Channel | None = None
        self._guitar_phrases: list[pygame.mixer.Sound] = []
        self._slide_notes:    list[pygame.mixer.Sound] = []

        # Volume crossfade targets
        self._vol_targets: dict[str, float] = {
            "drum": 0.0, "bass": 0.0, "arp": 0.0,
        }
        self._vol_current: dict[str, float] = dict(self._vol_targets)
        self._vol_fade_rate = 1.0 / 0.4

        self._gtr_cd:         float = 12.0
        self._gtr_interval:   tuple[float, float] = (0.0, 0.0)
        self._slide_cd:       float = 4.0
        self._slide_interval: tuple[float, float] = (0.0, 0.0)

        # ---- flight_pressure system ----
        self._pressure:    float = 0.0
        self._hull_pct:    float = 1.0
        self._barge_threat: float = 0.0
        self._sector_idx:  int   = 0
        self._cargo_alarm: float = 0.0

        # Drum tier management — swap only at bar boundaries
        self._drum_tiers: list[pygame.mixer.Sound] = []
        self._bass_tiers: list[pygame.mixer.Sound] = []
        self._cur_tier:   int   = 1    # index into _drum_tiers
        self._pending_tier: int | None = None
        self._bar_t:      float = 0.0  # time within current bar
        self._bar_dur:    float = 60.0 / _DEFAULT_BPM * 4  # 4 beats = 1 bar

        # Slingshot pad modulation state
        self._sling_pad_tiers: list[pygame.mixer.Sound] = []  # 5 transpositions
        self._sling_semitones: int = 0    # currently applied transposition
        self._sling_bars_left: int = 0    # bars remaining in modulation

        # Tether snap musical resolution scheduling
        self._snap_resolve_t: float = 0.0   # countdown to trigger
        self._snap_beats_left: int  = 0

        # Barge motif state
        self._barge_motif_snd: pygame.mixer.Sound | None = None
        self._barge_nearby: bool = False

        # Chapter state
        self._chapter: int = 1
        self._chapter_root: float = _CHAPTER_ROOTS[1]
        self._chapter_mode: str   = _CHAPTER_MODES[1]
        self._chapter_stem_gates: dict[str, float] = {"drum": 1.0, "bass": 1.0, "arp": 1.0}

        # Lick mood filter — set by Bax event handler
        self._next_lick_mood: str | None = None
        # Edge-trigger cooldowns so repeating events don't queue the same mood every frame
        self._barge_mood_cd:   float = 0.0
        self._hull_crit_mood_cd: float = 0.0
        # Idle harp alternates lonely / weary so two consecutive licks aren't the same mood
        self._idle_mood_toggle: int = 0

        # Master FX (hull degradation)
        self._master_fx = None
        try:
            from audio.master_fx import MasterFX
            self._master_fx = MasterFX()
            self._master_fx.install()
        except Exception:
            pass

        # --- Decanting choreography state machine ---
        # Step list: (delay_s, action_key) — action runs after delay elapses
        # actions: "slide_high", "printer", "slide_low", "hold"
        self._decant_steps: list[tuple[float, str]] = []
        self._decant_t:     float = 0.0
        self._decant_active: bool = False

        # --- Main menu long-form mode ---
        self._menu_idle_t:    float = 0.0
        self._long_form_pad:  pygame.mixer.Sound | None = None
        self._long_form_active: bool = False

        # --- Radio stations ---
        self._radio_stations: dict[str, pygame.mixer.Sound] = {}
        self._radio_current_idx: int = 0
        self._radio_ch:        pygame.mixer.Channel | None = None

        # --- Chapter inflection modules (lazy-loaded) ---
        self._chapter_modules: dict[int, object] = {}

        self._build()
        self._start_loops()
        self._wire()
        self.set_scene(SCENE_MENU)

    # ------------------------------------------------------------------
    def _build(self):
        print("[audio] generating engine tones…", flush=True)
        for tier in range(_N_TIERS):
            self._eng_snd.append(engine_drone(tier, root_freq=self._chapter_root))

        print("[audio] generating SFX…", flush=True)
        self._sfx["ambient"]   = ambient_static()
        self._sfx["gun"]       = gun_shot()
        self._sfx["hull"]      = hull_impact()
        self._sfx["clang"]     = tether_clang()
        self._sfx["snap"]      = tether_snap()
        self._sfx["beep"]      = terminal_beep()
        self._sfx["spore"]     = spore_sting()
        self._sfx["death"]     = death_sting()
        self._sfx["slingshot"] = slingshot_whoosh()
        self._sfx["canister"]  = canister_chime()
        self._sfx["barge"]     = barge_alert()
        self._sfx["drone"]     = terminal_drone()
        self._sfx["jump"]      = jump_ready_charge()
        self._sfx["debt_ding"] = debt_ding()
        self._sfx["d_step"]    = delivery_footstep()
        self._sfx["d_hit"]     = delivery_hit_sting()
        self._sfx["d_door"]    = delivery_door_chime()
        self._sfx["sling_stinger"] = slingshot_stinger()
        self._sfx["printer"]       = decanting_printer()
        self._sfx["tape_hum"]      = tape_hum_bed()
        self._sfx["npc_dispatcher"] = npc_sig_dispatcher()
        self._sfx["npc_adjuster"]   = npc_sig_adjuster()
        self._sfx["torch_clap"]     = torch_slow_clap()
        self._barge_motif_snd      = barge_motif()

        print("[audio] generating blues licks…", flush=True)
        self._licks = prebuild_all()

        print("[audio] generating character voices…", flush=True)
        self._voices = prebuild_voices()

        print("[audio] generating Bax hums…", flush=True)
        from audio.bax_hum import prebuild_all_hums
        self._bax_hums = prebuild_all_hums()

        print("[audio] generating sector pads…", flush=True)
        from config import settings as S
        self._music_pads = [sector_pad(i) for i in range(S.SECTORS_PER_RUN)]

        print("[audio] generating drum tiers (5 BPMs)…", flush=True)
        intensity_map = [0.6, 0.75, 0.85, 1.0, 1.15]
        for i, bpm in enumerate(_DRUM_BPMS):
            self._drum_tiers.append(_build_drum_loop(bpm=bpm, length_bars=2,
                                                     intensity=intensity_map[i]))
            self._bass_tiers.append(_build_bass_loop(_PROGRESSION, bpm=bpm))

        print("[audio] generating pad (chapter-keyed)…", flush=True)
        self._pad_loop = build_new_wave_pad(
            _PROGRESSION, duration_per_chord=2.5, mode=self._chapter_mode,
            with_arpeggio=True,
        )

        print("[audio] generating slingshot pad transpositions…", flush=True)
        for st in _SLING_SEMITONES:
            self._sling_pad_tiers.append(
                _transpose_pad(_PROGRESSION, st, mode=self._chapter_mode)
            )

        print("[audio] generating guitar phrases…", flush=True)
        self._guitar_phrases = prebuild_phrases()

        print("[audio] generating slide notes…", flush=True)
        self._slide_notes = [
            slide_blues_note(220.0,  174.61, duration=1.6),
            slide_blues_note(196.0,  146.83, duration=1.8),
            slide_blues_note(164.81, 130.81, duration=2.0),
            slide_blues_note(146.83, 110.0,  duration=2.2),
        ]
        # Specific notes for choreographed decanting: D3 (146.83) and C3 (130.81)
        # one whole step lower
        self._decant_slide_high = slide_blues_note(220.0,  174.61, duration=1.6)
        self._decant_slide_low  = slide_blues_note(196.0,  155.56, duration=1.8)

        print("[audio] generating long-form menu pad (90s)…", flush=True)
        try:
            self._long_form_pad = build_long_form_menu_pad()
        except Exception as e:
            print(f"[audio] long-form pad skipped: {e}")
            self._long_form_pad = None

        print("[audio] generating radio stations…", flush=True)
        try:
            from audio.radio_stations import build_all_stations, RADIO_STATIONS
            self._radio_stations = build_all_stations()
            self._radio_station_order = list(RADIO_STATIONS)
        except Exception as e:
            print(f"[audio] radio stations skipped: {e}")
            self._radio_station_order = []

        print("[audio] loading chapter inflection modules…", flush=True)
        for ch_num in (1, 2, 3, 4):
            try:
                mod = __import__(f"audio.chapter_{ch_num}", fromlist=["*"])
                self._chapter_modules[ch_num] = mod
            except Exception as e:
                print(f"[audio] chapter {ch_num} module skipped: {e}")

        print("[audio] ready.", flush=True)

    def _start_loops(self):
        for i in range(_N_TIERS):
            ch = pygame.mixer.Channel(_ENG_CH + i)
            ch.set_volume(0.0)
            ch.play(self._eng_snd[i], loops=-1)
            self._eng_ch.append(ch)

        self._amb_ch = pygame.mixer.Channel(_AMB_CH)
        self._amb_ch.set_volume(self._master * 0.20)
        self._amb_ch.play(self._sfx["ambient"], loops=-1)

        self._lick_ch  = pygame.mixer.Channel(_LICK_CH)
        self._bax_v_ch = pygame.mixer.Channel(_BAX_V_CH)
        self._npc_v_ch = pygame.mixer.Channel(_NPC_V_CH)
        self._drone_ch = pygame.mixer.Channel(_DRONE_CH)
        self._music_a  = pygame.mixer.Channel(_MUSIC_CH_A)
        self._music_b  = pygame.mixer.Channel(_MUSIC_CH_B)
        if self._music_pads:
            self._music_a.set_volume(self._master * self._music_target_vol)
            self._music_a.play(self._music_pads[0], loops=-1)
            self._music_b.set_volume(0.0)

        self._drum_ch  = pygame.mixer.Channel(_DRUM_CH)
        self._bass_ch  = pygame.mixer.Channel(_BASS_CH)
        self._gtr_ch   = pygame.mixer.Channel(_GTR_CH)
        self._arp_ch   = pygame.mixer.Channel(_ARP_CH)
        self._slide_ch = pygame.mixer.Channel(_SLIDE_CH)

        if self._drum_tiers:
            self._drum_ch.set_volume(0.0)
            self._drum_ch.play(self._drum_tiers[self._cur_tier], loops=-1)
        if self._bass_tiers:
            self._bass_ch.set_volume(0.0)
            self._bass_ch.play(self._bass_tiers[self._cur_tier], loops=-1)
        if self._pad_loop:
            self._arp_ch.set_volume(0.0)
            self._arp_ch.play(self._pad_loop, loops=-1)

        # Tape hum bed — always on at subliminal level
        self._hum_ch = pygame.mixer.Channel(_HUM_CH)
        if self._sfx.get("tape_hum"):
            self._hum_ch.set_volume(self._master * 0.038)  # -32 dBFS relative
            self._hum_ch.play(self._sfx["tape_hum"], loops=-1)

        # Barge motif channel — starts silent
        self._barge_ch = pygame.mixer.Channel(_BARGE_CH)
        if self._barge_motif_snd:
            self._barge_ch.set_volume(0.0)
            self._barge_ch.play(self._barge_motif_snd, loops=-1)

        # Bax hum voice channel (§7.4) — own channel so voice-duck logic
        # (which handles speaking blips) doesn't squash the hum.
        self._hum_voice_ch = pygame.mixer.Channel(_HUM_VOICE_CH)
        self._hum_voice_ch.set_volume(0.0)

        # Radio piggybacks on the slide channel (only one ever active at a time)
        self._radio_ch = self._slide_ch

    def _wire(self):
        bus.subscribe(EVT_HULL_DAMAGE,    self._on_hull)
        bus.subscribe(EVT_TETHER_HIT,     self._on_clang)
        bus.subscribe(EVT_TETHER_SNAP,    self._on_snap)
        bus.subscribe(EVT_GUN_FIRE,       self._on_gun)
        bus.subscribe(EVT_TERMINAL_OPEN,  self._on_term_open)
        bus.subscribe(EVT_TERMINAL_CLOSE, self._on_term_close)
        bus.subscribe(EVT_SPORE_INVERTED, self._on_spore)
        bus.subscribe(EVT_SHIP_DESTROYED, self._on_death)
        bus.subscribe(EVT_SLINGSHOT,      self._on_slingshot)
        bus.subscribe(EVT_CANISTER_GRAB,  self._on_canister)
        bus.subscribe(EVT_BARGE_NEARBY,   self._on_barge_nearby)
        bus.subscribe(EVT_BAX_SPEAK,      self._on_bax_speak)
        bus.subscribe(EVT_COMMS_SPEAK,    self._on_comms_speak)
        bus.subscribe(EVT_VOICE_CHAR,     self._on_voice_char)
        bus.subscribe(EVT_JUMP_READY,     self._on_jump_ready)
        bus.subscribe(EVT_DEBT_DING,      self._on_debt_ding)
        bus.subscribe(EVT_DELIVERY_STEP,  self._on_d_step)
        bus.subscribe(EVT_DELIVERY_HIT,   self._on_d_hit)
        bus.subscribe(EVT_DELIVERY_DONE,  self._on_d_done)
        bus.subscribe(EVT_SECTOR_CLEAR,   self._on_sector_clear)
        from core.event_bus import EVT_HULL_CRITICAL, EVT_MODULE_UNBOLTED, EVT_TORCH_ACTIVE
        bus.subscribe(EVT_HULL_CRITICAL,  self._on_hull_critical)
        bus.subscribe(EVT_MODULE_UNBOLTED, self._on_module_unbolted)
        bus.subscribe(EVT_TORCH_ACTIVE,   self._on_torch_active)
        bus.subscribe(EVT_RUN_START,      self._on_run_start)

    # ------------------------------------------------------------------
    def update(self, speed: float, dt: float = 0.016,
               hull_pct: float = 1.0, barge_threat: float = 0.0,
               sector_idx: int = 0, cargo_alarm: float = 0.0):
        self._hull_pct    = hull_pct
        self._barge_threat = barge_threat
        self._sector_idx  = sector_idx
        self._cargo_alarm = cargo_alarm

        self._update_pressure(speed)
        self._tick_bar(dt)

        # Edge-trigger cooldowns for repeating mood-queue events
        if self._barge_mood_cd > 0.0:
            self._barge_mood_cd -= dt
        if self._hull_crit_mood_cd > 0.0:
            self._hull_crit_mood_cd -= dt

        if not self._in_terminal:
            self._update_engine(speed)
            self._tick_licks(dt)
        self._tick_bax_voice(dt)
        self._tick_voice_duck(dt)
        self._tick_music_xfade(dt)
        self._tick_band_volumes(dt)
        self._tick_guitar_phrases(dt)
        self._tick_slide_notes(dt)
        self._tick_barge_motif()
        self._tick_snap_resolve(dt)
        self._tick_slingshot_modulation(dt)
        self._tick_decanting(dt)
        self._tick_menu_idle(dt)
        self._tick_chapter_cargo(dt)
        # Plan §2.4 — keep the active stem count at or below 5 by ducking the
        # lowest-priority hot stem when a 6th wants in.
        self._enforce_stem_budget()

        if self._master_fx:
            self._master_fx.update(hull_pct, cargo_alarm)

    # ------------------------------------------------------------------
    # flight_pressure + tempo system

    def _update_pressure(self, speed: float):
        from config import settings as S
        max_v = getattr(S, 'MAX_VELOCITY', 600.0)
        s_norm = min(1.0, speed / max(1.0, max_v))
        sectors = getattr(S, 'SECTORS_PER_RUN', 5)
        self._pressure = min(1.0, max(0.0,
            0.20 * s_norm
            + 0.30 * (1.0 - self._hull_pct)
            + 0.25 * self._barge_threat
            + 0.10 * (self._sector_idx / max(1, sectors))
            + 0.15 * self._cargo_alarm
        ))

    def _tick_bar(self, dt: float):
        """Track bar position; swap drum tier at bar boundary."""
        self._bar_t += dt
        if self._bar_t >= self._bar_dur:
            self._bar_t -= self._bar_dur
            # Decrement slingshot bar counter
            if self._sling_bars_left > 0:
                self._sling_bars_left -= 1
                if self._sling_bars_left == 0:
                    self._restore_pad_transposition()
            # Apply pending drum tier swap
            desired = _select_drum_tier(self._pressure)
            if desired != self._cur_tier:
                self._swap_drum_tier(desired)
            # Apply pending snap bass walk
            if self._snap_beats_left > 0:
                self._snap_beats_left -= 1

    def _swap_drum_tier(self, tier: int):
        if not self._drum_tiers or not self._bass_tiers:
            return
        tier = max(0, min(len(self._drum_tiers) - 1, tier))
        self._cur_tier = tier
        bpm = _DRUM_BPMS[tier]
        self._bar_dur = 60.0 / bpm * 4
        if self._drum_ch:
            vol = self._drum_ch.get_volume()
            self._drum_ch.stop()
            self._drum_ch.play(self._drum_tiers[tier], loops=-1)
            self._drum_ch.set_volume(vol)
        if self._bass_ch:
            vol = self._bass_ch.get_volume()
            self._bass_ch.stop()
            self._bass_ch.play(self._bass_tiers[tier], loops=-1)
            self._bass_ch.set_volume(vol)

    # ------------------------------------------------------------------
    # Scene system

    def set_scene(self, scene_name: str, chapter: int | None = None):
        """Switch musical scene. Optionally load a chapter's sonic palette."""
        if chapter is not None and chapter != self._chapter:
            self.load_chapter(chapter)
        prev_scene = self._scene
        self._scene = scene_name

        # Exit long-form mode if leaving menu
        if prev_scene == SCENE_MENU and scene_name != SCENE_MENU and self._long_form_active:
            self._exit_long_form()
        # Reset menu idle timer on any scene change
        if scene_name != SCENE_MENU:
            self._menu_idle_t = 0.0

        # Stop radio if leaving radio scene
        if prev_scene == SCENE_RADIO and scene_name != SCENE_RADIO and self._radio_ch:
            if self._radio_ch.get_busy():
                self._radio_ch.stop()

        # Start choreographed decanting if entering decanting; cancel otherwise
        if scene_name == SCENE_DECANTING:
            self._start_decanting_sequence()
        else:
            self._decant_active = False
            self._decant_steps = []

        if scene_name == SCENE_FLIGHT:
            # Voicing width driven by pressure (0→1 maps 1.0→0.5)
            self._vol_targets = {"drum": 0.42, "bass": 0.46, "arp": 0.30}
            self._gtr_interval   = (8.0, 16.0)
            self._slide_interval = (0.0, 0.0)

        elif scene_name == SCENE_TERMINAL:
            self._vol_targets = {"drum": 0.0, "bass": 0.0, "arp": 0.18}
            self._gtr_interval   = (0.0, 0.0)
            self._slide_interval = (0.0, 0.0)

        elif scene_name == SCENE_DELIVERY:
            self._vol_targets = {"drum": 0.48, "bass": 0.50, "arp": 0.34}
            self._gtr_interval   = (4.0, 9.0)
            self._slide_interval = (0.0, 0.0)

        elif scene_name in (SCENE_MENU, SCENE_INTERSTITIAL):
            self._vol_targets = {"drum": 0.0, "bass": 0.0, "arp": 0.32}
            self._gtr_interval   = (0.0, 0.0)
            self._slide_interval = (6.0, 12.0)

        elif scene_name == SCENE_SHOP:
            self._vol_targets = {"drum": 0.0, "bass": 0.0, "arp": 0.30}
            self._gtr_interval   = (5.0, 11.0)
            self._slide_interval = (0.0, 0.0)

        elif scene_name == SCENE_DECANTING:
            # Choreographed sequence handled in _tick_decanting — no looping slide
            self._vol_targets = {"drum": 0.0, "bass": 0.0, "arp": 0.0}
            self._gtr_interval   = (0.0, 0.0)
            self._slide_interval = (0.0, 0.0)

        elif scene_name == SCENE_LOADOUT:
            self._vol_targets = {"drum": 0.0, "bass": 0.0, "arp": 0.28}
            self._gtr_interval   = (10.0, 20.0)
            self._slide_interval = (0.0, 0.0)

        elif scene_name == SCENE_RADIO:
            self._vol_targets = {"drum": 0.0, "bass": 0.0, "arp": 0.10}
            self._gtr_interval   = (0.0, 0.0)
            self._slide_interval = (0.0, 0.0)

        else:
            self._vol_targets = {"drum": 0.0, "bass": 0.0, "arp": 0.0}
            self._gtr_interval   = (0.0, 0.0)
            self._slide_interval = (0.0, 0.0)

        if self._gtr_interval[1] > 0:
            self._gtr_cd = random.uniform(*self._gtr_interval) * 0.4
        if self._slide_interval[1] > 0:
            self._slide_cd = random.uniform(*self._slide_interval) * 0.4

    def load_chapter(self, chapter: int):
        """Retune engine drones and pad to the chapter's home key.
        Pulls metadata from audio/chapter_N.py module when available."""
        self._chapter = chapter
        mod = self._chapter_modules.get(chapter)
        if mod is not None:
            self._chapter_root = getattr(mod, "HOME_KEY_ROOT", _CHAPTER_ROOTS.get(chapter, 220.0))
            self._chapter_mode = getattr(mod, "MODE", _CHAPTER_MODES.get(chapter, "minor"))
        else:
            self._chapter_root = _CHAPTER_ROOTS.get(chapter, 220.0)
            self._chapter_mode = _CHAPTER_MODES.get(chapter, "minor")
        # Rebuild engine drones at new root
        for i, ch in enumerate(self._eng_ch):
            was_vol = ch.get_volume()
            snd = engine_drone(i, root_freq=self._chapter_root)
            self._eng_snd[i] = snd
            ch.stop()
            ch.play(snd, loops=-1)
            ch.set_volume(was_vol)
        # Apply chapter STEM_GATES to volume targets (e.g. chapter 4 silences bass)
        gates = getattr(mod, "STEM_GATES", {}) if mod else {}
        self._chapter_stem_gates = {
            "drum": gates.get("drum", 1.0),
            "bass": gates.get("bass", 1.0),
            "arp":  gates.get("arp",  1.0),
        }

    # ------------------------------------------------------------------
    def _tick_band_volumes(self, dt: float):
        """Ramp current volumes toward targets, also apply pressure-based pad narrowing."""
        step    = self._vol_fade_rate * dt
        changed = False
        # Arp target is modulated by pressure (arp drops out above 0.7)
        arp_tgt = self._vol_targets["arp"]
        if self._scene == SCENE_FLIGHT and self._pressure > 0.7:
            arp_tgt = self._vol_targets["arp"] * max(0.0, 1.0 - (self._pressure - 0.7) / 0.3)
        effective = dict(self._vol_targets)
        effective["arp"] = arp_tgt

        for k, tgt in effective.items():
            cur = self._vol_current.get(k, 0.0)
            if cur < tgt:
                cur = min(tgt, cur + step);  changed = True
            elif cur > tgt:
                cur = max(tgt, cur - step);  changed = True
            self._vol_current[k] = cur
        if changed:
            self._apply_band_volumes()

    def _music_gain(self) -> float:
        """Master scale for music/stems — reduced while voices speak."""
        return self._master * self._voice_duck

    def _tick_voice_duck(self, dt: float) -> None:
        if self._npc_speak_t > 0:
            self._npc_speak_t = max(0.0, self._npc_speak_t - dt)
        if self._bax_speaking or self._npc_speak_t > 0:
            self._voice_duck_target = self._VOICE_DUCK_FLOOR
        else:
            self._voice_duck_target = 1.0
        # Asymmetric attack/release so duck-in is gentle (~200 ms) but
        # duck-out is brisk (~170 ms) — music breathes back fast after a line.
        if self._voice_duck > self._voice_duck_target:
            rate = 3.0   # attack (going down)
            self._voice_duck = max(self._voice_duck_target,
                                   self._voice_duck - rate * dt)
        elif self._voice_duck < self._voice_duck_target:
            rate = 6.0   # release (going up)
            self._voice_duck = min(self._voice_duck_target,
                                   self._voice_duck + rate * dt)
        self._refresh_ducked_loops()

    def _refresh_ducked_loops(self) -> None:
        """Re-apply duck to channels not driven every frame by band mixer."""
        m = self._music_gain()
        if self._amb_ch and not self._in_terminal:
            base = 0.20 if not self._in_terminal else 0.06
            self._amb_ch.set_volume(m * (base / self._master) if self._master else 0)
        if self._hum_ch:
            self._hum_ch.set_volume(m * (0.038 / self._master) if self._master else 0)
        if self._lick_ch and self._lick_ch.get_busy():
            # Plan §2.4 — harp is the 5th-priority voice, sits *under* the band.
            self._lick_ch.set_volume(m * (0.55 / self._master) if self._master else 0)
        if self._gtr_ch and self._gtr_ch.get_busy():
            vol = 0.55 if self._scene == SCENE_DELIVERY else 0.42
            self._gtr_ch.set_volume(m * (vol / self._master) if self._master else 0)
        if self._slide_ch and self._slide_ch.get_busy():
            vol = 0.65 if self._scene == SCENE_DECANTING else 0.40
            self._slide_ch.set_volume(m * (vol / self._master) if self._master else 0)
        if self._barge_ch and self._barge_ch.get_busy():
            # Plan §6.2 target: -24 dBFS drone, not a foreground harp.
            self._barge_ch.set_volume(m * (0.09 / self._master) if self._master else 0)

    def _apply_band_volumes(self):
        m = self._music_gain()
        g = self._chapter_stem_gates
        if self._drum_ch is not None:
            self._drum_ch.set_volume(m * self._vol_current["drum"] * g.get("drum", 1.0))
        if self._bass_ch is not None:
            self._bass_ch.set_volume(m * self._vol_current["bass"] * g.get("bass", 1.0))
        if self._arp_ch is not None:
            self._arp_ch.set_volume(m * self._vol_current["arp"] * g.get("arp", 1.0))

    def _enforce_stem_budget(self):
        """Duck the lowest-priority active stem if more than 5 are hot."""
        # Priority order: engine, drum, bass, arp, harp/guitar/slide
        stems = [
            ("drum",   self._drum_ch,  self._vol_current.get("drum", 0.0)),
            ("bass",   self._bass_ch,  self._vol_current.get("bass", 0.0)),
            ("arp",    self._arp_ch,   self._vol_current.get("arp",  0.0)),
            ("guitar", self._gtr_ch,   0.42 if self._gtr_ch and self._gtr_ch.get_busy() else 0.0),
            ("lick",   self._lick_ch,  1.0  if self._lick_ch and self._lick_ch.get_busy() else 0.0),
        ]
        active = [(name, ch, vol) for name, ch, vol in stems if vol > 0.01]
        if len(active) > 5:
            # Duck the last (lowest priority) active stem
            _, ch, _ = active[-1]
            if ch:
                ch.set_volume(ch.get_volume() * 0.5)

    # ------------------------------------------------------------------
    def _tick_music_xfade(self, dt: float):
        if self._music_xfade <= 0.0 or not (self._music_a and self._music_b):
            return
        self._music_xfade = max(0.0, self._music_xfade - dt / self._music_xfade_dur)
        frac = 1.0 - self._music_xfade
        gain = (0.18 if self._in_terminal else self._music_target_vol) * self._voice_duck
        mg = self._master
        if self._music_active == 1:
            self._music_b.set_volume(mg * gain * frac)
            self._music_a.set_volume(mg * gain * (1.0 - frac))
        else:
            self._music_a.set_volume(mg * gain * frac)
            self._music_b.set_volume(mg * gain * (1.0 - frac))
        if self._music_xfade <= 0.0:
            (self._music_a if self._music_active == 1 else self._music_b).stop()

    def _update_engine(self, speed: float):
        # Silence engine when ship is not thrusting (delivery corridor, terminal, etc.)
        if speed < 8.0:
            for ch in self._eng_ch:
                ch.set_volume(0.0)
            return
        tier  = 0
        for i in range(_N_TIERS - 1):
            if speed >= _SPEED_BP[i]:
                tier = i
        upper = min(tier + 1, _N_TIERS - 1)
        blend = 0.0
        if upper != tier:
            span  = max(1.0, _SPEED_BP[upper] - _SPEED_BP[tier])
            blend = min(1.0, (speed - _SPEED_BP[tier]) / span)
        eng_m = self._music_gain()
        for i, ch in enumerate(self._eng_ch):
            if i == tier:
                vol = eng_m * 0.56 * (1.0 - blend)
            elif i == upper:
                vol = eng_m * 0.56 * blend
            else:
                vol = 0.0
            ch.set_volume(vol)

    def _tick_licks(self, dt: float):
        if not self._licks or self._lick_ch is None:
            return
        self._lick_cd -= dt
        if self._lick_cd <= 0.0 and not self._lick_ch.get_busy():
            # Use mood-filtered lick if one was requested by Bax
            if self._next_lick_mood is not None:
                lick = generate_lick(mood=self._next_lick_mood)
                self._next_lick_mood = None
            else:
                # Idle ambient — alternate lonely / weary so the score's resting
                # texture is melancholy, not random.  (Plan §7.3.)
                idle_mood = "lonely" if self._idle_mood_toggle == 0 else "weary"
                self._idle_mood_toggle ^= 1
                lick = generate_lick(mood=idle_mood)
            # Plan §2.4 — harp is the 5th-priority voice, sits *under* the band.
            self._lick_ch.set_volume(self._music_gain() * (0.55 / self._master) if self._master else 0)
            self._lick_ch.play(lick)
            if self._scene == SCENE_TERMINAL:
                self._lick_cd = random.uniform(18.0, 32.0)
            else:
                self._lick_cd = random.uniform(8.0, 18.0)

    def _tick_bax_voice(self, dt: float):
        if not self._bax_speaking:
            return
        self._bax_speak_t += dt
        self._bax_blip_cd -= dt
        if self._bax_speak_t >= self._bax_speak_dur:
            self._bax_speaking = False
            return
        if self._bax_blip_cd <= 0.0:
            self._play_voice_blip("bax", channel=self._bax_v_ch)
            self._bax_blip_cd = 0.095

    def _tick_guitar_phrases(self, dt: float):
        if not self._guitar_phrases or self._gtr_ch is None:
            return
        lo, hi = self._gtr_interval
        if hi <= 0.0 or self._gtr_ch.get_busy():
            return
        self._gtr_cd -= dt
        if self._gtr_cd <= 0.0:
            snd = random.choice(self._guitar_phrases)
            vol = 0.55 if self._scene == SCENE_DELIVERY else 0.42
            self._gtr_ch.set_volume(self._music_gain() * (vol / self._master) if self._master else 0)
            self._gtr_ch.play(snd)
            self._gtr_cd = random.uniform(lo, hi)

    def _tick_slide_notes(self, dt: float):
        if not self._slide_notes or self._slide_ch is None:
            return
        lo, hi = self._slide_interval
        if hi <= 0.0 or self._slide_ch.get_busy():
            return
        self._slide_cd -= dt
        if self._slide_cd <= 0.0:
            snd = random.choice(self._slide_notes)
            vol = 0.55 if self._scene == SCENE_DECANTING else 0.40
            self._slide_ch.set_volume(self._music_gain() * (vol / self._master) if self._master else 0)
            self._slide_ch.play(snd)
            self._slide_cd = random.uniform(lo, hi)

    def _tick_barge_motif(self):
        """Fade barge motif drone in/out based on proximity."""
        if self._barge_ch is None:
            return
        # Plan §6.2: -24 dBFS drone — under the bandstand, not over it.
        target_vol = self._music_gain() * 0.09 if self._barge_nearby else 0.0
        cur = self._barge_ch.get_volume()
        step = 0.016 * 0.4   # ~2.5s fade
        if cur < target_vol:
            self._barge_ch.set_volume(min(target_vol, cur + step))
        elif cur > target_vol:
            self._barge_ch.set_volume(max(target_vol, cur - step))
        self._barge_nearby = False   # reset; re-set next frame if still nearby

    def _tick_snap_resolve(self, dt: float):
        if self._snap_resolve_t <= 0.0:
            return
        self._snap_resolve_t -= dt
        if self._snap_resolve_t <= 0.0:
            # Open pad to full voicing for 2 bars
            if self._arp_ch and self._sling_pad_tiers:
                vol = self._arp_ch.get_volume()
                self._arp_ch.stop()
                self._arp_ch.play(self._sling_pad_tiers[0], loops=-1)  # root = open voicing
                self._arp_ch.set_volume(max(vol, self._master * 0.35))

    def _tick_slingshot_modulation(self, dt: float):
        pass   # bar counter handled in _tick_bar

    # ------------------------------------------------------------------
    # Decanting choreography (Section 7.5)
    # Sequence:
    #   t=0.0  slide-blues note (high), 1.6s
    #   t=1.6  3s silence (just tape hum)
    #   t=4.6  receipt printer SFX
    #   t=5.0  4s silence
    #   t=9.0  slide-blues note (whole step lower), 1.8s
    #   t=10.8 hold (silent) until ENTER → scene change

    def _start_decanting_sequence(self):
        self._decant_t = 0.0
        self._decant_active = True
        self._decant_steps = [
            (0.0,  "slide_high"),
            (4.6,  "printer"),
            (9.0,  "slide_low"),
        ]
        # Mute all music stems so the silence is real
        for ch in (self._drum_ch, self._bass_ch, self._arp_ch,
                   self._music_a, self._music_b, self._lick_ch,
                   self._gtr_ch, self._barge_ch):
            if ch is not None:
                ch.set_volume(0.0)

    def _tick_decanting(self, dt: float):
        if not self._decant_active or not self._decant_steps:
            return
        self._decant_t += dt
        # Execute any step whose time has passed
        while self._decant_steps and self._decant_t >= self._decant_steps[0][0]:
            _, action = self._decant_steps.pop(0)
            if action == "slide_high" and self._slide_ch and self._decant_slide_high:
                self._slide_ch.set_volume(self._master * 0.65)
                self._slide_ch.play(self._decant_slide_high)
            elif action == "printer" and self._sfx.get("printer"):
                ch = pygame.mixer.find_channel(True)
                if ch:
                    ch.set_volume(self._master * 0.55)
                    ch.play(self._sfx["printer"])
            elif action == "slide_low" and self._slide_ch and self._decant_slide_low:
                self._slide_ch.set_volume(self._master * 0.65)
                self._slide_ch.play(self._decant_slide_low)

    # ------------------------------------------------------------------
    # Main-menu listening room (Section 7.6) — long-form pad after 120s idle

    def _tick_menu_idle(self, dt: float):
        if self._scene != SCENE_MENU or self._long_form_pad is None:
            self._menu_idle_t = 0.0
            if self._long_form_active:
                self._exit_long_form()
            return
        self._menu_idle_t += dt
        if not self._long_form_active and self._menu_idle_t >= 120.0:
            self._enter_long_form()

    def _enter_long_form(self):
        """Swap menu pad to the 90s composition; mute slide/lick distractions."""
        if self._arp_ch and self._long_form_pad:
            vol = self._arp_ch.get_volume()
            self._arp_ch.stop()
            self._arp_ch.play(self._long_form_pad, loops=-1)
            self._arp_ch.set_volume(max(vol, self._master * 0.32))
            self._long_form_active = True
            self._slide_interval = (0.0, 0.0)   # no slide overlays
            # Stop any ongoing slide
            if self._slide_ch and self._slide_ch.get_busy():
                self._slide_ch.stop()

    def _exit_long_form(self):
        if self._arp_ch and self._pad_loop:
            vol = self._arp_ch.get_volume()
            self._arp_ch.stop()
            self._arp_ch.play(self._pad_loop, loops=-1)
            self._arp_ch.set_volume(vol)
        self._long_form_active = False

    # ------------------------------------------------------------------
    # Radio stations (Section 7.1)

    def cycle_radio_station(self):
        """Advance to next radio station; engage SCENE_RADIO."""
        if not self._radio_stations or not self._radio_station_order:
            return
        self._radio_current_idx = (self._radio_current_idx + 1) % len(self._radio_station_order)
        self.set_scene(SCENE_RADIO)

    def _play_current_radio_station(self):
        if not self._radio_stations or not self._radio_station_order or self._radio_ch is None:
            return
        key = self._radio_station_order[self._radio_current_idx]
        snd = self._radio_stations.get(key)
        if snd is None:
            return
        if self._radio_ch.get_busy():
            self._radio_ch.stop()
        self._radio_ch.set_volume(self._master * 0.52)
        self._radio_ch.play(snd, loops=-1)

    # ------------------------------------------------------------------
    # Chapter cargo alarm (Section 4)

    def _tick_chapter_cargo(self, dt: float):
        mod = self._chapter_modules.get(self._chapter)
        if mod is None:
            return
        cb = getattr(mod, "cargo_alarm_callback", None)
        if cb is None:
            return
        try:
            cb(self._cargo_alarm, master_fx=self._master_fx)
        except Exception:
            pass

    def play_bax_hum(self, idx: int) -> None:
        """Play one of the 8 prebuilt Bax hums on a dedicated channel.
        Ducks the bandstand (drum/bass/arp targets × 0.25) so the hum is the
        clear foreground.  Bandstand restores naturally on next set_scene().
        Plan §7.4.
        """
        if not 0 <= idx < len(self._bax_hums) or self._hum_voice_ch is None:
            return
        # Duck the band so the hum is the foreground voice
        self._vol_targets = {k: v * 0.25 for k, v in self._vol_targets.items()}
        self._hum_voice_ch.stop()
        self._hum_voice_ch.set_volume(self._master * 0.62)
        self._hum_voice_ch.play(self._bax_hums[idx])

    def _restore_pad_transposition(self):
        """Return pad to root transposition after slingshot key change."""
        if self._arp_ch and self._sling_pad_tiers:
            vol = self._arp_ch.get_volume()
            self._arp_ch.stop()
            self._arp_ch.play(self._sling_pad_tiers[0], loops=-1)
            self._arp_ch.set_volume(vol)
        self._sling_semitones = 0

    # ------------------------------------------------------------------
    def _play_sfx(self, key: str, vol_scale: float = 1.0):
        snd = self._sfx.get(key)
        if snd is None:
            return
        ch = pygame.mixer.find_channel(True)
        if ch:
            ch.set_volume(self._master * vol_scale)
            ch.play(snd)

    def _play_voice_blip(self, speaker: str, channel: pygame.mixer.Channel | None):
        key   = resolve_voice_key(speaker or "")
        blips = self._voices.get(key) or self._voices.get("default")
        if not blips or channel is None:
            return
        snd = random.choice(blips)
        channel.set_volume(self._master * self._VOICE_BLIP_VOL)
        channel.play(snd)

    # ------------------------------------------------------------------
    # Event handlers

    def _on_hull(self, amount, **_):
        if amount > 5:
            self._play_sfx("hull", 0.82)

    def _on_clang(self, **_):   self._play_sfx("clang", 0.72)
    def _on_gun(self, **_):     self._play_sfx("gun", 0.62)
    def _on_canister(self, **_):
        self._play_sfx("canister", 0.70)
        self._next_lick_mood = "cocky"
    def _on_spore(self, active, **_):
        if active:
            self._play_sfx("spore", 0.75)

    def _on_snap(self, **_):
        self._play_sfx("snap", 0.78)
        # Schedule musical resolution: snare flam on next sub-beat, then pad opens
        self._snap_resolve_t = self._bar_dur * 0.25   # quarter-bar ahead
        self._snap_beats_left = 2
        self._next_lick_mood = "cocky"

    def _on_death(self, **_):
        self._play_sfx("death", 0.90)
        # Choreographed decanting: stop band immediately
        if self._drum_ch:  self._drum_ch.set_volume(0.0)
        if self._bass_ch:  self._bass_ch.set_volume(0.0)
        if self._arp_ch:   self._arp_ch.set_volume(0.0)

    def _on_slingshot(self, **_):
        self._play_sfx("slingshot", 0.80)
        # Play the musical stinger SFX
        self._play_sfx("sling_stinger", 0.65)
        # Modulate pad up a perfect fifth (+7 semitones) for 4 bars
        if self._arp_ch and len(self._sling_pad_tiers) >= 4:
            # index 3 = +7 semitones (perfect fifth)
            vol = self._arp_ch.get_volume()
            self._arp_ch.stop()
            self._arp_ch.play(self._sling_pad_tiers[3], loops=-1)
            self._arp_ch.set_volume(max(vol, self._master * 0.30))
            self._sling_semitones  = 7
            self._sling_bars_left  = 4
        # Queue a delighted lick for the next harp fire
        self._next_lick_mood = "delighted"

    def _on_barge_nearby(self, distance=0, **_):
        self._barge_nearby = True
        ch = self._bax_v_ch
        if ch and not ch.get_busy():
            self._play_sfx("barge", 0.65)
        # Edge-trigger: queue a sarcastic harp lick only once per ~15s window,
        # not every frame the barge is in range.
        if self._barge_mood_cd <= 0.0:
            self._next_lick_mood = "sarcastic"
            self._barge_mood_cd  = 15.0

    def _on_hull_critical(self, hp=0, **_):
        # Fires repeatedly while hull is critical — cooldown keeps it from spamming.
        if self._hull_crit_mood_cd <= 0.0:
            self._next_lick_mood = "panic"
            self._hull_crit_mood_cd = 10.0

    def _on_module_unbolted(self, **_):
        self._next_lick_mood = "weary"

    def _on_torch_active(self, **_):
        # Plays each time the barge re-cycles its torch (every ~5s).  Already
        # spaced by the emitter, so no cooldown needed here.
        self._play_sfx("torch_clap", 0.50)

    def _on_bax_speak(self, line: str = "", **_):
        if not line:
            return
        self._bax_speaking  = True
        self._bax_speak_t   = 0.0
        self._bax_speak_dur = len(line) / _BAX_CHARS_PER_SEC
        self._bax_blip_cd   = 0.0

    def _on_comms_speak(self, speaker: str = "", line: str = "", **_):
        """Duck music for radio/comms lines (Kress, Medi-Corp, etc.)."""
        if line:
            self._npc_speak_t = max(self._npc_speak_t, len(line) / 22.0)
        sp = (speaker or "").strip().upper()
        if sp and sp != "BAX":
            self._play_voice_blip(speaker, self._npc_v_ch)

    def _on_voice_char(self, speaker: str = "", **_):
        self._npc_speak_t = max(self._npc_speak_t, 0.55)
        self._play_voice_blip(speaker, self._npc_v_ch)

    def _on_jump_ready(self, **_):  self._play_sfx("jump", 0.82)
    def _on_debt_ding(self, **_):   self._play_sfx("debt_ding", 0.55)
    def _on_d_step(self, **_):      self._play_sfx("d_step", 0.42)
    def _on_d_hit(self,  **_):      self._play_sfx("d_hit",  0.78)
    def _on_d_done(self, **_):      self._play_sfx("d_door", 0.85)

    def _on_sector_clear(self, sector_num=0, **_):
        if not self._music_pads or not (self._music_a and self._music_b):
            return
        next_idx  = sector_num % len(self._music_pads)
        target_ch = self._music_b if self._music_active == 0 else self._music_a
        target_ch.stop()
        target_ch.set_volume(0.0)
        target_ch.play(self._music_pads[next_idx], loops=-1)
        self._music_active = 1 - self._music_active
        self._music_xfade  = 1.0

    def _on_run_start(self, **_):
        if not self._music_pads or not (self._music_a and self._music_b):
            return
        self._music_a.stop()
        self._music_b.stop()
        self._music_a.set_volume(self._master * self._music_target_vol)
        self._music_a.play(self._music_pads[0], loops=-1)
        self._music_b.set_volume(0.0)
        self._music_active = 0
        self._music_xfade  = 0.0

    def _on_term_open(self, npc=None, **_):
        self._in_terminal = True
        for ch in self._eng_ch:
            ch.set_volume(0.0)
        if self._amb_ch:
            self._amb_ch.set_volume(self._master * 0.06)
        if self._lick_ch:
            self._lick_ch.stop()
        active_music = self._music_a if self._music_active == 0 else self._music_b
        if active_music:
            active_music.set_volume(self._master * 0.18)
        self._play_sfx("beep", 0.50)
        if self._drone_ch and self._sfx.get("drone"):
            self._drone_ch.set_volume(self._master * 0.32)
            self._drone_ch.play(self._sfx["drone"], loops=-1)
        # NPC-specific sonic signatures (plan §7.2)
        npc_cls = type(npc).__name__ if npc is not None else ""
        if npc_cls == "UnionDispatcher":
            self._play_sfx("npc_dispatcher", 0.55)
        elif npc_cls == "InsuranceAdjuster":
            self._play_sfx("npc_adjuster", 0.50)

    def _on_term_close(self, **_):
        self._in_terminal = False
        if self._amb_ch:
            self._amb_ch.set_volume(self._master * 0.20)
        if self._drone_ch:
            self._drone_ch.stop()
        active_music = self._music_a if self._music_active == 0 else self._music_b
        if active_music:
            active_music.set_volume(self._master * self._music_target_vol)
        self._lick_cd = random.uniform(8.0, 20.0)
