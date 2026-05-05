from __future__ import annotations
import os
import pygame
from core.event_bus import bus, EVT_BAX_SPEAK, EVT_HULL_DAMAGE, EVT_TETHER_HIT
from config import settings as S


class AudioManager:
    """
    Diegetic audio routing.
    All ship sounds come through the distorted dashboard speaker channel.
    Terminal phase: engine audio cuts, replaced by server fan hum + keyboard clacks.
    """

    def __init__(self):
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._music_vol  = 0.6
        self._sfx_vol    = 0.8
        self._in_terminal = False

        bus.subscribe(EVT_BAX_SPEAK,   self._on_bax_speak)
        bus.subscribe(EVT_HULL_DAMAGE, self._on_hull_damage)
        bus.subscribe(EVT_TETHER_HIT,  self._on_tether_hit)

    # ------------------------------------------------------------------
    def load_sound(self, key: str, filepath: str) -> bool:
        if not os.path.exists(filepath):
            return False
        self._sounds[key] = pygame.mixer.Sound(filepath)
        return True

    def play(self, key: str, volume: float | None = None):
        snd = self._sounds.get(key)
        if snd:
            snd.set_volume(volume if volume is not None else self._sfx_vol)
            snd.play()

    def play_music(self, filepath: str, loop: bool = True):
        if not os.path.exists(filepath):
            return
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.set_volume(self._music_vol)
        pygame.mixer.music.play(-1 if loop else 0)

    def stop_music(self):
        pygame.mixer.music.stop()

    # ------------------------------------------------------------------
    def enter_terminal(self):
        """Cut flight audio, start server fan hum."""
        self._in_terminal = True
        pygame.mixer.music.set_volume(0.0)
        self.play("server_fan")

    def exit_terminal(self):
        self._in_terminal = False
        pygame.mixer.music.set_volume(self._music_vol)

    # ------------------------------------------------------------------
    def _on_bax_speak(self, line, **_):
        self.play("bax_static", volume=0.5)

    def _on_hull_damage(self, amount, **_):
        if amount > 10:
            self.play("hull_impact")

    def _on_tether_hit(self, **_):
        self.play("harpoon_lock")
