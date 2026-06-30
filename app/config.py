import fcntl
import os
import tomllib
from typing import TextIO, TypeVar

from app.constants import CONFIG_FILE, LOCK_FILE
from app.style import step_warn

T = TypeVar("T")


def acquire_single_instance_lock() -> TextIO | None:
    fp = open(LOCK_FILE, "w")
    try:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fp.close()
        return None
    return fp


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError:
        broken = CONFIG_FILE.with_name(CONFIG_FILE.name + ".broken")
        CONFIG_FILE.replace(broken)
        step_warn(
            f"settings.toml is malformed — saved as {broken.name}, "
            "starting with defaults"
        )
        return {}


def save_config(cfg: dict) -> None:
    lines = ["[settings]"]
    s = cfg.get("settings", {})
    for k, v in s.items():
        if isinstance(v, str):
            lines.append(f"{k} = '{v}'")
        elif isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        else:
            lines.append(f"{k} = {v}")
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_name(CONFIG_FILE.name + ".tmp")
    tmp.write_text("\n".join(lines) + "\n")
    os.replace(tmp, CONFIG_FILE)


def get_setting(cfg: dict, key: str, default: T) -> T:
    return cfg.get("settings", {}).get(key, default)


def set_setting(cfg: dict, key: str, value: object) -> None:
    cfg.setdefault("settings", {})[key] = value
