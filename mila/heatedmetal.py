import json
import os
import shutil
import subprocess
import tarfile
import zipfile
from collections.abc import Callable
from pathlib import Path

from mila.config import get_setting
from mila.constants import (
    BIN_DIR,
    DEFAULT_USERNAME,
    HELIOS_DIR,
    HELIOS_FILES,
    HELIOS_JSON,
    HM_API_URL,
    HM_BIN_DIR,
    HM_FOLDER_SUFFIX,
    HM_KEY,
    HM_MOD_DIR,
    HM_RELEASE_URL_FMT,
    JVAV_HELIOS_URL,
    SEVENZ_API_URL,
    SEVENZ_BIN,
)
from mila.depot import fetch_to, github_asset
from mila.input import go_back, select
from mila.manifest import display_name, installed_downloads, installed_username, resolve_install
from mila.spinner import LazySpinner, Reporter
from mila.steam import wait_for_game_closed
from mila.style import clear, mag, screen_header, step_fail, step_pass, step_warn

_last_error: str = ""
_release_cache: dict[str, tuple[str, str]] = {}


def _set_error(detail: str) -> None:
    global _last_error
    _last_error = detail


def _fail_message(fail_text: str) -> str:
    return f"{fail_text} — {_last_error}" if _last_error else fail_text


def _default_args(mod_dir: Path) -> Path | None:
    for name in ("DefaultArgs.dll", "defaultargs.dll"):
        candidate = mod_dir / name
        if candidate.exists():
            return candidate
    return None


def ensure_7zz(update: Callable[[str], None], force: bool = False) -> Path | None:
    if SEVENZ_BIN.exists() and not force:
        return SEVENZ_BIN

    update("Fetching 7zz")
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    tarxz_path = BIN_DIR / "_7zz.tar.xz"
    tmp_dir = BIN_DIR / ".7zz.tmp"
    try:
        _, asset_url = github_asset(SEVENZ_API_URL, "linux-x64.tar.xz")
        fetch_to(asset_url, tarxz_path)
        with tarfile.open(tarxz_path) as t:
            if hasattr(tarfile, "data_filter"):
                t.extraction_filter = tarfile.data_filter
            t.extract("7zz", tmp_dir)
        tmp_bin = tmp_dir / "7zz"
        tmp_bin.chmod(tmp_bin.stat().st_mode | 0o111)
        os.replace(tmp_bin, SEVENZ_BIN)
        return SEVENZ_BIN
    except Exception as e:
        _set_error(f"7zz download failed: {e}")
        return None
    finally:
        tarxz_path.unlink(missing_ok=True)
        shutil.rmtree(tmp_dir, ignore_errors=True)


def ensure_helios(update: Callable[[str], None]) -> bool:
    if all((HELIOS_DIR / f).exists() for f in HELIOS_FILES):
        return True

    update("Fetching HeliosLoader")
    tmp_dir = HELIOS_DIR.with_name(HELIOS_DIR.name + ".tmp")
    zip_path = HM_BIN_DIR / "_helios.zip"
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(parents=True)
        fetch_to(JVAV_HELIOS_URL, zip_path)
        with zipfile.ZipFile(zip_path) as z:
            for name in HELIOS_FILES:
                with z.open(f"HeliosLoader/{name}") as f:
                    (tmp_dir / name).write_bytes(f.read())
        if HELIOS_DIR.exists():
            shutil.rmtree(HELIOS_DIR)
        os.replace(tmp_dir, HELIOS_DIR)
        return True
    except Exception as e:
        _set_error(f"HeliosLoader download failed: {e}")
        return False
    finally:
        zip_path.unlink(missing_ok=True)
        shutil.rmtree(tmp_dir, ignore_errors=True)


def resolve_hm_release(hm_version: str) -> tuple[str, str] | None:
    if hm_version != "latest":
        return hm_version, HM_RELEASE_URL_FMT.format(tag=hm_version)
    cached = _release_cache.get(HM_API_URL)
    if cached is not None:
        return cached
    try:
        resolved = github_asset(HM_API_URL, ".7z")
    except Exception as e:
        _set_error(f"Heated Metal release lookup failed: {e}")
        return None
    _release_cache[HM_API_URL] = resolved
    return resolved


