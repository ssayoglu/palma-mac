#!/usr/bin/env python3
"""
PALMA macOS — Ana giriş noktası.

Kullanım:
    python3 -m palma          # GUI ile başlat
    python3 -m palma --server  # Yalnızca sunucu (headless)
    python3 -m palma --test    # Kart bağlantı testi
"""
import argparse
import logging
import os
import sys

# Proje kök dizinini Python path'ine ekle
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

LOG_DIR = os.path.expanduser("~/Library/Logs/PalmaMac")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "palma.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("palma")


def _create_pkcs11_module():
    """PKCS#11 modülünü yükle."""
    from src.core.pkcs11_wrapper import PKCS11Module
    mod = PKCS11Module()
    mod.initialize()
    return mod


def _run_test():
    """Kart bağlantı testi — sertifikaları listele."""
    print("=" * 50)
    print("PALMA macOS — Kart Bağlantı Testi")
    print("=" * 50)

    try:
        mod = _create_pkcs11_module()
    except Exception as e:
        print(f"\n✗ PKCS#11 kütüphanesi yüklenemedi: {e}")
        print("  libakisp11.dylib yolunu kontrol edin.")
        return 1

    from src.core.card_manager import CardManager
    cm = CardManager(mod)

    try:
        slots = cm.get_slots(token_present=False)
        print(f"\nOkuyucular ({len(slots)}):")
        for s in slots:
            tp = "✓ Kart var" if s.token_present else "✗ Kart yok"
            desc = getattr(s, 'description', '') or f"Slot {s.slot_id}"
            print(f"  [{s.slot_id}] {desc} — {tp}")

        token_slots = cm.get_slots(token_present=True)
        if not token_slots:
            print("\n⚠ Kart takılı slot bulunamadı.")
            return 0

        slot = token_slots[0]
        info = cm.get_token_info(slot.slot_id)
        print(f"\nToken Bilgisi:")
        print(f"  Etiket:      {info.label}")
        print(f"  Üretici:     {info.manufacturer}")
        print(f"  Model:       {info.model}")
        print(f"  Seri No:     {info.serial_number}")

        print(f"\n✓ Kart bağlantısı başarılı!")
        return 0

    except Exception as e:
        print(f"\n✗ Hata: {e}")
        return 1
    finally:
        try:
            mod.finalize()
        except Exception:
            pass


def _run_server_only():
    """Yalnızca sunucuyu başlat (headless mod)."""
    print("PALMA macOS — Headless Sunucu Modu")
    print("Sunucu: https://localhost:8443")
    print("Durdurmak için Ctrl+C\n")

    try:
        mod = _create_pkcs11_module()
    except Exception as e:
        print(f"✗ PKCS#11 yüklenemedi: {e}")
        return 1

    from src.core.card_manager import CardManager
    from src.core.pin_manager import PINManager
    from src.server.local_server import PalmaLocalServer

    cm = CardManager(mod)
    pm = PINManager(mod)
    server = PalmaLocalServer(cm, pm)

    try:
        server.start()
        print("✓ Sunucu başlatıldı. Bekleniyor…")
        import signal
        signal.pause()
    except KeyboardInterrupt:
        print("\nSunucu durduruluyor…")
        server.stop()
        mod.finalize()
        print("✓ Durduruldu.")
        return 0
    except Exception as e:
        print(f"✗ Sunucu hatası: {e}")
        return 1


def _run_gui():
    """GUI uygulamasını başlat."""
    logger.info("PALMA macOS GUI başlatılıyor…")

    try:
        mod = _create_pkcs11_module()
    except Exception as e:
        logger.error(f"PKCS#11 yüklenemedi: {e}")
        # GUI'yi yine de başlat, kart işlemleri hata verir
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("PALMA Hatası",
                             f"PKCS#11 kütüphanesi yüklenemedi:\n{e}\n\n"
                             "libakisp11.dylib dosyasının /usr/local/lib/ "
                             "dizininde olduğundan emin olun.")
        root.destroy()
        return 1

    from src.core.card_manager import CardManager
    from src.core.pin_manager import PINManager
    from src.server.local_server import PalmaLocalServer
    from src.services.activation import ActivationService
    from src.gui.app import PalmaApp

    cm = CardManager(mod)
    pm = PINManager(mod)
    server = PalmaLocalServer(cm, pm)
    activation = ActivationService()

    app = PalmaApp(cm, pm, server=server, activation_service=activation)

    try:
        app.run()
    finally:
        if server.is_running():
            server.stop()
        try:
            mod.finalize()
        except Exception:
            pass
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="palma",
        description="PALMA macOS — TÜRKTRUST Akıllı Kart Yönetimi"
    )
    parser.add_argument("--test", action="store_true",
                        help="Kart bağlantı testi")
    parser.add_argument("--server", action="store_true",
                        help="Yalnızca HTTPS sunucu (headless)")
    parser.add_argument("--version", action="version",
                        version="PALMA macOS 2.9.0")
    args = parser.parse_args()

    if args.test:
        sys.exit(_run_test())
    elif args.server:
        sys.exit(_run_server_only())
    else:
        sys.exit(_run_gui())


if __name__ == "__main__":
    main()
