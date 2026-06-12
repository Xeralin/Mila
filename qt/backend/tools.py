import shutil
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from mila.constants import DOWNLOADS_DIR, HELIOS_JSON, LAUNCH_BAT, STEAM_COMPATDATA, TEXTURE_QUALITIES
from mila.heatedmetal import hm_folder_name
from mila.manifest import launcher_name
from mila.shears import cut_download, scan_download
from mila.steam import find_existing_appid, is_game_running
from mila.style import fmt_bytes


class ToolsController(QObject):
    busy_changed = Signal()
    error = Signal(str)
    shears_scanned = Signal("QVariant")
    shears_done = Signal(bool, str)
    prefix_deleted = Signal(bool, str)

    _scan_done = Signal("QVariant")
    _cut_done = Signal(bool, str)
    _delete_done = Signal(bool, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._busy = ""
        self._peer: QObject | None = None
        self._scan_done.connect(self._on_scan_done)
        self._cut_done.connect(self._on_cut_done)
        self._delete_done.connect(self._on_delete_done)

    @Property(str, notify=busy_changed)
    def busy(self) -> str:
        return self._busy

    def _set_busy(self, value: str) -> None:
        if value != self._busy:
            self._busy = value
            self.busy_changed.emit()

    @Slot(QObject)
    def set_peer(self, peer: QObject) -> None:
        self._peer = peer

    @Slot(str, result="QVariant")
    def installed_variants(self, key: str) -> dict:
        hm_dir = DOWNLOADS_DIR / hm_folder_name(key)
        return {
            "throwback": (DOWNLOADS_DIR / key / LAUNCH_BAT).exists(),
            "hm": (hm_dir / launcher_name(True)).exists() and (hm_dir / HELIOS_JSON).exists(),
        }

    @Slot(str)
    def scan_shears(self, key: str) -> None:
        if self._busy:
            return
        self._set_busy("scan")
        threading.Thread(target=self._scan, args=(key,), daemon=True).start()

    def _scan(self, key: str) -> None:
        try:
            info = scan_download(DOWNLOADS_DIR / key)
        except OSError as e:
            self.error.emit(f"Scan failed — {e}")
            self._scan_done.emit(None)
            return
        tiers, videos, events = info["tiers"], info["videos"], info["events"]
        rows = [
            {"label": f"{qname} textures", "size": fmt_bytes(tiers[level])}
            for level, qname in enumerate(TEXTURE_QUALITIES)
            if tiers.get(level, 0) > 0
        ]
        if videos > 0:
            rows.append({"label": "Videos", "size": fmt_bytes(videos)})
        if events > 0:
            rows.append({"label": "Events", "size": fmt_bytes(events)})
        actions = []
        if videos > 0:
            actions.append({"label": "Cut videos", "kind": "videos", "level": 0})
        if events > 0:
            actions.append({"label": "Cut events", "kind": "events", "level": 0})
        for keep in sorted(tiers.keys())[:-1]:
            actions.append({"label": f"Cut to {TEXTURE_QUALITIES[keep]} textures", "kind": "textures", "level": keep})
        self._scan_done.emit({"key": key, "total": fmt_bytes(info["total"]), "rows": rows, "actions": actions})

    def _on_scan_done(self, payload: object) -> None:
        self._set_busy("")
        if payload is not None:
            self.shears_scanned.emit(payload)

    @Slot(str, str, int)
    def cut_shears(self, key: str, kind: str, level: int) -> None:
        if self._busy:
            return
        if self._peer is not None and bool(self._peer.property("running")):
            self.error.emit("A download is running — wait for it to finish")
            return
        if is_game_running():
            self.error.emit("Close the game to continue")
            return
        self._set_busy("cut")
        threading.Thread(target=self._cut, args=(key, kind, level), daemon=True).start()

    def _cut(self, key: str, kind: str, level: int) -> None:
        try:
            freed = cut_download(DOWNLOADS_DIR / key, kind, level)
        except OSError as e:
            self._cut_done.emit(False, f"Cut failed — {e}")
            return
        self._cut_done.emit(True, f"Freed {fmt_bytes(freed)}")

    def _on_cut_done(self, ok: bool, message: str) -> None:
        self._set_busy("")
        self.shears_done.emit(ok, message)

    def _prefix_path(self, key: str, is_hm: bool) -> Path | None:
        target = DOWNLOADS_DIR / (hm_folder_name(key) if is_hm else key)
        appid = find_existing_appid(target / launcher_name(is_hm))
        if appid is None:
            return None
        return STEAM_COMPATDATA / str(appid)

    @Slot(str, bool, result=bool)
    def prefix_exists(self, key: str, is_hm: bool) -> bool:
        prefix = self._prefix_path(key, is_hm)
        return prefix is not None and (prefix / "pfx").exists()

    @Slot(str, bool)
    def delete_prefix(self, key: str, is_hm: bool) -> None:
        if self._busy:
            return
        if is_game_running():
            self.error.emit("Close the game to continue")
            return
        prefix = self._prefix_path(key, is_hm)
        if prefix is None:
            self.prefix_deleted.emit(False, "Could not delete prefix — not found")
            return
        self._set_busy("delete")
        threading.Thread(target=self._delete, args=(prefix,), daemon=True).start()

    def _delete(self, prefix: Path) -> None:
        try:
            shutil.rmtree(prefix)
        except OSError as e:
            self._delete_done.emit(False, f"Could not delete prefix — {e}")
            return
        self._delete_done.emit(True, "Prefix deleted")

    def _on_delete_done(self, ok: bool, message: str) -> None:
        self._set_busy("")
        self.prefix_deleted.emit(ok, message)
