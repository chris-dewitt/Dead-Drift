"""
audio_dev.py — Dead Drift audio debug console.

Boots in ~1s (no NLTK, no game loop). Gives you interactive control
over every audio cue and parameter so you can hear things without playing.

Controls:
  1-8     Set scene  (1=menu 2=flight 3=terminal 4=delivery 5=shop 6=decanting 7=loadout 8=interstitial)
  Q/A     Pressure -0.1 / +0.1   (drives BPM, kit intensity, arp gate)
  W/S     Hull % +10 / -10
  C 1-4   Load chapter  (e.g. press C then 1)
  E       Fire EVT_SLINGSHOT (musical stinger + pad modulation)
  T       Fire EVT_TETHER_SNAP (snare flam + pad open)
  B       Fire EVT_BARGE_NEARBY (motif drone toggle)
  D       Fire EVT_SHIP_DESTROYED (death sting + band stop)
  H       Fire harp lick (cycles through all 30)
  M       Cycle lick mood (cocky / weary / panic / delighted / lonely / sarcastic)
  F       Toggle master FX on/off
  R       Toggle SCENE_RADIO
  X       Exit
"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pygame
from core.event_bus import (
    bus, EVT_SLINGSHOT, EVT_TETHER_SNAP, EVT_BARGE_NEARBY,
    EVT_SHIP_DESTROYED, EVT_HULL_DAMAGE,
)
from audio.audio_manager import (
    AudioManager,
    SCENE_MENU, SCENE_FLIGHT, SCENE_TERMINAL, SCENE_DELIVERY,
    SCENE_SHOP, SCENE_DECANTING, SCENE_LOADOUT, SCENE_INTERSTITIAL, SCENE_RADIO,
)
from audio.blues_licks import generate_lick

_SCENES = [
    SCENE_MENU, SCENE_FLIGHT, SCENE_TERMINAL, SCENE_DELIVERY,
    SCENE_SHOP, SCENE_DECANTING, SCENE_LOADOUT, SCENE_INTERSTITIAL,
]
_SCENE_LABELS = ["menu", "flight", "terminal", "delivery",
                 "shop", "decanting", "loadout", "interstitial"]
_MOODS = ["cocky", "weary", "panic", "delighted", "lonely", "sarcastic"]

_AMBER  = (255, 176, 0)
_GREEN  = (0, 255, 128)
_RED    = (255, 50, 50)
_GREY   = (80, 80, 100)
_WHITE  = (200, 200, 200)
_DIM    = (50, 50, 60)
_VOID   = (4, 4, 8)

W, H = 720, 460


def _label(font, text, col, x, y, surf):
    surf.blit(font.render(text, True, col), (x, y))


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Dead Drift — Audio Dev Console")
    clock  = pygame.time.Clock()

    print("[audio_dev] initialising AudioManager…")
    audio = AudioManager()
    print("[audio_dev] ready. press keys to explore.")

    scene_idx   = 0
    pressure    = 0.0
    hull_pct    = 1.0
    chapter     = 1
    lick_idx    = 0
    mood_idx    = 0
    fx_enabled  = True
    barge_active = False
    await_chapter = False
    radio_on    = False

    font    = pygame.font.SysFont("monospace", 14)
    font_hd = pygame.font.SysFont("monospace", 18, bold=True)
    font_sm = pygame.font.SysFont("monospace", 11)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                k = event.key

                if await_chapter and pygame.K_1 <= k <= pygame.K_4:
                    chapter = k - pygame.K_0
                    audio.set_scene(_SCENES[scene_idx], chapter=chapter)
                    await_chapter = False
                    continue
                await_chapter = False

                if k == pygame.K_x or k == pygame.K_ESCAPE:
                    running = False

                elif pygame.K_1 <= k <= pygame.K_8:
                    scene_idx = k - pygame.K_1
                    audio.set_scene(_SCENES[scene_idx])

                elif k == pygame.K_q:
                    pressure = max(0.0, pressure - 0.1)
                elif k == pygame.K_a:
                    pressure = min(1.0, pressure + 0.1)

                elif k == pygame.K_w:
                    hull_pct = min(1.0, hull_pct + 0.1)
                elif k == pygame.K_s:
                    hull_pct = max(0.0, hull_pct - 0.1)
                    bus.emit(EVT_HULL_DAMAGE, amount=15)

                elif k == pygame.K_c:
                    await_chapter = True

                elif k == pygame.K_e:
                    bus.emit(EVT_SLINGSHOT)

                elif k == pygame.K_t:
                    bus.emit(EVT_TETHER_SNAP)

                elif k == pygame.K_b:
                    barge_active = not barge_active
                    if barge_active:
                        bus.emit(EVT_BARGE_NEARBY, distance=200)

                elif k == pygame.K_d:
                    bus.emit(EVT_SHIP_DESTROYED)

                elif k == pygame.K_h:
                    snd = generate_lick(pattern_idx=lick_idx % 30)
                    ch  = pygame.mixer.find_channel(True)
                    if ch:
                        ch.set_volume(0.7)
                        ch.play(snd)
                    lick_idx += 1

                elif k == pygame.K_m:
                    mood_idx = (mood_idx + 1) % len(_MOODS)
                    mood     = _MOODS[mood_idx]
                    snd      = generate_lick(mood=mood)
                    ch       = pygame.mixer.find_channel(True)
                    if ch:
                        ch.set_volume(0.7)
                        ch.play(snd)

                elif k == pygame.K_f:
                    fx_enabled = not fx_enabled
                    if audio._master_fx:
                        if fx_enabled:
                            audio._master_fx.install()
                        else:
                            audio._master_fx.uninstall()

                elif k == pygame.K_r:
                    radio_on = not radio_on
                    if radio_on:
                        audio.set_scene(SCENE_RADIO)
                    else:
                        audio.set_scene(_SCENES[scene_idx])

        # Sustain barge nearby signal every frame when active
        if barge_active:
            bus.emit(EVT_BARGE_NEARBY, distance=200)

        audio.update(
            speed=pressure * 520.0, dt=dt,
            hull_pct=hull_pct,
            barge_threat=1.0 if barge_active else 0.0,
            sector_idx=0,
            cargo_alarm=0.0,
        )

        # ---- Draw HUD ----
        screen.fill(_VOID)

        # Title
        _label(font_hd, "DEAD DRIFT — AUDIO DEV CONSOLE", _AMBER, 20, 14, screen)
        pygame.draw.line(screen, _DIM, (20, 38), (W - 20, 38), 1)

        # Left column: status
        lx, ly = 20, 52
        row = font.get_linesize() + 2

        def stat(label, val, col=_WHITE):
            nonlocal ly
            _label(font, f"{label:<18} {val}", col, lx, ly, screen)
            ly += row

        cur_scene = _SCENES[scene_idx] if not radio_on else "radio"
        bpm_tiers  = [84, 96, 108, 120, 128]
        tier_idx   = 0
        if pressure < 0.2: tier_idx = 0
        elif pressure < 0.4: tier_idx = 1
        elif pressure < 0.6: tier_idx = 2
        elif pressure < 0.8: tier_idx = 3
        else: tier_idx = 4

        stat("SCENE",     cur_scene.upper(), _AMBER)
        stat("CHAPTER",   str(chapter), _WHITE)
        stat("PRESSURE",  f"{pressure:.1f}  [Q-=  A+=]",
             _RED if pressure > 0.7 else _AMBER if pressure > 0.4 else _GREEN)
        stat("HULL",      f"{hull_pct*100:.0f}%  [W+  S-]",
             _RED if hull_pct < 0.3 else _AMBER if hull_pct < 0.6 else _GREEN)
        stat("BPM TIER",  f"{bpm_tiers[tier_idx]} BPM  (tier {tier_idx})", _WHITE)
        stat("BARGE",     "NEAR  [B toggle]" if barge_active else "clear  [B]",
             _RED if barge_active else _GREY)
        stat("MASTER FX", "ON  [F]" if fx_enabled else "OFF  [F]",
             _GREEN if fx_enabled else _GREY)
        stat("LICK",      f"idx {lick_idx % 30}  [H play next]", _WHITE)
        stat("MOOD",      f"{_MOODS[mood_idx]}  [M cycle+play]", _WHITE)

        # Divider
        ly += 4
        pygame.draw.line(screen, _DIM, (lx, ly), (lx + 300, ly), 1)
        ly += 8

        # Events legend
        _label(font_sm, "EVENTS:", _GREY, lx, ly, screen);  ly += 16
        for line in [
            "E = slingshot stinger + pad +5th (4 bars)",
            "T = tether snap → pad open + bass walk",
            "B = barge motif drone (toggle)",
            "D = death sting + band stop",
            "H = play next harp lick (0-29)",
            "M = cycle mood filter + play lick",
        ]:
            _label(font_sm, line, _GREY, lx + 4, ly, screen);  ly += 14

        ly += 6
        _label(font_sm, "SCENES: 1=menu 2=flight 3=terminal 4=delivery", _DIM, lx, ly, screen); ly += 14
        _label(font_sm, "        5=shop  6=decanting 7=loadout 8=intersit", _DIM, lx, ly, screen); ly += 14
        _label(font_sm, "C then 1-4 = load chapter palette", _DIM, lx, ly, screen); ly += 14
        _label(font_sm, "R = cockpit radio scene", _DIM, lx, ly, screen); ly += 14
        _label(font_sm, "X / ESC = quit", _DIM, lx, ly, screen)

        # Right column: pressure bar + hull bar
        rx, ry = 440, 52
        bar_h = 180

        # Pressure
        _label(font_sm, "PRESSURE", _AMBER, rx, ry - 14, screen)
        pygame.draw.rect(screen, _DIM, (rx, ry, 28, bar_h))
        fill_h = int(bar_h * pressure)
        col = _RED if pressure > 0.7 else _AMBER if pressure > 0.4 else _GREEN
        pygame.draw.rect(screen, col, (rx, ry + bar_h - fill_h, 28, fill_h))
        # BPM tier marks
        for i, frac in enumerate([0.2, 0.4, 0.6, 0.8]):
            my = ry + bar_h - int(bar_h * frac)
            pygame.draw.line(screen, (100, 100, 100), (rx + 28, my), (rx + 36, my), 1)
            _label(font_sm, str(bpm_tiers[i + 1 if i < 4 else 4]), _GREY, rx + 38, my - 6, screen)

        # Hull
        _label(font_sm, "HULL", _AMBER, rx + 80, ry - 14, screen)
        pygame.draw.rect(screen, _DIM, (rx + 80, ry, 28, bar_h))
        fill_h_h = int(bar_h * hull_pct)
        hcol = _RED if hull_pct < 0.3 else _AMBER if hull_pct < 0.6 else _GREEN
        pygame.draw.rect(screen, hcol, (rx + 80, ry + bar_h - fill_h_h, 28, fill_h_h))
        for frac, lbl in [(0.3, "30%"), (0.6, "60%")]:
            my = ry + bar_h - int(bar_h * frac)
            pygame.draw.line(screen, (100, 100, 100), (rx + 108, my), (rx + 116, my), 1)
            _label(font_sm, lbl, _GREY, rx + 118, my - 6, screen)

        # Chapter badges
        cx2, cy2 = rx, ry + bar_h + 30
        _label(font_sm, "CHAPTER  (press C then 1-4)", _AMBER, cx2, cy2 - 14, screen)
        for i in range(1, 5):
            bx = cx2 + (i - 1) * 52
            bc = _AMBER if i == chapter else _DIM
            pygame.draw.rect(screen, (20, 15, 5) if i == chapter else (10, 10, 15),
                             (bx, cy2, 44, 26))
            pygame.draw.rect(screen, bc, (bx, cy2, 44, 26), 1)
            _label(font, f"CH.{i}", bc, bx + 6, cy2 + 6, screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
