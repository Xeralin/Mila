import re
import shutil
import tomllib
import zipfile
from pathlib import Path

from app.constants import (
    LAUNCHER_EXE,
    TL_API_URL,
    TL_DIR,
    TL_DLLS_COMMON,
    TL_EXTRACT,
    TL_TOML,
    TL_VERSION_FILE,
)
from app.depot import fetch_to, github_asset
from app.spinner import LazySpinner, Reporter


def ensure_tl(reporter: Reporter | None = None, force: bool = False) -> bool:
    if all((TL_DIR / f).exists() for f in TL_EXTRACT) and not force:
        return True

    with (reporter or LazySpinner()) as sp:
        sp.update("Fetching ThrowbackLoader")
        TL_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = TL_DIR / "_throwbackloader.zip"
        try:
            tag, asset_url = github_asset(TL_API_URL, ".zip")
            fetch_to(asset_url, zip_path)
            with zipfile.ZipFile(zip_path) as z:
                for name in TL_EXTRACT:
                    z.extract(name, TL_DIR)
        except Exception as e:
            sp.fail(f"ThrowbackLoader download failed — {e}")
            zip_path.unlink(missing_ok=True)
            return False

        zip_path.unlink(missing_ok=True)
        if all((TL_DIR / f).exists() for f in TL_EXTRACT):
            (TL_DIR / TL_VERSION_FILE).write_text(tag)
            sp.succeed("ThrowbackLoader ready")
            return True
        sp.fail("ThrowbackLoader extraction failed")
        return False


def write_tl_toml(target_dir: Path, username: str) -> None:
    dest = target_dir / TL_TOML
    src = dest if dest.exists() else TL_DIR / TL_TOML
    text = src.read_text()
    text = re.sub(
        r"""username\s*=\s*["'][^"']*["']""",
        f'username = "{username}"',
        text,
        count=1,
    )
    dest.write_text(text)


def apply_tl(target_dir: Path, username: str, loader: str) -> None:
    for name in (*TL_DLLS_COMMON, f"{loader}_loader64.dll"):
        shutil.copy2(TL_DIR / name, target_dir / name)
    write_tl_toml(target_dir, username)


def write_launcher(target_dir: Path) -> None:
    src = TL_DIR / LAUNCHER_EXE
    if not src.exists():
        ensure_tl()
    shutil.copy2(src, target_dir / LAUNCHER_EXE)


def read_tools(target_dir: Path) -> list[str]:
    config = target_dir / TL_TOML
    if not config.exists():
        return []
    try:
        with open(config, "rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return []
    return [
        t
        for t in data.get("Launch", {}).get("tools", [])
        if isinstance(t, str)
    ]


def set_tools(target_dir: Path, tools: list[str]) -> None:
    config = target_dir / TL_TOML
    if not config.exists():
        return
    text = config.read_text()
    array = "[" + ", ".join(f"'{t}'" for t in tools) + "]"
    existing = re.search(
        r"(?m)^(tools[ \t]*=[ \t]*)\[.*?\]([ \t]*#[^\n]*)?$", text
    )
    if existing:
        text = (
            text[:existing.start()]
            + existing.group(1)
            + array
            + (existing.group(2) or "")
            + text[existing.end():]
        )
    elif re.search(r"(?m)^\[Launch\]", text):
        text = re.sub(
            r"(?m)^(\[Launch\][^\n]*)$",
            lambda m: m.group(1) + f"\ntools = {array}",
            text,
            count=1,
        )
    else:
        text = text.rstrip("\n") + f"\n\n[Launch]\ntools = {array}\n"
    config.write_text(text)
