#!/bin/sh
set -e

repo="Xeralin/Downloader"
dir="$HOME/.local/share/Downloader"
bin="$dir/downloader"

if [ "$(id -u)" -eq 0 ]; then
    echo "Please run as a normal user, not root."
    exit 1
fi

mkdir -p "$dir"

if [ -e "$bin" ]; then action="Updating"; else action="Downloading"; fi

curl -fsSL "https://github.com/$repo/releases/latest/download/downloader" -o "$bin" &
pid=$!
while kill -0 "$pid" 2>/dev/null; do
    for f in ⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏; do
        printf '\r\033[95m%s\033[0m %s Downloader' "$f" "$action"
        sleep 0.1
        kill -0 "$pid" 2>/dev/null || break
    done
done
wait "$pid" || { printf '\r\033[K'; echo "Download failed."; exit 1; }
printf '\r\033[K'

chmod +x "$bin"

mkdir -p "$HOME/.local/bin"
ln -sf "$bin" "$HOME/.local/bin/downloader"

echo "Installed to $bin"
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) echo "Add ~/.local/bin to your PATH to run 'downloader' from anywhere." ;;
esac

echo
exec "$bin"
