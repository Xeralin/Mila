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
    THROWBACK_VERSION_FILE,
)
from mila.depot import fetch_to, github_asset
from mila.spinner import Spinner


def ensure_throwback(force: bool = False) -> bool:
    if all((THROWBACK_DIR / f).exists() for f in THROWBACK_EXTRACT) and not force:
        return True

    with Spinner("Fetching ThrowbackLoader") as sp:
        THROWBACK_DIR.mkdir(parents=True, exist_ok=True)
        zip_path = THROWBACK_DIR / "_throwbackloader.zip"
        try:
            tag, asset_url = github_asset(THROWBACK_API_URL, ".zip")
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
            (THROWBACK_DIR / THROWBACK_VERSION_FILE).write_text(tag)
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


def write_launch_bat(target_dir: Path, ct_filename: str | None, liberator_name: str | None = None) -> None:
    template = (THROWBACK_DIR / LAUNCH_BAT).read_bytes()
    if liberator_name:
        start_line = f'start "" "%~dp0..\\..\\bin\\{liberator_name}"\r\n'.encode()
        kill_line = f'taskkill /IM {liberator_name} /F /T >nul 2>&1\r\n'.encode()
    elif ct_filename:
        ce_exe = "C:\\Program Files\\Cheat Engine\\cheatengine-x86_64.exe"
        start_line = (
            f'if not exist "{ce_exe}" "%~dp0..\\..\\bin\\{CE_INSTALLER.name}"\r\n'
            f'start "" "{ce_exe}" "%~dp0..\\..\\plugins\\ct\\{ct_filename}"\r\n'
        ).encode()
        kill_line = b""
    else:
        start_line = b""
        kill_line = b""
    text = template.replace(b"__INJECT_START__\r\n", start_line)
    text = text.replace(b"__INJECT_KILL__\r\n", kill_line)
    (target_dir / LAUNCH_BAT).write_bytes(text)
