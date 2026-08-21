#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  PALMA macOS ARM64 — Tek Komutla Kurulum
#  Kullanım:
#    curl -fsSL https://raw.githubusercontent.com/ssayoglu/palma-mac/main/kur.sh | bash
# ─────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

INSTALL_DIR="$HOME/palma-mac"
REPO_URL="https://github.com/ssayoglu/palma-mac.git"

log()  { echo -e "${GREEN}>>>${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
err()  { echo -e "${RED}✗${NC}  $*"; exit 1; }

# ───────────────────── Banner
echo ""
echo -e "${BLUE}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}${BOLD}║     PALMA macOS — Akıllı Kart Yönetimi          ║${NC}"
echo -e "${BLUE}${BOLD}║     ARM64 (Apple Silicon) Kurulumu               ║${NC}"
echo -e "${BLUE}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Bu kurucu resmi değildir; PALMA'nın topluluk portudur.${NC}"
echo ""

# ───────────────────── Mimari kontrolü
ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    err "Bu kurulum yalnızca Apple Silicon (ARM64) için. Mimariniz: $ARCH"
fi
log "Platform: macOS $ARCH ✓"

# ───────────────────── Homebrew
if command -v brew &>/dev/null; then
    log "Homebrew zaten kurulu ✓"
    BREW="$(command -v brew)"
elif [ -x /opt/homebrew/bin/brew ]; then
    log "Homebrew bulundu: /opt/homebrew/bin/brew ✓"
    BREW=/opt/homebrew/bin/brew
    eval "$($BREW shellenv zsh 2>/dev/null)" || true
else
    log "Homebrew kuruluyor..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    BREW=/opt/homebrew/bin/brew
    eval "$($BREW shellenv zsh 2>/dev/null)" || true
    log "Homebrew kuruldu ✓"
fi

# PATH'e ekle (mevcut oturum için)
export PATH="/opt/homebrew/bin:$PATH"

# ───────────────────── Python 3.13 + tkinter
PYTHON=""
if command -v python3.13 &>/dev/null; then
    PY_TK=$( python3.13 -c "import tkinter; print(tkinter.TkVersion)" 2>/dev/null || echo "yok" )
    if [ "$PY_TK" != "yok" ]; then
        log "Python 3.13 + Tk $PY_TK zaten kurulu ✓"
        PYTHON="$(command -v python3.13)"
    fi
fi

if [ -z "$PYTHON" ]; then
    log "Python 3.13 ve tkinter kuruluyor..."
    $BREW install python@3.13 python-tk@3.13 2>&1 | tail -5
    PYTHON="$($BREW --prefix python@3.13)/bin/python3.13"
    if [ ! -x "$PYTHON" ]; then
        PYTHON=/opt/homebrew/bin/python3.13
    fi
    log "Python 3.13 kuruldu ✓"
fi

# Doğrulama
PY_VER=$($PYTHON --version 2>&1)
TK_VER=$($PYTHON -c "import tkinter; print(tkinter.TkVersion)" 2>/dev/null || echo "?")
log "Python: $PY_VER — Tk: $TK_VER"

# ───────────────────── AKIS sürücü kontrolü ve kurulumu
PKCS11_LIB="/usr/local/lib/libakisp11.dylib"
DRIVER_PKG="$INSTALL_DIR/drivers/Akia_macos_arm_6_8_2.pkg"

_install_akis_driver() {
    if [ -f "$DRIVER_PKG" ]; then
        log "AKIS sürücüsü repo içinden kuruluyor..."
        log "  → $DRIVER_PKG"
        warn "Kurulum için yönetici şifresi gerekecektir."
        sudo installer -pkg "$DRIVER_PKG" -target / 2>&1 | tail -3
        if [ -f "$PKCS11_LIB" ]; then
            log "AKIS sürücüsü kuruldu ✓"
            return 0
        else
            warn "Kurulum tamamlandı ama sürücü dosyası bulunamadı."
            return 1
        fi
    else
        return 1
    fi
}

if [ -f "$PKCS11_LIB" ]; then
    log "AKIS PKCS#11 sürücüsü bulundu ✓"
    if file "$PKCS11_LIB" | grep -q "arm64"; then
        log "  → ARM64 desteği mevcut ✓"
    else
        warn "  → ARM64 dilimi bulunamadı! Sürücü güncelleniyor..."
        _install_akis_driver || warn "Sürücü güncellenemedi. Manuel olarak kurun."
    fi
else
    log "AKIS PKCS#11 sürücüsü bulunamadı, kuruluyor..."
    if ! _install_akis_driver; then
        echo ""
        warn "AKIS sürücüsü otomatik kurulamadı!"
        warn "Manuel kurulum:"
        warn "  1. https://eimza.bilgem.tubitak.gov.tr/akis-surucu adresinden indirin"
        warn "  2. .pkg dosyasını çift tıklayarak kurun"
        warn ""
    fi
fi

# ───────────────────── Projeyi indir/güncelle
if [ -d "$INSTALL_DIR/.git" ]; then
    log "Mevcut kurulum güncelleniyor: $INSTALL_DIR"
    cd "$INSTALL_DIR"
    git pull --ff-only 2>&1 | tail -3
else
    if [ -d "$INSTALL_DIR" ]; then
        warn "$INSTALL_DIR dizini zaten var ama git deposu değil, yedekleniyor..."
        mv "$INSTALL_DIR" "${INSTALL_DIR}.bak.$(date +%s)"
    fi
    log "Proje indiriliyor: $INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
chmod +x palma.sh
log "Proje hazır ✓"

# ───────────────────── Başlatıcı oluştur
LAUNCHER="$HOME/.local/bin/palma"
mkdir -p "$(dirname "$LAUNCHER")"
cat > "$LAUNCHER" <<SCRIPT
#!/usr/bin/env bash
if [ "\${1:-}" = "--update" ]; then
    exec bash "$INSTALL_DIR/guncelle.sh"
fi
exec "$PYTHON" "$INSTALL_DIR/src/__main__.py" "\$@"
SCRIPT
chmod +x "$LAUNCHER"
log "Komut satırı başlatıcısı: $LAUNCHER"

# PATH kontrolü
if echo "$PATH" | grep -q "$HOME/.local/bin"; then
    :
else
    # .zprofile'a ekle
    ZPROFILE="$HOME/.zprofile"
    if ! grep -q '.local/bin' "$ZPROFILE" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$ZPROFILE"
        log "PATH güncellendi (.zprofile)"
    fi
    export PATH="$HOME/.local/bin:$PATH"
fi

# ───────────────────── macOS .app oluştur
APP_DIR="$HOME/Applications/PALMA.app"
log "macOS uygulaması oluşturuluyor: $APP_DIR"

mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

cat > "$APP_DIR/Contents/Info.plist" <<'PLIST'
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

# İkon
if [ -f "$INSTALL_DIR/resources/palma.icns" ]; then
    cp "$INSTALL_DIR/resources/palma.icns" "$APP_DIR/Contents/Resources/palma.icns"
fi

# Başlatıcı
cat > "$APP_DIR/Contents/MacOS/palma" <<APPLAUNCHER
#!/bin/bash
export PATH="/opt/homebrew/bin:\\\$PATH"
PYTHON="\\\$(command -v python3.13 || echo /opt/homebrew/bin/python3.13)"
exec "\\\$PYTHON" "$INSTALL_DIR/src/__main__.py" "\\\$@"
APPLAUNCHER
chmod +x "$APP_DIR/Contents/MacOS/palma"

# Dock'u yenile
touch "$APP_DIR"
killall Dock 2>/dev/null || true
log "PALMA.app oluşturuldu ✓ (Launchpad'de görünecek)"

# ───────────────────── Tamamlandı
echo ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║         ✓ Kurulum tamamlandı!                   ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Başlatma:${NC}"
echo -e "    ${BLUE}PALMA.app${NC}        Uygulamalar'dan veya Launchpad'den"
echo -e "    ${BLUE}palma${NC}            Terminal'den GUI ile"
echo -e "    ${BLUE}palma --server${NC}   Tarayıcı sunucusu (headless)"
echo -e "    ${BLUE}palma --test${NC}     Kart bağlantı testi"
echo ""

# İlk test
if [ -f "$PKCS11_LIB" ]; then
    log "Kart bağlantı testi yapılıyor..."
    $PYTHON "$INSTALL_DIR/src/__main__.py" --test 2>&1 || true
    echo ""
fi

echo -e "${GREEN}İyi kullanımlar!${NC}"

