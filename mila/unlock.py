from pathlib import Path

from mila.constants import BIN_DIR, CE_INSTALLER, LAUNCH_BAT, LIBERATOR_API_URL, LIBERATOR_GLOB
from mila.style import C, clear, cyn, line, screen_header, step_fail, step_warn
from mila.input import go_back, select
from mila.spinner import Spinner
from mila.depot import fetch_to, github_asset
from mila.throwback import write_launch_bat
from mila.manifest import display_name, installed_downloads


def cheat_engine_missing() -> None:
    step_fail("Cheat Engine not found")
    line(f"Download the Windows version from {cyn('cheatengine.org')}, move to {BIN_DIR.name}/ and rename to {CE_INSTALLER.name}")


def ensure_liberator() -> Path | None:
    existing = sorted(BIN_DIR.glob(LIBERATOR_GLOB))
    with Spinner("Fetching Liberator") as sp:
        try:
            _, url = github_asset(LIBERATOR_API_URL, ".exe")
        except Exception as e:
            if existing:
                sp.succeed("Liberator ready")
                return existing[-1]
            sp.fail(f"Liberator download failed — {e}")
            return None
        dest = BIN_DIR / url.rsplit("/", 1)[-1]
        if dest.exists():
            sp.succeed("Liberator ready")
            return dest
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        try:
            fetch_to(url, dest)
        except Exception as e:
            sp.fail(f"Liberator download failed — {e}")
            dest.unlink(missing_ok=True)
            return None
        for old in existing:
            if old != dest:
                old.unlink(missing_ok=True)
        sp.succeed("Liberator ready")
        return dest


def _is_enabled(target: Path) -> bool:
    bat = target / LAUNCH_BAT
    if not bat.exists():
        return False
    return b"plugins\\ct" in bat.read_bytes()


def _is_liberator(target: Path) -> bool:
    bat = target / LAUNCH_BAT
    if not bat.exists():
        return False
    return b"bin\\Liberator-" in bat.read_bytes()


def _unlock_active(target: Path) -> bool:
    return _is_enabled(target) or _is_liberator(target)


def screen_unlock(downloads: list[dict]) -> None:
    by_key = {d["key"]: d for d in downloads if "ct" in d or d.get("liberator")}
    present = [d for d in installed_downloads() if d.name in by_key]

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
            color, mark = (C.MAG, "✓") if _unlock_active(d) else (C.ORN, "✗")
            labels.append(f"{display_name(d.name, downloads):<20}{' ' * 2}{color}{mark}{C.R}")
        labels.append("Back")

        pick = select("Toggle Unlock-All", labels, current=current)
        if pick is None or pick == len(labels) - 1:
            return
        current = pick

        target = present[pick]
        download = by_key[target.name]

        if _unlock_active(target):
            write_launch_bat(target, None, None)
            continue

        if download.get("liberator"):
            liberator = ensure_liberator()
            if liberator is None:
                go_back()
                return
            write_launch_bat(target, None, liberator.name)
            continue

        if not CE_INSTALLER.exists():
            clear()
            screen_header("Toggle Unlock-All")
            cheat_engine_missing()
            go_back()
            return
        write_launch_bat(target, download["ct"])
