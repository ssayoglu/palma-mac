#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  PALMA macOS — Kaldırma Betiği
#  Kullanım:
#    palma --uninstall
#    veya: curl -fsSL https://raw.githubusercontent.com/ssayoglu/palma-mac/main/kaldir.sh | bash
#
#  NOT: AKIS PKCS#11 sürücüsünü (libakisp11.dylib) KALDIRMAZ.
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

echo ""
echo -e "${RED}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${RED}${BOLD}║     PALMA macOS — Kaldırma                      ║${NC}"
echo -e "${RED}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Aşağıdakiler kaldırılacak:"
echo -e "    ${BLUE}•${NC} ~/palma-mac (veya mevcut kurulum dizini)"
echo -e "    ${BLUE}•${NC} ~/Applications/PALMA.app"
echo -e "    ${BLUE}•${NC} ~/.local/bin/palma"
echo -e "    ${BLUE}•${NC} ~/.palma (SSL sertifikaları)"
echo -e "    ${BLUE}•${NC} ~/Library/Logs/PalmaMac"
echo ""
echo -e "  ${GREEN}Korunacak:${NC}"
echo -e "    ${BLUE}•${NC} AKIS PKCS#11 sürücüsü (/usr/local/lib/libakisp11.dylib)"
echo -e "    ${BLUE}•${NC} Homebrew / Python 3.13"
echo ""

read -rp "Kaldırmak istediğinizden emin misiniz? [e/H]: " confirm
if [[ ! "$confirm" =~ ^[eEyY]$ ]]; then
    echo "İptal edildi."
    exit 0
fi

echo ""

# ───────────────────── PALMA.app
APP_DIR="$HOME/Applications/PALMA.app"
if [ -d "$APP_DIR" ]; then
    rm -rf "$APP_DIR"
    log "PALMA.app kaldırıldı ✓"
else
    log "PALMA.app bulunamadı, atlanıyor"
fi

# ───────────────────── CLI launcher
LAUNCHER="$HOME/.local/bin/palma"
if [ -f "$LAUNCHER" ]; then
    rm -f "$LAUNCHER"
    log "palma komutu kaldırıldı ✓"
else
    log "palma komutu bulunamadı, atlanıyor"
fi

# ───────────────────── SSL sertifikaları
CERT_DIR="$HOME/.palma"
if [ -d "$CERT_DIR" ]; then
    rm -rf "$CERT_DIR"
    log "SSL sertifikaları kaldırıldı ✓"
fi

# ───────────────────── Log dosyaları
LOG_DIR="$HOME/Library/Logs/PalmaMac"
if [ -d "$LOG_DIR" ]; then
    rm -rf "$LOG_DIR"
    log "Log dosyaları kaldırıldı ✓"
fi

# ───────────────────── Proje dizini (en son — çünkü bu script de burada)
for d in "$HOME/palma-mac" "$HOME/Documents/antigravity/friendly-newton/palma-mac"; do
    if [ -d "$d/.git" ]; then
        rm -rf "$d"
        log "Proje dizini kaldırıldı: $d ✓"
    fi
done

# ───────────────────── Dock yenile
killall Dock 2>/dev/null || true

echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║         ✓ PALMA kaldırıldı!                     ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  AKIS sürücüsü korundu: /usr/local/lib/libakisp11.dylib"
echo -e "  Yeniden kurmak için:"
echo -e "    ${BLUE}curl -fsSL https://raw.githubusercontent.com/ssayoglu/palma-mac/main/kur.sh | bash${NC}"
echo ""
