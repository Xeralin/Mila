import json
import os
import re
import shutil
import subprocess
import zlib
from pathlib import Path

from app.constants import (
    PROTON_BUILTIN,
    SHORTCUTS_VDF,
    STEAM_COMMON,
    STEAM_COMPATDATA,
    STEAM_COMPAT_TOOLS_D,
    STEAM_CONFIG_VDF,
    STEAM_DIR,
    STEAM_USERDATA,
)
from app.input import confirm, go_back, select
from app.manifest import (
    hm_display_name,
    installed_downloads,
    launcher_name,
    resolve_install,
)
from app.spinner import Spinner
from app.style import clear, mag, render_header, step_fail, step_warn


def is_steam_running() -> bool:
    try:
        return subprocess.run(
            ["pgrep", "-x", "steam"], capture_output=True
        ).returncode == 0
    except FileNotFoundError:
        return False


def is_game_running() -> bool:
    try:
        return subprocess.run(
            ["pgrep", "-f", r"RainbowSix.*\.exe"], capture_output=True
        ).returncode == 0
    except FileNotFoundError:
        return False


def _wait_for(check_running, title: str, warn_msg: str) -> bool:
    waited = False
    proceed = True
    while check_running():
        clear()
        render_header(title)
        step_warn(warn_msg)
        print()
        waited = True
        if select("", ["Retry", "Back"], clear_first=False) != 0:
            proceed = False
            break
    if waited:
        clear()
        render_header(title)
    return proceed


def wait_for_game_closed(title: str) -> bool:
    return _wait_for(is_game_running, title, "Close the game to continue")


def wait_for_steam_closed(title: str) -> bool:
    return _wait_for(
        is_steam_running, title, "Close Steam completely to apply"
    )


def _parse_vdf(data: bytes) -> dict:
    pos = 0

    def read_string() -> str:
        nonlocal pos
        start = pos
        while pos < len(data) and data[pos] != 0:
            pos += 1
        if pos >= len(data):
            raise ValueError("Truncated string in binary VDF")
        s = data[start:pos].decode("utf-8", errors="replace")
        pos += 1
        return s

    def read_int(size: int) -> int:
        nonlocal pos
        if pos + size > len(data):
            raise ValueError("Truncated integer in binary VDF")
        value = int.from_bytes(data[pos:pos + size], "little", signed=False)
        pos += size
        return value

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
                result[key] = read_int(4)
            elif t == 0x07:
                result[key] = read_int(8)
            else:
                raise ValueError(f"Unknown type byte 0x{t:02x} in binary VDF")
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


def _backup_and_write(path: Path, data: bytes) -> None:
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _active_userdata() -> Path | None:
    login = STEAM_DIR / "config" / "loginusers.vdf"
    if login.exists():
        text = login.read_text(errors="replace")
        for m in re.finditer(r'"(\d{17})"\s*\{[^}]*?"MostRecent"\s*"1"', text):
            account_id = int(m.group(1)) - 76561197960265728
            user_dir = STEAM_USERDATA / str(account_id)
            if user_dir.is_dir():
                return user_dir
    users = [
        p for p in STEAM_USERDATA.glob("*")
        if p.is_dir() and p.name != "0"
    ]
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


def list_protons() -> list[dict]:
    protons: list[dict] = []
    for dirname, internal, display in PROTON_BUILTIN:
        binary = STEAM_COMMON / dirname / "proton"
        if binary.exists():
            protons.append(
                {"display": display, "internal": internal, "binary": binary}
            )

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
            protons.append(
                {"display": display, "internal": internal, "binary": binary}
            )

    return protons


def select_proton() -> dict | None:
    protons = list_protons()
    if not protons:
        step_warn("No Proton found")
        return None
    labels = [p["display"] for p in protons] + ["Back"]
    pick = select("Pick Proton", labels)
    if pick is None or pick == len(labels) - 1:
        return None
    return protons[pick]


def _compat_tool_for(appid: int) -> str | None:
    if not STEAM_CONFIG_VDF.exists():
        return None
    text = STEAM_CONFIG_VDF.read_text(errors="replace")
    block = re.search(r'"CompatToolMapping"\s*\{', text)
    if not block:
        return None
    m = re.search(
        rf'"{re.escape(str(appid))}"\s*\{{[^}}]*?"name"\s*"([^"]*)"',
        text[block.end():],
    )
    if not m:
        return None
    return m.group(1) or None


