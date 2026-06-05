import os
import sys
import termios
import tty
from collections.abc import Callable
from select import select as _readable

from mila.config import get_setting, save_config, set_setting
from mila.constants import NAME_PATTERN
from mila.style import C, clear, heading, step_fail


def _read_key() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1).decode(errors="ignore")
        match ch:
            case "\x1b":
                if not _readable([fd], [], [], 0.05)[0]:
                    return "left"
                seq = os.read(fd, 2).decode(errors="ignore")
                match seq:
                    case "[A" | "OA": return "up"
                    case "[B" | "OB": return "down"
                    case "[C" | "OC": return "right"
                    case "[D" | "OD": return "left"
                    case _:           return "left"
            case "\r" | "\n": return "enter"
            case "\x03":      return "ctrl-c"
            case "w":         return "up"
            case "a":         return "left"
            case "s":         return "down"
            case "d":         return "right"
            case _:           return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def go_back() -> None:
    print()
    sys.stdout.write(f"   {C.CYN}▸{C.R} {C.UNDER}Back{C.UNDER_OFF}")
    sys.stdout.write(C.HIDE_CURSOR)
    sys.stdout.flush()
    try:
        while True:
            match _read_key():
                case "enter" | "left" | "right" | "ctrl-c":
                    return
    finally:
        sys.stdout.write(C.SHOW_CURSOR + "\n")
        sys.stdout.flush()


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" ({default})" if default else ""
    try:
        out = input(f"     {prompt}{suffix} › ").strip()
    except EOFError:
        return default or ""
    return out or (default or "")


def prompt_steam_account(cfg: dict) -> str | None:
    stored = get_setting(cfg, "steam_account", "")
    account = ask("Enter your Steam account", default=stored or None)
    if not account:
        step_fail("No Steam account entered")
        return None
    if not NAME_PATTERN.match(account):
        step_fail("Invalid Steam account")
        return None
    set_setting(cfg, "steam_account", account)
    save_config(cfg)
    return account


def confirm(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            answer = input(f"     {prompt} {hint} › ").strip().lower()
        except EOFError:
            return default
        match answer:
            case "":             return default
            case "y" | "yes":    return True
            case "n" | "no":     return False


def select(title: str, options: list[str], current: int = 0, clear_first: bool = True,
           toggles: dict[int, Callable[[], str]] | None = None) -> int | None:
    if not sys.stdin.isatty():
        if title:
            heading(title)
        else:
            print()
        for i, opt in enumerate(options, 1):
            print(f"  {i:>2}  {opt}")
        print()
        raw = ask("What is your selection?")
        if not raw.isdigit():
            return None
        n = int(raw) - 1
        return n if 0 <= n < len(options) else None

    SCROLL_SIZE = 6
    n = len(options)
    selected = current
    window_start = 0
    rendered = 0

    def render() -> None:
        nonlocal rendered, window_start
        if rendered:
            sys.stdout.write(f"\033[{rendered}A")
        sys.stdout.write(C.CLEAR_DOWN)
        prompt = title or "What would you like to do?"
        if n <= SCROLL_SIZE:
            window_start = 0
        else:
            if selected < window_start:
                window_start = selected
            elif selected >= window_start + SCROLL_SIZE:
                window_start = selected - SCROLL_SIZE + 1
            window_start = max(0, min(window_start, n - SCROLL_SIZE))
        window_end = min(n, window_start + SCROLL_SIZE)
        if clear_first:
            out = [
                "Use the arrow keys to navigate: ↓ ↑ → ←",
                f"{C.YEL}?{C.R} {prompt}",
            ]
        else:
            out = []
        for i in range(window_start, window_end):
            opt = options[i]
            if i == window_start and window_start > 0:
                left = "↑"
            elif i == window_end - 1 and window_end < n:
                left = "↓"
            else:
                left = " "
            if i == selected:
                out.append(f"{left}  {C.CYN}▸{C.R} {C.UNDER}{opt}{C.UNDER_OFF}")
            else:
                out.append(f"{left}    {opt}")
        sys.stdout.write("\n".join(out) + "\n")
        sys.stdout.flush()
        rendered = len(out)

    if clear_first:
        clear()
    sys.stdout.write(C.HIDE_CURSOR + C.NORMAL_KEYS)
    sys.stdout.flush()
    try:
        render()
        while True:
            match _read_key():
                case "up":
                    selected = (selected - 1) % len(options)
                    render()
                case "down":
                    selected = (selected + 1) % len(options)
                    render()
                case "right" | "enter":
                    if toggles and selected in toggles:
                        options[selected] = toggles[selected]()
                        render()
                        continue
                    return selected
                case "left" | "ctrl-c":
                    return None
    finally:
        sys.stdout.write(C.SHOW_CURSOR)
        sys.stdout.flush()
