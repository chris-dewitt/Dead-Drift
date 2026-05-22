from __future__ import annotations
import random
import pygame
from core.event_bus import (
    bus,
    EVT_HULL_DAMAGE, EVT_TETHER_HIT, EVT_TETHER_SNAP,
    EVT_GUN_FIRE, EVT_TERMINAL_OPEN, EVT_TERMINAL_CLOSE,
    EVT_SPORE_INVERTED, EVT_SHIP_DESTROYED, EVT_SLINGSHOT,
    EVT_CANISTER_GRAB, EVT_BARGE_NEARBY, EVT_BAX_SPEAK,
    EVT_VOICE_CHAR, EVT_JUMP_READY, EVT_DEBT_DING,
    EVT_DELIVERY_STEP, EVT_DELIVERY_HIT, EVT_DELIVERY_DONE,
    EVT_SECTOR_CLEAR, EVT_RUN_START,
)
from audio.synth import (
    engine_drone, ambient_static, gun_shot, hull_impact,
    tether_clang, tether_snap, terminal_beep, spore_sting,
    death_sting, slingshot_whoosh, canister_chime,
    barge_alert, terminal_drone, jump_ready_charge, debt_ding,
    delivery_footstep, delivery_hit_sting, delivery_door_chime,
    sector_pad, slide_blues_note,
)
from audio.blues_licks import prebuild_all
from audio.voices import prebuild_voices
from audio.drum_loop import build_drum_loop, build_bass_loop
from audio.guitar_phrases import prebuild_phrases
from audio.new_wave_pad import build_new_wave_pad

# ---------------------------------------------------------------------------
# Channel layout
_N_TIERS  = 5
_SPEED_BP = [0.0, 120.0, 240.0, 380.0, 520.0]

_ENG_CH   = 0    # channels 0-4: engine tiers (5)
_AMB_CH   = 5    # deep-space ambient static
_LICK_CH  = 6    # blues harmonica licks
_BAX_V_CH = 7    # Bax voice blips
_NPC_V_CH = 8    # NPC terminal voice blips
_DRONE_CH = 9    # terminal drone pad
_MUSIC_CH_A = 20 # sector music pad — channel A (active)
_MUSIC_CH_B = 21 # sector music pad — channel B (crossfade target)
_DRUM_CH    = 22 # 80s drum-machine loop
_BASS_CH    = 23 # walking sub-bass loop (locked to drum BPM)
_GTR_CH     = 24 # acoustic guitar phrases (one-shot)
_ARP_CH     = 25 # new-wave arpeggio pad (with built-in arpeggio voice)
_SLIDE_CH   = 26 # mournful slide-blues notes (decanting / menu)
_SFX_POOL = 10   # channels 10-19: one-shot SFX pool

_BAX_CHARS_PER_SEC = 32.0   # matches cockpit_renderer typewriter speed

# Scene names — drives layer activation. Game.py calls set_scene() at state changes.
SCENE_MENU         = "menu"
SCENE_FLIGHT       = "flight"
SCENE_TERMINAL     = "terminal"
SCENE_DELIVERY     = "delivery"
SCENE_SHOP         = "shop"
SCENE_INTERSTITIAL = "interstitial"
SCENE_DECANTING    = "decanting"
SCENE_LOADOUT      = "loadout"

# Bluesy minor chord progression — Am, F, G, Em (Hz)
_PROGRESSION = [220.0, 174.61, 196.0, 164.81]
_DEFAULT_BPM = 96.0


