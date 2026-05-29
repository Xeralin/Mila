import json
import os
import re
import shutil
import subprocess
import zlib
from pathlib import Path

from mila.constants import (
    CE_INSTALLER,
    PROTON_BUILTIN,
    SHORTCUTS_VDF,
    STEAM_COMMON,
    STEAM_COMPATDATA,
    STEAM_COMPAT_TOOLS_D,
    STEAM_CONFIG_VDF,
    STEAM_DIR,
    STEAM_USERDATA,
)
from mila.input import confirm, go_back, select
from mila.manifest import hm_display_name, launcher_name, local_downloads, resolve_install
from mila.spinner import Spinner
from mila.style import clear, mag, screen_header, step_fail, step_pass, step_warn


def _is_steam_running() -> bool:
    return subprocess.run(
        ["pgrep", "-x", "steam"], capture_output=True
    ).returncode == 0


def _is_game_running() -> bool:
    return subprocess.run(
        ["pgrep", "-f", r"RainbowSix.*\.exe"], capture_output=True
    ).returncode == 0


def _wait_for(check_running, title: str, warn_msg: str) -> bool:
    waited = False
    proceed = True
    while check_running():
        clear()
        screen_header(title)
        step_warn(warn_msg)
        print()
        waited = True
        if select("", ["Retry", "Back"], clear_first=False) != 0:
            proceed = False
            break
    if waited:
        clear()
        screen_header(title)
    return proceed


def wait_for_game_closed(title: str) -> bool:
    return _wait_for(_is_game_running, title, "Close the game to continue")


def wait_for_steam_closed(title: str) -> bool:
    return _wait_for(_is_steam_running, title, "Close Steam to apply")


def _parse_vdf(data: bytes) -> dict:
    pos = 0

    def read_string() -> str:
        nonlocal pos
        start = pos
        while data[pos] != 0:
            pos += 1
        s = data[start:pos].decode("utf-8", errors="replace")
        pos += 1
        return s

    def read_map() -> dict:
        nonlocal pos
        result: dict = {}
        while pos < len(data):
            t = data[pos]
            pos += 1
            if t == 0x08:
                return result
            key = read_string()
            if t == 0x00:
                result[key] = read_map()
            elif t == 0x01:
                result[key] = read_string()
            elif t == 0x02:
                result[key] = int.from_bytes(data[pos:pos + 4], "little", signed=False)
                pos += 4
            elif t == 0x07:
                result[key] = int.from_bytes(data[pos:pos + 8], "little", signed=False)
                pos += 8
            else:
                return result
        return result

    return read_map()


def _serialize_vdf(obj: dict) -> bytes:
    buf = bytearray()

    def w_string(s: str) -> None:
        buf.extend(s.encode("utf-8"))
        buf.append(0)

    def w_map(m: dict) -> None:
        for k, v in m.items():
            if isinstance(v, dict):
                buf.append(0x00)
                w_string(k)
                w_map(v)
            elif isinstance(v, str):
                buf.append(0x01)
                w_string(k)
                w_string(v)
            elif isinstance(v, int):
                if 0 <= v < (1 << 32):
                    buf.append(0x02)
                    w_string(k)
                    buf.extend(v.to_bytes(4, "little"))
                else:
                    buf.append(0x07)
                    w_string(k)
                    buf.extend(v.to_bytes(8, "little"))
        buf.append(0x08)

    w_map(obj)
    return bytes(buf)


def _active_userdata() -> Path | None:
    login = STEAM_DIR / "config" / "loginusers.vdf"
    if login.exists():
        text = login.read_text(errors="replace")
        for m in re.finditer(r'"(\d{17})"\s*\{[^}]*?"MostRecent"\s*"1"', text):
            account_id = int(m.group(1)) - 76561197960265728
            user_dir = STEAM_USERDATA / str(account_id)
            if user_dir.is_dir():
                return user_dir
    users = [p for p in STEAM_USERDATA.glob("*") if p.is_dir() and p.name != "0"]
    if not users:
        return None
    return max(users, key=lambda p: p.stat().st_mtime)


def _shortcuts_path() -> Path | None:
    user_dir = _active_userdata()
    return user_dir / SHORTCUTS_VDF if user_dir else None


def _compute_shortcut_appid(name: str, exe: str) -> int:
    return zlib.crc32((exe + name).encode("utf-8")) | 0x80000000


