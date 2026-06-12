import sys
from pathlib import Path

QT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(QT_ROOT.parent))

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from mila.config import acquire_single_instance_lock, get_setting, load_config, save_config, set_setting
from mila.constants import CONFIG_FILE, MEDIA_DIR
from mila.manifest import load_downloads
from mila.radmin import detect_radmin_bridge
from mila.rpc import is_discord_installed, start_daemon

from backend.app import AppBackend
from backend.downloader import DownloadController
from backend.radmin import RadminController
from backend.tools import ToolsController
from backend.updater import UpdateController

def _show_error(app: QGuiApplication, message: str) -> int:
    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"message": message})
    engine.load(QUrl.fromLocalFile(str(QT_ROOT / "qml" / "ErrorWindow.qml")))
    if not engine.rootObjects():
        print(message, file=sys.stderr)
        return 1
    app.exec()
    del engine
    return 1


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Mila")
    app.setOrganizationName("Mila")
    QQuickStyle.setStyle("Material")
    icon = MEDIA_DIR / "throwback_icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    lock = acquire_single_instance_lock()
    if lock is None:
        return _show_error(app, "Mila is already running")

    cfg = load_config()
    if not CONFIG_FILE.exists():
        save_config(cfg)
    if not get_setting(cfg, "radmin_ip", ""):
        radmin_ip = detect_radmin_bridge()
        if radmin_ip:
            set_setting(cfg, "radmin_ip", radmin_ip)
            save_config(cfg)
    if get_setting(cfg, "discord_rpc", False) and is_discord_installed():
        start_daemon()

    try:
        downloads = load_downloads()
    except SystemExit as e:
        return _show_error(app, str(e.code) if e.code is not None else "Could not load manifest.toml")

    engine = QQmlApplicationEngine()
    backend = AppBackend(cfg, downloads, app)
    downloader = DownloadController(cfg, downloads, app)
    updater = UpdateController(cfg, downloads, app)
    tools = ToolsController(app)
    radmin = RadminController(cfg, app)
    downloader.set_peer(updater)
    updater.set_peer(downloader)
    tools.set_peer(downloader)
    radmin.ip_saved.connect(backend.settings_changed)
    app.aboutToQuit.connect(downloader.shutdown)
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty("downloader", downloader)
    engine.rootContext().setContextProperty("updater", updater)
    engine.rootContext().setContextProperty("tools", tools)
    engine.rootContext().setContextProperty("radmin", radmin)

    engine.load(QUrl.fromLocalFile(str(QT_ROOT / "qml" / "Main.qml")))
    if not engine.rootObjects():
        del engine
        return _show_error(app, "Could not load the interface")
    code = app.exec()
    del engine
    return code


if __name__ == "__main__":
    sys.exit(main())
