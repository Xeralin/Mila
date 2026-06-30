#!/usr/bin/env python3

import shutil
import sys

if sys.version_info < (3, 11):
    sys.exit("Downloader requires Python 3.11 or newer")

from app.constants import (
    DEFAULT_USERNAME,
    DOWNLOADS_DIR,
    PROJECT_ROOT,
    VERSION,
)
from app.style import (
    clear,
    fmt_bytes,
    line,
    render_header,
    step_fail,
    step_warn,
)
from app.spinner import Spinner
from app.input import go_back, select
from app.config import (
    acquire_single_instance_lock,
    get_setting,
    load_config,
    save_config,
    set_setting,
)
from app.manifest import installed_downloads, load_downloads
from app.radmin import detect_radmin_bridge, screen_radmin
from app.downloader import screen_downloader
from app.steam import screen_delete_prefix
from app.heatedmetal import hm_update_available, screen_update_hm
from app.settings import screen_settings
from app.shears import screen_shears
from app.cheatengine import screen_cheatengine
from app.liberator import screen_liberator
from app.verify import screen_verify
from app.help import screen_help
from app import update


def _screen_tools(cfg: dict, downloads: list[dict]) -> None:
    actions = [
        ("Verify",           lambda: screen_verify(cfg, downloads)),
        ("Shears",           lambda: screen_shears(downloads)),
        ("Toggle Liberator", lambda: screen_liberator(downloads)),
        ("Toggle CE",        lambda: screen_cheatengine(downloads)),
        ("RadminVPN",        lambda: screen_radmin(cfg)),
        ("Delete prefix",    lambda: screen_delete_prefix(downloads)),
    ]
    while True:
        labels = [label for label, _ in actions] + ["Back"]
        pick = select("Tools", labels)
        if pick is None or pick == len(labels) - 1:
            return
        clear()
        actions[pick][1]()


def _install_component(component: update.Component) -> None:
    render_header(f"Update {component.name}")
    success = component.apply()
    go_back()
    if success and component.restart:
        update.restart()


def _screen_info(cfg: dict, downloads: list[dict]) -> None:
    render_header("Info")
    line(f"Version:           {VERSION}")
    line(
        f"Username:          {get_setting(cfg, 'username', DEFAULT_USERNAME)}"
    )
    steam_account = get_setting(cfg, "steam_account", "")
    line(f"Steam account:     {steam_account or 'None'}")
    line()
    line(f"Downloads:         {len(installed_downloads())}")
    try:
        usage = (
            sum(
                f.stat().st_size
                for f in DOWNLOADS_DIR.rglob("*")
                if f.is_file()
            )
            if DOWNLOADS_DIR.exists()
            else 0
        )
        line(f"Disk usage:        {fmt_bytes(usage)}")
    except OSError:
        line("Disk usage:        ?")
    free = shutil.disk_usage(
        DOWNLOADS_DIR if DOWNLOADS_DIR.exists() else PROJECT_ROOT
    ).free
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
        screen_update_hm(cfg, downloads)
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
        except Exception as e:
            step_fail(f"Unexpected error — {e}")
            go_back()


def main() -> int:
    lock_fp = acquire_single_instance_lock()
    if lock_fp is None:
        step_fail("Downloader is already running")
        return 1
    try:
        cfg = load_config()
        if not get_setting(cfg, "radmin_ip", ""):
            rip = detect_radmin_bridge()
            if rip:
                set_setting(cfg, "radmin_ip", rip)
                save_config(cfg)
        downloads = load_downloads()
        _screen_main(cfg, downloads)
    except KeyboardInterrupt:
        print()
        step_warn("Interrupted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
