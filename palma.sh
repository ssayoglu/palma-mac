#!/usr/bin/env bash
# PALMA macOS — Başlatıcı
# Kullanım:
#   ./palma.sh          # GUI
#   ./palma.sh --test   # Kart testi
#   ./palma.sh --server # Headless sunucu
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

# Homebrew Python 3.13 (Tk 9.0 destekli) tercih et
if [ -x /opt/homebrew/bin/python3.13 ]; then
    PYTHON=/opt/homebrew/bin/python3.13
elif [ -x /opt/homebrew/bin/python3 ]; then
    PYTHON=/opt/homebrew/bin/python3
else
    PYTHON=python3
fi

exec "$PYTHON" "$ROOT/src/__main__.py" "$@"
