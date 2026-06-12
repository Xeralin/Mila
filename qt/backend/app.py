import re
import shutil
import threading

from PySide6.QtCore import QObject, QUrl, Property, Signal, Slot

from mila.config import get_setting, save_config, set_setting
from mila.constants import (
    DEFAULT_MAX_DOWNLOADS,
    DEFAULT_USERNAME,
    DOWNLOAD_SPEED_PRESETS,
    DOWNLOADS_DIR,
    HM_KEY,
    MAX_USERNAME_LENGTH,
    MEDIA_DIR,
    NAME_PATTERN,
    PROJECT_ROOT,
    VERSION,
)
from mila.manifest import display_name, installed_downloads
from mila.rpc import is_discord_installed, start_daemon, stop_daemon
from mila.settings import wipe_depot_token, write_download_username
from mila.style import fmt_bytes

_RADMIN_IP_PATTERN = re.compile(r"^26\.\d+\.\d+\.\d+$")


class AppBackend(QObject):
    settings_changed = Signal()
    info_changed = Signal()
    invalid_setting = Signal(str, str)
    notice = Signal(str)
    logged_out = Signal(bool, str)

    _info_done = Signal("QVariant")

    def __init__(self, cfg: dict, downloads: list[dict], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._downloads = downloads
        self._info_data: dict = {}
        self._info_running = False
        self._info_done.connect(self._on_info_done)

    @Property(str, constant=True)
    def version(self) -> str:
        return VERSION

    @Property("QVariantList", constant=True)
    def all_seasons(self) -> list:
        splash_dir = MEDIA_DIR / "splash"
        exts = (".jpg", ".jpeg", ".png", ".webp")
        result = []
        for s in self._downloads:
            code, _, name = s["label"].partition(" ")
            splash = next(
                (p for ext in exts if (p := splash_dir / f"{s['key']}{ext}").exists()),
                None,
            )
            result.append({
                "key": s["key"],
                "code": code,
                "name": name,
                "size_gb": s.get("size_gb", 0),
                "heated_metal": HM_KEY in s,
                "liberator": bool(s.get("liberator")),
                "has_splash": splash is not None,
                "splash": QUrl.fromLocalFile(str(splash)).toString() if splash else "",
            })
        return result

    @Property("QVariantList", constant=True)
    def speed_presets(self) -> list:
        return [{"label": label, "value": value} for label, value in DOWNLOAD_SPEED_PRESETS]

    @Property("QVariant", notify=info_changed)
    def info_data(self) -> dict:
        return self._info_data

    @Slot()
    def refresh_info(self) -> None:
        if self._info_running:
            return
        self._info_running = True
        threading.Thread(target=self._collect_info, daemon=True).start()

    def _collect_info(self) -> None:
        base = DOWNLOADS_DIR if DOWNLOADS_DIR.exists() else PROJECT_ROOT
        try:
            usage = (
                sum(f.stat().st_size for f in DOWNLOADS_DIR.rglob("*") if f.is_file())
                if DOWNLOADS_DIR.exists()
                else 0
            )
            disk_usage = fmt_bytes(usage)
        except OSError:
            disk_usage = "?"
        try:
            free_disk = fmt_bytes(shutil.disk_usage(base).free)
        except OSError:
            free_disk = "?"
        self._info_done.emit({
            "version": VERSION,
            "username": get_setting(self._cfg, "username", DEFAULT_USERNAME),
            "steam_account": get_setting(self._cfg, "steam_account", "") or "None",
            "downloads": len(installed_downloads()),
            "disk_usage": disk_usage,
            "free_disk": free_disk,
        })

    def _on_info_done(self, data: dict) -> None:
        self._info_data = data
        self._info_running = False
        self.info_changed.emit()

    @Slot()
    def log_out(self) -> None:
        self._cfg.get("settings", {}).pop("steam_account", None)
        save_config(self._cfg)
        self.settings_changed.emit()
        found, errors = wipe_depot_token()
        if not found:
            self.logged_out.emit(False, "No DepotDownloader token found — nothing to remove")
        elif errors:
            self.logged_out.emit(False, errors[0])
        else:
            self.logged_out.emit(True, "Logged out")

    def _store(self, key: str, value: object) -> None:
        set_setting(self._cfg, key, value)
        save_config(self._cfg)
        self.settings_changed.emit()

    def _reject(self, field: str, message: str) -> None:
        self.invalid_setting.emit(field, message)
        self.settings_changed.emit()

    @Property(str, notify=settings_changed)
    def username(self) -> str:
        return get_setting(self._cfg, "username", DEFAULT_USERNAME)

    @username.setter
    def username(self, value: str) -> None:
        if value == self.username:
            return
        if not value or len(value) > MAX_USERNAME_LENGTH or not NAME_PATTERN.match(value):
            self._reject("username", "Invalid username")
            return
        self._store("username", value)
        for d in installed_downloads():
            name = display_name(d.name, self._downloads)
            try:
                ok = write_download_username(d, value)
            except OSError:
                ok = False
            if not ok:
                self.notice.emit(f"Could not update {name}")

    @Property(str, notify=settings_changed)
    def steam_account(self) -> str:
        return get_setting(self._cfg, "steam_account", "")

    @steam_account.setter
    def steam_account(self, value: str) -> None:
        if value == self.steam_account:
            return
        if value and not NAME_PATTERN.match(value):
            self._reject("steam_account", "Invalid Steam account")
            return
        self._store("steam_account", value)

    @Property(int, notify=settings_changed)
    def max_downloads(self) -> int:
        return get_setting(self._cfg, "max_downloads", DEFAULT_MAX_DOWNLOADS)

    @max_downloads.setter
    def max_downloads(self, value: int) -> None:
        if value == self.max_downloads:
            return
        self._store("max_downloads", value)

    @Property(str, notify=settings_changed)
    def radmin_ip(self) -> str:
        return get_setting(self._cfg, "radmin_ip", "")

    @radmin_ip.setter
    def radmin_ip(self, value: str) -> None:
        if value == self.radmin_ip:
            return
        if value and not _RADMIN_IP_PATTERN.match(value):
            self._reject("radmin_ip", "Invalid IP")
            return
        self._store("radmin_ip", value)

    @Property(bool, notify=settings_changed)
    def discord_rpc(self) -> bool:
        return get_setting(self._cfg, "discord_rpc", False)

    @discord_rpc.setter
    def discord_rpc(self, value: bool) -> None:
        if value == self.discord_rpc:
            return
        if value and not is_discord_installed():
            self._reject("discord_rpc", "Discord not installed")
            return
        self._store("discord_rpc", value)
        if value:
            start_daemon()
        else:
            stop_daemon()
