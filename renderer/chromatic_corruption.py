"""
Chromatic corruption — heavy post-process effects that layer ON TOP of the
existing VisualFX grade. Focuses on the "haunted CRT" signature the base
grade lacks: aggressive full-screen channel split, signal-tear glitches,
sparse static noise tiles, and an optional iframe-protection shimmer.

Designed to be ADDITIVE — does not draw vignette or baseline scanlines, since
VisualFX.apply_flight_grade() already provides those. Apply this AFTER the
base grade for layered decay.

Usage:
    self._fx = ChromaticCorruption(S.SCREEN_W, S.FLIGHT_H)
    # ... draw scene → vfx.apply_flight_grade() ...
    self._fx.apply(screen, t, dt,
                   intensity=max(0.0, (1.0 - ship.hull_pct) - 0.2),
                   iframe_active=ship.iframe_active,
                   glitch_burst=just_took_damage)
"""
from __future__ import annotations
import math
import random
import pygame


class ChromaticCorruption:
    SPLIT_OFFSET_MIN     = 2
    SPLIT_OFFSET_MAX     = 8
    SPLIT_ALPHA_BASE     = 32
    SPLIT_ALPHA_PEAK     = 95
    NOISE_FRAME_INTERVAL = 0.06
    IFRAME_SPLIT_OFFSET  = 3
    IFRAME_SPLIT_ALPHA   = 38

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self._noise_tiles  = [self._build_noise_tile() for _ in range(4)]

        # Channel tint surfaces — solid RGB, multiplied into copies
        self._red_tint  = pygame.Surface((w, h))
        self._red_tint.fill((255, 60, 60))
        self._blue_tint = pygame.Surface((w, h))
        self._blue_tint.fill((50, 90, 255))

        # Lazy working buffers
        self._work_r: pygame.Surface | None = None
        self._work_b: pygame.Surface | None = None

        # Animation state
        self._noise_idx = 0
        self._noise_t   = 0.0

    # ------------------------------------------------------------------
    def _build_noise_tile(self) -> pygame.Surface:
        s = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        # ~one bright pixel per 700 — sparse signal noise, not snow
        n = (self.w * self.h) // 700
        for _ in range(n):
            x = random.randint(0, self.w - 1)
            y = random.randint(0, self.h - 1)
            v = random.randint(90, 220)
            s.set_at((x, y), (v, v, v, v))
        return s

    # ------------------------------------------------------------------
    def apply(self, target: pygame.Surface, t: float, dt: float,
              intensity: float, iframe_active: bool = False,
              glitch_burst: bool = False):
        """
        intensity: 0..1 — typically max(0, (1 - hull_pct) - 0.2)
        iframe_active: ship is in mercy window → cool blue shimmer
        glitch_burst: one-shot frame tear (call once on damage events)
        """
        intensity = max(0.0, min(1.0, intensity))

        # iframe shimmer takes priority — gentle blue chromatic doubling that
        # signals "you are protected" without screaming about it.
        if iframe_active and intensity < 0.4:
            self._iframe_shimmer(target, t)

        if intensity <= 0.04 and not glitch_burst:
            return

        # Channel split — the centerpiece of the corruption look
        if intensity > 0.06:
            offset = int(self.SPLIT_OFFSET_MIN +
                         (self.SPLIT_OFFSET_MAX - self.SPLIT_OFFSET_MIN) * intensity)
            # Subtle horizontal wobble — alive, not static
            offset += int(math.sin(t * 1.7) * intensity * 1.8)
            self._channel_split(target, max(1, offset),
                                self.SPLIT_ALPHA_BASE +
                                int((self.SPLIT_ALPHA_PEAK - self.SPLIT_ALPHA_BASE) * intensity))

        # Static signal noise — sparse, only at moderate+ corruption
        if intensity > 0.28:
            self._noise_t += dt
            if self._noise_t >= self.NOISE_FRAME_INTERVAL:
                self._noise_t = 0.0
                self._noise_idx = (self._noise_idx + 1) % len(self._noise_tiles)
            tile = self._noise_tiles[self._noise_idx]
            alpha = int(22 + 70 * ((intensity - 0.28) / 0.72))
            tile.set_alpha(min(255, alpha))
            target.blit(tile, (0, 0))

        # Glitch tears — signal cuts. Sparse but impactful.
        if intensity > 0.45 or glitch_burst:
            base_prob = max(0.0, (intensity - 0.45) / 0.55 * 0.14)
            prob      = 0.55 if glitch_burst else base_prob
            if random.random() < prob:
                self._glitch_tear(target, max_offset=int(10 + intensity * 32))
                # Stacking tears at high intensity sells the "signal collapse"
                if intensity > 0.72 and random.random() < 0.45:
                    self._glitch_tear(target, max_offset=int(10 + intensity * 32))

    # ------------------------------------------------------------------
    def _channel_split(self, target: pygame.Surface, offset: int, alpha: int):
        if self._work_r is None:
            self._work_r = pygame.Surface(target.get_size())
            self._work_b = pygame.Surface(target.get_size())

        self._work_r.blit(target, (0, 0))
        self._work_b.blit(target, (0, 0))
        self._work_r.blit(self._red_tint,  (0, 0),
                          special_flags=pygame.BLEND_RGB_MULT)
        self._work_b.blit(self._blue_tint, (0, 0),
                          special_flags=pygame.BLEND_RGB_MULT)

        alpha = max(0, min(255, alpha))
        self._work_r.set_alpha(alpha)
        self._work_b.set_alpha(alpha)

        target.blit(self._work_r, ( offset, 0), special_flags=pygame.BLEND_RGB_ADD)
        target.blit(self._work_b, (-offset, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _iframe_shimmer(self, target: pygame.Surface, t: float):
        # Gentle, fast-pulsing blue chromatic doubling. Communicates "shielded"
        # without obscuring gameplay. Uses only the blue tint so it reads cool.
        if self._work_b is None:
            self._work_b = pygame.Surface(target.get_size())
        self._work_b.blit(target, (0, 0))
        self._work_b.blit(self._blue_tint, (0, 0),
                          special_flags=pygame.BLEND_RGB_MULT)
        pulse = 0.5 + 0.5 * math.sin(t * 18.0)
        alpha = int(self.IFRAME_SPLIT_ALPHA * (0.55 + 0.45 * pulse))
        self._work_b.set_alpha(alpha)
        target.blit(self._work_b, ( self.IFRAME_SPLIT_OFFSET, 0),
                    special_flags=pygame.BLEND_RGB_ADD)
        target.blit(self._work_b, (-self.IFRAME_SPLIT_OFFSET, 0),
                    special_flags=pygame.BLEND_RGB_ADD)

    def _glitch_tear(self, target: pygame.Surface, max_offset: int):
        slice_h    = random.randint(4, 18)
        y          = random.randint(0, max(0, self.h - slice_h))
        slice_surf = target.subsurface((0, y, self.w, slice_h)).copy()
        dx         = random.randint(-max_offset, max_offset)
        # Black gap above the tear sells the "signal cut" feel
        gap = pygame.Surface((self.w, 2))
        gap.fill((0, 0, 0))
        target.blit(gap, (0, max(0, y - 1)))
        target.blit(slice_surf, (dx, y))
