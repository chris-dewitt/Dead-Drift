"""
Delivery v2 I.3b — parameterized room recipes.

Each recipe returns a themed `Room` built from a chapter's existing
palette, so new rooms read as chapter-native. Recipes place the I.3a
vocabulary (springs, conveyors, crates, ?-blocks, pipes, lifts) plus
I.2 chip language (arcs teach jumps, lines mark routes, greed lines
against the grain).

Chapters call these from `build()` and slot the results between their
original rooms and the boss finale.
"""
from __future__ import annotations
import math

from delivery.corridor.base import Room
from delivery.corridor.elements import (
    FLOOR_Y, CEIL_Y, PLAYER_H,
    Platform, MovingPlatform, Ladder, Hazard, MovingHazard, ToggleBeam,
    Collectible, Secret, Checkpoint, SteamVent, SecurityBeam,
    Spring, ConveyorBelt, BreakableBlock, QuestionBlock, WarpPipe,
    TimedLift, chip_arc, chip_line,
)


def spring_yard(palette: dict, name: str, *, secret_lore: str = "",
                bax_enter_line: str = "") -> Room:
    """Vertical playground: springs to platform tiers, chip arcs that
    ARE the flight paths, a high secret for the curious."""
    length = 1400
    t1_y = FLOOR_Y - 120     # tier 1
    t2_y = CEIL_Y + 70       # tier 2 (spring-only)
    els: list = [
        Spring(220),
        Platform(360, t1_y, 130),
        *chip_arc(220, FLOOR_Y - 30, 360, t1_y - 14, n=4),
        Platform(560, t1_y - 30, 110),
        *chip_arc(420, t1_y - 16, 560, t1_y - 46, n=3),
        Spring(700),
        Platform(840, t2_y, 150),
        *chip_arc(700, FLOOR_Y - 30, 840, t2_y - 14, n=5),
        Secret(900, t2_y - 18, value=500, lore=secret_lore),
        QuestionBlock(500, FLOOR_Y - 150, contains="chips", n_chips=3),
        Hazard(640, FLOOR_Y - 8, 56, 8),
        *chip_line(960, FLOOR_Y - 20, n=4, dx=36),
        MovingHazard(1130, CEIL_Y + 40, 20, 40,
                     left=1080, right=1230, speed=75),
        Checkpoint(1290),
    ]
    return Room(length=length, palette=palette, elements=els,
                name=name, bax_enter_line=bax_enter_line)


def conveyor_gallery(palette: dict, name: str, *,
                     bax_enter_line: str = "") -> Room:
    """Belt runs — one with you, one against you (the greed line), a
    Mag-Boots ?-block for the patient."""
    length = 1500
    belt_y = FLOOR_Y - 70
    els: list = [
        ConveyorBelt(330, belt_y, 260, drift=85.0),
        *chip_line(240, belt_y - 22, n=5, dx=44),
        Hazard(500, FLOOR_Y - 8, 60, 8),
        # The counter-belt: chips are worth more effort against the grain
        ConveyorBelt(760, belt_y - 40, 240, drift=-95.0),
        *chip_line(670, belt_y - 62, n=5, dx=40),
        QuestionBlock(900, FLOOR_Y - 150, contains="magboots"),
        SteamVent(1020, FLOOR_Y, phase_offset=0.6),
        ConveyorBelt(1220, belt_y, 240, drift=100.0),
        *chip_arc(1090, FLOOR_Y - 30, 1220, belt_y - 20, n=4),
        ToggleBeam(1380, 90, FLOOR_Y - 60, period=1.6),
    ]
    return Room(length=length, palette=palette, elements=els,
                name=name, bax_enter_line=bax_enter_line)


def crate_warren(palette: dict, name: str, *, secret_lore: str = "",
                 bax_enter_line: str = "") -> Room:
    """Breakables maze — sprint-through walls with chips behind each,
    a hardhat ?-block, and a secret pocket behind the last crate."""
    length = 1300
    els: list = [
        *chip_line(150, FLOOR_Y - 20, n=3, dx=34),
        BreakableBlock(420, chips=2),
        QuestionBlock(560, FLOOR_Y - 150, contains="hardhat"),
        SteamVent(660, FLOOR_Y, phase_offset=1.1),
        BreakableBlock(800, chips=2),
        Hazard(870, FLOOR_Y - 8, 50, 8),
        *chip_line(920, FLOOR_Y - 20, n=3, dx=34),
        BreakableBlock(1080, chips=3),
        Secret(1150, FLOOR_Y - 26, value=500, lore=secret_lore),
        Checkpoint(1230),
    ]
    return Room(length=length, palette=palette, elements=els,
                name=name, bax_enter_line=bax_enter_line)


