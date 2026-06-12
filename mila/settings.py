import json
import shutil
from pathlib import Path

from mila.constants import (
    BIN_DIR,
    DD_BIN,
    DEFAULT_MAX_DOWNLOADS,
    DEFAULT_USERNAME,
    DOWNLOAD_SPEED_PRESETS,
    HELIOS_JSON,
    HM_BIN_DIR,
    LIBERATOR_GLOB,
    MAX_USERNAME_LENGTH,
    NAME_PATTERN,
    SEVENZ_BIN,
    THROWBACK_DIR,
    THROWBACK_EXTRACT,
    THROWBACK_TOML,
)
from mila.style import C, clear, line, mag, screen_header, step_fail, step_pass, step_warn
from mila.input import ask, confirm, go_back, select
from mila.spinner import Spinner
from mila.config import get_setting, save_config, set_setting
from mila.throwback import write_throwback_toml
from mila.manifest import display_name, installed_downloads, installed_username
from mila.rpc import is_discord_installed, start_daemon, stop_daemon
from mila.liberator import screen_liberator


def _depot_token_stores(iso_dir: Path) -> list[Path]:
    return sorted({p.parent.parent for p in iso_dir.rglob("AssemFiles/account.config")})


def wipe_depot_token() -> tuple[bool, list[str]]:
    iso_dir = Path.home() / ".local" / "share" / "IsolatedStorage"
    stores = _depot_token_stores(iso_dir) if iso_dir.exists() else []
    if not stores:
        return False, []
    errors = []
    for store in stores:
        try:
            shutil.rmtree(store)
        except OSError as e:
            errors.append(f"Could not remove {store} — {e}")
    return True, errors


def write_download_username(d: Path, username: str) -> bool:
    if (d / THROWBACK_TOML).exists():
        write_throwback_toml(d, username)
        return True
    json_path = d / HELIOS_JSON
    if json_path.exists():
        try:
            config = json.loads(json_path.read_text())
        except (json.JSONDecodeError, OSError):
            return False
        config["Username"] = username
        json_path.write_text(json.dumps(config, indent=2))
        return True
    return False


def _prompt_new_username(current: str) -> str | None:
    line(f"Current: {current}")
    new = ask("Enter the new username")
    if not new:
        return None
    if not NAME_PATTERN.match(new) or len(new) > MAX_USERNAME_LENGTH:
        step_fail("Invalid username")
        go_back()
        return None
    if new == current:
        step_pass(f"Username already set to {new}")
        go_back()
        return None
    return new


def _change_username_default(cfg: dict, installs: list[Path], downloads: list[dict]) -> None:
    screen_header("Change username — default")
    current = get_setting(cfg, "username", DEFAULT_USERNAME)
    new = _prompt_new_username(current)
    if new is None:
        return
    clear()
    screen_header("Change username — default")
    set_setting(cfg, "username", new)
    save_config(cfg)
    step_pass(f"Default set: {new}")
    for d in installs:
        name = display_name(d.name, downloads)
        with Spinner(f"Updating {name}") as sp:
            try:
                ok = write_download_username(d, new)
            except OSError as e:
                sp.fail(f"{name} — {e}")
                continue
            if ok:
                sp.succeed(name)
            else:
                sp.fail(f"{name} — username file is missing or corrupt")
    go_back()


def _change_username_one(d: Path, downloads: list[dict]) -> None:
    name = display_name(d.name, downloads)
    screen_header(f"Change username — {mag(name)}")
    current = installed_username(d)
    new = _prompt_new_username(current)
    if new is None:
        return
    clear()
    screen_header(f"Change username — {mag(name)}")
    with Spinner(f"Updating {name}") as sp:
        try:
            ok = write_download_username(d, new)
        except OSError as e:
            sp.fail(f"Update failed — {e}")
        else:
            if ok:
                sp.succeed(f"Saved: {new}")
            else:
                sp.fail("Username file is missing or corrupt")
    go_back()


