from pathlib import Path

from app.constants import CHEATENGINE_EXE, LAUNCHER_EXE, STEAM_COMPATDATA
from app.style import C, clear, mag, render_header, step_fail, step_warn
from app.input import go_back, select
from app.spinner import Spinner
from app.manifest import display_name, installed_downloads
from app.steam import (
    find_existing_appid,
    proton_for_appid,
    proton_run,
    wait_for_game_closed,
)
from app.throwbackloader import read_tools, set_tools


_STATE_MARK = {
    True: f"{C.MAG}CE{C.R}",
    False: f"{C.ORN}✗{C.R}",
}


def _installed_launcher(drive_c: Path) -> Path | None:
    matches = sorted(
        drive_c.glob("Program Files*/Cheat Engine*/Cheat Engine.exe")
    )
    return matches[0] if matches else None


def _windows_path(host: Path, drive_c: Path) -> str:
    return "C:\\" + "\\".join(host.relative_to(drive_c).parts)


def _prefix_for(target: Path) -> Path | None:
    appid = find_existing_appid(target / LAUNCHER_EXE)
    if appid is None:
        return None
    prefix = STEAM_COMPATDATA / str(appid)
    return prefix if (prefix / "pfx").exists() else None


def _is_cheatengine(target: Path) -> bool:
    return any("Cheat Engine.exe" in t for t in read_tools(target))


def set_cheatengine(target: Path, path: str | None) -> None:
    tools = [t for t in read_tools(target) if "Cheat Engine.exe" not in t]
    if path:
        tools.append(path)
    set_tools(target, tools)


def _installed_path(prefix: Path) -> str | None:
    drive_c = prefix / "pfx" / "drive_c"
    launcher = _installed_launcher(drive_c)
    return _windows_path(launcher, drive_c) if launcher else None


def _install(prefix: Path) -> str | None:
    proton = proton_for_appid(int(prefix.name))
    if proton is None:
        step_fail("No Proton set for this season")
        return None
    drive_c = prefix / "pfx" / "drive_c"
    with Spinner("Installing CE") as sp:
        proton_run(proton, prefix, CHEATENGINE_EXE)
        launcher = _installed_launcher(drive_c)
        if launcher is None:
            sp.fail("CE installation not detected")
            return None
        sp.succeed("CE installed")
    return _windows_path(launcher, drive_c)


def screen_cheatengine(downloads: list[dict]) -> None:
    present = [d for d in installed_downloads() if (d / LAUNCHER_EXE).exists()]
    if not present:
        render_header("Toggle CE")
        print()
        step_warn("No downloads support CE")
        go_back()
        return

    current = 0
    while True:
        labels = [
            f"{display_name(d.name, downloads):<20}{' ' * 2}"
            f"{_STATE_MARK[_is_cheatengine(d)]}"
            for d in present
        ]
        labels.append("Back")

        pick = select("Toggle CE", labels, current=current)
        if pick is None or pick == len(labels) - 1:
            return
        current = pick

        target = present[pick]
        if _is_cheatengine(target):
            set_cheatengine(target, None)
            continue

        name = display_name(target.name, downloads)
        if not CHEATENGINE_EXE.exists():
            clear()
            render_header("Toggle CE")
            print()
            step_warn(f"Place CheatEngine.exe in {CHEATENGINE_EXE.parent}")
            go_back()
            continue

        prefix = _prefix_for(target)
        if prefix is None:
            clear()
            render_header("Toggle CE")
            print()
            step_warn("Add this season to Steam and launch it once first")
            go_back()
            continue

        existing = _installed_path(prefix)
        if existing:
            set_cheatengine(target, existing)
            continue

        clear()
        render_header(f"Toggle CE — {mag(name)}")
        if not wait_for_game_closed(mag(name)):
            continue
        path = _install(prefix)
        if path is None:
            go_back()
            continue
        set_cheatengine(target, path)
        go_back()
