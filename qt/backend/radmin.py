import re
import shutil
import threading

from PySide6.QtCore import QObject, Property, Signal, Slot

from mila import radmin
from mila.config import get_setting, save_config, set_setting
from mila.constants import VBOX_CMD

_IP_PATTERN = re.compile(r"^26\.\d+\.\d+\.\d+$")


class RadminController(QObject):
    busy_changed = Signal()
    status_changed = Signal()
    error = Signal(str)
    vms_listed = Signal("QVariant")
    create_done = Signal(bool, str)
    attach_done = Signal(bool, str)
    remove_done = Signal(bool, str)
    ip_saved = Signal()

    _status_done = Signal("QVariant")
    _create_finished = Signal(bool, str)
    _vms_finished = Signal("QVariant", str)
    _attach_finished = Signal(bool, str)
    _remove_finished = Signal(bool, str)

    def __init__(self, cfg: dict, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._busy = False
        self._status: dict = {"ready": False, "ip": get_setting(cfg, "radmin_ip", "")}
        self._status_running = False
        self._status_done.connect(self._on_status_done)
        self._create_finished.connect(self._on_create_finished)
        self._vms_finished.connect(self._on_vms_finished)
        self._attach_finished.connect(self._on_attach_finished)
        self._remove_finished.connect(self._on_remove_finished)

    @Property(bool, notify=busy_changed)
    def busy(self) -> bool:
        return self._busy

    @Property("QVariant", notify=status_changed)
    def status(self) -> dict:
        return self._status

    def _set_busy(self, value: bool) -> None:
        if value != self._busy:
            self._busy = value
            self.busy_changed.emit()

    def _require_tools(self, pkexec: bool) -> bool:
        if shutil.which(VBOX_CMD) is None:
            self.error.emit("Install VirtualBox first")
            return False
        if pkexec and shutil.which("pkexec") is None:
            self.error.emit("Install pkexec first")
            return False
        return True

    @Slot()
    def refresh_status(self) -> None:
        if self._status_running:
            return
        self._status_running = True
        threading.Thread(target=self._refresh_status, daemon=True).start()

    def _refresh_status(self) -> None:
        ip = get_setting(self._cfg, "radmin_ip", "")
        ready = bool(ip) and radmin.bridge_present() and radmin.verify_bridge(ip)
        self._status_done.emit({"ready": ready, "ip": ip})

    def _on_status_done(self, status: dict) -> None:
        self._status = status
        self._status_running = False
        self.status_changed.emit()

    @Slot(str)
    def create_bridge(self, ip: str) -> None:
        if self._busy:
            return
        if not _IP_PATTERN.match(ip):
            self.error.emit("Invalid IP")
            return
        if not self._require_tools(True):
            return
        self._set_busy(True)
        threading.Thread(target=self._create, args=(ip,), daemon=True).start()

    def _create(self, ip: str) -> None:
        conflict = radmin.competing_route()
        if conflict:
            self._create_finished.emit(False, f"Another interface '{conflict}' already routes 26.x — remove it first")
            return
        set_setting(self._cfg, "radmin_ip", ip)
        save_config(self._cfg)
        self.ip_saved.emit()
        error, changed, created = radmin.create_bridge(ip, ["pkexec"])
        if error:
            self._create_finished.emit(False, f"Bridge setup failed — {error}")
        elif not radmin.verify_bridge(ip):
            self._create_finished.emit(False, "Bridge verification failed")
        elif changed or created:
            self._create_finished.emit(True, "Bridge created")
        else:
            self._create_finished.emit(True, "Bridge already active")

    def _on_create_finished(self, ok: bool, message: str) -> None:
        self._set_busy(False)
        self.create_done.emit(ok, message)
        self.refresh_status()

    @Slot()
    def request_vms(self) -> None:
        if self._busy:
            return
        if not self._require_tools(False):
            return
        self._set_busy(True)
        threading.Thread(target=self._request_vms, daemon=True).start()

    def _request_vms(self) -> None:
        if not radmin.bridge_present():
            self._vms_finished.emit(None, "Bridge not set up — use Create bridge first")
            return
        vms = radmin.list_vms()
        if vms is None:
            self._vms_finished.emit(None, "Could not list VirtualBox VMs")
            return
        if not vms:
            self._vms_finished.emit(None, "No VirtualBox VMs found — create one first")
            return
        self._vms_finished.emit(vms, "")

    def _on_vms_finished(self, vms: object, message: str) -> None:
        self._set_busy(False)
        if message:
            self.error.emit(message)
        else:
            self.vms_listed.emit(vms)

    @Slot(str)
    def attach_vm(self, name: str) -> None:
        if self._busy:
            return
        if not self._require_tools(False):
            return
        self._set_busy(True)
        threading.Thread(target=self._attach, args=(name,), daemon=True).start()

    def _attach(self, name: str) -> None:
        state = radmin.vm_state(name)
        if state is None:
            self._attach_finished.emit(False, f"Could not read state of VM '{name}'")
            return
        if state not in ("poweroff", "aborted"):
            self._attach_finished.emit(False, f"VM '{name}' state is {state} — power it off first")
            return
        error = radmin.attach_vm(name)
        if error:
            self._attach_finished.emit(False, f"Could not attach '{name}' — {error}")
            return
        self._attach_finished.emit(True, f"Adapter 2 of '{name}' attached to the bridge")

    def _on_attach_finished(self, ok: bool, message: str) -> None:
        self._set_busy(False)
        self.attach_done.emit(ok, message)

    @Slot()
    def remove_bridge(self) -> None:
        if self._busy:
            return
        if not self._require_tools(True):
            return
        self._set_busy(True)
        threading.Thread(target=self._remove, daemon=True).start()

    def _remove(self) -> None:
        if not radmin.bridge_present():
            self._remove_finished.emit(False, "The bridge doesn't exist")
            return
        error = radmin.remove_bridge(["pkexec"])
        if error:
            self._remove_finished.emit(False, f"Bridge removal failed — {error}")
            return
        self._remove_finished.emit(True, "Bridge removed")

    def _on_remove_finished(self, ok: bool, message: str) -> None:
        self._set_busy(False)
        self.remove_done.emit(ok, message)
        self.refresh_status()
