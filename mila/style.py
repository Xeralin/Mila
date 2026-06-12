import os
import sys

_TTY = sys.stdout.isatty()
_COLOR = _TTY and not os.environ.get("NO_COLOR") and os.environ.get("TERM") != "dumb"


def _style(code: str) -> str:
    return code if _COLOR else ""


def _ctrl(code: str) -> str:
    return code if _TTY else ""


class C:
    R            = _style("\033[0m")
    B            = _style("\033[1m")
    UNDER        = _style("\033[4m")
    UNDER_OFF    = _style("\033[24m")
    YEL          = _style("\033[33m")
    MAG          = _style("\033[95m")
    CYN          = _style("\033[36m")
    ORN          = _style("\033[38;5;208m")
    HIDE_CURSOR  = _ctrl("\033[?25l")
    SHOW_CURSOR  = _ctrl("\033[?25h")
    NORMAL_KEYS  = _ctrl("\033[?1l")
    CLEAR_SCREEN = _ctrl("\033[H\033[2J")
    CLEAR_DOWN   = _ctrl("\033[J")
    CLEAR_LINE   = _ctrl("\033[K")


def cursor_up(n: int) -> str:
    return _ctrl(f"\033[{n}A")


def clear() -> None:
    sys.stdout.write(C.CLEAR_SCREEN)
    sys.stdout.flush()


def heading(text: str) -> None:
    print()
    print(f"  {C.B}{text}{C.R}")
    print()


def screen_header(title: str, hint: str = "Use the Enter key to return") -> None:
    print(hint)
    print(f"{C.YEL}?{C.R} {title}")


def step_pass(text: str) -> None:
    print(f"   {C.MAG}✓{C.R} {text}")


def step_fail(text: str) -> None:
    print(f"   {C.ORN}✗{C.R} {text}")


def step_warn(text: str) -> None:
    print(f"   {C.YEL}⚠{C.R} {text}")


def line(text: str = "") -> None:
    print(f"     {text}")


def info(text: str) -> None:
    print(f"     {C.CYN}{text}{C.R}")


def mag(s: str) -> str:
    return f"{C.MAG}{s}{C.R}"


def orn(s: str) -> str:
    return f"{C.ORN}{s}{C.R}"


def cyn(s: str) -> str:
    return f"{C.CYN}{s}{C.R}"


def fmt_bytes(n: int) -> str:
    for unit, factor in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= factor:
            return f"{n / factor:.1f} {unit}"
    return f"{n} B"


ARROW = mag("→")
