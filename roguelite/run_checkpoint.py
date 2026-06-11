"""Mid-run checkpoint save/load for flight, shop, and loadout states."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import settings as S
from physics.body import RigidBody2D, Vec2
from physics.gravity import GravityWell, ThreeBodySystem
from roguelite.procedural import SectorLayout

CHECKPOINT_VERSION = 1


def _vec(d: dict) -> Vec2:
    return Vec2(float(d["x"]), float(d["y"]))


def _vec_dict(v: Vec2) -> dict:
    return {"x": v.x, "y": v.y}


# ---------------------------------------------------------------------------
# Cargo
# ---------------------------------------------------------------------------

def _cargo_to_dict(cargo) -> dict | None:
    if cargo is None:
        return None
    t = type(cargo).__name__
    d: dict[str, Any] = {
        "type": t,
        "integrity": cargo.integrity,
        "is_damaged": cargo.is_damaged,
    }
    if t == "EpistemologicalShrooms":
        d.update({
            "spore_level": cargo.spore_level,
            "invert_active": cargo._invert_active,
            "invert_t": cargo._invert_t,
            "next_cd": cargo._next_cd,
        })
    elif t == "AcousticArchive":
        d["sorrow_level"] = getattr(cargo, "sorrow_level", 0.0)
    elif t == "SentientPaperwork":
        d.update({
            "forms_filed": getattr(cargo, "_forms_filed", 0),
            "next_trigger": getattr(cargo, "_next_trigger", 0.0),
        })
    elif t == "SchrodingerVIP":
        d["alive_state"] = getattr(cargo, "alive_state", "unknown")
    elif t == "EncryptedDrive":
        d["trace_level"] = getattr(cargo, "trace_level", 0.0)
        d["ping_t"] = getattr(cargo, "_ping_t", 0.0)
    return d


def _cargo_from_dict(d: dict | None):
    if d is None:
        return None
    from cargo.acoustic_archive import AcousticArchive
    from cargo.epi_shrooms import EpistemologicalShrooms
    from cargo.paperwork import SentientPaperwork
    from cargo.schrodinger_vip import SchrodingerVIP
    from cargo.encrypted_drive import EncryptedDrive

    factories = {
        "AcousticArchive": AcousticArchive,
        "EpistemologicalShrooms": EpistemologicalShrooms,
        "SentientPaperwork": SentientPaperwork,
        "SchrodingerVIP": SchrodingerVIP,
        "EncryptedDrive": EncryptedDrive,
    }
    cls = factories.get(d["type"])
    if cls is None:
        return None
    c = cls()
    c.integrity = float(d.get("integrity", 100.0))
    c.is_damaged = bool(d.get("is_damaged", False))
    if d["type"] == "EpistemologicalShrooms":
        c.spore_level = float(d.get("spore_level", 0.0))
        c._invert_active = bool(d.get("invert_active", False))
        c._invert_t = float(d.get("invert_t", 0.0))
        c._next_cd = float(d.get("next_cd", 30.0))
    elif d["type"] == "AcousticArchive":
        c.sorrow_level = float(d.get("sorrow_level", 0.0))
    elif d["type"] == "SentientPaperwork":
        c._forms_filed = int(d.get("forms_filed", 0))
        c._next_trigger = float(d.get("next_trigger", 20.0))
    elif d["type"] == "SchrodingerVIP":
        c.alive_state = d.get("alive_state", "unknown")
    elif d["type"] == "EncryptedDrive":
        c.trace_level = float(d.get("trace_level", 0.0))
        c._ping_t = float(d.get("ping_t", 0.0))
    return c


# ---------------------------------------------------------------------------
# Ship
# ---------------------------------------------------------------------------

def _ship_to_dict(ship) -> dict:
    from ship.modules.thruster import Thruster
    from ship.modules.life_support import LifeSupport

    modules = []
    for i, mod in enumerate(ship.chain.slots):
        if mod is None:
            continue
        ent: dict[str, Any] = {"slot": i, "kind": type(mod).__name__}
        if isinstance(mod, Thruster):
            tier = "salvage"
            for tag in mod.tags:
                if tag in ("salvage", "standard", "military"):
                    tier = tag
                    break
            ent["tier"] = tier
            ent["name"] = mod.name
            ent["integrity"] = mod.integrity
            ent["heat"] = mod.heat
            ent["overheated"] = mod.overheated
        elif isinstance(mod, LifeSupport):
            ent["integrity"] = mod.integrity
        else:
            ent["name"] = getattr(mod, "name", "MODULE")
            ent["integrity"] = getattr(mod, "integrity", 100.0)
        modules.append(ent)

    bullets = [
        {
            "x": b.pos.x, "y": b.pos.y,
            "vx": b.vel.x, "vy": b.vel.y,
            "life": b.lifetime,
            "damage": getattr(b, "damage", 1),
        }
        for b in ship.gun.bullets
    ]
    return {
        "pos": _vec_dict(ship.body.pos),
        "vel": _vec_dict(ship.body.vel),
        "angle": ship.body.angle,
        "mass": ship.body.mass,
        "hull": ship.hull,
        "fuel": getattr(ship, "fuel", S.FUEL_MAX),
        "destroyed": ship._destroyed,
        "controls_inverted": ship.controls_inverted,
        "cargo": _cargo_to_dict(ship.cargo),
        "modules": modules,
        "gun": {
            "cooldown": ship.gun._cooldown,
            "jam_t": ship.gun._jam_t,
            "fire_rate_mult": getattr(ship.gun, "fire_rate_mult", 1.0),
            "damage_mult": getattr(ship.gun, "damage_mult", 1),
            "bullets": bullets,
        },
    }


def _restore_ship(ship, d: dict) -> None:
    from ship.gun import Bullet
    from ship.modules.life_support import LifeSupport
    from ship.modules.thruster import Thruster

    ship.body.pos = _vec(d["pos"])
    ship.body.vel = _vec(d["vel"])
    ship.body.angle = float(d["angle"])
    ship.body.mass = float(d.get("mass", S.SHIP_MASS))
    ship.hull = float(d["hull"])
    ship.fuel = float(d.get("fuel", S.FUEL_MAX))
    ship._destroyed = bool(d.get("destroyed", False))
    ship.controls_inverted = bool(d.get("controls_inverted", False))
    ship.cargo = _cargo_from_dict(d.get("cargo"))

    for slot in range(ship.chain.MAX_SLOTS):
        ship.chain.remove(slot)
    ship.chain.install(LifeSupport(), 0)
    for ent in d.get("modules", []):
        slot = int(ent["slot"])
        if ent.get("kind") == "Thruster":
            mod = Thruster(ent.get("name", "THRUSTER"), tier=ent.get("tier", "salvage"))
            mod.integrity = float(ent.get("integrity", 100.0))
            mod.heat = float(ent.get("heat", 0.0))
            mod.overheated = bool(ent.get("overheated", False))
            ship.chain.install(mod, slot)
        elif ent.get("kind") == "LifeSupport":
            ls = LifeSupport()
            ls.integrity = float(ent.get("integrity", 100.0))
            ship.chain.install(ls, slot)

    g = d.get("gun", {})
    ship.gun._cooldown = float(g.get("cooldown", 0.0))
    ship.gun._jam_t = float(g.get("jam_t", 0.0))
    ship.gun.fire_rate_mult = float(g.get("fire_rate_mult", 1.0))
    ship.gun.damage_mult = int(g.get("damage_mult", 1))
    ship.gun.bullets.clear()
    for b in g.get("bullets", []):
        bul = Bullet(_vec({"x": b["x"], "y": b["y"]}), 0.0,
                     damage=int(b.get("damage", 1)))
        bul.vel = _vec({"x": b["vx"], "y": b["vy"]})
        bul.lifetime = float(b["life"])
        ship.gun.bullets.append(bul)


# ---------------------------------------------------------------------------
# Sector layout
# ---------------------------------------------------------------------------

def _sector_to_dict(sector: SectorLayout) -> dict:
    wells = []
    for w in sector.gravity.wells:
        wells.append({
            "x": w.pos.x, "y": w.pos.y,
            "vx": w.vel.x, "vy": w.vel.y,
            "mass": w.mass, "radius": w.radius,
        })
    return {
        "index": sector.index,
        "theme": sector.theme,
        "name": sector.name,
        "formerly": sector.formerly,
        "hazards": list(sector.hazards),
        "enemy_budget": sector.enemy_budget,
        "is_ambush": sector.is_ambush,
        "wells": wells,
    }


def _sector_from_dict(d: dict) -> SectorLayout:
    wells = []
    for w in d.get("wells", []):
        gw = GravityWell(w["x"], w["y"], w["mass"], w.get("radius", 60.0))
        gw.vel = Vec2(w.get("vx", 0.0), w.get("vy", 0.0))
        wells.append(gw)
    return SectorLayout(
        index=int(d["index"]),
        gravity=ThreeBodySystem(wells),
        hazards=list(d.get("hazards", [])),
        enemy_budget=int(d.get("enemy_budget", 1)),
        is_ambush=bool(d.get("is_ambush", False)),
        theme=d.get("theme", ""),
        name=d.get("name", ""),
        formerly=d.get("formerly", ""),
    )


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

def _debris_dict(r) -> dict:
    return {
        "t": "debris",
        "x": r.pos.x, "y": r.pos.y,
        "vx": r.vel.x, "vy": r.vel.y,
        "angle": r.angle, "rot": r.rot_speed,
        "radius": r.radius, "hp": r.hp,
    }


def _debris_from(d: dict):
    from antagonists.debris import DebrisRock
    r = DebrisRock(d["x"], d["y"])
    r.vel = Vec2(d["vx"], d["vy"])
    r.angle = float(d["angle"])
    r.rot_speed = float(d["rot"])
    r.radius = int(d["radius"])
    r.hp = int(d["hp"])
    return r


def _canister_dict(c) -> dict:
    return {
        "t": "canister",
        "x": c.pos.x, "y": c.pos.y,
        "picked": c.picked_up,
        "phase": c._phase,
    }


def _canister_from(d: dict):
    from antagonists.fuel_canister import FuelCanister
    c = FuelCanister(d["x"], d["y"])
    c.picked_up = bool(d.get("picked", False))
    c._phase = float(d.get("phase", 0.0))
    return c


def _satellite_dict(s) -> dict:
    return {
        "t": "satellite",
        "x": s.pos.x, "y": s.pos.y,
        "vx": s.vel.x, "vy": s.vel.y,
        "angle": s.angle,
    }


def _satellite_from(d: dict):
    from antagonists.satellite import SpinningSatellite
    s = SpinningSatellite(d["x"], d["y"])
    s.vel = Vec2(d["vx"], d["vy"])
    s.angle = float(d.get("angle", 0.0))
    return s


def _barge_dict(b) -> dict:
    return {
        "t": "barge",
        "x": b.body.pos.x, "y": b.body.pos.y,
        "vx": b.body.vel.x, "vy": b.body.vel.y,
        "angle": b.body.angle,
        "state": b.state,
        "hp": b._hp,
        "destroyed": b.is_destroyed,
        "retreat_t": b._retreat_t,
        "intercept_cd": b._intercept_cd,
        "aim_t": b._aim_t,
    }


def _barge_from(d: dict, run_mgr):
    from antagonists.repo_barge import RepoBarge
    b = RepoBarge(d["x"], d["y"], run_mgr)
    b.body.vel = Vec2(d["vx"], d["vy"])
    b.body.angle = float(d.get("angle", 0.0))
    b.state = d.get("state", b.state)
    b._hp = float(d.get("hp", 60.0))
    b.is_destroyed = bool(d.get("destroyed", False))
    b._retreat_t = float(d.get("retreat_t", 0.0))
    b._intercept_cd = float(d.get("intercept_cd", 0.0))
    b._aim_t = float(d.get("aim_t", 0.0))
    return b


def _alien_dict(a) -> dict:
    return {
        "t": "alien",
        "x": a.pos.x, "y": a.pos.y,
        "vx": a.vel.x, "vy": a.vel.y,
        "heading": a.heading,
        "alive": a.alive,
    }


def _alien_from(d: dict):
    from antagonists.alien_ship import AlienShip
    a = AlienShip.__new__(AlienShip)
    a.pos = Vec2(d["x"], d["y"])
    a.vel = Vec2(d["vx"], d["vy"])
    a.heading = float(d.get("heading", 0.0))
    a.alive = bool(d.get("alive", True))
    a._trail = []
    return a


def _wreck_dict(w) -> dict:
    return {
        "t": "wreck",
        "x": w.pos.x, "y": w.pos.y,
        "subtype": getattr(w, "subtype", None),
        "angle": getattr(w, "angle", 0.0),
        "rot_speed": getattr(w, "rot_speed", 0.0),
        "length": getattr(w, "length", 160),
        "width": getattr(w, "width", 55),
        "gap_frac": getattr(w, "gap_frac", 0.5),
        "weak_hp": getattr(w, "weak_hp", 3),
        "is_triggered": getattr(w, "is_triggered", False),
        "trigger_t": getattr(w, "_trigger_t", 0.0),
    }


def _wreck_from(d: dict):
    from antagonists.wreck import SpaceWreck
    w = SpaceWreck(d.get("x"), d.get("y"), subtype=d.get("subtype"))
    w.angle = float(d.get("angle", w.angle))
    w.rot_speed = float(d.get("rot_speed", w.rot_speed))
    w.length = int(d.get("length", w.length))
    w.width = int(d.get("width", w.width))
    w.gap_frac = float(d.get("gap_frac", w.gap_frac))
    w.weak_hp = int(d.get("weak_hp", w.weak_hp))
    w.is_triggered = bool(d.get("is_triggered", w.is_triggered))
    w._trigger_t = float(d.get("trigger_t", w._trigger_t))
    return w


def _entities_to_dict(rm) -> list[dict]:
    out: list[dict] = []
    for r in rm._debris:
        out.append(_debris_dict(r))
    for c in rm._canisters:
        out.append(_canister_dict(c))
    for s in rm._satellites:
        out.append(_satellite_dict(s))
    for b in rm._barges:
        out.append(_barge_dict(b))
    if rm._alien is not None:
        out.append(_alien_dict(rm._alien))
    if rm._dead_station is not None:
        out.append({"t": "dead_station"})
    if rm._trash_field is not None:
        out.append({"t": "trash_field"})
    if rm._mine_field is not None:
        out.append({"t": "mine_field"})
    if rm._ice_field is not None:
        out.append({"t": "ice_field"})
    if rm._comet_trail is not None:
        out.append({"t": "comet_trail"})
    for w in rm._wrecks:
        out.append(_wreck_dict(w))
    return out


def _restore_entities(rm, entities: list[dict]) -> None:
    from antagonists.comet_trail import CometTrail
    from antagonists.dead_station import DeadStation
    from antagonists.ice_field import IceField
    from antagonists.mine_field import MineField
    from antagonists.trash_field import TrashField

    rm._debris.clear()
    rm._canisters.clear()
    rm._satellites.clear()
    rm._barges.clear()
    rm._alien = None
    rm._wrecks.clear()
    rm._compliance_vessels.clear()
    rm._dead_station = None
    rm._trash_field = None
    rm._mine_field = None
    rm._ice_field = None
    rm._comet_trail = None

    for d in entities:
        t = d.get("t")
        if t == "debris":
            rm._debris.append(_debris_from(d))
        elif t == "canister":
            rm._canisters.append(_canister_from(d))
        elif t == "satellite":
            rm._satellites.append(_satellite_from(d))
        elif t == "barge":
            rm._barges.append(_barge_from(d, rm))
        elif t == "alien":
            rm._alien = _alien_from(d)
        elif t == "dead_station":
            rm._dead_station = DeadStation()
        elif t == "trash_field":
            rm._trash_field = TrashField()
        elif t == "mine_field":
            rm._mine_field = MineField()
        elif t == "ice_field":
            rm._ice_field = IceField()
        elif t == "comet_trail":
            rm._comet_trail = CometTrail()
        elif t == "wreck":
            rm._wrecks.append(_wreck_from(d))


# ---------------------------------------------------------------------------
# Run manager snapshot
# ---------------------------------------------------------------------------

def build_checkpoint(game) -> dict:
    """Serialize in-run state from a Game instance."""
    rm = game.run_mgr
    ship = game.ship
    state_name = game.states.state.name
    if game.states.state.name == "PAUSED" and game._state_before_pause is not None:
        state_name = game._state_before_pause.name

    return {
        "version": CHECKPOINT_VERSION,
        "game_state": state_name,
        "run_seed": getattr(rm, "_run_seed", 0),
        "chapter": rm._current_chapter(),
        "draft_applied": rm._sector is not None,
        "sector": _sector_to_dict(rm._sector) if rm._sector else None,
        "entities": _entities_to_dict(rm),
        "run_mgr": {
            "sector_index": rm._sector_index,
            "sector_timer": rm._sector_timer,
            "sector_dur": rm._sector_dur,
            # Aliveness hotfix: persist hardcore total time so a resumed
            # run keeps its accumulated flight seconds.
            "run_total_time": getattr(rm, "_run_total_time", 0.0),
            "jump_ready_fired": rm._jump_ready_fired,
            "pending_advance": rm._pending_advance,
            "shop_pending": rm._shop_pending,
            "spawn_queue": list(rm._spawn_queue),
            "flare_cd": rm._flare_cd,
            "flare_active": rm._flare_active,
            "flare_t": rm._flare_t,
            "toll_pending": rm._toll_pending,
            "toll_t": rm._toll_t,
            "event_cd": rm._event_cd,
            "kress_cd": rm._kress_cd,
            "collector_cd": rm._collector_cd,
            "kress_called": rm._kress_called_this_sector,
            "kress_tip_pending": getattr(rm, "_kress_tip_pending", False),
            "barge_suppression_t": getattr(rm, "_barge_suppression_t", 0.0),
            "compliance_spawn_cd": getattr(rm, "_compliance_spawn_cd", 12.0),
            "emp_burst_available": getattr(rm, "_emp_burst_available", False),
            "emp_burst_active_t": getattr(rm, "_emp_burst_active_t", 0.0),
            "run_debt_reduced": rm._run_debt_reduced,
            "run_snaps": rm._run_snaps,
            "run_slingshots": rm._run_slingshots,
            "sector_slingshots": rm._sector_slingshots,
            "sector_snaps": rm._sector_snaps,
            "sector_credits": rm._sector_credits,
            "sector_start_hull": rm._sector_start_hull,
            "last_winning_path": rm._last_winning_path,
            "alien_spoken": rm._alien_spoken,
            "well_hit_times": {str(k): v for k, v in rm._well_hit_times.items()},
        },
        "ship": _ship_to_dict(ship),
        "frame_name": getattr(rm, "_frame_name", ""),
    }


def restore_checkpoint(game, data: dict) -> bool:
    """Restore in-run state. Returns False if data is invalid."""
    if data.get("version") != CHECKPOINT_VERSION:
        return False
    rm = game.run_mgr
    ship = game.ship
    rm._run_seed = int(data.get("run_seed", 0))

    rmd = data.get("run_mgr", {})
    rm._sector_index = int(rmd.get("sector_index", 0))
    rm._sector_timer = float(rmd.get("sector_timer", 0.0))
    rm._sector_dur = float(rmd.get("sector_dur", 20.0))
    # Aliveness hotfix  default to 0.0 for pre-fix checkpoints that
    # don't have this field yet (old saves stay loadable).
    rm._run_total_time = float(rmd.get("run_total_time", 0.0))
    rm._jump_ready_fired = bool(rmd.get("jump_ready_fired", False))
    rm._pending_advance = bool(rmd.get("pending_advance", False))
    rm._shop_pending = bool(rmd.get("shop_pending", False))
    rm._spawn_queue = [tuple(x) for x in rmd.get("spawn_queue", [])]
    rm._flare_cd = float(rmd.get("flare_cd", 22.0))
    rm._flare_active = bool(rmd.get("flare_active", False))
    rm._flare_t = float(rmd.get("flare_t", 0.0))
    rm._toll_pending = bool(rmd.get("toll_pending", False))
    rm._toll_t = float(rmd.get("toll_t", 10.0))
    rm._event_cd = float(rmd.get("event_cd", 40.0))
    rm._kress_cd = float(rmd.get("kress_cd", 80.0))
    rm._collector_cd = float(rmd.get("collector_cd", 110.0))
    rm._kress_called_this_sector = bool(rmd.get("kress_called", False))
    rm._kress_tip_pending = bool(rmd.get("kress_tip_pending", False))
    rm._barge_suppression_t = float(rmd.get("barge_suppression_t", 0.0))
    rm._compliance_spawn_cd = float(rmd.get("compliance_spawn_cd", 12.0))
    rm._emp_burst_available = bool(rmd.get("emp_burst_available", False))
    rm._emp_burst_active_t = float(rmd.get("emp_burst_active_t", 0.0))
    rm._run_debt_reduced = int(rmd.get("run_debt_reduced", 0))
    rm._run_snaps = int(rmd.get("run_snaps", 0))
    rm._run_slingshots = int(rmd.get("run_slingshots", 0))
    rm._sector_slingshots = int(rmd.get("sector_slingshots", 0))
    rm._sector_snaps = int(rmd.get("sector_snaps", 0))
    rm._sector_credits = int(rmd.get("sector_credits", 0))
    rm._sector_start_hull = float(rmd.get("sector_start_hull", S.HULL_MAX))
    rm._last_winning_path = str(rmd.get("last_winning_path", ""))
    rm._alien_spoken = bool(rmd.get("alien_spoken", False))
    rm._well_hit_times = {}
    rm._active_terminal = None
    rm._intercepting_barge = None
    rm._ship = ship

    sec = data.get("sector")
    if sec:
        rm._sector = _sector_from_dict(sec)
    else:
        rm._sector = None

    _restore_entities(rm, data.get("entities", []))
    _restore_ship(ship, data.get("ship", {}))
    rm._frame_name = data.get("frame_name", "")
    return True


def save_checkpoint_file(path: Path, game) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_checkpoint(game)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_checkpoint_file(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
