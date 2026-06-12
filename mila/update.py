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

from mila.constants import (
    DD_API_URL,
    DD_BIN,
    LIBERATOR_API_URL,
    LIBERATOR_GLOB,
    MAIN_SCRIPT,
    PROJECT_ROOT,
    SEVENZ_API_URL,
    SEVENZ_BIN,
    THROWBACK_API_URL,
    THROWBACK_DIR,
    THROWBACK_EXTRACT,
    THROWBACK_VERSION_FILE,
    UPDATE_API_URL,
    VERSION,
)
from mila.depot import ensure_depotdownloader, fetch_to, github_tag
from mila.heatedmetal import ensure_7zz
from mila.spinner import LazySpinner, Reporter
from mila.style import mag, step_fail
from mila.throwback import ensure_throwback
from mila.liberator import ensure_liberator, liberator_file


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


_mila_release: dict | None = None


def _mila_fetch() -> dict:
    global _mila_release
    if _mila_release is None:
        try:
            req = urllib.request.Request(UPDATE_API_URL, headers={"User-Agent": "Mila"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            _mila_release = {"tag": data["tag_name"], "zipball": data["zipball_url"]}
        except Exception:
            return {}
    return _mila_release


def _mila_latest() -> str | None:
    return _mila_fetch().get("tag", "").removeprefix("v") or None


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


def _mila_apply(reporter: Reporter | None = None) -> bool:
    release = _mila_fetch()
    if not release:
        return False
    if (PROJECT_ROOT / ".git").exists():
        step_fail(f"Git clone detected — use {mag('git pull')} to update")
        return False
    with (reporter or LazySpinner()) as sp:
        sp.update("Downloading update")
        try:
            with TemporaryDirectory() as tmp:
                archive = Path(tmp) / "mila.zip"
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


def _throwback_current() -> str | None:
    f = THROWBACK_DIR / THROWBACK_VERSION_FILE
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
    Component("Mila", lambda: True, lambda: VERSION, _mila_latest, _mila_apply, restart=True),
    Component("Liberator", lambda: liberator_file() is not None, _liberator_current, _liberator_latest,
              lambda reporter=None: ensure_liberator(reporter) is not None),
    Component("DepotDownloader", DD_BIN.exists, lambda: _binary_version(DD_BIN, ["--version"], r"v(\d+(?:\.\d+)+)"),
              _dd_latest, lambda reporter=None: ensure_depotdownloader(reporter, force=True) is not None),
    Component("7zz", SEVENZ_BIN.exists, lambda: _binary_version(SEVENZ_BIN, [], r"\(z\)\s+(\d+(?:\.\d+)+)"),
              lambda: _safe_tag(SEVENZ_API_URL), _sevenz_apply),
    Component("Throwback", lambda: all((THROWBACK_DIR / f).exists() for f in THROWBACK_EXTRACT),
              _throwback_current, lambda: _safe_tag(THROWBACK_API_URL),
              lambda reporter=None: ensure_throwback(reporter, force=True)),
]


def available() -> list[Component]:
    present = [c for c in COMPONENTS if c.present()]
    if not present:
        return []
    with ThreadPoolExecutor(max_workers=len(present)) as ex:
        latests = list(ex.map(lambda c: c.latest(), present))
    return [c for c, latest in zip(present, latests) if latest is not None and c.pending(latest)]


def restart() -> None:
    os.execv(sys.executable, [sys.executable, str(MAIN_SCRIPT)])
