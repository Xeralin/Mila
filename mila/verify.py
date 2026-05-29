from mila.constants import DEFAULT_MAX_DOWNLOADS, DEFAULT_USERNAME, HM_KEY
from mila.style import clear, line, mag, screen_header, step_fail, step_pass, step_warn
from mila.input import go_back, prompt_steam_account, select
from mila.spinner import Spinner
from mila.config import get_setting
from mila.depot import ensure_runtime, run_depots
from mila.manifest import display_name, local_downloads, resolve_install
from mila.heatedmetal import apply_heatedmetal
from mila.steam import wait_for_game_closed
from mila.throwback import apply_throwback


def screen_verify(cfg: dict, downloads: list[dict]) -> None:
    present = local_downloads()
    if not present:
        screen_header("Verify")
        print()
        step_warn("No downloads found")
        go_back()
        return

    labels = [display_name(d.name, downloads) for d in present] + ["Back"]
    pick = select("Verify", labels)
    if pick is None or pick == len(labels) - 1:
        return
    target = present[pick]

    resolved = resolve_install(target.name, downloads)
    if resolved is None:
        clear()
        screen_header("Verify")
        step_fail(f"No manifest entry for {target.name}")
        go_back()
        return
    download, is_hm = resolved

    clear()
    screen_header(mag(download["label"]))

    steam_account = prompt_steam_account(cfg)
    if not steam_account:
        go_back()
        return

    dd = ensure_runtime(is_hm)
    if dd is None:
        go_back()
        return

    if not wait_for_game_closed(mag(download["label"])):
        go_back()
        return

    max_downloads = get_setting(cfg, "max_downloads", DEFAULT_MAX_DOWNLOADS)

    print()
    line(f"Validating {target}")
    rc, which = run_depots(dd, download, steam_account, target, max_downloads, is_hm=is_hm)
    if rc != 0:
        step_fail(f"{which} depot validation failed — exit code {rc}")
        go_back()
        return

    clear()
    screen_header(mag(download["label"]))

    username = get_setting(cfg, "username", DEFAULT_USERNAME)
    if is_hm:
        hm_block = download[HM_KEY]
        is_manual = hm_block.get("manual", False)
        hm_version = hm_block.get("hm_version") if not is_manual else None
        if not apply_heatedmetal(target, username, hm_version, manual=is_manual):
            go_back()
            return
    else:
        with Spinner("Copying files") as sp:
            apply_throwback(target, username, download["loader"])
            sp.succeed("ThrowbackLoader applied")

    step_pass(f"{download['label']} verified")
    go_back()
