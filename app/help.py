from collections.abc import Callable

from app.style import ARROW, clear, cyn, mag, orn, render_header
from app.input import go_back, select
from app.settings import screen_logout


def _help_entries(
    cfg: dict,
) -> list[tuple[str, str, tuple[str, Callable[[], None]] | None]]:
    return [
        (
            "Add a downloaded game to Steam",
            f"1.  Confirm {mag('Add to Steam?')} at the end of the download\n"
            f"2.  Close {cyn('Steam')} and pick a compatibility layer\n"
            f"3.  Open {cyn('Steam')} and click {mag('Play')}",
            None,
        ),
        (
            "Enable Liberator",
            f"1.  Confirm {mag('Enable Liberator?')} "
            f"at the download prompt\n"
            f"    — {cyn('Liberator')} is fetched automatically "
            f"and launches with the game\n"
            f"2.  Already downloaded? Toggle {mag('Liberator')} "
            f"in {mag('Settings')}",
            None,
        ),
        (
            "Join RadminVPN networks on Linux",
            f"1. Use {cyn('VirtualBox')} to create a {cyn('Windows')} VM, "
            f"then install {cyn('RadminVPN')} on it\n"
            f"2. Tools {ARROW} RadminVPN {ARROW} Create bridge "
            f"{ARROW} enter your Radmin IP\n"
            f"3. Shut down the VM, then Tools {ARROW} RadminVPN "
            f"{ARROW} Attach VM to bridge\n"
            f"4. Start the VM. In {cyn('Windows')}, open {orn('ncpa.cpl')},\n"
            f"   select {mag('Ethernet 2')} and {mag('Radmin VPN')}\n"
            f"   {ARROW} right-click {ARROW} Bridge Connections\n"
            f"5. The bridge does not survive a {cyn('Linux')} reboot. Go to\n"
            f"   Tools {ARROW} RadminVPN {ARROW} Create bridge\n"
            f"6. Restarting {cyn('Windows')} breaks the bridge. "
            f"If {cyn('RadminVPN')} shows\n"
            f"   \"waiting for adapter response\", "
            f"delete the Network Bridge in {orn('ncpa.cpl')}\n"
            "   and bridge the adapters again — "
            "it's bound to work eventually\n"
            "\n"
            f"If you don't need {cyn('RadminVPN')}, "
            f"you can use native programs like\n"
            f"{cyn('ZeroTier')}",
            None,
        ),
        (
            "How does Shears work?",
            "Shears frees disk space by removing optional files\n"
            "\n"
            f"{cyn('Heated Metal')} downloads aren't listed since the mod\n"
            "relies on some of these files\n"
            "\n"
            f"If a download won't run after Shears, use {mag('Verify')}\n"
            "to restore the missing files",
            None,
        ),
        (
            "Does my Steam login get stored?",
            f"After your first successful login, "
            f"{cyn('DepotDownloader')} caches an encrypted\n"
            f"access token in .NET IsolatedStorage: "
            f"{orn('~/.local/share/IsolatedStorage/<hash>/')}\n"
            "\n"
            "Subsequent runs reuse the token — no password prompt, "
            "and Steam Guard 2FA\n"
            "usually only needs to be entered once per device. "
            "Your password itself\n"
            "is never written to disk",
            ("Log out", lambda: screen_logout(cfg)),
        ),
    ]


def screen_help(cfg: dict) -> None:
    while True:
        entries = _help_entries(cfg)
        questions = [q for q, _, _ in entries] + ["Back"]
        pick = select("Help", questions)
        if pick is None or pick == len(questions) - 1:
            return
        clear()
        question, body, action = entries[pick]
        render_header(question)
        for raw in body.splitlines():
            print(f"     {raw}")
        if action:
            print()
            label, fn = action
            choice = select("", [label, "Back"], current=1, clear_first=False)
            if choice == 0:
                clear()
                fn()
        else:
            go_back()
