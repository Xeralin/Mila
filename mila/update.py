import json
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from mila.constants import MAIN_SCRIPT, PROJECT_ROOT, UPDATE_API_URL, VERSION
from mila.depot import fetch_to
from mila.spinner import Spinner
from mila.style import mag, step_fail

_release: dict | None = None
_checked = False


def _version_tuple(tag: str) -> tuple[int, ...]:
    return tuple(int(p) for p in tag.removeprefix("v").split("."))


def _fetch_latest() -> None:
    global _release
    try:
        req = urllib.request.Request(UPDATE_API_URL, headers={"User-Agent": "Mila"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        _release = {"tag": data["tag_name"], "zipball": data["zipball_url"]}
    except Exception:
        _release = None


def _available() -> str | None:
    if _release is None:
        return None
    try:
        if _version_tuple(_release["tag"]) > _version_tuple(VERSION):
            return _release["tag"].removeprefix("v")
    except ValueError:
        return None
    return None


def check() -> str | None:
    global _checked
    if not _checked:
        _fetch_latest()
        _checked = True
    return _available()


def _overwrite_from(src_root: Path) -> None:
    for item in src_root.rglob("*"):
        if item.is_file():
            target = PROJECT_ROOT / item.relative_to(src_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def apply() -> bool:
    if _release is None:
        return False
    if (PROJECT_ROOT / ".git").exists():
        step_fail(f"Git clone detected — use {mag('git pull')} to update")
        return False
    with Spinner("Downloading update") as sp:
        try:
            with TemporaryDirectory() as tmp:
                archive = Path(tmp) / "mila.zip"
                fetch_to(_release["zipball"], archive)
                with zipfile.ZipFile(archive) as z:
                    z.extractall(tmp)
                roots = [d for d in Path(tmp).iterdir() if d.is_dir()]
                if len(roots) != 1:
                    sp.fail("Update failed — unexpected archive layout")
                    return False
                sp.text = "Applying update"
                _overwrite_from(roots[0])
        except Exception as e:
            sp.fail(f"Update failed — {e}")
            return False
        sp.succeed(f"Updated to {_release['tag'].removeprefix('v')}")
    return True


def restart() -> None:
    os.execv(sys.executable, [sys.executable, str(MAIN_SCRIPT)])
