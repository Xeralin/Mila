import os
import re
import tempfile
from pathlib import Path

VERSION = "1.6.0"

_COMPILED = globals().get("__compiled__")
FROZEN = _COMPILED is not None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = (
    Path(_COMPILED.containing_dir).resolve() / "data"
    if _COMPILED else PROJECT_ROOT
)
BINARY_PATH = (
    Path(_COMPILED.containing_dir) / Path(_COMPILED.original_argv0).name
    if _COMPILED else None
)

MAIN_SCRIPT = PROJECT_ROOT / "main.py"
MEDIA_DIR = PROJECT_ROOT / "media"
MANIFEST_FILE = PROJECT_ROOT / "manifest.toml"

DOWNLOADS_DIR = DATA_ROOT / "downloads"
CONFIG_FILE = DATA_ROOT / "settings.toml"
LOCK_FILE = Path(tempfile.gettempdir()) / f"downloader-{os.getuid()}.lock"
BIN_DIR = DATA_ROOT / "bin"
TL_DIR = BIN_DIR / "ThrowbackLoader"
DD_BIN = BIN_DIR / "DepotDownloader"
DD_ZIP = BIN_DIR / "DepotDownloader-linux-x64.zip"
DD_URL = (
    "https://github.com/SteamRE/DepotDownloader/releases/latest/download/"
    "DepotDownloader-linux-x64.zip"
)
DD_API_URL = (
    "https://api.github.com/repos/SteamRE/DepotDownloader/releases/latest"
)

LIBERATOR_GLOB = "Liberator-*.exe"
LIBERATOR_API_URL = (
    "https://api.github.com/repos/Xeralin/Liberator/releases/latest"
)

CHEATENGINE_EXE = BIN_DIR / "CheatEngine.exe"

TL_API_URL = (
    "https://api.github.com/repos/Xeralin/ThrowbackLoader/releases/latest"
)
TL_DLLS_COMMON = ("defaultargs.dll", "steam_api64.dll")
UPC_LOADERS = ("upc_r1_loader64.dll", "upc_r2_loader64.dll")
TL_TOML = "Config.toml"
LAUNCHER_EXE = "LaunchR6S.exe"
TL_VERSION_FILE = ".version"
TL_EXTRACT = (
    TL_DLLS_COMMON
    + ("uplay_r1_loader64.dll",)
    + UPC_LOADERS
    + (TL_TOML, LAUNCHER_EXE)
)

HM_KEY = "heatedmetal"
HM_FOLDER_SUFFIX = "_HeatedMetal"

HM_BIN_DIR = BIN_DIR / "HeatedMetal"
HELIOS_DIR = HM_BIN_DIR / "helios"
HM_MOD_DIR = HM_BIN_DIR / "mod"
SEVENZ_BIN = BIN_DIR / "7zz"

UPDATE_API_URL = (
    "https://api.github.com/repos/Xeralin/Downloader/releases/latest"
)
UPDATE_ASSET = "downloader"
SEVENZ_API_URL = "https://api.github.com/repos/ip7z/7zip/releases/latest"
HM_API_URL = (
    "https://api.github.com/repos/DataCluster0/HeatedMetal/releases/latest"
)
HM_RELEASE_URL_FMT = (
    "https://github.com/DataCluster0/HeatedMetal/releases/download/"
    "{tag}/HeatedMetal.7z"
)
JVAV_HELIOS_URL = (
    "https://raw.githubusercontent.com/JOJOVAV/r6-downloader/main/"
    "cracks/HeliosLoader.zip"
)

HELIOS_JSON = "HeliosLoader.json"
HELIOS_FILES = (
    HELIOS_JSON,
    "steam_api64.dll",
    "upc_r2_loader64.dll",
    "uplay_r1_loader64.dll",
    "uplay_r2_loader64.dll",
)

STEAM_DIR = Path.home() / ".local" / "share" / "Steam"
STEAM_USERDATA = STEAM_DIR / "userdata"
STEAM_COMPATDATA = STEAM_DIR / "steamapps" / "compatdata"
STEAM_COMMON = STEAM_DIR / "steamapps" / "common"
STEAM_COMPAT_TOOLS_D = STEAM_DIR / "compatibilitytools.d"
STEAM_CONFIG_VDF = STEAM_DIR / "config" / "config.vdf"
SHORTCUTS_VDF = "config/shortcuts.vdf"

PROTON_BUILTIN = (
    ("Proton - Experimental", "proton_experimental", "Proton Experimental"),
    ("Proton Hotfix", "proton_hotfix", "Proton Hotfix"),
)

VBOX_IFACE = "vboxnet0"
VBOX_CMD = "VBoxManage"

DEFAULT_USERNAME = "ThrowbackUser"
DEFAULT_MAX_DOWNLOADS = 25

DOWNLOAD_SPEED_PRESETS = (
    ("Slow",   15),
    ("Normal", 25),
    ("Fast",   50),
)

NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
MAX_USERNAME_LENGTH = 16

TEXTURE_QUALITIES = ("Low", "Medium", "High", "Very High", "Ultra")
TEXTURE_RX = re.compile(r"textures(\d)")
