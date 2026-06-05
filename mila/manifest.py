import re
import sys
import tomllib
from pathlib import Path

from mila.constants import DOWNLOADS_DIR, HM_FOLDER_SUFFIX, HM_KEY, LAUNCH_BAT, MANIFEST_FILE

_INSTALL_PATTERN = re.compile(r"^Y\d+S\d+_")


def load_downloads() -> list[dict]:
    try:
        with open(MANIFEST_FILE, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        sys.exit(f"manifest.toml not found at {MANIFEST_FILE}")
    except tomllib.TOMLDecodeError as e:
        sys.exit(f"manifest.toml is malformed: {e}")

    defaults = {
        "app": data.get("app"),
        "depot_main": data.get("depot_main"),
        "depot_lang": data.get("depot_lang"),
        "depot_other": data.get("depot_other"),
        "loader": data.get("default_loader"),
    }
    return [
        {"key": key, **defaults, **block}
        for key, block in data.items()
        if isinstance(block, dict)
    ]


def local_downloads() -> list[Path]:
    if not DOWNLOADS_DIR.exists():
        return []
    return [
        d for d in sorted(DOWNLOADS_DIR.glob("*"))
        if d.is_dir() and _INSTALL_PATTERN.match(d.name)
    ]


def resolve_install(folder_name: str, downloads: list[dict]) -> tuple[dict, bool] | None:
    if folder_name.endswith(HM_FOLDER_SUFFIX):
        prefix = folder_name.removesuffix(HM_FOLDER_SUFFIX) + "_"
        for d in downloads:
            if d["key"].startswith(prefix) and HM_KEY in d:
                return d, True
        return None
    for d in downloads:
        if d["key"] == folder_name:
            return d, False
    return None


def hm_display_name(download: dict) -> str:
    return f"{download['label'].split(' ', 1)[0]} Heated Metal"


def launcher_name(is_hm: bool) -> str:
    return "RainbowSix.exe" if is_hm else LAUNCH_BAT


def installed_downloads() -> list[Path]:
    return [
        d for d in local_downloads()
        if (d / launcher_name(d.name.endswith(HM_FOLDER_SUFFIX))).exists()
    ]


def display_name(folder_name: str, downloads: list[dict]) -> str:
    resolved = resolve_install(folder_name, downloads)
    if resolved is None:
        if folder_name.endswith(HM_FOLDER_SUFFIX):
            return f"{folder_name.removesuffix(HM_FOLDER_SUFFIX)} Heated Metal"
        return folder_name
    download, is_hm = resolved
    if is_hm:
        return hm_display_name(download)
    return download["label"]
