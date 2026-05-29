import sys


class C:
    R            = "\033[0m"
    B            = "\033[1m"
    UNDER        = "\033[4m"
    UNDER_OFF    = "\033[24m"
    YEL          = "\033[33m"
    MAG          = "\033[95m"
    CYN          = "\033[36m"
    ORN          = "\033[38;5;208m"
    HIDE_CURSOR  = "\033[?25l"
    SHOW_CURSOR  = "\033[?25h"
    NORMAL_KEYS  = "\033[?1l"
    CLEAR_SCREEN = "\033[H\033[2J"
    CLEAR_DOWN   = "\033[J"
    CLEAR_LINE   = "\033[K"


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