def _sevenz_error(rc: subprocess.CompletedProcess) -> str:
    stderr_line = next(
        (line.strip() for line in rc.stderr.decode(errors="replace").splitlines() if line.strip()),
        "",
    )
    detail = f"7z exited with code {rc.returncode}"
    return f"{detail}: {stderr_line}" if stderr_line else detail


def ensure_heatedmetal_mod(hm_version: str, update: Callable[[str], None]) -> Path | None:
    if hm_version == "latest":
        update("Looking up Heated Metal release")
    resolved = resolve_hm_release(hm_version)
    if resolved is None:
        return None
    tag, asset_url = resolved

    mod_dir = HM_MOD_DIR / tag
    if _default_args(mod_dir):
        return mod_dir

    sevenz = ensure_7zz(update)
    if sevenz is None:
        return None

    update(f"Fetching Heated Metal {tag}")
    tmp_dir = HM_MOD_DIR / f".{tag}.tmp"
    archive_path = tmp_dir / "_heatedmetal.7z"
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(parents=True)
        fetch_to(asset_url, archive_path)
        rc = subprocess.run(
            [str(sevenz), "x", "-y", f"-o{tmp_dir}", str(archive_path)],
            capture_output=True, check=False,
        )
        if rc.returncode != 0:
            _set_error(_sevenz_error(rc))
            return None
        archive_path.unlink()
        if _default_args(tmp_dir) is None:
            _set_error(f"DefaultArgs.dll missing in Heated Metal {tag} archive")
            return None
        if mod_dir.exists():
            shutil.rmtree(mod_dir)
        os.replace(tmp_dir, mod_dir)
        return mod_dir
    except Exception as e:
        _set_error(f"Heated Metal download failed: {e}")
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _detect_cpu_variant() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("flags"):
                tokens = line.split()
                if "avx" in tokens:
                    return "AVX"
                if "sse4_2" in tokens:
                    return "SSE"
                break
    except OSError:
        pass
    return ""


def _install_helios(target_dir: Path, username: str) -> None:
    for name in HELIOS_FILES:
        if name == HELIOS_JSON:
            continue
        shutil.copy2(HELIOS_DIR / name, target_dir / name)

    config = json.loads((HELIOS_DIR / HELIOS_JSON).read_text())
    config["Username"] = username
    (target_dir / HELIOS_JSON).write_text(json.dumps(config, indent=2))

    for variant in ("DefaultArgs.dll", "defaultargs.dll"):
        (target_dir / variant).unlink(missing_ok=True)
    target_hm = target_dir / "HeatedMetal"
    if target_hm.exists():
        shutil.rmtree(target_hm)


def apply_heatedmetal(target_dir: Path, username: str, hm_version: str,
                      success_text: str = "Heated Metal applied",
                      fail_text: str = "Heated Metal setup failed",
                      reporter: Reporter | None = None) -> bool:
    _set_error("")
    with (reporter or LazySpinner()) as sp:
        if not ensure_helios(sp.update):
            sp.fail(_fail_message(fail_text))
            return False

        mod_dir = ensure_heatedmetal_mod(hm_version, sp.update)
        if mod_dir is None:
            sp.fail(_fail_message(fail_text))
            return False

        sp.update("Copying files")
        _install_helios(target_dir, username)

        src = mod_dir / "DefaultArgs.dll"
        if not src.exists():
            src = mod_dir / "defaultargs.dll"
        shutil.copy2(src, target_dir / "defaultargs.dll")

        target_hm = target_dir / "HeatedMetal"
        shutil.copytree(mod_dir / "HeatedMetal", target_hm)

        variant = _detect_cpu_variant()
        if variant:
            variant_dll = target_hm / f"HeatedMetal{variant}.dll"
            if variant_dll.exists():
                shutil.copy2(variant_dll, target_hm / "HeatedMetal.dll")

        (target_hm / ".version").write_text(mod_dir.name)

        notices = mod_dir / "ThirdPartyLegalNotices.txt"
        if notices.exists():
            shutil.copy2(notices, target_dir / "ThirdPartyLegalNotices.txt")

        sp.succeed(success_text)
        return True


