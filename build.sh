#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python3 -m nuitka \
    --onefile \
    --assume-yes-for-downloads \
    --remove-output \
    --output-filename=downloader \
    --include-data-dir=media=media \
    --include-data-file=manifest.toml=manifest.toml \
    main.py

echo "Built ./downloader"
