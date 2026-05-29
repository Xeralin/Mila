from collections.abc import Callable

from mila.style import ARROW, clear, cyn, mag, orn, screen_header
from mila.input import go_back, select
from mila.settings import screen_logout


def _help_entries(cfg: dict) -> list[tuple[str, str, tuple[str, Callable[[], None]] | None]]:
    return [
        (
            "Add a downloaded game to Steam",
            f"1.  Confirm {mag('Add to Steam?')} at the end of the download\n"
            f"2.  Close {cyn('Steam')} and pick a compatibility layer\n"
            f"3.  Open {cyn('Steam')} and click {mag('Play')}",
            None,
        ),
        (
            "Enable Unlock-All",
            f"1.  Download the {cyn('Windows')} version from {cyn('cheatengine.org')}, move to {orn('bin/')} and rename to {orn('CheatEngine.exe')}\n"
            f"2.  Confirm {mag('Enable Unlock-All?')} at the download prompt\n"
            f"3.  Click through the {cyn('Cheat Engine')} installer when it opens — deny any bundled offers to avoid adware\n"
            f"4.  First run: tick {mag('Always')} on the Lua script prompt, click {mag('Yes')}, then restart the game once\n"
            f"5.  For Y7S4 and Y7S2, also add the stealthedit plugin in {cyn('Cheat Engine')}:\n"
            f"    Edit {ARROW} Settings {ARROW} Plugins {ARROW} Add New\n"
            f"    {orn('/')} drive {ARROW} {orn('home/<user>/.../Mila/plugins/stealthedit/umstealthedit-x86_64.dll')}\n"
            f"    Tick its checkbox, then click {mag('OK')}\n"
            f"6.  The cheat enables ~7 seconds after {cyn('Cheat Engine')} attaches to the game",
            None,
        ),
        (
            "Join RadminVPN networks on Linux",
            f"1. Use {cyn('VirtualBox')} to create a {cyn('Windows')} VM, then install {cyn('RadminVPN')} on it\n"
            f"2. Tools {ARROW} RadminVPN {ARROW} Create bridge {ARROW} enter your Radmin IP\n"
            f"3. Shut down the VM, then Tools {ARROW} RadminVPN {ARROW} Attach VM to bridge\n"
            f"4. Start the VM. In {cyn('Windows')}, open {orn('ncpa.cpl')}, select {mag('Ethernet 2')} and {mag('Radmin VPN')}\n"
            f"   {ARROW} right-click {ARROW} Bridge Connections\n"
            f"5. The bridge does not survive a {cyn('Linux')} reboot. Go to\n"
            f"   Tools {ARROW} RadminVPN {ARROW} Create bridge\n"
            f"6. Restarting {cyn('Windows')} breaks the bridge. If {cyn('RadminVPN')} shows\n"
            f"   \"waiting for adapter response\", delete the Network Bridge in {orn('ncpa.cpl')}\n"
            "   and bridge the adapters again — it's bound to work eventually\n"
            "\n"
            f"If you don't need {cyn('RadminVPN')}, you can use native programs like\n"
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
            f"After your first successful login, {cyn('DepotDownloader')} caches an encrypted\n"
            f"access token in .NET IsolatedStorage: {orn('~/.local/share/IsolatedStorage/<hash>/')}\n"
            "\n"
            "Subsequent runs reuse the token — no password prompt, and Steam Guard 2FA\n"
            "usually only needs to be entered once per device. Your password itself\n"
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
        screen_header(question)
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