def find_existing_appid(exe: Path) -> int | None:
    path = _shortcuts_path()
    if path is None or not path.exists():
        return None
    try:
        parsed = _parse_vdf(path.read_bytes())
    except Exception:
        return None
    exe_str = str(exe)
    for entry in parsed.get("shortcuts", {}).values():
        entry_exe = entry.get("exe", "").strip('"')
        if entry_exe == exe_str:
            return entry.get("appid")
    return None


def _list_protons() -> list[dict]:
    protons: list[dict] = []
    for dirname, internal, display in PROTON_BUILTIN:
        binary = STEAM_COMMON / dirname / "proton"
        if binary.exists():
            protons.append({"display": display, "internal": internal, "binary": binary})

    if STEAM_COMPAT_TOOLS_D.exists():
        for d in sorted(STEAM_COMPAT_TOOLS_D.iterdir()):
            binary = d / "proton"
            vdf = d / "compatibilitytool.vdf"
            if not binary.exists() or not vdf.exists():
                continue
            text = vdf.read_text(errors="replace")
            m = re.search(r'"compat_tools"\s*\{\s*"([^"]+)"', text)
            if not m:
                continue
            internal = m.group(1)
            display_m = re.search(r'"display_name"\s+"([^"]+)"', text)
            display = display_m.group(1) if display_m else internal
            protons.append({"display": display, "internal": internal, "binary": binary})

    return protons


def select_proton() -> dict | None:
    protons = _list_protons()
    if not protons:
        step_warn("No Proton found")
        return None
    labels = [p["display"] for p in protons] + ["Back"]
    pick = select("Pick Proton", labels)
    if pick is None or pick == len(labels) - 1:
        return None
    return protons[pick]


def _add_shortcut(appid: int, name: str, exe: Path, start_dir: Path, icon: Path | None = None) -> bool:
    path = _shortcuts_path()
    if path is None:
        return False

    parsed = _parse_vdf(path.read_bytes()) if path.exists() else {"shortcuts": {}}
    shortcuts = parsed.setdefault("shortcuts", {})
    icon_value = str(icon) if icon else ""

    for idx, entry in shortcuts.items():
        if entry.get("appid") == appid:
            entry["appname"] = name
            entry["exe"] = str(exe)
            entry["StartDir"] = str(start_dir)
            entry["icon"] = icon_value
            entry["AllowOverlay"] = 0
            path.write_bytes(_serialize_vdf(parsed))
            return True

    new_index = str(max((int(k) for k in shortcuts.keys() if k.isdigit()), default=-1) + 1)
    shortcuts[new_index] = {
        "appid": appid,
        "appname": name,
        "exe": str(exe),
        "StartDir": str(start_dir),
        "icon": icon_value,
        "ShortcutPath": "",
        "LaunchOptions": "",
        "IsHidden": 0,
        "AllowDesktopConfig": 1,
        "AllowOverlay": 0,
        "OpenVR": 0,
        "Devkit": 0,
        "DevkitGameID": "",
        "DevkitOverrideAppID": 0,
        "LastPlayTime": 0,
        "FlatpakAppID": "",
        "sortas": "",
        "tags": {},
    }
    path.write_bytes(_serialize_vdf(parsed))
    return True


def _set_compat_tool(appid: int, internal_name: str) -> bool:
    if not STEAM_CONFIG_VDF.exists():
        return False

    text = STEAM_CONFIG_VDF.read_text()

    block_match = re.search(r'"CompatToolMapping"\s*\{', text)
    if not block_match:
        return False
    block_start = block_match.end()
    depth = 1
    pos = block_start
    while depth > 0 and pos < len(text):
        if text[pos] == '{':
            depth += 1
        elif text[pos] == '}':
            depth -= 1
        pos += 1
    if depth != 0:
        return False
    block_end = pos - 1
    block_inner = text[block_start:block_end]

    entry = (
        f'\t\t\t\t\t"{appid}"\n'
        f'\t\t\t\t\t{{\n'
        f'\t\t\t\t\t\t"name"\t\t"{internal_name}"\n'
        f'\t\t\t\t\t\t"config"\t\t""\n'
        f'\t\t\t\t\t\t"priority"\t\t"250"\n'
        f'\t\t\t\t\t}}'
    )

    existing = re.search(
        rf'\t*"{re.escape(str(appid))}"\s*\{{[^}}]*\}}',
        block_inner,
    )
    if existing:
        new_inner = block_inner[:existing.start()] + entry + block_inner[existing.end():]
    else:
        new_inner = "\n" + entry + block_inner

    STEAM_CONFIG_VDF.write_text(text[:block_start] + new_inner + text[block_end:])
    return True


