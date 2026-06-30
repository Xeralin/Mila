from pathlib import Path

from app.constants import BIN_DIR, LIBERATOR_API_URL, LIBERATOR_GLOB
from app.style import C, render_header, step_warn
from app.input import go_back, select
from app.spinner import LazySpinner, Reporter
from app.depot import fetch_to, github_asset
from app.throwbackloader import read_tools, set_tools
from app.manifest import display_name, installed_downloads


def _version_key(path: Path) -> tuple[int, tuple[int, ...], str]:
    prefix, suffix = LIBERATOR_GLOB.split("*")
    version = path.name.removeprefix(prefix).removesuffix(suffix)
    try:
        return 1, tuple(int(p) for p in version.split(".")), version
    except ValueError:
        return 0, (), version


def liberator_file() -> Path | None:
    files = sorted(BIN_DIR.glob(LIBERATOR_GLOB), key=_version_key)
    return files[-1] if files else None


def _liberator_arg(name: str) -> str:
    return f"..\\..\\bin\\{name}"


def _is_liberator(target: Path) -> bool:
    return any("\\bin\\Liberator-" in t for t in read_tools(target))


def set_liberator(target: Path, name: str | None) -> None:
    tools = [t for t in read_tools(target) if "\\bin\\Liberator-" not in t]
    if name:
        tools.append(_liberator_arg(name))
    set_tools(target, tools)


def ensure_liberator(reporter: Reporter | None = None) -> Path | None:
    existing = sorted(BIN_DIR.glob(LIBERATOR_GLOB), key=_version_key)
    with (reporter or LazySpinner()) as sp:
        sp.update("Fetching Liberator")
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
            return None
        for target in installed_downloads():
            if _is_liberator(target):
                set_liberator(target, dest.name)
        for old in existing:
            if old != dest:
                old.unlink(missing_ok=True)
        sp.succeed("Liberator ready")
        return dest


_STATE_MARK = {
    True: f"{C.MAG}Liberator{C.R}",
    False: f"{C.ORN}✗{C.R}",
}


def screen_liberator(downloads: list[dict]) -> None:
    by_key = {d["key"]: d for d in downloads if d.get("liberator")}
    present = [d for d in installed_downloads() if d.name in by_key]

    if not present:
        render_header("Toggle Liberator")
        print()
        step_warn("No downloads support Liberator")
        go_back()
        return

    current = 0
    while True:
        labels = [
            f"{display_name(d.name, downloads):<20}{' ' * 2}"
            f"{_STATE_MARK[_is_liberator(d)]}"
            for d in present
        ]
        labels.append("Back")

        pick = select("Toggle Liberator", labels, current=current)
        if pick is None or pick == len(labels) - 1:
            return
        current = pick

        target = present[pick]
        if _is_liberator(target):
            set_liberator(target, None)
        else:
            liberator = liberator_file() or ensure_liberator()
            if liberator is None:
                go_back()
                return
            set_liberator(target, liberator.name)
