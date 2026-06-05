#!/usr/bin/env python3

import fcntl
import shutil
import sys
from typing import TextIO

if sys.version_info < (3, 11):
    sys.exit("Mila requires Python 3.11 or newer")

from mila.constants import CE_INSTALLER, CONFIG_FILE, DEFAULT_USERNAME, DOWNLOADS_DIR, LOCK_FILE, PROJECT_ROOT, VERSION
from mila.style import C, clear, fmt_bytes, line, orn, screen_header, step_fail, step_warn
from mila.spinner import Spinner
from mila.input import go_back, select
from mila.config import get_setting, load_config, save_config, set_setting
from mila.manifest import installed_downloads, load_downloads
from mila.radmin import detect_radmin_bridge, screen_radmin
from mila.rpc import is_discord_installed, start_daemon
from mila.downloader import screen_downloader
from mila.steam import screen_delete_prefix
from mila.heatedmetal import hm_update_available, screen_update_heatedmetal
from mila.settings import screen_settings
from mila.shears import screen_shears
from mila.verify import screen_verify
from mila.help import screen_help
from mila import update


def _screen_tools(cfg: dict, downloads: list[dict]) -> None:
    actions = [
        ("Verify",             lambda: screen_verify(cfg, downloads)),
        ("Shears",             lambda: screen_shears(downloads)),
        ("Update Heated Metal", lambda: screen_update_heatedmetal(cfg, downloads)),
        ("RadminVPN",          lambda: screen_radmin(cfg)),
        ("Delete prefix",      lambda: screen_delete_prefix(downloads)),
    ]
    while True:
        labels = [label for label, _ in actions] + ["Back"]
        pick = select("Tools", labels)
        if pick is None or pick == len(labels) - 1:
            return
        clear()
        actions[pick][1]()


def _install_component(component: update.Component) -> None:
    screen_header(f"Update {component.name}")
    success = component.apply()
    go_back()
    if success and component.restart:
        update.restart()


def _screen_info(cfg: dict, downloads: list[dict]) -> None:
    screen_header("Info")
    line(f"Version:           {VERSION}")
    line(f"Username:          {get_setting(cfg, 'username', DEFAULT_USERNAME)}")
    steam_account = get_setting(cfg, "steam_account", "")
    line(f"Steam account:     {steam_account or 'None'}")
    if CE_INSTALLER.exists():
        unlock_marker = f"{C.MAG}✓{C.R} ready"
    else:
        unlock_marker = f"{C.YEL}⚠{C.R} needs {orn('CheatEngine.exe')} in {orn('bin/')}"
    line(f"Unlock-All:        {unlock_marker}")
    line()
    line(f"Downloads:         {len(installed_downloads())}")
    usage = sum(f.stat().st_size for f in DOWNLOADS_DIR.rglob("*") if f.is_file()) if DOWNLOADS_DIR.exists() else 0
    line(f"Disk usage:        {fmt_bytes(usage)}")
    free = shutil.disk_usage(DOWNLOADS_DIR if DOWNLOADS_DIR.exists() else PROJECT_ROOT).free
    line(f"Free disk space:   {fmt_bytes(free)}")
    line()
    with Spinner("Checking for updates"):
        updates = update.available()
        hm = hm_update_available(downloads)
    options = [f"Update {c.name} to {c.target}" for c in updates]
    if hm:
        options.append("Update Heated Metal")
    options.append("Back")
    pick = select("", options, clear_first=False)
    if pick is None or options[pick] == "Back":
        return
    clear()
    if hm and pick == len(updates):
        screen_update_heatedmetal(cfg, downloads)
    else:
        _install_component(updates[pick])


def _screen_main(cfg: dict, downloads: list[dict]) -> None:
    actions = [
        ("Game downloader",   lambda: screen_downloader(cfg, downloads)),
        ("Settings",          lambda: screen_settings(cfg, downloads)),
        ("Tools",             lambda: _screen_tools(cfg, downloads)),
        ("Help",              lambda: screen_help(cfg)),
        ("Info",              lambda: _screen_info(cfg, downloads)),
        ("Exit",              None),
    ]
    while True:
        labels = [a[0] for a in actions]
        pick = select("", labels)
        if pick is None or actions[pick][1] is None:
            return
        clear()
        try:
            actions[pick][1]()
        except KeyboardInterrupt:
            print()
            step_warn("Interrupted")
            go_back()


def _acquire_single_instance_lock() -> TextIO:
    fp = open(LOCK_FILE, "w")
    try:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        step_fail("Mila is already running")
        sys.exit(1)
    return fp


def main() -> int:
    lock_fp = _acquire_single_instance_lock()
    cfg = load_config()
    if not CONFIG_FILE.exists():
        save_config(cfg)
    if not get_setting(cfg, "radmin_ip", ""):
        rip = detect_radmin_bridge()
        if rip:
            set_setting(cfg, "radmin_ip", rip)
            save_config(cfg)
    if get_setting(cfg, "discord_rpc", False) and is_discord_installed():
        start_daemon()
    downloads = load_downloads()

    try:
        _screen_main(cfg, downloads)
    except KeyboardInterrupt:
        print()
        step_warn("Interrupted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
