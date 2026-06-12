import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from mila.constants import BIN_DIR, DD_BIN, DD_URL, DD_ZIP, HM_KEY
from mila.style import C, line, step_warn
from mila.spinner import LazySpinner, Reporter


def fetch_to(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mila"})
    part = dest.with_name(dest.name + ".part")
    try:
        with urllib.request.urlopen(req, timeout=30) as r, open(part, "wb") as f:
            shutil.copyfileobj(r, f)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    part.replace(dest)


def github_asset(api_url: str, suffix: str) -> tuple[str, str]:
    req = urllib.request.Request(api_url, headers={"User-Agent": "Mila"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    url = next(a["browser_download_url"] for a in data["assets"] if a["name"].endswith(suffix))
    return data["tag_name"], url


def github_tag(api_url: str) -> str:
    req = urllib.request.Request(api_url, headers={"User-Agent": "Mila"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["tag_name"]


def ensure_depotdownloader(reporter: Reporter | None = None, force: bool = False) -> Path | None:
    if DD_BIN.exists() and not force and os.access(DD_BIN, os.X_OK):
        return DD_BIN

    with (reporter or LazySpinner()) as sp:
        sp.update("Fetching DepotDownloader")
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        part = DD_BIN.with_name(DD_BIN.name + ".part")
        try:
            fetch_to(DD_URL, DD_ZIP)
            with zipfile.ZipFile(DD_ZIP) as z, z.open("DepotDownloader") as src, open(part, "wb") as f:
                shutil.copyfileobj(src, f)
            part.chmod(part.stat().st_mode | 0o111)
            part.replace(DD_BIN)
        except Exception as e:
            sp.fail(f"DepotDownloader download failed — {e}")
            return None
        finally:
            part.unlink(missing_ok=True)
            DD_ZIP.unlink(missing_ok=True)
        sp.succeed("DepotDownloader ready")
        return DD_BIN


def ensure_runtime(is_hm: bool, reporter: Reporter | None = None) -> Path | None:
    dd = ensure_depotdownloader(reporter)
    if dd is None:
        return None
    if not is_hm:
        from mila.throwback import ensure_throwback
        if not ensure_throwback(reporter):
            return None
    return dd


def _run_depot(binary: Path, args: list[str]) -> int:
    cmd = [str(binary), *args]
    line(f"$ {' '.join(cmd)}")
    rc = subprocess.run(cmd, check=False).returncode
    sys.stdout.write(C.NORMAL_KEYS + C.SHOW_CURSOR)
    sys.stdout.flush()
    return rc


def _other_depot(download: dict, source: dict) -> tuple[int, str, str, bool] | None:
    if "manifest_other" not in source:
        return None
    return (download["depot_other"], source["manifest_other"], "Other", True)


def depot_commands(download: dict, steam_account: str, target: Path, max_downloads: int, *, is_hm: bool) -> list[dict]:
    source = download[HM_KEY] if is_hm else download
    depots: list[tuple[int, str, str, bool]] = [
        (download["depot_main"], source["manifest_main"], "Main", False),
        (download["depot_lang"], source["manifest_lang"], "Language", False),
    ]
    other = _other_depot(download, source)
    if other:
        depots.insert(1, other)
    common = [
        "-app", str(download["app"]),
        "-username", steam_account,
        "-remember-password",
        "-dir", str(target),
        "-validate",
        "-max-downloads", str(max_downloads),
    ]
    return [
        {
            "args": ["-depot", str(depot_id), "-manifest", manifest_id, *common],
            "name": name,
            "optional": optional,
        }
        for depot_id, manifest_id, name, optional in depots
    ]


def run_depots(dd: Path, download: dict, steam_account: str, target: Path, max_downloads: int, *,
               is_hm: bool) -> tuple[int, str]:
    for cmd in depot_commands(download, steam_account, target, max_downloads, is_hm=is_hm):
        rc = _run_depot(dd, cmd["args"])
        if rc != 0:
            if not cmd["optional"]:
                return rc, cmd["name"]
            step_warn(f"{cmd['name']} depot failed — continuing without it")
    return 0, ""
