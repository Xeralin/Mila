import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from app.constants import (
    BINARY_PATH,
    DD_API_URL,
    DD_BIN,
    FROZEN,
    LIBERATOR_API_URL,
    LIBERATOR_GLOB,
    MAIN_SCRIPT,
    PROJECT_ROOT,
    SEVENZ_API_URL,
    SEVENZ_BIN,
    TL_API_URL,
    TL_DIR,
    TL_EXTRACT,
    TL_VERSION_FILE,
    UPDATE_API_URL,
    UPDATE_ASSET,
    VERSION,
)
from app.depot import ensure_depotdownloader, fetch_to, github_tag
from app.heatedmetal import ensure_7zz
from app.spinner import LazySpinner, Reporter
from app.style import mag, step_fail
from app.throwbackloader import ensure_tl
from app.liberator import ensure_liberator, liberator_file


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split("."))


def _newer(latest: str, current: str) -> bool:
    try:
        return _version_tuple(latest) > _version_tuple(current)
    except ValueError:
        return latest != current


def _safe_tag(api_url: str) -> str | None:
    try:
        return github_tag(api_url)
    except Exception:
        return None


def _binary_version(binary: Path, args: list[str], pattern: str) -> str | None:
    try:
        out = subprocess.run(
            [str(binary), *args],
            capture_output=True, text=True, timeout=30, check=False,
        ).stdout
    except Exception:
        return None
    match = re.search(pattern, out)
    return match.group(1) if match else None


_downloader_release: dict | None = None