def screen_change_username(cfg: dict, downloads: list[dict]) -> None:
    while True:
        installs = installed_downloads()
        current_default = get_setting(cfg, "username", DEFAULT_USERNAME)
        labels = [f"{'Default':<20}{current_default:>8}"]
        labels += [f"{display_name(d.name, downloads):<20}{installed_username(d):>8}" for d in installs]
        labels.append("Back")
        pick = select("Change username", labels)
        if pick is None or pick == len(labels) - 1:
            return
        clear()
        if pick == 0:
            _change_username_default(cfg, installs, downloads)
        else:
            _change_username_one(installs[pick - 1], downloads)


def screen_logout(cfg: dict) -> None:
    screen_header("Log out")
    step_warn("This wipes the cached DepotDownloader access token")
    line("Your next download will require password and Steam Guard entry")
    print()
    if not confirm("Continue?", default=False):
        return
    clear()
    screen_header("Log out")
    cfg.get("settings", {}).pop("steam_account", None)
    save_config(cfg)
    found, errors = wipe_depot_token()
    if not found:
        step_warn("No DepotDownloader token found — nothing to remove")
        go_back()
        return
    for err in errors:
        step_fail(err)
    if not errors:
        step_pass("Logged out")
    go_back()


def screen_set_download_speed(cfg: dict) -> None:
    current_value = get_setting(cfg, "max_downloads", DEFAULT_MAX_DOWNLOADS)
    options = [label for label, _ in DOWNLOAD_SPEED_PRESETS] + ["Back"]
    indices = {v: i for i, (_, v) in enumerate(DOWNLOAD_SPEED_PRESETS)}
    current = indices.get(current_value, indices[DEFAULT_MAX_DOWNLOADS])
    pick = select("Set download speed", options, current=current)
    if pick is None or pick == len(options) - 1:
        return
    clear()
    screen_header("Set download speed")
    label, value = DOWNLOAD_SPEED_PRESETS[pick]
    set_setting(cfg, "max_downloads", value)
    save_config(cfg)
    step_pass(f"Download speed set: {label} ({value})")
    go_back()


def screen_clear_cache() -> None:
    screen_header("Clear download cache")
    step_warn("This wipes the cache — everything is fetched from upstream next time")
    print()
    if not confirm("Continue?", default=False):
        return
    clear()
    screen_header("Clear download cache")
    with Spinner("Clearing cache") as sp:
        DD_BIN.unlink(missing_ok=True)
        SEVENZ_BIN.unlink(missing_ok=True)
        for name in THROWBACK_EXTRACT:
            (THROWBACK_DIR / name).unlink(missing_ok=True)
        for exe in BIN_DIR.glob(LIBERATOR_GLOB):
            exe.unlink(missing_ok=True)
        shutil.rmtree(HM_BIN_DIR, ignore_errors=True)
        sp.succeed("Cache cleared")
    go_back()


def _rpc_label(cfg: dict) -> str:
    enabled = get_setting(cfg, "discord_rpc", False)
    mark = f"{C.MAG}✓{C.R}" if enabled else f"{C.ORN}✗{C.R}"
    return f"Discord RPC  {mark}"


def _toggle_discord_rpc(cfg: dict) -> str:
    enabled = not get_setting(cfg, "discord_rpc", False)
    if enabled and not is_discord_installed():
        return f"Discord not installed  {C.ORN}✗{C.R}"
    set_setting(cfg, "discord_rpc", enabled)
    save_config(cfg)
    if enabled:
        start_daemon()
    else:
        stop_daemon()
    return _rpc_label(cfg)


def screen_settings(cfg: dict, downloads: list[dict]) -> None:
    current = 0
    while True:
        actions = [
            ("Change username",      lambda: screen_change_username(cfg, downloads)),
            ("Toggle Liberator",     lambda: screen_liberator(downloads)),
            (_rpc_label(cfg),        lambda: _toggle_discord_rpc(cfg)),
            ("Clear download cache", screen_clear_cache),
            ("Set download speed",   lambda: screen_set_download_speed(cfg)),
        ]
        labels = [label for label, _ in actions] + ["Back"]
        pick = select("Settings", labels, current=current, toggles={2: actions[2][1]})
        if pick is None or pick == len(labels) - 1:
            return
        current = pick
        clear()
        actions[pick][1]()
