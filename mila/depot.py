import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from mila.constants import BIN_DIR, DD_BIN, DD_URL, DD_ZIP, HM_KEY
from mila.style import C, line
from mila.spinner import Spinner


def fetch_to(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mila"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


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


def ensure_depotdownloader(force: bool = False) -> Path | None:
    if DD_BIN.exists() and not force:
        return DD_BIN

    with Spinner("Fetching DepotDownloader") as sp:
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        try:
            fetch_to(DD_URL, DD_ZIP)
            with zipfile.ZipFile(DD_ZIP) as z:
                z.extract("DepotDownloader", BIN_DIR)
        except Exception as e:
            sp.fail(f"DepotDownloader download failed — {e}")
            DD_ZIP.unlink(missing_ok=True)
            return None
        DD_ZIP.unlink(missing_ok=True)
        if DD_BIN.exists():
            DD_BIN.chmod(DD_BIN.stat().st_mode | 0o111)
            sp.succeed("DepotDownloader ready")
            return DD_BIN
        sp.fail("DepotDownloader extraction failed")
        return None


def ensure_runtime(is_hm: bool) -> Path | None:
    dd = ensure_depotdownloader()
    if dd is None:
        return None
    if not is_hm:
        from mila.throwback import ensure_throwback
        if not ensure_throwback():
            return None
    return dd


def _run_depot(binary: Path, args: list[str]) -> int:
    cmd = [str(binary), *args]
    line(f"$ {' '.join(cmd)}")
    rc = subprocess.run(cmd, check=False).returncode
    sys.stdout.write(C.NORMAL_KEYS + C.SHOW_CURSOR)
    sys.stdout.flush()
    return rc


def _run_depots(
    dd: Path,
    app: int,
    depots: list[tuple[int, str, str, bool]],
    steam_account: str,
    target: Path,
    max_downloads: int,
) -> tuple[int, str]:
    common = [
        "-app", str(app),
        "-username", steam_account,
        "-remember-password",
        "-dir", str(target),
        "-validate",
        "-max-downloads", str(max_downloads),
    ]
    for depot_id, manifest_id, name, optional in depots:
        rc = _run_depot(dd, ["-depot", str(depot_id), "-manifest", manifest_id, *common])
        if rc != 0 and not optional:
            return rc, name
    return 0, ""


def _other_depot(download: dict, source: dict) -> tuple[int, str, str, bool] | None:
    if "manifest_other" not in source:
        return None
    return (download["depot_other"], source["manifest_other"], "Other", True)


def run_depots(dd: Path, download: dict, steam_account: str, target: Path, max_downloads: int, *, is_hm: bool) -> tuple[int, str]:
    source = download[HM_KEY] if is_hm else download
    depots: list[tuple[int, str, str, bool]] = [
        (download["depot_main"], source["manifest_main"], "Main", False),
        (download["depot_lang"], source["manifest_lang"], "Language", False),
    ]
    other = _other_depot(download, source)
    if other:
        depots.insert(1, other)
    return _run_depots(dd, download["app"], depots, steam_account, target, max_downloads)
