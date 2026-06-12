import os
import re
import shutil
import sys
import termios
import tty
from collections.abc import Callable
from select import select as _readable

from mila.config import get_setting, save_config, set_setting
from mila.constants import NAME_PATTERN
from mila.style import C, clear, cursor_up, heading, step_fail

_ANSI_SEQ = re.compile(r"\033\[[0-9;?]*[A-Za-z]")
_ARROWS = {"A": "up", "B": "down", "C": "right", "D": "left"}
_ESC_TIMEOUT = 0.05
_SEQ_TIMEOUT = 0.2
_SEQ_MAX = 16


def _next_byte(fd: int, timeout: float) -> str | None:
    if not _readable([fd], [], [], timeout)[0]:
        return None
    data = os.read(fd, 1)
    if not data:
        return None
    return data.decode(errors="ignore")


def _read_escape(fd: int) -> str | None:
    first = _next_byte(fd, _ESC_TIMEOUT)
    if first is None:
        return "left"
    if first == "O":
        final = _next_byte(fd, _SEQ_TIMEOUT)
        return _ARROWS.get(final or "")
    if first != "[":
        return None
    for _ in range(_SEQ_MAX):
        b = _next_byte(fd, _SEQ_TIMEOUT)
        if not b:
            return None
        if b == "~":
            return None
        if b.isascii() and b.isalpha():
            return _ARROWS.get(b)
    return None


def _read_key() -> str | None:
    if not sys.stdin.isatty():
        try:
            entered = input().strip().lower()
        except EOFError:
            return "ctrl-c"
        match entered:
            case "":
                return "enter"
            case "w":
                return "up"
            case "a":
                return "left"
            case "s":
                return "down"
            case "d":
                return "right"
            case _:
                return entered
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1).decode(errors="ignore")
        match ch:
            case "\x1b":
                return _read_escape(fd)
            case "\r" | "\n":
                return "enter"
            case "\x03":
                return "ctrl-c"
            case "w":
                return "up"
            case "a":
                return "left"
            case "s":
                return "down"
            case "d":
                return "right"
            case _:
                return ch
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
            case "":
                return default
            case "y" | "yes":
                return True
            case "n" | "no":
                return False


def _fit(text: str, limit: int) -> str:
    if limit < 4 or len(_ANSI_SEQ.sub("", text)) <= limit:
        return text
    out: list[str] = []
    visible = 0
    i = 0
    while visible < limit - 1:
        m = _ANSI_SEQ.match(text, i)
        if m:
            out.append(m.group())
            i = m.end()
        else:
            out.append(text[i])
            visible += 1
            i += 1
    return "".join(out) + "…" + C.R


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
            sys.stdout.write(cursor_up(rendered))
        sys.stdout.write(C.CLEAR_DOWN)
        limit = shutil.get_terminal_size().columns - 1
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
        sys.stdout.write("\n".join(_fit(row, limit) for row in out) + "\n")
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
