import os
import sys
import threading
import urllib.request
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

from mila import update
from mila.config import get_setting
from mila.constants import DEFAULT_USERNAME
from mila.heatedmetal import hm_pending_updates, update_hm

from backend.reporter import SignalReporter

_PROBE_URL = "https://api.github.com"


def _probe_connectivity() -> bool:
    req = urllib.request.Request(_PROBE_URL, method="HEAD", headers={"User-Agent": "Mila"})
    try:
        with urllib.request.urlopen(req, timeout=5):
            return True
    except OSError:
        return False


class UpdateController(QObject):
    checking_changed = Signal()
    busy_changed = Signal()
    updates_changed = Signal()
    status_changed = Signal()
    error = Signal(str)
    apply_progress = Signal(str)
    restart_required = Signal()

    _check_done = Signal(list, str)
    _apply_done = Signal(str, str, bool)

    def __init__(self, cfg: dict, downloads: list[dict], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._downloads = downloads
        self._checking = False
        self._busy = ""
        self._updates: list = []
        self._status = "idle"
        self._peer: QObject | None = None
        self._check_done.connect(self._on_check_done)
        self._apply_done.connect(self._on_apply_done)

    @Property(bool, notify=checking_changed)
    def checking(self) -> bool:
        return self._checking

    @Property(str, notify=busy_changed)
    def busy(self) -> str:
        return self._busy

    @Property("QVariantList", notify=updates_changed)
    def updates(self) -> list:
        return self._updates

    @Property(str, notify=status_changed)
    def status(self) -> str:
        return self._status

    def _set_checking(self, value: bool) -> None:
        if value != self._checking:
            self._checking = value
            self.checking_changed.emit()

    def _set_busy(self, value: str) -> None:
        if value != self._busy:
            self._busy = value
            self.busy_changed.emit()

    def _set_status(self, value: str) -> None:
        if value != self._status:
            self._status = value
            self.status_changed.emit()

    @Slot(QObject)
    def set_peer(self, peer: QObject) -> None:
        self._peer = peer

    def _peer_blocked(self) -> bool:
        if self._peer is not None and bool(self._peer.property("running")):
            self.error.emit("A download is running — wait for it to finish")
            return True
        return False

    @Slot()
    def check(self) -> None:
        if self._checking or self._busy:
            return
        if self._peer_blocked():
            return
        self._set_checking(True)
        self._set_status("checking")
        threading.Thread(target=self._check, daemon=True).start()

    def _check(self) -> None:
        result: list[dict] = []
        failed = False
        try:
            for component in update.available():
                result.append({
                    "kind": "component",
                    "key": component.name,
                    "name": component.name,
                    "current": component.current() or "?",
                    "target": component.target or "?",
                })
            for u in hm_pending_updates(self._downloads):
                result.append({
                    "kind": "hm",
                    "key": u["key"],
                    "name": u["name"],
                    "current": u["current"],
                    "target": u["target"],
                })
        except Exception as e:
            failed = True
            self.error.emit(f"Update check failed — {e}")
        status = "ok" if result or (not failed and _probe_connectivity()) else "failed"
        self._check_done.emit(result, status)

    def _on_check_done(self, result: list, status: str) -> None:
        self._updates = result
        self.updates_changed.emit()
        self._set_checking(False)
        self._set_status(status)

    @Slot(str)
    def apply(self, key: str) -> None:
        if self._busy or self._checking:
            return
        if self._peer_blocked():
            return
        item = next((u for u in self._updates if u["key"] == key), None)
        if item is None:
            return
        self._set_busy(key)
        threading.Thread(target=self._apply, args=(item,), daemon=True).start()

    def _apply(self, item: dict) -> None:
        reporter = SignalReporter(self.apply_progress.emit)
        ok = False
        try:
            if item["kind"] == "component":
                component = next((c for c in update.COMPONENTS if c.name == item["key"]), None)
                ok = bool(component and component.apply(reporter=reporter))
            else:
                username = get_setting(self._cfg, "username", DEFAULT_USERNAME)
                ok = update_hm(item["key"], self._downloads, username, reporter=reporter)
        except Exception as e:
            reporter.fail(str(e))
            ok = False
        self._apply_done.emit(item["key"], item["name"], ok)

    def _on_apply_done(self, key: str, name: str, ok: bool) -> None:
        self._set_busy("")
        if not ok:
            self.error.emit(f"{name} update failed")
        if ok and key == "Mila":
            self.restart_required.emit()
            return
        self.check()

    @Slot()
    def restart(self) -> None:
        main_script = Path(__file__).resolve().parent.parent / "main.py"
        os.execv(sys.executable, [sys.executable, str(main_script)])