def current_hm_version(target: Path) -> str:
    f = target / "HeatedMetal" / ".version"
    return f.read_text().strip() if f.exists() else "?"


def hm_update_available(downloads: list[dict]) -> bool:
    return bool(hm_pending_updates(downloads))


def hm_pending_updates(downloads: list[dict]) -> list[dict]:
    pending = []
    for target in installed_downloads():
        resolved = resolve_install(target.name, downloads)
        if resolved is None or not resolved[1]:
            continue
        download = resolved[0]
        release = resolve_hm_release(download[HM_KEY]["hm_version"])
        if release is None:
            continue
        current = current_hm_version(target)
        if current != release[0]:
            pending.append({
                "key": download["key"],
                "name": display_name(target.name, downloads),
                "current": current,
                "target": release[0],
            })
    return pending


def _prune_mod_cache(downloads: list[dict], keep_tag: str) -> None:
    if not HM_MOD_DIR.exists():
        return
    referenced = {keep_tag}
    for target in installed_downloads():
        resolved = resolve_install(target.name, downloads)
        if resolved is None or not resolved[1]:
            continue
        referenced.add(current_hm_version(target))
    for entry in HM_MOD_DIR.iterdir():
        if entry.is_dir() and entry.name not in referenced:
            shutil.rmtree(entry, ignore_errors=True)


def update_hm(download_key: str, downloads: list[dict], username: str,
              reporter: Reporter | None = None) -> bool:
    for target in installed_downloads():
        resolved = resolve_install(target.name, downloads)
        if resolved is None or not resolved[1] or resolved[0]["key"] != download_key:
            continue
        release = resolve_hm_release(resolved[0][HM_KEY]["hm_version"])
        if release is None:
            return False
        shutil.rmtree(HELIOS_DIR, ignore_errors=True)
        effective_username = installed_username(target) or username
        ok = apply_heatedmetal(
            target, effective_username, release[0],
            success_text=f"{resolved[0]['label']} updated to {release[0]}",
            fail_text="Heated Metal update failed",
            reporter=reporter,
        )
        if ok:
            _prune_mod_cache(downloads, release[0])
        return ok
    return False


def hm_folder_name(key: str) -> str:
    return f"{key.split('_', 1)[0]}{HM_FOLDER_SUFFIX}"


def screen_update_heatedmetal(cfg: dict, downloads: list[dict]) -> None:
    hm_downloads = [
        (target, resolved[0])
        for target in installed_downloads()
        if (resolved := resolve_install(target.name, downloads)) and resolved[1]
    ]
    if not hm_downloads:
        screen_header("Update Heated Metal")
        print()
        step_warn("No Heated Metal downloads found")
        go_back()
        return

    while True:
        labels = []
        for target, download in hm_downloads:
            labels.append(f"{display_name(target.name, downloads):<20}{current_hm_version(target):>8}")
        labels.append("Back")
        pick = select("Update Heated Metal", labels)
        if pick is None or pick == len(labels) - 1:
            return

        target, download = hm_downloads[pick]
        name = display_name(target.name, downloads)
        clear()
        screen_header(mag(name))

        resolved = resolve_hm_release(download[HM_KEY]["hm_version"])
        if resolved is None:
            step_fail("Heated Metal version lookup failed")
            go_back()
            continue
        target_tag, _ = resolved

        if current_hm_version(target) == target_tag:
            step_pass("Already up to date")
            go_back()
            continue

        if not wait_for_game_closed(mag(name)):
            continue

        shutil.rmtree(HELIOS_DIR, ignore_errors=True)
        username = installed_username(target) or get_setting(cfg, "username", DEFAULT_USERNAME)
        if apply_heatedmetal(
            target, username, target_tag,
            success_text=f"{name} updated to {target_tag}",
            fail_text=f"{name} update failed",
        ):
            _prune_mod_cache(downloads, target_tag)
        go_back()
