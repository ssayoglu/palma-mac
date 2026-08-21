#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  PALMA macOS — Güncelleme Betiği
#  Kullanım:
#    palma --update
#    veya: curl -fsSL https://raw.githubusercontent.com/ssayoglu/palma-mac/main/guncelle.sh | bash
# ─────────────────────────────────────────────────────────
set -euo pipefail

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

# ───────────────────── .app ikonunu güncelle
APP_DIR="$HOME/Applications/PALMA.app"
if [ -d "$APP_DIR" ] && [ -f "resources/palma.icns" ]; then
    cp resources/palma.icns "$APP_DIR/Contents/Resources/palma.icns" 2>/dev/null || true
    touch "$APP_DIR"
    log ".app ikonu güncellendi"
fi

# ───────────────────── palma CLI'ı güncelle
PYTHON="$(command -v python3.13 || echo /opt/homebrew/bin/python3.13)"
LAUNCHER="$HOME/.local/bin/palma"
if [ -f "$LAUNCHER" ]; then
    cat > "$LAUNCHER" <<SCRIPT
#!/usr/bin/env bash
if [ "\${1:-}" = "--update" ]; then
    exec bash "$INSTALL_DIR/guncelle.sh"
fi
exec "$PYTHON" "$INSTALL_DIR/src/__main__.py" "\$@"
SCRIPT
    chmod +x "$LAUNCHER"
fi

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║         ✓ Güncelleme tamamlandı!                ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Sürüm: ${BOLD}$NEW_VERSION${NC} ($NEW_COMMIT)"
echo ""
