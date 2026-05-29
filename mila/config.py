import tomllib
from typing import TypeVar

from mila.constants import CONFIG_FILE

T = TypeVar("T")


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError:
        return {}


def save_config(cfg: dict) -> None:
    lines = ["[settings]"]
    s = cfg.get("settings", {})
    for k, v in s.items():
        if isinstance(v, str):
            esc = v.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{k} = "{esc}"')
        elif isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        else:
            lines.append(f"{k} = {v}")
    CONFIG_FILE.write_text("\n".join(lines) + "\n")


def get_setting(cfg: dict, key: str, default: T) -> T:
    return cfg.get("settings", {}).get(key, default)


def set_setting(cfg: dict, key: str, value: object) -> None:
    cfg.setdefault("settings", {})[key] = value