def proton_for_appid(appid: int) -> dict | None:
    internal = _compat_tool_for(appid)
    if internal is None:
        return None
    for proton in list_protons():
        if proton["internal"] == internal:
            return proton
    return None


def proton_run(proton: dict, prefix: Path, exe: Path) -> bool:
    env = {
        **os.environ,
        "STEAM_COMPAT_DATA_PATH": str(prefix),
        "STEAM_COMPAT_CLIENT_INSTALL_PATH": str(STEAM_DIR),
    }
    try:
        return subprocess.run(
            [str(proton["binary"]), "run", str(exe)], env=env, check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _add_shortcut(
    appid: int,
    name: str,
    exe: Path,
    start_dir: Path,
    icon: Path | None = None,
) -> bool:
    path = _shortcuts_path()
    if path is None:
        return False

    if path.exists():
        try:
            parsed = _parse_vdf(path.read_bytes())
        except Exception:
            return False
    else:
        parsed = {"shortcuts": {}}
    shortcuts = parsed.setdefault("shortcuts", {})
    icon_value = str(icon) if icon else ""

    for entry in shortcuts.values():
        if entry.get("appid") == appid:
            entry["appname"] = name
            entry["exe"] = f'"{exe}"'
            entry["StartDir"] = f'"{start_dir}"'
            entry["icon"] = icon_value
            entry["AllowOverlay"] = 0
            _backup_and_write(path, _serialize_vdf(parsed))
            return True

    new_index = str(
        max((int(k) for k in shortcuts if k.isdigit()), default=-1) + 1
    )
    shortcuts[new_index] = {
        "appid": appid,
        "appname": name,
        "exe": f'"{exe}"',
        "StartDir": f'"{start_dir}"',
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
    _backup_and_write(path, _serialize_vdf(parsed))
    return True


def _set_compat_tool(appid: int, internal_name: str) -> bool:
    if not STEAM_CONFIG_VDF.exists():
        return False

    text = STEAM_CONFIG_VDF.read_text(errors="replace")

    block_match = re.search(r'"CompatToolMapping"\s*\{', text)
    if not block_match:
        steam_match = re.search(r'"Steam"\s*\{', text, re.IGNORECASE)
        if not steam_match:
            return False
        insert_at = steam_match.end()
        text = (
            text[:insert_at]
            + '\n\t\t\t\t"CompatToolMapping"\n\t\t\t\t{\n\t\t\t\t}'
            + text[insert_at:]
        )
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
        new_inner = (
            block_inner[:existing.start()]
            + entry
            + block_inner[existing.end():]
        )
    else:
        new_inner = "\n" + entry + block_inner

    new_text = text[:block_start] + new_inner + text[block_end:]
    _backup_and_write(STEAM_CONFIG_VDF, new_text.encode("utf-8"))
    return True


def _write_grid_artwork(appid: int, logo: Path | None) -> None:
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


def screen_delete_prefix(downloads: list[dict]) -> None:
    eligible: list[tuple[str, int, Path]] = []
    for target in installed_downloads():
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
        display_name = (
            hm_display_name(download) if is_hm else download["label"]
        )
        eligible.append((display_name, appid, prefix))

    if not eligible:
        render_header("Delete prefix")
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
        render_header(mag(label))
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


def apply_steam_setup(
    name: str,
    exe: Path,
    start_dir: Path,
    proton: dict,
    icon: Path | None = None,
    logo: Path | None = None,
) -> bool:
    if is_steam_running():
        step_warn("Close Steam completely to apply")
        return False

    if _active_userdata() is None:
        step_fail("No Steam account found")
        return False

    appid = find_existing_appid(exe) or _compute_shortcut_appid(name, str(exe))

    if not _set_compat_tool(appid, proton["internal"]):
        step_fail("Could not update config.vdf")
        return False
    if not _add_shortcut(appid, name, exe, start_dir, icon):
        step_fail("Could not write shortcuts.vdf")
        return False

    _write_grid_artwork(appid, logo)

    return True
