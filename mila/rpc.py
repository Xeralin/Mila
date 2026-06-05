import fcntl
import json
import os
import select
import shutil
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from mila.constants import (
    DISCORD_CLIENT_ID_HEATEDMETAL,
    DISCORD_CLIENT_ID_THROWBACK,
    DOWNLOADS_DIR,
    RPC_LOCK_FILE,
)
from mila.manifest import hm_display_name, load_downloads, resolve_install

OP_HANDSHAKE = 0
OP_FRAME = 1
OP_CLOSE = 2
OP_PING = 3
OP_PONG = 4

POLL_INTERVAL = 10
MAX_RECONNECT_DELAY = 30
IPC_TIMEOUT = 10

_stop = threading.Event()


def _ipc_paths():
    bases = []
    for env in ("XDG_RUNTIME_DIR", "TMPDIR", "TMP", "TEMP"):
        v = os.environ.get(env)
        if v:
            bases.append(v)
    bases.append("/tmp")
    subs = (
        "",
        "app/com.discordapp.Discord",
        ".flatpak/com.discordapp.Discord/xdg-run",
    )
    for base in bases:
        for sub in subs:
            d = Path(base) / sub
            for i in range(10):
                p = d / f"discord-ipc-{i}"
                if p.exists():
                    yield str(p)


class Presence:
    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self.sock: socket.socket | None = None

    @property
    def connected(self) -> bool:
        return self.sock is not None

    def connect(self) -> bool:
        for path in _ipc_paths():
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(IPC_TIMEOUT)
                s.connect(path)
                self.sock = s
                self._send(OP_HANDSHAKE, {"v": 1, "client_id": self.client_id})
                op, _ = self._recv()
                if op == OP_FRAME:
                    return True
                self.close()
            except (OSError, ConnectionError):
                continue
        return False

    def _send(self, op: int, payload: dict) -> None:
        sock = self.sock
        if sock is None:
            raise ConnectionError("not connected")
        data = json.dumps(payload).encode()
        sock.sendall(struct.pack("<II", op, len(data)) + data)

    def _recv(self) -> tuple[int, dict]:
        sock = self.sock
        if sock is None:
            raise ConnectionError("not connected")
        header = b""
        while len(header) < 8:
            chunk = sock.recv(8 - len(header))
            if not chunk:
                raise ConnectionError("socket closed")
            header += chunk
        op, length = struct.unpack("<II", header)
        body = b""
        while len(body) < length:
            chunk = sock.recv(length - len(body))
            if not chunk:
                raise ConnectionError("socket closed")
            body += chunk
        return op, json.loads(body.decode())

    def _await_response(self, nonce: str) -> bool:
        while True:
            op, payload = self._recv()
            if op == OP_PING:
                self._send(OP_PONG, payload)
                continue
            if op == OP_FRAME and payload.get("nonce") == nonce:
                return True

    def _send_activity(self, activity: dict | None) -> bool:
        try:
            nonce = str(uuid.uuid4())
            self._send(OP_FRAME, {
                "cmd": "SET_ACTIVITY",
                "args": {"pid": os.getpid(), "activity": activity},
                "nonce": nonce,
            })
            return self._await_response(nonce)
        except (OSError, ConnectionError):
            self.close()
            return False

    def set(self, activity: dict) -> bool:
        return self._send_activity(activity)

    def clear(self) -> bool:
        return self._send_activity(None)

    def drain(self) -> None:
        if not self.sock:
            return
        try:
            while select.select([self.sock], [], [], 0)[0]:
                op, payload = self._recv()
                if op == OP_PING:
                    self._send(OP_PONG, payload)
        except (OSError, ConnectionError):
            self.close()

    def close(self) -> None:
        if self.sock:
            try:
                self._send(OP_CLOSE, {})
            except (OSError, ConnectionError):
                pass
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None


