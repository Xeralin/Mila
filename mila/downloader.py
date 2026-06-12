from pathlib import Path

from mila.constants import (
    DEFAULT_MAX_DOWNLOADS,
    DEFAULT_USERNAME,
    DOWNLOADS_DIR,
    HM_KEY,
    MEDIA_DIR,
)
from mila.style import clear, info, line, mag, screen_header, step_fail, step_pass
from mila.input import confirm, go_back, prompt_steam_account, select
from mila.spinner import LazySpinner, Reporter
from mila.config import get_setting
from mila.depot import ensure_runtime, run_depots
from mila.heatedmetal import apply_heatedmetal, hm_folder_name
from mila.steam import apply_steam_setup, find_existing_appid, select_proton, wait_for_steam_closed
from mila.throwback import apply_throwback, write_launch_bat
from mila.manifest import hm_display_name, launcher_name
from mila.liberator import ensure_liberator


def screen_downloader(cfg: dict, downloads: list[dict]) -> None:
    by_year: dict[str, list[dict]] = {}
    for s in downloads:
        by_year.setdefault(s["key"].split("S", 1)[0], []).append(s)
    years_sorted = sorted(by_year.keys(), key=lambda y: int(y[1:]))

    while True:
        year_options = [f"Year {y[1:]}" for y in years_sorted] + ["Back"]
        pick = select("Select year", year_options)
        if pick is None or pick == len(year_options) - 1:
            return
        year = years_sorted[pick]

        year_downloads = by_year[year]
        download_options = [s["label"] for s in year_downloads] + ["Back"]

        pick = select(f"Year {year[1:]}", download_options)
        if pick is None or pick == len(download_options) - 1:
            continue
        _run_download(cfg, year_downloads[pick])
        return


def _header_label(download: dict, enable_hm: bool = False) -> str:
    size = (download.get(HM_KEY) or {}).get("size_gb") if enable_hm else download.get("size_gb")
    return f"{mag(download['label'])} — {size} GB" if size else mag(download['label'])


def apply_install(target: Path, download: dict, is_hm: bool, username: str,
                  liberator_name: str | None = None, write_bat: bool = True,
                  reporter: Reporter | None = None) -> bool:
    if is_hm:
        return apply_heatedmetal(target, username, download[HM_KEY]["hm_version"], reporter=reporter)
    with (reporter or LazySpinner()) as sp:
        sp.update("Copying files")
        try:
            apply_throwback(target, username, download["loader"])
            if write_bat:
                write_launch_bat(target, liberator_name)
        except OSError as e:
            sp.fail(f"ThrowbackLoader setup failed — {e}")
            return False
        sp.succeed("ThrowbackLoader applied")
        return True


def _run_download(cfg: dict, download: dict) -> None:
    clear()
    screen_header(_header_label(download))

    username = get_setting(cfg, "username", DEFAULT_USERNAME)

    steam_account = prompt_steam_account(cfg)
    if not steam_account:
        go_back()
        return

    enable_liberator = False
    if download.get("liberator"):
        enable_liberator = confirm("Enable Liberator?", default=True)

    enable_hm = False
    if not enable_liberator and HM_KEY in download:
        enable_hm = confirm("Enable Heated Metal?", default=True)

    liberator_name = None
    if enable_liberator:
        liberator = ensure_liberator()
        if liberator is None:
            go_back()
            return
        liberator_name = liberator.name

    target = DOWNLOADS_DIR / (hm_folder_name(download["key"]) if enable_hm else download["key"])
    target.mkdir(parents=True, exist_ok=True)

    dd = ensure_runtime(enable_hm)
    if dd is None:
        go_back()
        return

    max_downloads = get_setting(cfg, "max_downloads", DEFAULT_MAX_DOWNLOADS)

    print()
    line(f"Downloading to {target}")
    info("Don't worry about timeouts — just wait or run the download again.")
    rc, which = run_depots(dd, download, steam_account, target, max_downloads, is_hm=enable_hm)
    if rc != 0:
        step_fail(f"{which} depot download failed — exit code {rc}")
        go_back()
        return

    clear()
    screen_header(_header_label(download, enable_hm))

    if not apply_install(target, download, enable_hm, username, liberator_name):
        go_back()
        return

    added_to_steam = False
    if confirm("Add to Steam?", default=True) and wait_for_steam_closed(mag(download['label'])):
        name = hm_display_name(download) if enable_hm else download["label"]
        launcher = target / launcher_name(enable_hm)
        existing = find_existing_appid(launcher) is not None
        proton = select_proton()
        if proton is not None:
            clear()
            screen_header(_header_label(download, enable_hm))
            mode = "heatedmetal" if enable_hm else "throwback"
            logo = MEDIA_DIR / f"{mode}_logo.png"
            icon = MEDIA_DIR / f"{mode}_icon.png"
            hero = None if enable_hm else MEDIA_DIR / "throwback_background.jpg"
            if apply_steam_setup(name, launcher, target, proton, icon=icon, logo=logo, hero=hero):
                added_to_steam = True
                verb = "updated in" if existing else "added to"
                step_pass(f"{name} was {verb} Steam")

    if not added_to_steam:
        step_pass(f"{download['label']} downloaded to {target}")
        line(f"See {mag('Help')} for how to add this download manually to Steam")
    go_back()