def lift_shaft(palette: dict, name: str, *,
               bax_enter_line: str = "") -> Room:
    """Timed lifts to an upper track; the ladder is the slow, safe way."""
    length = 1200
    top_y = CEIL_Y + 70
    els: list = [
        TimedLift(300, y_top=top_y + 10, y_bot=FLOOR_Y - 40, speed=60),
        Ladder(180, top_y, FLOOR_Y - 10),
        Platform(470, top_y, 130),
        *chip_arc(320, top_y + 2, 470, top_y - 14, n=3),
        ToggleBeam(600, 80, top_y + 46, period=1.4),
        Platform(720, top_y, 130),
        TimedLift(900, y_top=top_y + 10, y_bot=FLOOR_Y - 40, speed=75),
        *chip_line(690, top_y - 22, n=4, dx=36),
        QuestionBlock(840, FLOOR_Y - 150, contains="chips", n_chips=3),
        *chip_line(1000, FLOOR_Y - 20, n=3, dx=36),
        Checkpoint(1130),
    ]
    return Room(length=length, palette=palette, elements=els,
                name=name, bax_enter_line=bax_enter_line)


def pipe_junction(palette: dict, name: str, *, secret_lore: str = "",
                  bax_enter_line: str = "") -> Room:
    """Warp pipes offer a skip over the hazard yard — but the chips and
    the stim soles live INSIDE the yard. Skipping is the trade."""
    length = 1400
    els: list = [
        *chip_line(160, FLOOR_Y - 20, n=3, dx=34),
        WarpPipe(350, exit_x=1090),           # the skip
        # The hazard yard the pipe skips:
        SteamVent(520, FLOOR_Y, phase_offset=0.0),
        Hazard(620, FLOOR_Y - 8, 54, 8),
        SecurityBeam(700, CEIL_Y + 12, length=230, phase=0.0),
        *chip_line(540, FLOOR_Y - 20, n=6, dx=40),
        QuestionBlock(760, FLOOR_Y - 150, contains="stimsoles"),
        SteamVent(880, FLOOR_Y, phase_offset=1.4),
        Secret(960, FLOOR_Y - 26, value=500, lore=secret_lore),
        WarpPipe(1120, exit_x=380),           # the regret pipe (go back)
        *chip_line(1180, FLOOR_Y - 20, n=3, dx=34),
        Checkpoint(1310),
    ]
    return Room(length=length, palette=palette, elements=els,
                name=name, bax_enter_line=bax_enter_line)


def chase_sweep(palette: dict, name: str, *, speed: float = 150.0,
                bax_enter_line: str = "") -> Room:
    """I.3.4 — the one auto-scroll room in the campaign. The building
    sweeps you out; crates must be sprinted through UNDER pressure."""
    length = 2100
    els: list = [
        *chip_line(220, FLOOR_Y - 20, n=4, dx=40),
        Hazard(400, FLOOR_Y - 8, 50, 8),
        Platform(520, FLOOR_Y - 90, 120),
        *chip_arc(400, FLOOR_Y - 30, 520, FLOOR_Y - 104, n=4),
        BreakableBlock(760, chips=2),
        Spring(900),
        Platform(1040, CEIL_Y + 90, 140),
        *chip_arc(900, FLOOR_Y - 30, 1040, CEIL_Y + 76, n=5),
        Hazard(1160, FLOOR_Y - 8, 60, 8),
        BreakableBlock(1350, chips=2),
        *chip_line(1450, FLOOR_Y - 20, n=5, dx=40),
        SteamVent(1650, FLOOR_Y, phase_offset=0.4),
        *chip_line(1800, FLOOR_Y - 20, n=4, dx=40),
    ]
    return Room(length=length, palette=palette, elements=els,
                name=name, auto_scroll=speed,
                bax_enter_line=bax_enter_line)
