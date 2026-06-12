from collections.abc import Iterator
from pathlib import Path

from mila.constants import HM_FOLDER_SUFFIX, TEXTURE_QUALITIES, TEXTURE_RX, UPC_LOADERS
from mila.style import clear, fmt_bytes, line, mag, screen_header, step_pass, step_warn
from mila.input import confirm, go_back, select
from mila.spinner import Spinner
from mila.manifest import display_name, installed_downloads
from mila.steam import wait_for_game_closed


def _folder_size(path: Path) -> int:
    try:
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    except OSError:
        return 0


def _texture_forges(path: Path) -> Iterator[tuple[Path, int, int]]:
    for f in path.iterdir():
        if f.suffix.lower() != ".forge":
            continue
        m = TEXTURE_RX.search(f.stem)
        if not m:
            continue
        level = int(m.group(1))
        if not 0 <= level < len(TEXTURE_QUALITIES):
            continue
        try:
            yield f, level, f.stat().st_size
        except OSError:
            continue


def _texture_tiers(path: Path) -> dict[int, int]:
    tiers: dict[int, int] = {}
    for _, level, size in _texture_forges(path):
        tiers[level] = tiers.get(level, 0) + size
    return tiers


def _videos_size(path: Path) -> int:
    v = path / "videos"
    if not v.is_dir():
        return 0
    try:
        return sum(f.stat().st_size for f in v.iterdir() if f.is_file())
    except OSError:
        return 0


def _event_files(path: Path) -> list[Path]:
    return [
        f for f in path.iterdir()
        if f.is_file()
        and f.suffix.lower() in (".forge", ".depgraphbin")
        and "events" in f.stem.lower()
    ]


def _events_size(path: Path) -> int:
    return sum(f.stat().st_size for f in _event_files(path))


def _delete_videos(path: Path) -> int:
    v = path / "videos"
    if not v.is_dir():
        return 0
    freed = 0
    for f in v.iterdir():
        if not f.is_file():
            continue
        try:
            size = f.stat().st_size
            f.unlink()
        except OSError:
            continue
        freed += size
    return freed


def _delete_events(path: Path) -> int:
    freed = 0
    for f in _event_files(path):
        try:
            size = f.stat().st_size
            f.unlink()
        except OSError:
            continue
        freed += size
    return freed


def _delete_textures_above(path: Path, keep_level: int) -> int:
    freed = 0
    for f, level, size in _texture_forges(path):
        if level > keep_level:
            try:
                f.unlink()
                freed += size
            except OSError:
                pass
    return freed


def _uses_upc_loader(d: Path) -> bool:
    return any((d / dll).exists() for dll in UPC_LOADERS)


def scan_download(d: Path) -> dict:
    return {
        "total":  _folder_size(d),
        "tiers":  _texture_tiers(d),
        "videos": _videos_size(d),
        "events": 0 if _uses_upc_loader(d) else _events_size(d),
    }


def cut_download(d: Path, kind: str, level: int = 0) -> int:
    if kind == "videos":
        return _delete_videos(d)
    if kind == "events":
        return _delete_events(d)
    return _delete_textures_above(d, level)


def _shears_action(download_dir: Path, kind: str, level: int = 0) -> None:
    titles = {
        "videos":   "Cut videos",
        "events":   "Cut events",
        "textures": f"Cut to {TEXTURE_QUALITIES[level]} textures",
    }
    screen_header(titles[kind])
    if not wait_for_game_closed(titles[kind]):
        return
    if kind == "videos":
        step_warn("This permanently deletes the video files")
    elif kind == "events":
        step_warn("This permanently deletes event forge files")
    else:
        step_warn(f"This permanently deletes all textures above {TEXTURE_QUALITIES[level]}")
    print()
    if not confirm("Continue?", default=False):
        return

    clear()
    screen_header(titles[kind])
    with Spinner("Cutting") as sp:
        freed = cut_download(download_dir, kind, level)
        sp.succeed(f"Freed {fmt_bytes(freed)}")
    go_back()


def _shears_download(download_dir: Path, infos: dict[Path, dict], downloads: list[dict]) -> None:
    name = display_name(download_dir.name, downloads)
    while True:
        clear()
        if download_dir not in infos:
            with Spinner(f"Scanning {name}"):
                infos[download_dir] = scan_download(download_dir)
        info = infos[download_dir]
        total, tiers, videos, events = info["total"], info["tiers"], info["videos"], info["events"]

        screen_header(f"{mag(name)} — {fmt_bytes(total)} total")
        for level, qname in enumerate(TEXTURE_QUALITIES):
            size = tiers.get(level, 0)
            if size > 0:
                line(f"{qname + ' textures':<20}{fmt_bytes(size):>8}")
        if videos > 0:
            line(f"{'Videos':<20}{fmt_bytes(videos):>8}")
        if events > 0:
            line(f"{'Events':<20}{fmt_bytes(events):>8}")
        print()

        actions = []
        if videos > 0:
            actions.append(("Cut videos", lambda: _shears_action(download_dir, "videos")))
        if events > 0:
            actions.append(("Cut events", lambda: _shears_action(download_dir, "events")))
        present_levels = sorted(tiers.keys())
        for keep in present_levels[:-1]:
            actions.append((
                f"Cut to {TEXTURE_QUALITIES[keep]} textures",
                lambda k=keep: _shears_action(download_dir, "textures", k),
            ))

        if not actions:
            step_pass("There's nothing to cut")
            go_back()
            return

        labels = [label for label, _ in actions] + ["Back"]
        pick = select("", labels, clear_first=False)
        if pick is None or pick == len(labels) - 1:
            return
        del infos[download_dir]
        clear()
        actions[pick][1]()


def screen_shears(downloads: list[dict]) -> None:
    present = [d for d in installed_downloads() if not d.name.endswith(HM_FOLDER_SUFFIX)]
    if not present:
        screen_header("Shears")
        print()
        step_warn("No Throwback downloads found")
        go_back()
        return

    infos = {}
    with Spinner(f"Scanning {display_name(present[0].name, downloads)}") as sp:
        for d in present:
            sp.text = f"Scanning {display_name(d.name, downloads)}"
            infos[d] = scan_download(d)

    while True:
        labels = [f"{display_name(d.name, downloads):<20}{fmt_bytes(infos[d]['total']):>8}" for d in present]
        labels.append("Back")
        pick = select("Shears", labels)
        if pick is None or pick == len(labels) - 1:
            return
        _shears_download(present[pick], infos, downloads)