def _write_grid_artwork(appid: int, logo: Path | None, hero: Path | None) -> None:
    user = _active_userdata()
    if user is None:
        return
    grid = user / "config" / "grid"
    grid.mkdir(parents=True, exist_ok=True)
    if logo and logo.exists():
        shutil.copy2(logo, grid / f"{appid}_logo{logo.suffix}")
        position = {
            "nVersion": 1,
            "logoPosition": {
                "pinnedPosition": "BottomLeft",
                "nWidthPct": 30,
                "nHeightPct": 30,
            },
        }
        (grid / f"{appid}.json").write_text(json.dumps(position))
    if hero and hero.exists():
        shutil.copy2(hero, grid / f"{appid}_hero{hero.suffix}")


def _ce_installed_in_prefix(appid: int) -> bool:
    return (STEAM_COMPATDATA / str(appid) / "pfx/drive_c/Program Files/Cheat Engine/cheatengine-x86_64.exe").exists()


def _install_ce_in_prefix(proton: dict, appid: int) -> int:
    env = {
        **os.environ,
        "STEAM_COMPAT_DATA_PATH": str(STEAM_COMPATDATA / str(appid)),
        "STEAM_COMPAT_CLIENT_INSTALL_PATH": str(STEAM_DIR),
    }
    (STEAM_COMPATDATA / str(appid)).mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [str(proton["binary"]), "run", str(CE_INSTALLER)],
        env=env,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode


def screen_delete_prefix(downloads: list[dict]) -> None:
    eligible: list[tuple[str, int, Path]] = []
    for target in local_downloads():
        resolved = resolve_install(target.name, downloads)
        if resolved is None:
            continue
        download, is_hm = resolved
        launcher = target / launcher_name(is_hm)
        appid = find_existing_appid(launcher)
        if appid is None:
            continue
        prefix = STEAM_COMPATDATA / str(appid)
        if not (prefix / "pfx").exists():
            continue
        display_name = hm_display_name(download) if is_hm else download["label"]
        eligible.append((display_name, appid, prefix))

    if not eligible:
        screen_header("Delete prefix")
        print()
        step_warn("No prefixes found")
        go_back()
        return

    while True:
        labels = [label for label, _, _ in eligible] + ["Back"]
        pick = select("Delete prefix", labels)
        if pick is None or pick == len(labels) - 1:
            return

        label, appid, prefix = eligible[pick]
        clear()
        screen_header(mag(label))
        if not wait_for_game_closed(mag(label)):
            continue
        step_warn("This permanently deletes the Proton prefix")
        print()
        if not confirm("Continue?", default=False):
            continue

        with Spinner("Deleting prefix") as sp:
            try:
                shutil.rmtree(prefix)
                sp.succeed("Prefix deleted")
            except OSError as e:
                sp.fail(f"Could not delete prefix — {e}")
                continue

        del eligible[pick]
        if not eligible:
            return


def apply_steam_setup(name: str, exe: Path, start_dir: Path, proton: dict, install_ce: bool, icon: Path | None = None, logo: Path | None = None, hero: Path | None = None) -> bool:
    if _is_steam_running():
        step_warn("Close Steam to apply")
        return False

    if _active_userdata() is None:
        step_fail("No Steam account found")
        return False

    appid = find_existing_appid(exe) or _compute_shortcut_appid(name, str(exe))

    if not _add_shortcut(appid, name, exe, start_dir, icon):
        step_fail("Could not write shortcuts.vdf")
        return False
    if not _set_compat_tool(appid, proton["internal"]):
        step_fail("Could not update config.vdf")
        return False

    _write_grid_artwork(appid, logo, hero)

    if install_ce:
        if _ce_installed_in_prefix(appid):
            step_pass("Cheat Engine already installed")
        else:
            with Spinner("Installing Cheat Engine") as sp:
                rc = _install_ce_in_prefix(proton, appid)
                if rc != 0:
                    sp.fail("Cheat Engine install failed — will install on first run")
                else:
                    sp.succeed("Cheat Engine installed")

    return True
