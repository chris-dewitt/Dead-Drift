from __future__ import annotations
import random
import pygame
from core.event_bus import (bus, EVT_HULL_DAMAGE, EVT_TETHER_HIT, EVT_TETHER_SNAP,
                             EVT_GUN_FIRE, EVT_TERMINAL_OPEN, EVT_TERMINAL_CLOSE,
                             EVT_SPORE_INVERTED)
from audio.synth import (engine_drone, ambient_static, gun_shot,
                          hull_impact, tether_clang, tether_snap,
                          terminal_beep, spore_sting)
from audio.blues_licks import prebuild_all

_N_TIERS   = 5
_SPEED_BP  = [0.0, 120.0, 240.0, 380.0, 520.0]
_ENG_CH    = 0   # channels 0-4: engine tiers
_AMB_CH    = 5
_LICK_CH   = 6   # dedicated channel for blues licks
_SFX_START = 7


class AudioManager:
    """
    Procedural space-blues audio — no asset files required.
    Engine: 5 numpy drone loops crossfaded by ship speed.
    Blues licks: random harmonica ditties every 22-55s during flight.
    Ambient: looping deep-space static.
    SFX: event-driven one-shots.
    """

    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.set_num_channels(20)

        self._eng_ch:   list[pygame.mixer.Channel] = []
        self._eng_snd:  list[pygame.mixer.Sound]   = []
        self._amb_ch:   pygame.mixer.Channel | None = None
        self._lick_ch:  pygame.mixer.Channel | None = None
        self._licks:    list[pygame.mixer.Sound]   = []
        self._sfx:      dict[str, pygame.mixer.Sound] = {}

        self._master      = 0.70
        self._in_terminal = False
        self._lick_cd     = random.uniform(18.0, 38.0)

        self._build()
        self._start_loops()
        self._wire()

    def _build(self):
        print("[audio] generating engine tones…", flush=True)
        for tier in range(_N_TIERS):
            self._eng_snd.append(engine_drone(tier))
        self._sfx["ambient"] = ambient_static()
        self._sfx["gun"]     = gun_shot()
        self._sfx["hull"]    = hull_impact()
        self._sfx["clang"]   = tether_clang()
        self._sfx["snap"]    = tether_snap()
        self._sfx["beep"]    = terminal_beep()
        self._sfx["spore"]   = spore_sting()
        print("[audio] generating blues licks…", flush=True)
        self._licks = prebuild_all()
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

        self._lick_ch = pygame.mixer.Channel(_LICK_CH)

    def _wire(self):
        bus.subscribe(EVT_HULL_DAMAGE,    self._on_hull)
        bus.subscribe(EVT_TETHER_HIT,     self._on_clang)
        bus.subscribe(EVT_TETHER_SNAP,    self._on_snap)
        bus.subscribe(EVT_GUN_FIRE,       self._on_gun)
        bus.subscribe(EVT_TERMINAL_OPEN,  self._on_term_open)
        bus.subscribe(EVT_TERMINAL_CLOSE, self._on_term_close)
        bus.subscribe(EVT_SPORE_INVERTED, self._on_spore)

    # ------------------------------------------------------------------
    def update(self, speed: float, dt: float = 0.016):
        if self._in_terminal:
            return
        self._update_engine(speed)
        self._tick_licks(dt)

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
            self._lick_ch.set_volume(self._master * 0.55)
            self._lick_ch.play(lick)
            self._lick_cd = random.uniform(22.0, 55.0)

    # ------------------------------------------------------------------
    def _play_sfx(self, key: str, vol_scale: float = 1.0):
        snd = self._sfx.get(key)
        if snd:
            ch = pygame.mixer.find_channel(True)
            if ch:
                ch.set_volume(self._master * vol_scale)
                ch.play(snd)

    def _on_hull(self, amount, **_):
        if amount > 5:
            self._play_sfx("hull", 0.82)

    def _on_clang(self, **_):  self._play_sfx("clang")
    def _on_snap(self, **_):   self._play_sfx("snap")
    def _on_gun(self, **_):    self._play_sfx("gun", 0.62)
    def _on_spore(self, active, **_):
        if active:
            self._play_sfx("spore", 0.75)

    def _on_term_open(self, **_):
        self._in_terminal = True
        for ch in self._eng_ch:
            ch.set_volume(0.0)
        if self._amb_ch:
            self._amb_ch.set_volume(self._master * 0.06)
        if self._lick_ch:
            self._lick_ch.stop()
        self._play_sfx("beep", 0.50)

    def _on_term_close(self, **_):
        self._in_terminal = False
        if self._amb_ch:
            self._amb_ch.set_volume(self._master * 0.20)
        self._lick_cd = random.uniform(8.0, 20.0)   # resume soon after terminal
