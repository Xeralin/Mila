import re
import shutil
import zipfile
from pathlib import Path

from mila.constants import (
    CE_INSTALLER,
    LAUNCH_BAT,
    THROWBACK_API_URL,
    THROWBACK_DIR,
    THROWBACK_DLLS_COMMON,
    THROWBACK_EXTRACT,
    THROWBACK_TOML,
)
from mila.depot import fetch_to, github_asset
from mila.spinner import Spinner


def ensure_throwback() -> bool:
    if all((THROWBACK_DIR / f).exists() for f in THROWBACK_EXTRACT):
        return True

    with Spinner("Fetching ThrowbackLoader") as sp:
        THROWBACK_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = THROWBACK_DIR / "_throwbackloader.zip"
        try:
            _, asset_url = github_asset(THROWBACK_API_URL, ".zip")
            fetch_to(asset_url, zip_path)
            with zipfile.ZipFile(zip_path) as z:
                for name in THROWBACK_EXTRACT:
                    z.extract(name, THROWBACK_DIR)
        except Exception as e:
            sp.fail(f"ThrowbackLoader download failed — {e}")
            zip_path.unlink(missing_ok=True)
            return False

        zip_path.unlink(missing_ok=True)
        if all((THROWBACK_DIR / f).exists() for f in THROWBACK_EXTRACT):
            sp.succeed("ThrowbackLoader ready")
            return True
        sp.fail("ThrowbackLoader extraction failed")
        return False


def write_throwback_toml(target_dir: Path, username: str) -> None:
    src = THROWBACK_DIR / THROWBACK_TOML
    text = src.read_text()
    text = re.sub(
        r"username\s*=\s*'[^']*'",
        f"username = '{username}'",
        text,
        count=1,
    )
    text = re.sub(
        r"custom_user_id\s*=\s*'[^']*'",
        f"custom_user_id = '{username}'",
        text,
        count=1,
    )
    (target_dir / THROWBACK_TOML).write_text(text)


def apply_throwback(target_dir: Path, username: str, loader: str) -> None:
    for name in (*THROWBACK_DLLS_COMMON, f"{loader}_loader64.dll"):
        shutil.copy2(THROWBACK_DIR / name, target_dir / name)
    write_throwback_toml(target_dir, username)


def write_launch_bat(target_dir: Path, ct_filename: str | None) -> None:
    template = (THROWBACK_DIR / LAUNCH_BAT).read_bytes()
    if ct_filename:
        ce_exe = "C:\\Program Files\\Cheat Engine\\cheatengine-x86_64.exe"
        ce_line = (
            f'if not exist "{ce_exe}" "%~dp0..\\..\\bin\\{CE_INSTALLER.name}"\r\n'
            f'start "" "{ce_exe}" "%~dp0..\\..\\plugins\\ct\\{ct_filename}"\r\n'
        ).encode()
    else:
        ce_line = b""
    (target_dir / LAUNCH_BAT).write_bytes(
        template.replace(b"__CE_START__\r\n", ce_line)
    )