class AudioManager:
    """
    Procedural 80s-new-wave-meets-delta-blues soundtrack. No asset files.

    Channels:
      0-4   engine tier drones (crossfaded by ship speed)
      5     deep-space ambient static (looping)
      6     blues harmonica licks (random interval)
      7     Bax voice blips (during EVT_BAX_SPEAK typewriter)
      8     NPC terminal voice blips (via EVT_VOICE_CHAR)
      9     terminal drone pad (looping while in terminal)
      10-19 one-shot SFX pool
      20-21 sector pad A/B (existing crossfade between sector mood pads)
      22    drum-machine loop (96 BPM, 2-bar 80s pattern)
      23    sub-bass loop (locked to drum BPM, walks chord progression)
      24    acoustic guitar phrases (one-shot, scene-gated interval)
      25    new-wave arpeggio pad (long chord progression + arp top voice)
      26    slide-blues notes (mournful, slow, for menu/decanting)

    Scene activation table (set via set_scene(scene_name)):
      menu        : pad+arp on   | slide every 6-12s        | no drums/bass/gtr
      loadout     : pad+arp on   | very rare guitar         | no drums/bass
      flight      : DRUMS+BASS+PAD+ARP on | guitar every 8-16s
      terminal    : pad+arp quiet only    | sparser blues licks (existing)
      shop        : pad+arp on            | guitar every 5-11s
      delivery    : DRUMS+BASS+PAD+ARP loud | guitar every 4-9s
      interstitial: pad+arp on   | slide every 6-12s        | no drums/bass
      decanting   : everything off | slow slide every 4-5s
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
        self._licks:    list[pygame.mixer.Sound]   = []
        self._sfx:      dict[str, pygame.mixer.Sound] = {}
        self._voices:   dict[str, list[pygame.mixer.Sound]] = {}

        self._master      = 0.70
        self._in_terminal = False
        self._lick_cd     = random.uniform(3.0, 7.0)  # hear a lick early every sector

        # Sector music — two channels for crossfade between sectors
        self._music_a:   pygame.mixer.Channel | None = None
        self._music_b:   pygame.mixer.Channel | None = None
        self._music_pads: list[pygame.mixer.Sound] = []   # cached per-sector pads
        self._music_active = 0       # 0 = A is currently playing, 1 = B
        self._music_xfade  = 0.0     # 0.0 → 1.0 progress of in-progress crossfade
        self._music_xfade_dur = 2.5  # seconds
        self._music_target_vol = 0.34

        # Bax voice timer — fires blips for the duration of a Bax line
        self._bax_speaking   = False
        self._bax_speak_t    = 0.0
        self._bax_speak_dur  = 0.0
        self._bax_blip_cd    = 0.0

        # ---- New-wave-blues bandstand state ----
        self._scene: str = SCENE_MENU
        self._drum_ch:    pygame.mixer.Channel | None = None
        self._bass_ch:    pygame.mixer.Channel | None = None
        self._gtr_ch:     pygame.mixer.Channel | None = None
        self._arp_ch:     pygame.mixer.Channel | None = None
        self._slide_ch:   pygame.mixer.Channel | None = None
        self._drum_loop:  pygame.mixer.Sound   | None = None
        self._bass_loop:  pygame.mixer.Sound   | None = None
        self._pad_loop:   pygame.mixer.Sound   | None = None
        self._guitar_phrases: list[pygame.mixer.Sound] = []
        self._slide_notes:    list[pygame.mixer.Sound] = []

        # Target / current volumes per band (0..1, before master). Smoothly ramped.
        self._vol_targets: dict[str, float] = {
            "drum": 0.0, "bass": 0.0, "arp":  0.0,
        }
        self._vol_current: dict[str, float] = dict(self._vol_targets)
        self._vol_fade_rate = 1.0 / 0.4   # ~0.4 s for a full 0→1 crossfade

        # Guitar phrase scheduler
        self._gtr_cd:        float = 12.0
        self._gtr_interval:  tuple[float, float] = (0.0, 0.0)  # off by default
        # Slide-note scheduler (menu / decanting / interstitial)
        self._slide_cd:      float = 4.0
        self._slide_interval: tuple[float, float] = (0.0, 0.0)

        self._build()
        self._start_loops()
        self._wire()
        # Default to menu scene so layers come up sensibly at boot
        self.set_scene(SCENE_MENU)

    # ------------------------------------------------------------------
    def _build(self):
        print("[audio] generating engine tones…", flush=True)
        for tier in range(_N_TIERS):
            self._eng_snd.append(engine_drone(tier))

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
        self._sfx["jump"]         = jump_ready_charge()
        self._sfx["debt_ding"]    = debt_ding()
        self._sfx["d_step"]       = delivery_footstep()
        self._sfx["d_hit"]        = delivery_hit_sting()
        self._sfx["d_door"]       = delivery_door_chime()

        print("[audio] generating blues licks…", flush=True)
        self._licks = prebuild_all()

        print("[audio] generating character voices…", flush=True)
        self._voices = prebuild_voices()   # {char_name: [Sound, ...]}

        print("[audio] generating sector pads…", flush=True)
        from config import settings as S
        self._music_pads = [sector_pad(i) for i in range(S.SECTORS_PER_RUN)]

        print("[audio] generating 80s drum loop…", flush=True)
        self._drum_loop = build_drum_loop(bpm=_DEFAULT_BPM, length_bars=2, intensity=1.0)

        print("[audio] generating sub-bass loop…", flush=True)
        self._bass_loop = build_bass_loop(_PROGRESSION, bpm=_DEFAULT_BPM, notes_per_chord=4)

        print("[audio] generating new-wave pad…", flush=True)
        # 2.5s per chord = 4 beats @ 96 BPM → 10s loop, locks with bass + drums
        self._pad_loop = build_new_wave_pad(
            _PROGRESSION, duration_per_chord=2.5, mode="minor", with_arpeggio=True,
        )

        print("[audio] generating acoustic guitar phrases…", flush=True)
        self._guitar_phrases = prebuild_phrases()

        print("[audio] generating mournful slide notes…", flush=True)
        self._slide_notes = [
            slide_blues_note(220.0,  174.61, duration=1.6),
            slide_blues_note(196.0,  146.83, duration=1.8),
            slide_blues_note(164.81, 130.81, duration=2.0),
            slide_blues_note(146.83, 110.0,  duration=2.2),
        ]

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

        # New-wave-blues bandstand channels
        self._drum_ch  = pygame.mixer.Channel(_DRUM_CH)
        self._bass_ch  = pygame.mixer.Channel(_BASS_CH)
        self._gtr_ch   = pygame.mixer.Channel(_GTR_CH)
        self._arp_ch   = pygame.mixer.Channel(_ARP_CH)
        self._slide_ch = pygame.mixer.Channel(_SLIDE_CH)

        # All band loops start muted — set_scene() ramps them up
        if self._drum_loop:
            self._drum_ch.set_volume(0.0)
            self._drum_ch.play(self._drum_loop, loops=-1)
        if self._bass_loop:
            self._bass_ch.set_volume(0.0)
            self._bass_ch.play(self._bass_loop, loops=-1)
        if self._pad_loop:
            self._arp_ch.set_volume(0.0)
            self._arp_ch.play(self._pad_loop, loops=-1)

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
        bus.subscribe(EVT_VOICE_CHAR,     self._on_voice_char)
        bus.subscribe(EVT_JUMP_READY,     self._on_jump_ready)
        bus.subscribe(EVT_DEBT_DING,      self._on_debt_ding)
        bus.subscribe(EVT_DELIVERY_STEP,  self._on_d_step)
        bus.subscribe(EVT_DELIVERY_HIT,   self._on_d_hit)
        bus.subscribe(EVT_DELIVERY_DONE,  self._on_d_done)
        bus.subscribe(EVT_SECTOR_CLEAR,   self._on_sector_clear)
        bus.subscribe(EVT_RUN_START,      self._on_run_start)

    # ------------------------------------------------------------------
    def update(self, speed: float, dt: float = 0.016):
        if not self._in_terminal:
            self._update_engine(speed)
            self._tick_licks(dt)
        self._tick_bax_voice(dt)
        self._tick_music_xfade(dt)
        self._tick_band_volumes(dt)
        self._tick_guitar_phrases(dt)
        self._tick_slide_notes(dt)

    # ------------------------------------------------------------------
    # Scene system — toggles which musical layers are active

    def set_scene(self, scene_name: str):
        """Switch musical scene. Layer volumes crossfade over ~0.4s."""
        self._scene = scene_name
        if scene_name == SCENE_FLIGHT:
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
            self._vol_targets = {"drum": 0.0, "bass": 0.0, "arp": 0.0}
            self._gtr_interval   = (0.0, 0.0)
            self._slide_interval = (4.0, 5.5)

        elif scene_name == SCENE_LOADOUT:
            self._vol_targets = {"drum": 0.0, "bass": 0.0, "arp": 0.28}
            self._gtr_interval   = (10.0, 20.0)
            self._slide_interval = (0.0, 0.0)

        else:
            self._vol_targets = {"drum": 0.0, "bass": 0.0, "arp": 0.0}
            self._gtr_interval   = (0.0, 0.0)
            self._slide_interval = (0.0, 0.0)

        # Re-seed the phrase cooldowns so they fire reasonably soon (not instantly)
        if self._gtr_interval[1] > 0:
            self._gtr_cd = random.uniform(*self._gtr_interval) * 0.4
        if self._slide_interval[1] > 0:
            self._slide_cd = random.uniform(*self._slide_interval) * 0.4

    def _tick_band_volumes(self, dt: float):
        """Ramp current volumes toward targets at the crossfade rate."""
        step = self._vol_fade_rate * dt
        changed = False
        for k, tgt in self._vol_targets.items():
            cur = self._vol_current.get(k, 0.0)
            if cur < tgt:
                cur = min(tgt, cur + step)
                changed = True
            elif cur > tgt:
                cur = max(tgt, cur - step)
                changed = True
            self._vol_current[k] = cur
        if changed:
            self._apply_band_volumes()

    def _apply_band_volumes(self):
        m = self._master
        if self._drum_ch is not None:
            self._drum_ch.set_volume(m * self._vol_current["drum"])
        if self._bass_ch is not None:
            self._bass_ch.set_volume(m * self._vol_current["bass"])
        if self._arp_ch is not None:
            self._arp_ch.set_volume(m * self._vol_current["arp"])

    def _tick_guitar_phrases(self, dt: float):
        if not self._guitar_phrases or self._gtr_ch is None:
            return
        lo, hi = self._gtr_interval
        if hi <= 0.0:
            return
        if self._gtr_ch.get_busy():
            return
        self._gtr_cd -= dt
        if self._gtr_cd <= 0.0:
            snd = random.choice(self._guitar_phrases)
            vol = 0.55 if self._scene == SCENE_DELIVERY else 0.42
            self._gtr_ch.set_volume(self._master * vol)
            self._gtr_ch.play(snd)
            self._gtr_cd = random.uniform(lo, hi)

    def _tick_slide_notes(self, dt: float):
        if not self._slide_notes or self._slide_ch is None:
            return
        lo, hi = self._slide_interval
        if hi <= 0.0:
            return
        if self._slide_ch.get_busy():
            return
        self._slide_cd -= dt
        if self._slide_cd <= 0.0:
            snd = random.choice(self._slide_notes)
            vol = 0.55 if self._scene == SCENE_DECANTING else 0.40
            self._slide_ch.set_volume(self._master * vol)
            self._slide_ch.play(snd)
            self._slide_cd = random.uniform(lo, hi)

    # ------------------------------------------------------------------
    def _tick_music_xfade(self, dt: float):
        if self._music_xfade <= 0.0 or self._music_a is None or self._music_b is None:
            return
        self._music_xfade = max(0.0, self._music_xfade - dt / self._music_xfade_dur)
        frac = 1.0 - self._music_xfade   # 0.0 → 1.0
        # Reduce music under terminal
        gain = 0.18 if self._in_terminal else self._music_target_vol
        if self._music_active == 1:
            self._music_b.set_volume(self._master * gain * frac)
            self._music_a.set_volume(self._master * gain * (1.0 - frac))
        else:
            self._music_a.set_volume(self._master * gain * frac)
            self._music_b.set_volume(self._master * gain * (1.0 - frac))
        if self._music_xfade <= 0.0:
            (self._music_a if self._music_active == 1 else self._music_b).stop()

    def _update_engine(self, speed: float):
        tier = 0
        for i in range(_N_TIERS - 1):
            if speed >= _SPEED_BP[i]:
                tier = i
        upper = min(tier + 1, _N_TIERS - 1)

        blend = 0.0
        if upper != tier:
            span  = max(1.0, _SPEED_BP[upper] - _SPEED_BP[tier])
            blend = min(1.0, (speed - _SPEED_BP[tier]) / span)

        for i, ch in enumerate(self._eng_ch):
            if i == tier:
                vol = self._master * 0.56 * (1.0 - blend)
            elif i == upper:
                vol = self._master * 0.56 * blend
            else:
                vol = 0.0
            ch.set_volume(vol)

    def _tick_licks(self, dt: float):
        if not self._licks or self._lick_ch is None:
            return
        self._lick_cd -= dt
        if self._lick_cd <= 0.0 and not self._lick_ch.get_busy():
            lick = random.choice(self._licks)
            self._lick_ch.set_volume(self._master * 1.0)
            self._lick_ch.play(lick)
            # Terminal scene gets sparser harmonica; flight is normal cadence.
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
            self._bax_blip_cd = 0.095   # blip every ~95ms

    # ------------------------------------------------------------------
    def _play_sfx(self, key: str, vol_scale: float = 1.0):
        snd = self._sfx.get(key)
        if snd is None:
            return
        ch = pygame.mixer.find_channel(True)
        if ch and ch.get_busy() is False or ch:
            ch.set_volume(self._master * vol_scale)
            ch.play(snd)

    def _play_voice_blip(self, speaker: str, channel: pygame.mixer.Channel | None):
        key   = speaker.lower().lstrip("[").rstrip("]").strip()
        blips = self._voices.get(key) or self._voices.get("bax")
        if not blips or channel is None:
            return
        snd = random.choice(blips)
        channel.set_volume(self._master * 0.48)
        channel.play(snd)

    # ------------------------------------------------------------------
    # Event handlers

    def _on_hull(self, amount, **_):
        if amount > 5:
            self._play_sfx("hull", 0.82)

    def _on_clang(self, **_):   self._play_sfx("clang")
    def _on_snap(self, **_):    self._play_sfx("snap")
    def _on_gun(self, **_):     self._play_sfx("gun", 0.62)
    def _on_death(self, **_):   self._play_sfx("death", 0.90)
    def _on_slingshot(self, **_): self._play_sfx("slingshot", 0.80)
    def _on_canister(self, **_):  self._play_sfx("canister", 0.70)

    def _on_spore(self, active, **_):
        if active:
            self._play_sfx("spore", 0.75)

    def _on_barge_nearby(self, distance=0, **_):
        ch = self._bax_v_ch
        if ch and not ch.get_busy():
            self._play_sfx("barge", 0.65)

    def _on_bax_speak(self, line: str = "", **_):
        if not line:
            return
        self._bax_speaking  = True
        self._bax_speak_t   = 0.0
        self._bax_speak_dur = len(line) / _BAX_CHARS_PER_SEC
        self._bax_blip_cd   = 0.0

    def _on_voice_char(self, speaker: str = "", **_):
        self._play_voice_blip(speaker, self._npc_v_ch)

    def _on_jump_ready(self, **_):
        self._play_sfx("jump", 0.82)

    def _on_debt_ding(self, **_):
        self._play_sfx("debt_ding", 0.55)

    def _on_d_step(self, **_):  self._play_sfx("d_step",  0.42)
    def _on_d_hit(self,  **_):  self._play_sfx("d_hit",   0.78)
    def _on_d_done(self, **_):  self._play_sfx("d_door",  0.85)

    def _on_sector_clear(self, sector_num=0, **_):
        """Crossfade to the new sector's music pad."""
        if not self._music_pads or self._music_a is None or self._music_b is None:
            return
        next_idx = sector_num % len(self._music_pads)
        target_ch = self._music_b if self._music_active == 0 else self._music_a
        target_ch.stop()
        target_ch.set_volume(0.0)
        target_ch.play(self._music_pads[next_idx], loops=-1)
        self._music_active = 1 - self._music_active
        self._music_xfade  = 1.0

    def _on_run_start(self, **_):
        """Reset music to sector 0's pad on a fresh run."""
        if not self._music_pads or self._music_a is None or self._music_b is None:
            return
        self._music_a.stop()
        self._music_b.stop()
        self._music_a.set_volume(self._master * self._music_target_vol)
        self._music_a.play(self._music_pads[0], loops=-1)
        self._music_b.set_volume(0.0)
        self._music_active = 0
        self._music_xfade  = 0.0

    def _on_term_open(self, **_):
        self._in_terminal = True
        for ch in self._eng_ch:
            ch.set_volume(0.0)
        if self._amb_ch:
            self._amb_ch.set_volume(self._master * 0.06)
        if self._lick_ch:
            self._lick_ch.stop()
        # Duck the sector music under terminal
        if self._music_a and self._music_active == 0:
            self._music_a.set_volume(self._master * 0.18)
        elif self._music_b:
            self._music_b.set_volume(self._master * 0.18)
        self._play_sfx("beep", 0.50)

        if self._drone_ch and self._sfx.get("drone"):
            self._drone_ch.set_volume(self._master * 0.32)
            self._drone_ch.play(self._sfx["drone"], loops=-1)

    def _on_term_close(self, **_):
        self._in_terminal = False
        if self._amb_ch:
            self._amb_ch.set_volume(self._master * 0.20)
        if self._drone_ch:
            self._drone_ch.stop()
        if self._music_a and self._music_active == 0:
            self._music_a.set_volume(self._master * self._music_target_vol)
        elif self._music_b:
            self._music_b.set_volume(self._master * self._music_target_vol)
        self._lick_cd = random.uniform(8.0, 20.0)
