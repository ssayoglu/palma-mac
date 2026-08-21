# PALMA macOS — Akıllı Kart Yönetimi (ARM64)

PALMA'nın macOS ARM64 (Apple Silicon) platformuna topluluk tarafından oluşturulmuş portudur.
TÜRKTRUST akıllı kart (e-imza/e-mühür) yönetimi ve tarayıcı entegrasyonu sağlar.

> ⚠️ **Bu uygulama resmi değildir.** PALMA Windows uygulamasının tersine mühendislik ile oluşturulan macOS portudur.

---

## ✨ Özellikler

| Özellik | Durum |
|---------|-------|
| 📜 Sertifika okuma ve görüntüleme | ✅ |
| 🔑 PIN doğrulama | ✅ |
| 🔑 PIN değiştirme | ✅ |
| 📋 Kart/Token bilgisi okuma | ✅ |
| 🌐 Tarayıcı entegrasyonu (localhost:8443) | ✅ |
| 🖥️ macOS .app (Launchpad desteği) | ✅ |
| 🔄 Otomatik güncelleme | ✅ |
| ✅ Sertifika aktivasyonu | ⚠️ TÜRKTRUST servisi gerekli |
| 📞 Telefon doğrulama (arama) | ⚠️ TÜRKTRUST servisi gerekli |

## 📋 Gereksinimler

- **macOS** (Apple Silicon / ARM64)
- **Akıllı kart okuyucu** (PCSC uyumlu, ör. ACS ACR39U)
- **TÜRKTRUST e-imza kartı**

> Diğer bağımlılıklar (Homebrew, Python 3.13, AKIS sürücüsü) kurulum betiği tarafından otomatik yüklenir.

## 🚀 Kurulum (Tek Komut)

```bash
curl -fsSL https://raw.githubusercontent.com/ssayoglu/palma-mac/main/kur.sh | bash
```

Bu komut otomatik olarak:
- ✅ Homebrew'u kurar (yoksa)
- ✅ Python 3.13 + tkinter kurar
- ✅ AKIS PKCS#11 sürücüsünü kurar (`libakisp11.dylib`)
- ✅ Projeyi `~/palma-mac` dizinine indirir
- ✅ **PALMA.app** oluşturur (Launchpad'de görünür)
- ✅ `palma` komutunu PATH'e ekler
- ✅ Kart bağlantı testini çalıştırır

## 🔄 Güncelleme

```bash
palma --update
```

veya:

```bash
curl -fsSL https://raw.githubusercontent.com/ssayoglu/palma-mac/main/guncelle.sh | bash
```

Güncelleme betiği:
- GitHub'dan son sürümü kontrol eder
- Değişiklik listesini gösterir
- Yerel değişiklikleri koruyarak günceller
- .app ve CLI launcher'ı günceller

## 🎯 Kullanım

### Launchpad / Uygulamalar
Kurulumdan sonra **PALMA** uygulaması Launchpad'de ve `~/Applications` dizininde görünür. Tıklayarak başlatın.

### Terminal

```bash
palma              # GUI ile başlat
palma --server     # Tarayıcı sunucusu (headless)
palma --test       # Kart bağlantı testi
palma --update     # Güncelleme kontrolü
palma --version    # Sürüm bilgisi
```

## 🌐 Tarayıcı Entegrasyonu (API)

Sunucu başlatıldığında (`--server` veya GUI → Sunucu sekmesi) aşağıdaki endpoint'ler `https://localhost:8443` üzerinden kullanılabilir:

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| GET | `/status` | Sunucu durumu |
| GET | `/readers` | Bağlı okuyucu listesi |
| GET | `/token-info?slot=N` | Kart/token bilgileri |
| GET | `/certificates?slot=N&pin=XXXX` | Sertifika listesi |
| POST | `/verify-pin` | PIN doğrulama |
| POST | `/sign` | İmza işlemi |

### Örnek

```bash
curl -sk https://localhost:8443/status
# {"running": true, "version": "2.9.0-mac"}

curl -sk https://localhost:8443/readers
# [{"name": "ACS ACR39U ICC Reader", "slot_id": 1}]

curl -sk "https://localhost:8443/token-info?slot=1"
# {"label": "AKIS_...", "manufacturer": "TUBITAK_UEKAE", ...}
```

> **Not:** İlk çalıştırmada `~/.palma/` dizininde kendinden imzalı SSL sertifikası oluşturulur.

## 📁 Proje Yapısı

```
palma-mac/
├── kur.sh                      # Tek komutla kurulum
├── guncelle.sh                 # Otomatik güncelleme
├── palma.sh                    # Başlatıcı betik
├── drivers/
│   └── Akia_macos_arm_6_8_2.pkg  # AKIS PKCS#11 sürücüsü (ARM64)
├── resources/
│   └── palma.icns              # macOS uygulama ikonu
└── src/
    ├── __main__.py             # Ana giriş noktası
    ├── core/
    │   ├── pkcs11_wrapper.py   # PKCS#11 ctypes wrapper
    │   ├── card_manager.py     # Kart yönetimi ve X.509 parser
    │   └── pin_manager.py      # PIN doğrulama ve değiştirme
    ├── gui/
    │   └── app.py              # tkinter GUI (Tk 9.0)
    ├── server/
    │   ├── local_server.py     # HTTPS sunucu (localhost:8443)
    │   └── cert_generator.py   # SSL sertifika üretici
    └── services/
        ├── soap_client.py      # Jenerik SOAP 1.1 istemci
        ├── activation.py       # TÜRKTRUST aktivasyon servisi
        └── renewal.py          # TÜRKTRUST yenileme servisi
```

## 🔧 Teknik Detaylar

### PKCS#11 Wrapper
- `/usr/local/lib/libakisp11.dylib` → `ctypes` ile yükleme
- `C_GetFunctionList` → `c_void_p` function table (ARM64 alignment-safe)
- 64-bit `CK_ULONG` desteği

### Tarayıcı Sunucusu
- `https://localhost:8443` — HTTPS, CORS destekli
- Thread-safe smart kart erişimi (mutex)
- e-Devlet, UYAP, MERSİS vb. ile uyumlu

### Uyumluluk

| Bileşen | Sürüm |
|---------|-------|
| macOS | Sonoma 14+ / Sequoia 15+ (ARM64) |
| Python | 3.13+ (Homebrew) |
| Tk | 9.0+ |
| AKIS sürücü | v6.8.2+ (ARM64) |

## 🐛 Bilinen Sorunlar

1. **macOS sistem Python'u ile GUI çalışmaz** — Tk 8.5 sorunu. Homebrew Python 3.13 gereklidir.
2. **TÜRKTRUST aktivasyon servisi** — Sunucu tarafı bakımda olabilir. Aktif kartlar için bu özellik gerekmez.
3. **İlk başlatmada SSL uyarısı** — Kendinden imzalı sertifika nedeniyle tarayıcı uyarı verebilir.

## 📄 Lisans

Bu proje topluluk katkısıyla oluşturulmuştur. PALMA, TÜRKTRUST markasıdır.
Yalnızca eğitim ve kişisel kullanım amaçlıdır.
