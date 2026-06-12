import re
import threading
from collections import deque
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Property, Signal, Slot

from mila.config import get_setting
from mila.constants import (
    DEFAULT_MAX_DOWNLOADS,
    DEFAULT_USERNAME,
    DOWNLOADS_DIR,
    LAUNCH_BAT,
    MEDIA_DIR,
    NAME_PATTERN,
)
from mila.depot import depot_commands, ensure_runtime
from mila.downloader import apply_install
from mila.heatedmetal import hm_folder_name
from mila.manifest import hm_display_name, installed_username, launcher_name
from mila.steam import apply_steam_setup, is_game_running, is_steam_running as steam_running, list_protons
from mila.throwback import write_launch_bat
from mila.liberator import ensure_liberator

from backend.reporter import SignalReporter

_PERCENT = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*%")


class DownloadController(QObject):
    log_line = Signal(str)
    progress_changed = Signal()
    running_changed = Signal()
    state_changed = Signal()
    finished = Signal(int)
    login_required = Signal(str)
    error = Signal(str)
    active_key_changed = Signal()
    protons_changed = Signal()
    steam_setup_done = Signal(bool, str)

    _prepare_done = Signal(int, str, str, str)
    _apply_done = Signal(int, bool)
    _steam_done = Signal(int, bool, str)

    def __init__(self, cfg: dict, downloads: list[dict], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._downloads = downloads
        self._peer: QObject | None = None
        self._process: QProcess | None = None
        self._proc_done = False
        self._progress = 0.0
        self._running = False
        self._state = "idle"
        self._active_key = ""
        self._cancelled = False
        self._generation = 0
        self._login_pending = False
        self._buffer = ""
        self._history: deque[str] = deque(maxlen=2000)
        self._commands: list[dict] = []
        self._index = 0
        self._download: dict = {}
        self._enable_hm = False
        self._verify = False
        self._liberator_name: str | None = None
        self._steam_account = ""
        self._max_downloads = DEFAULT_MAX_DOWNLOADS
        self._target = DOWNLOADS_DIR
        self._dd = ""
        self._protons: list[dict] = []
        self.log_line.connect(self._history.append)
        self._prepare_done.connect(self._on_prepare_done)
        self._apply_done.connect(self._on_apply_done)
        self._steam_done.connect(self._on_steam_done)

    @Property(float, notify=progress_changed)
    def progress(self) -> float:
        return self._progress

    @Property(bool, notify=running_changed)
    def running(self) -> bool:
        return self._running

    @Property(str, notify=state_changed)
    def state(self) -> str:
        return self._state

    @Property(str, notify=active_key_changed)
    def active_key(self) -> str:
        return self._active_key

    @Property("QVariantList", notify=protons_changed)
    def protons(self) -> list:
        return [{"index": i, "display": p["display"]} for i, p in enumerate(self._protons)]

    def _set_progress(self, value: float) -> None:
        if value != self._progress:
            self._progress = value
            self.progress_changed.emit()

    def _set_running(self, value: bool) -> None:
        if value != self._running:
            self._running = value
            self.running_changed.emit()

    def _set_state(self, value: str) -> None:
        if value != self._state:
            self._state = value
            self.state_changed.emit()

    @Slot(QObject)
    def set_peer(self, peer: QObject) -> None:
        self._peer = peer

    def _accept(self, season_key: str) -> dict | None:
        if self._running:
            return None
        if self._peer is not None and (self._peer.property("busy") or self._peer.property("checking")):
            self.error.emit("Updates are running — wait for them to finish")
            return None
        download = next((d for d in self._downloads if d["key"] == season_key), None)
        if download is None:
            self.error.emit("Unknown download")
            return None
        steam_account = get_setting(self._cfg, "steam_account", "")
        if not steam_account or not NAME_PATTERN.match(steam_account):
            self.error.emit("Invalid Steam account")
            return None
        self._steam_account = steam_account
        return download

    @Slot(str, bool, bool)
    def start(self, season_key: str, enable_liberator: bool, enable_hm: bool) -> None:
        download = self._accept(season_key)
        if download is None:
            return
        if enable_liberator:
            enable_hm = False
        target = DOWNLOADS_DIR / (hm_folder_name(season_key) if enable_hm else season_key)
        self._launch(download, season_key, target, enable_liberator, enable_hm, verify=False)

    @Slot(str, bool)
    def verify(self, season_key: str, is_hm: bool) -> None:
        download = self._accept(season_key)
        if download is None:
            return
        target = DOWNLOADS_DIR / (hm_folder_name(season_key) if is_hm else season_key)
        if not target.is_dir():
            self.error.emit("Not installed")
            return
        if is_game_running():
            self.error.emit("Close the game to continue")
            return
        self._launch(download, season_key, target, False, is_hm, verify=True)

    def _launch(self, download: dict, season_key: str, target: Path,
                enable_liberator: bool, enable_hm: bool, verify: bool) -> None:
        self._generation += 1
        self._download = download
        self._enable_hm = enable_hm
        self._verify = verify
        self._liberator_name = None
        self._max_downloads = get_setting(self._cfg, "max_downloads", DEFAULT_MAX_DOWNLOADS)
        self._target = target
        self._cancelled = False
        self._history.clear()
        if self._active_key != season_key:
            self._active_key = season_key
            self.active_key_changed.emit()
        self._set_progress(0.0)
        self._set_state("preparing")
        self._set_running(True)
        threading.Thread(
            target=self._prepare,
            args=(self._generation, enable_liberator, enable_hm),
            daemon=True,
        ).start()

    def _prepare(self, generation: int, enable_liberator: bool, enable_hm: bool) -> None:
        reporter = SignalReporter(self.log_line.emit)
        try:
            liberator_name = ""
            if enable_liberator:
                liberator = ensure_liberator(reporter)
                if liberator is None:
                    self._prepare_done.emit(generation, "", "", "Liberator setup failed")
                    return
                liberator_name = liberator.name
            dd = ensure_runtime(enable_hm, reporter)
            if dd is None:
                self._prepare_done.emit(generation, "", "", "Runtime setup failed")
                return
            self._prepare_done.emit(generation, str(dd), liberator_name, "")
        except Exception as e:
            self._prepare_done.emit(generation, "", "", f"Setup failed — {e}")

    def _on_prepare_done(self, generation: int, dd: str, liberator_name: str, err: str) -> None:
        if generation != self._generation or self._cancelled:
            return
        if err:
            self.log_line.emit(err)
            self._finish(1)
            return
        self._dd = dd
        self._liberator_name = liberator_name or None
        try:
            self._commands = depot_commands(
                self._download, self._steam_account, self._target, self._max_downloads, is_hm=self._enable_hm
            )
            self._target.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.log_line.emit(f"Setup failed — {e}")
            self._finish(1)
            return
        self.log_line.emit(f"Validating {self._target}" if self._verify else f"Downloading to {self._target}")
        self._set_state("downloading")
        self._index = 0
        self._run_next()

    def _run_next(self) -> None:
        if self._index >= len(self._commands):
            self._set_progress(100.0)
            self._start_apply()
            return
        cmd = self._commands[self._index]
        self._buffer = ""
        self._login_pending = False
        self._proc_done = False
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.MergedChannels)
        proc.readyReadStandardOutput.connect(self._on_output)
        proc.finished.connect(self._on_process_finished)
        proc.errorOccurred.connect(self._on_process_error)
        self._process = proc
        self.log_line.emit(f"$ DepotDownloader {' '.join(cmd['args'])}")
        proc.start(self._dd, cmd["args"])

    def _on_output(self) -> None:
        proc = self.sender()
        if proc is None or proc is not self._process:
            return
        self._buffer += bytes(proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        while True:
            nl = self._buffer.find("\n")
            if nl < 0:
                break
            line = self._buffer[:nl].rstrip("\r")
            self._buffer = self._buffer[nl + 1:]
            self._emit_line(line)
        self._check_prompt(self._buffer)

    def _emit_line(self, line: str) -> None:
        self.log_line.emit(line)
        match = _PERCENT.match(line)
        if match and self._commands:
            depot_pct = min(float(match.group(1)), 100.0)
            overall = (self._index + depot_pct / 100.0) / len(self._commands) * 100.0
            self._set_progress(min(overall, 100.0))

    def _check_prompt(self, text: str) -> None:
        if self._login_pending:
            return
        stripped = text.rstrip()
        if not stripped.endswith(":"):
            return
        low = stripped.lower()
        if any(token in low for token in ("auth code", "2-factor", "two-factor", "steam guard")):
            kind = "guard"
        elif "password" in low:
            kind = "password"
        else:
            return
        self._login_pending = True
        self.log_line.emit(stripped)
        self.login_required.emit(kind)

    @Slot(str)
    def submit_login(self, text: str) -> None:
        if self._process is None or not self._login_pending:
            return
        self._login_pending = False
        self._process.write((text + "\n").encode())

    def _on_process_finished(self, code: int, status: QProcess.ExitStatus) -> None:
        proc = self.sender()
        if proc is not self._process:
            if isinstance(proc, QProcess):
                proc.deleteLater()
            return
        if self._proc_done:
            return
        self._proc_done = True
        self._process = None
        proc.deleteLater()
        if self._cancelled:
            self._finish(1)
            return
        if status == QProcess.ExitStatus.CrashExit:
            self.log_line.emit("DepotDownloader crashed")
            self._finish(1)
            return
        cmd = self._commands[self._index]
        if code != 0:
            if not cmd["optional"]:
                self.log_line.emit(f"{cmd['name']} depot download failed — exit code {code}")
                self._finish(code)
                return
            self.log_line.emit(f"{cmd['name']} depot failed — continuing without it")
        self._index += 1
        self._run_next()

    def _on_process_error(self, err: QProcess.ProcessError) -> None:
        proc = self.sender()
        if proc is not self._process or self._proc_done:
            return
        if err != QProcess.ProcessError.FailedToStart:
            return
        self._proc_done = True
        self._process = None
        proc.deleteLater()
        self.log_line.emit("DepotDownloader failed to start")
        self.error.emit("DepotDownloader failed to start")
        self._finish(1)

    def _start_apply(self) -> None:
        self._set_state("applying")
        username = get_setting(self._cfg, "username", DEFAULT_USERNAME)
        if self._verify:
            username = installed_username(self._target) or username
        threading.Thread(
            target=self._apply,
            args=(self._generation, self._target, self._download, self._enable_hm, username,
                  self._liberator_name, self._verify),
            daemon=True,
        ).start()

    def _apply(self, generation: int, target: Path, download: dict, is_hm: bool,
               username: str, liberator_name: str | None, verify: bool) -> None:
        reporter = SignalReporter(self.log_line.emit)
        try:
            ok = apply_install(target, download, is_hm, username,
                               liberator_name=liberator_name, write_bat=not verify, reporter=reporter)
            if ok and verify and not is_hm and not (target / LAUNCH_BAT).exists():
                write_launch_bat(target)
        except Exception as e:
            self.log_line.emit(f"Install failed — {e}")
            ok = False
        self._apply_done.emit(generation, ok)

    def _on_apply_done(self, generation: int, ok: bool) -> None:
        if generation != self._generation or self._cancelled:
            return
        if ok:
            if self._verify:
                self.log_line.emit(f"{self._download['label']} verified")
            else:
                self.log_line.emit(f"{self._download['label']} installed to {self._target}")
            self._finish(0)
        else:
            self._finish(1)

    @Slot()
    def cancel(self) -> None:
        if not self._running:
            return
        self._cancelled = True
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
        else:
            self._finish(1)

    @Slot()
    def shutdown(self) -> None:
        self.cancel()
        proc = self._process
        if proc is not None and proc.state() != QProcess.ProcessState.NotRunning:
            proc.kill()
            proc.waitForFinished(2000)

    @Slot(result=str)
    def log_history(self) -> str:
        return "\n".join(self._history)

    @Slot()
    def refresh_protons(self) -> None:
        self._protons = list_protons()
        self.protons_changed.emit()

    @Slot(result=bool)
    def is_steam_running(self) -> bool:
        return steam_running()

    @Slot(int)
    def steam_setup(self, proton_index: int) -> None:
        if self._running:
            return
        if not self._download or proton_index < 0 or proton_index >= len(self._protons):
            self.steam_setup_done.emit(False, "Could not update Steam files")
            return
        proton = self._protons[proton_index]
        name = hm_display_name(self._download) if self._enable_hm else self._download["label"]
        launcher = self._target / launcher_name(self._enable_hm)
        mode = "heatedmetal" if self._enable_hm else "throwback"
        logo = MEDIA_DIR / f"{mode}_logo.png"
        icon = MEDIA_DIR / f"{mode}_icon.png"
        hero = None if self._enable_hm else MEDIA_DIR / "throwback_background.jpg"
        threading.Thread(
            target=self._steam_setup,
            args=(self._generation, name, launcher, self._target, proton, icon, logo, hero),
            daemon=True,
        ).start()

    def _steam_setup(self, generation: int, name: str, launcher: Path, target: Path,
                     proton: dict, icon: Path, logo: Path, hero: Path | None) -> None:
        try:
            if steam_running():
                self._steam_done.emit(generation, False, "Close Steam to apply")
                return
            ok = apply_steam_setup(name, launcher, target, proton, icon=icon, logo=logo, hero=hero)
        except Exception:
            ok = False
        self._steam_done.emit(generation, ok, f"{name} was added to Steam" if ok else "Could not update Steam files")

    def _on_steam_done(self, generation: int, ok: bool, message: str) -> None:
        if generation != self._generation:
            return
        self.steam_setup_done.emit(ok, message)

    def _finish(self, code: int) -> None:
        if self._process is not None:
            self._process.deleteLater()
            self._process = None
        self._login_pending = False
        self._buffer = ""
        if self._cancelled:
            self._set_state("idle")
            if self._active_key:
                self._active_key = ""
                self.active_key_changed.emit()
        else:
            self._set_state("done" if code == 0 else "failed")
        self._set_running(False)
        self.finished.emit(code)