def _find_game_folder() -> str | None:
    out = subprocess.run(
        ["pgrep", "-f", r"RainbowSix.*\.exe"],
        capture_output=True, text=True, check=False,
    )
    downloads_root = DOWNLOADS_DIR.resolve()
    for pid in out.stdout.split():
        try:
            cwd = Path(f"/proc/{pid}/cwd").resolve()
        except (FileNotFoundError, PermissionError, OSError):
            continue
        try:
            rel = cwd.relative_to(downloads_root)
        except ValueError:
            continue
        if rel.parts:
            return rel.parts[0]
    return None


def _resolve_session(folder: str, downloads: list[dict]) -> tuple[str, str, str] | None:
    resolved = resolve_install(folder, downloads)
    if resolved is None:
        return None
    download, is_hm = resolved
    client_id = DISCORD_CLIENT_ID_HEATEDMETAL if is_hm else DISCORD_CLIENT_ID_THROWBACK
    icon = "heatedmetal" if is_hm else "throwback"
    label = hm_display_name(download) if is_hm else download["label"]
    return client_id, icon, label


def _build_activity(label: str, icon: str, start_time: int) -> dict:
    return {
        "details": label,
        "assets": {
            "large_image": icon,
            "large_text": label,
        },
        "timestamps": {"start": start_time},
        "buttons": [
            {"label": "Rainbow Six on Linux", "url": "https://github.com/Xeralin/Mila/"},
        ],
    }


def _acquire_lock():
    fp = open(RPC_LOCK_FILE, "a+")
    try:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fp.close()
        return None
    fp.seek(0)
    fp.truncate()
    fp.write(str(os.getpid()))
    fp.flush()
    return fp


def _handle_signal(signum: int, frame) -> None:
    _stop.set()


def is_daemon_running() -> bool:
    try:
        fp = open(RPC_LOCK_FILE, "r")
    except FileNotFoundError:
        return False
    try:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
        return False
    except BlockingIOError:
        return True
    finally:
        fp.close()


def is_discord_installed() -> bool:
    for name in ("discord", "Discord", "discord-stable", "discord-canary", "discord-ptb"):
        if shutil.which(name):
            return True
    try:
        return subprocess.run(
            ["flatpak", "info", "com.discordapp.Discord"],
            capture_output=True, check=False,
        ).returncode == 0
    except FileNotFoundError:
        return False


def start_daemon() -> None:
    if is_daemon_running():
        return
    subprocess.Popen(
        [sys.executable, "-m", "mila.rpc"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )


def stop_daemon() -> None:
    try:
        pid = int(RPC_LOCK_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def main() -> int:
    lock_fp = _acquire_lock()
    if lock_fp is None:
        return 0

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    downloads = load_downloads()
    presence: Presence | None = None
    current_folder: str | None = None
    current_client_id: str | None = None
    start_time = 0
    reconnect_delay = 1

    try:
        while not _stop.is_set():
            if presence and presence.connected:
                presence.drain()

            folder = _find_game_folder()

            if folder is None:
                if current_folder is not None:
                    if presence:
                        presence.clear()
                        presence.close()
                        presence = None
                    current_folder = None
                    current_client_id = None
                    start_time = 0
                    reconnect_delay = 1
            else:
                session = _resolve_session(folder, downloads)
                if session is not None:
                    client_id, icon, label = session
                    if (presence is None
                            or not presence.connected
                            or current_client_id != client_id):
                        if presence is not None:
                            presence.close()
                        presence = Presence(client_id)
                        if not presence.connect():
                            delay = reconnect_delay
                            reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)
                            if _stop.wait(delay):
                                break
                            continue
                        current_client_id = client_id
                        reconnect_delay = 1
                        need_push = True
                    else:
                        need_push = current_folder != folder

                    if need_push:
                        if current_folder != folder:
                            start_time = int(time.time())
                        if presence.set(_build_activity(label, icon, start_time)):
                            current_folder = folder

            if _stop.wait(POLL_INTERVAL):
                break
    finally:
        if presence:
            presence.clear()
            presence.close()
        lock_fp.close()
        RPC_LOCK_FILE.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