def _downloader_fetch() -> dict:
    global _downloader_release
    if _downloader_release is None:
        try:
            req = urllib.request.Request(
                UPDATE_API_URL, headers={"User-Agent": "Downloader"}
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            asset = next(
                (a["browser_download_url"] for a in data.get("assets", [])
                 if a["name"] == UPDATE_ASSET),
                "",
            )
            _downloader_release = {
                "tag": data["tag_name"],
                "zipball": data["zipball_url"],
                "asset": asset,
            }
        except Exception:
            return {}
    return _downloader_release


def _downloader_latest() -> str | None:
    return _downloader_fetch().get("tag", "").removeprefix("v") or None


def _overwrite_from(src_root: Path) -> None:
    staged: list[tuple[Path, Path]] = []
    try:
        for item in src_root.rglob("*"):
            if item.is_file():
                target = PROJECT_ROOT / item.relative_to(src_root)
                target.parent.mkdir(parents=True, exist_ok=True)
                staged.append((target.with_name(target.name + ".new"), target))
                shutil.copy2(item, staged[-1][0])
    except BaseException:
        for new, _ in staged:
            new.unlink(missing_ok=True)
        raise
    for new, target in staged:
        os.replace(new, target)


def _downloader_apply_binary(reporter: Reporter | None = None) -> bool:
    release = _downloader_fetch()
    if not release:
        return False
    if not release.get("asset"):
        step_fail("No matching binary in the latest release")
        return False
    staged = BINARY_PATH.with_name(BINARY_PATH.name + ".new")
    with (reporter or LazySpinner()) as sp:
        sp.update("Downloading update")
        try:
            fetch_to(release["asset"], staged)
            staged.chmod(0o755)
            os.replace(staged, BINARY_PATH)
        except Exception as e:
            staged.unlink(missing_ok=True)
            sp.fail(f"Update failed — {e}")
            return False
        sp.succeed(f"Updated to {release['tag'].removeprefix('v')}")
    return True


def _downloader_apply(reporter: Reporter | None = None) -> bool:
    if FROZEN:
        return _downloader_apply_binary(reporter)
    release = _downloader_fetch()
    if not release:
        return False
    if (PROJECT_ROOT / ".git").exists():
        step_fail(f"Git clone detected — use {mag('git pull')} to update")
        return False
    with (reporter or LazySpinner()) as sp:
        sp.update("Downloading update")
        try:
            with TemporaryDirectory() as tmp:
                archive = Path(tmp) / "downloader.zip"
                fetch_to(release["zipball"], archive)
                with zipfile.ZipFile(archive) as z:
                    z.extractall(tmp)
                roots = [d for d in Path(tmp).iterdir() if d.is_dir()]
                if len(roots) != 1:
                    sp.fail("Update failed — unexpected archive layout")
                    return False
                sp.update("Applying update")
                _overwrite_from(roots[0])
        except Exception as e:
            sp.fail(f"Update failed — {e}")
            return False
        sp.succeed(f"Updated to {release['tag'].removeprefix('v')}")
    return True


def _liberator_current() -> str | None:
    f = liberator_file()
    if f is None:
        return None
    prefix, suffix = LIBERATOR_GLOB.split("*")
    return f.name.removeprefix(prefix).removesuffix(suffix)


def _liberator_latest() -> str | None:
    tag = _safe_tag(LIBERATOR_API_URL)
    return tag.removeprefix("v") if tag else None


def _dd_latest() -> str | None:
    tag = _safe_tag(DD_API_URL)
    return tag.removeprefix("DepotDownloader_") if tag else None


def _sevenz_apply(reporter: Reporter | None = None) -> bool:
    with (reporter or LazySpinner()) as sp:
        sp.update("Updating 7zz")
        if ensure_7zz(sp.update, force=True) is None:
            sp.fail("7zz update failed")
            return False
        sp.succeed("7zz updated")
    return True


def _tl_current() -> str | None:
    f = TL_DIR / TL_VERSION_FILE
    return f.read_text().strip() if f.exists() else None


class Component:
    def __init__(
        self,
        name: str,
        present: Callable[[], bool],
        current: Callable[[], str | None],
        latest: Callable[[], str | None],
        apply: Callable[..., bool],
        restart: bool = False,
    ) -> None:
        self.name = name
        self.present = present
        self.current = current
        self.latest = latest
        self.apply = apply
        self.restart = restart
        self.target: str | None = None

    def pending(self, latest: str | None = None) -> str | None:
        if not self.present():
            return None
        if latest is None:
            latest = self.latest()
        if latest is None:
            return None
        current = self.current()
        if current is None or _newer(latest, current):
            self.target = latest
            return latest
        return None


COMPONENTS = [
    Component(
        "Downloader", lambda: True, lambda: VERSION, _downloader_latest,
        _downloader_apply, restart=True,
    ),
    Component(
        "Liberator", lambda: liberator_file() is not None,
        _liberator_current, _liberator_latest,
        lambda reporter=None: ensure_liberator(reporter) is not None,
    ),
    Component(
        "DepotDownloader", DD_BIN.exists,
        lambda: _binary_version(DD_BIN, ["--version"], r"v(\d+(?:\.\d+)+)"),
        _dd_latest,
        lambda reporter=None: (
            ensure_depotdownloader(reporter, force=True) is not None
        ),
    ),
    Component(
        "7zz", SEVENZ_BIN.exists,
        lambda: _binary_version(SEVENZ_BIN, [], r"\(z\)\s+(\d+(?:\.\d+)+)"),
        lambda: _safe_tag(SEVENZ_API_URL), _sevenz_apply,
    ),
    Component(
        "ThrowbackLoader",
        lambda: all((TL_DIR / f).exists() for f in TL_EXTRACT),
        _tl_current, lambda: _safe_tag(TL_API_URL),
        lambda reporter=None: ensure_tl(reporter, force=True),
    ),
]


def available() -> list[Component]:
    present = [c for c in COMPONENTS if c.present()]
    if not present:
        return []
    with ThreadPoolExecutor(max_workers=len(present)) as ex:
        latests = list(ex.map(lambda c: c.latest(), present))
    return [
        c for c, latest in zip(present, latests)
        if latest is not None and c.pending(latest)
    ]


def restart() -> None:
    if FROZEN:
        os.execv(str(BINARY_PATH), [str(BINARY_PATH)])
    else:
        os.execv(sys.executable, [sys.executable, str(MAIN_SCRIPT)])
