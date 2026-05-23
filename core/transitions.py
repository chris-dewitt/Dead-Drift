"""
CRT power-down scene transitions.

Captures the outgoing scene as a surface, plays a horizontal-collapse
animation (TV power-off style), holds a brief black gap, then expands
the incoming scene back open. The game loop blits the transition
overlay last each frame; while a transition is active, input is
suppressed by the caller.

Phases:
    COLLAPSE  — outgoing scene vertically squashes toward a thin line
    GAP       — pure black (very short)
    SCANLINE  — bright horizontal scanline pulse
    EXPAND    — incoming scene vertically expands from the scanline

Usage from Game:
    self.transition = TransitionManager()
    # ...when changing state:
    self.transition.start(self.screen.copy())   # capture old frame
    self.states.transition(GameState.TERMINAL)
    # ...in main loop AFTER rendering current state:
    self.transition.draw(self.screen, dt)
"""
from __future__ import annotations
import pygame


# Phase timings — total ~0.55s, snappy but readable
_T_COLLAPSE  = 0.22
_T_GAP       = 0.05
_T_SCANLINE  = 0.06
_T_EXPAND    = 0.22
_T_TOTAL     = _T_COLLAPSE + _T_GAP + _T_SCANLINE + _T_EXPAND


class TransitionManager:
    def __init__(self):
        self._active: bool = False
        self._t: float = 0.0
        self._old_frame: pygame.Surface | None = None
        # Latest fully-rendered frame of the NEW scene (captured each
        # frame during EXPAND so the expand uses the live new render).
        self._latest_frame: pygame.Surface | None = None

    def start(self, old_frame: pygame.Surface):
        """Capture the outgoing scene and begin the transition."""
        self._active = True
        self._t = 0.0
        self._old_frame = old_frame.copy()
        self._latest_frame = None

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def is_blocking_input(self) -> bool:
        """True during the visually-opaque part of the transition."""
        return self._active

    @property
    def progress(self) -> float:
        if not self._active:
            return 0.0
        return min(1.0, self._t / _T_TOTAL)

    def draw(self, screen: pygame.Surface, dt: float):
        """
        Render the transition overlay on top of whatever's already on
        screen. Should be called LAST each frame, after the scene draw.
        """
        if not self._active:
            return

        W, H = screen.get_size()
        self._t += dt
        t = self._t

        # During EXPAND we capture the current (new) frame so the
        # vertical expand reveals the live new scene.
        if t >= _T_COLLAPSE + _T_GAP + _T_SCANLINE:
            self._latest_frame = screen.copy()

        # Solid black overlay underneath everything else this frame
        screen.fill((0, 0, 0))

        if t < _T_COLLAPSE:
            # COLLAPSE: old frame squashes to centre
            p = t / _T_COLLAPSE
            self._draw_squash(screen, self._old_frame, 1.0 - p)

        elif t < _T_COLLAPSE + _T_GAP:
            # GAP: pure black
            pass

        elif t < _T_COLLAPSE + _T_GAP + _T_SCANLINE:
            # SCANLINE: bright horizontal flash + fading bloom
            sl_t = (t - _T_COLLAPSE - _T_GAP) / _T_SCANLINE
            self._draw_scanline_pulse(screen, sl_t)

        elif t < _T_TOTAL:
            # EXPAND: new frame opens up from centre
            p = (t - _T_COLLAPSE - _T_GAP - _T_SCANLINE) / _T_EXPAND
            self._draw_squash(screen,
                              self._latest_frame or self._old_frame, p)
            # Trailing scanline that recedes
            if p < 0.5:
                self._draw_scanline_pulse(screen, 1.0 - p * 2)
        else:
            # DONE
            self._active = False
            self._old_frame = None
            self._latest_frame = None

    # ── internal drawing helpers ────────────────────────────────────
    @staticmethod
    def _draw_squash(screen: pygame.Surface,
                     frame: pygame.Surface,
                     openness: float):
        """Draw `frame` vertically scaled to `openness` fraction of full height,
        centred. At openness=0 it's a single horizontal line; at 1.0 it's full."""
        if frame is None or openness <= 0.0:
            return
        W, H = screen.get_size()
        squash_h = max(2, int(H * openness))
        # Slight horizontal stretch as it collapses (CRT power-off feel)
        stretch = 1.0 + (1.0 - openness) * 0.06
        squash_w = int(W * stretch)
        try:
            scaled = pygame.transform.smoothscale(frame, (squash_w, squash_h))
        except (ValueError, pygame.error):
            scaled = pygame.transform.scale(frame, (squash_w, squash_h))
        x = (W - squash_w) // 2
        y = (H - squash_h) // 2
        screen.blit(scaled, (x, y))
        # Bright edge lines top + bottom while collapsing
        edge_intensity = int(220 * (1.0 - openness))
        if edge_intensity > 20:
            pygame.draw.line(screen, (edge_intensity, edge_intensity, edge_intensity),
                             (x, y), (x + squash_w, y), 1)
            pygame.draw.line(screen, (edge_intensity, edge_intensity, edge_intensity),
                             (x, y + squash_h - 1),
                             (x + squash_w, y + squash_h - 1), 1)

    @staticmethod
    def _draw_scanline_pulse(screen: pygame.Surface, intensity: float):
        """Bright horizontal scanline pulse in the centre."""
        W, H = screen.get_size()
        cy = H // 2
        # Thin bright core
        core_alpha = max(0, min(255, int(255 * intensity)))
        bloom_alpha = max(0, min(160, int(160 * intensity)))
        if core_alpha <= 0:
            return
        # Core line
        pygame.draw.line(screen, (255, 255, 255), (0, cy), (W, cy), 1)
        pygame.draw.line(screen, (220, 220, 220), (0, cy - 1), (W, cy - 1), 1)
        pygame.draw.line(screen, (220, 220, 220), (0, cy + 1), (W, cy + 1), 1)
        # Soft bloom above + below
        bloom = pygame.Surface((W, 24), pygame.SRCALPHA)
        for off in range(-12, 13):
            a = max(0, bloom_alpha - abs(off) * 14)
            pygame.draw.line(bloom, (255, 255, 255, a),
                             (0, 12 + off), (W, 12 + off), 1)
        screen.blit(bloom, (0, cy - 12))
