# Mila

**M**ila **I**s **L**inux **A**pproved

![Preview](media/preview.png)

A CLI downloader and manager for **Operation Throwback** and **Heated Metal** (Tom Clancy’s Rainbow Six® Siege) on Linux.

## Requirements

- A Linux machine
- Python 3.11 or newer
- Native Steam (no Flatpak, no Snap)
- A Steam account that owns Tom Clancy’s Rainbow Six® Siege

## Installation

1. Download and extract the **Mila.zip** from the [latest release](https://github.com/Xeralin/Mila/releases)
2. Open a terminal in the extracted folder and run `python main.py`
3. Have fun :)

> [!NOTE]
> The **Info** screen lists available updates — for Mila itself, its bundled tools, and Heated Metal. Updating Mila applies in place and restarts. If you cloned the repo with git, use `git pull` for Mila instead.

> Mila supports HM Y5S3 Shadow Legacy and HM Y5S4 Neon Dawn. Unfortunately, HM Y9S2 New Blood is currently broken.

## Usage

Pick a season from the **Game downloader** option and log in with your Steam account. The season will then be downloaded to the `downloads/` folder.

### Automatic (recommended)

1. Confirm *Add to Steam?* at the end of the download
2. **Close Steam** and pick a compatibility layer
3. Mila adds the entry to your Steam library
4. Open Steam and click *Play*

### Manual

1. Open Steam > Games > Add a Non-Steam Game > Browse
2. Inside `downloads/<season>/`, select `LaunchR6.bat` (Throwback) or `RainbowSix.exe` (Heated Metal)
3. Right-click the entry > Properties, then
   - General > uncheck *Enable the Steam Overlay while in-game*
   - Compatibility > enable *Force the use of a specific Steam Play tool* and pick a compatibility layer

> [!IMPORTANT]
> Mila downloads the season files directly from Steam, so you log in with a Steam account that owns Rainbow Six Siege. Your password is never stored — DepotDownloader keeps only an encrypted access token, just like the Steam client. To log out, open Help > *Does my Steam login get stored?* > Log out.

## Liberator

Confirm *Enable Liberator?* at the download prompt — Mila fetches [Liberator](https://github.com/Xeralin/Liberator) automatically and wires it into the season's launch script. For seasons already in `downloads/`, toggle **Liberator** in *Settings*.

The unlock enables a few seconds after the game launches. Supported seasons carry `liberator = true` in `manifest.toml`.

## RadminVPN

Unfortunately, RadminVPN is only available for Windows. To join a RadminVPN network on Linux, we need a bridge. If you don't need RadminVPN, you can use native programs like [ZeroTier](https://www.zerotier.com/).

### Using a virtual machine (recommended)

1. Use [VirtualBox](https://www.virtualbox.org/) to create a virtual machine running Windows, on which you install RadminVPN
2. Tools > RadminVPN > Create bridge > Enter your own RadminVPN IP address here
3. Shut down your VM and run Tools > RadminVPN > Attach VM to bridge
4. In Windows, open `ncpa.cpl`, select the Ethernet 2 host-only adapter and the Radmin VPN adapter > right-click > Bridge Connections

### Using a second Windows PC

1. Connect both machines with an Ethernet cable
2. On Linux, replace `<iface>` with your Ethernet adapter (find with `ip -br link`) and `<radmin-ip>` with your RadminVPN IP, then run this command:
   ```bash
   IFACE=<iface>
   IP=<radmin-ip>

   sudo ip addr add $IP/8 dev $IFACE
   sudo ip link set $IFACE up
   sudo ip route add 224.0.0.0/4 dev $IFACE
   sudo ip route add 26.255.255.255/32 dev $IFACE
   sudo ip route add 255.255.255.255/32 dev $IFACE
   ```
3. On the second PC, open `ncpa.cpl`, select the Ethernet adapter and the Radmin VPN adapter > right-click > Bridge Connections

> [!NOTE]
> **Linux:** The bridge does not survive a reboot. Go to Tools > RadminVPN > Create bridge.
>
> **Windows:** The bridge breaks if you restart windows (RadminVPN shows *waiting for adapter response*) or fails to create the bridge (Windows shows *An unexpected error occurred while configuring the Network Bridge.*). Delete the Network Bridge in `ncpa.cpl` and bridge the adapters again — it's bound to work eventually.
>
> ![Bridge](media/bridge.png)
