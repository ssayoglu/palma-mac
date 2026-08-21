#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  PALMA macOS — Güncelleme Betiği
#  Kullanım:
#    palma --update
#    veya: curl -fsSL https://raw.githubusercontent.com/ssayoglu/palma-mac/main/guncelle.sh | bash
# ─────────────────────────────────────────────────────────
set -euo pipefail

if [ ! -t 0 ]; then
    exec < /dev/tty
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

log()  { echo -e "${GREEN}>>>${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "${RED}✗${NC}  $*"; exit 1; }

# ───────────────────── Kurulum dizinini bul
INSTALL_DIR=""
for d in "$HOME/palma-mac" "$HOME/Documents/antigravity/friendly-newton/palma-mac"; do
    if [ -d "$d/.git" ]; then
        INSTALL_DIR="$d"
        break
    fi
done

if [ -z "$INSTALL_DIR" ]; then
    err "PALMA kurulumu bulunamadı. Önce kurulum yapın:\n    curl -fsSL https://raw.githubusercontent.com/ssayoglu/palma-mac/main/kur.sh | bash"
fi

cd "$INSTALL_DIR"

echo ""
echo -e "${BLUE}${BOLD}  PALMA macOS — Güncelleme Kontrolü${NC}"
echo ""

# ───────────────────── Mevcut sürümü oku
LOCAL_VERSION="bilinmiyor"
if [ -f "src/__main__.py" ]; then
    LOCAL_VERSION=$(grep -o 'version.*[0-9]\+\.[0-9]\+\.[0-9]\+' src/__main__.py 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1 || echo "bilinmiyor")
fi
LOCAL_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "?")
log "Mevcut sürüm: $LOCAL_VERSION ($LOCAL_COMMIT)"

# ───────────────────── Uzak değişiklikleri kontrol et
log "GitHub kontrol ediliyor..."
git fetch origin main --quiet 2>/dev/null || err "GitHub'a bağlanılamadı. İnternet bağlantınızı kontrol edin."

REMOTE_COMMIT=$(git rev-parse --short origin/main 2>/dev/null || echo "?")
LOCAL_FULL=$(git rev-parse HEAD 2>/dev/null)
REMOTE_FULL=$(git rev-parse origin/main 2>/dev/null)

if [ "$LOCAL_FULL" = "$REMOTE_FULL" ]; then
    echo ""
    echo -e "  ${GREEN}${BOLD}✓ PALMA güncel!${NC} ($LOCAL_VERSION — $LOCAL_COMMIT)"
    echo ""
    exit 0
fi

# ───────────────────── Değişiklikleri göster
BEHIND=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "?")
echo ""
echo -e "  ${YELLOW}${BOLD}⬆ Güncelleme mevcut!${NC}"
echo -e "  Yerel:  $LOCAL_COMMIT"
echo -e "  Uzak:   $REMOTE_COMMIT ($BEHIND yeni commit)"
echo ""

# Son değişiklikleri listele
log "Değişiklikler:"
git log --oneline HEAD..origin/main 2>/dev/null | head -10 | while read -r line; do
    echo -e "  ${BLUE}•${NC} $line"
done
echo ""

# ───────────────────── Güncelle
log "Güncelleniyor..."

# Yerel değişiklik varsa stash'le
if ! git diff --quiet 2>/dev/null; then
    warn "Yerel değişiklikler tespit edildi, yedekleniyor..."
    git stash push -m "palma-update-$(date +%s)" --quiet
fi

git pull --ff-only origin main --quiet 2>/dev/null || {
    warn "Hızlı güncelleme yapılamadı, zorla güncelleniyor..."
    git reset --hard origin/main --quiet
}

# ───────────────────── Sürüm bilgisini yeniden oku
NEW_VERSION=$(grep -o 'version.*[0-9]\+\.[0-9]\+\.[0-9]\+' src/__main__.py 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1 || echo "?")
NEW_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "?")

# ───────────────────── .app oluştur/güncelle
APP_DIR="/Applications/PALMA.app"
PYTHON="$(command -v python3.13 || echo /opt/homebrew/bin/python3.13)"

if [ ! -d "$APP_DIR" ]; then
    log "PALMA.app oluşturuluyor..."
    warn "Uygulamalar klasörü için yönetici şifresi gerekebilir."
    sudo mkdir -p "$APP_DIR/Contents/MacOS"
    sudo mkdir -p "$APP_DIR/Contents/Resources"

    sudo tee "$APP_DIR/Contents/Info.plist" > /dev/null <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>PALMA</string>
    <key>CFBundleDisplayName</key>
    <string>PALMA — Akıllı Kart Yönetimi</string>
    <key>CFBundleIdentifier</key>
    <string>com.turktrust.palma-mac</string>
    <key>CFBundleVersion</key>
    <string>2.9.0</string>
    <key>CFBundleShortVersionString</key>
    <string>2.9.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>palma</string>
    <key>CFBundleIconFile</key>
    <string>palma</string>
    <key>LSMinimumSystemVersion</key>
    <string>14.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST
fi

# Başlatıcı (her zaman güncelle — yol değişmiş olabilir)
sudo tee "$APP_DIR/Contents/MacOS/palma" > /dev/null <<APPLAUNCHER
#!/bin/bash
export PATH="/opt/homebrew/bin:\$PATH"
PY="\$(command -v python3.13 || echo /opt/homebrew/bin/python3.13)"
exec "\$PY" "$INSTALL_DIR/src/__main__.py" "\$@"
APPLAUNCHER
sudo chmod +x "$APP_DIR/Contents/MacOS/palma"

# İkon
if [ -f "$INSTALL_DIR/resources/palma.icns" ]; then
    sudo cp "$INSTALL_DIR/resources/palma.icns" "$APP_DIR/Contents/Resources/palma.icns" 2>/dev/null || true
fi

sudo touch "$APP_DIR"
killall Dock 2>/dev/null || true
log "PALMA.app hazır ✓"

# ───────────────────── palma CLI güncelle
LAUNCHER="$HOME/.local/bin/palma"
mkdir -p "$(dirname "$LAUNCHER")"
cat > "$LAUNCHER" <<SCRIPT
#!/usr/bin/env bash
case "\${1:-}" in
    --update)    exec bash "$INSTALL_DIR/guncelle.sh" ;;
    --uninstall) exec bash "$INSTALL_DIR/kaldir.sh" ;;
esac
exec "$PYTHON" "$INSTALL_DIR/src/__main__.py" "\$@"
SCRIPT
chmod +x "$LAUNCHER"
log "CLI güncellendi ✓"

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║         ✓ Güncelleme tamamlandı!                ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Sürüm: ${BOLD}$NEW_VERSION${NC} ($NEW_COMMIT)"
echo ""
