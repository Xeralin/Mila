from pathlib import Path

from mila.constants import BIN_DIR, CE_INSTALLER, LAUNCH_BAT
from mila.style import C, clear, cyn, line, screen_header, step_fail, step_warn
from mila.input import go_back, select
from mila.throwback import write_launch_bat
from mila.manifest import display_name, local_downloads


def cheat_engine_missing() -> None:
    step_fail("Cheat Engine not found")
    line(f"Download the Windows version from {cyn('cheatengine.org')}, move to {BIN_DIR.name}/ and rename to {CE_INSTALLER.name}")


def _is_enabled(target: Path) -> bool:
    bat = target / LAUNCH_BAT
    if not bat.exists():
        return False
    return b"plugins\\ct" in bat.read_bytes()


def screen_unlock(downloads: list[dict]) -> None:
    by_key = {d["key"]: d for d in downloads if "ct" in d}
    present = [d for d in local_downloads() if d.name in by_key]

    if not present:
        screen_header("Toggle Unlock-All")
        print()
        step_warn("No downloads support Unlock-All")
        go_back()
        return

    current = 0
    while True:
        labels = []
        for d in present:
            color, mark = (C.MAG, "✓") if _is_enabled(d) else (C.ORN, "✗")
            labels.append(f"{display_name(d.name, downloads):<20}{' ' * 2}{color}{mark}{C.R}")
        labels.append("Back")

        pick = select("Toggle Unlock-All", labels, current=current)
        if pick is None or pick == len(labels) - 1:
            return
        current = pick

        target = present[pick]
        download = by_key[target.name]
        currently_enabled = _is_enabled(target)

        if not currently_enabled and not CE_INSTALLER.exists():
            clear()
            screen_header("Toggle Unlock-All")
            cheat_engine_missing()
            go_back()
            return

        write_launch_bat(target, None if currently_enabled else download["ct"])
