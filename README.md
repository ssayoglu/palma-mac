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
| ✅ Sertifika aktivasyonu | ⚠️ TÜRKTRUST servisi gerekli |
| 📱 Telefon doğrulama | ⚠️ TÜRKTRUST servisi gerekli |

## 📋 Gereksinimler

- **macOS** (Apple Silicon / ARM64)
- **Python 3.13+** (Homebrew) — Tk 9.0 GUI desteği için
- **AKIS PKCS#11 sürücüsü** (`libakisp11.dylib`)
- **Akıllı kart okuyucu** (PCSC uyumlu, ör. ACS ACR39U)
- **TÜRKTRUST e-imza kartı**

## 🚀 Kurulum

### Hızlı Kurulum (Tek Komut)

```bash
curl -fsSL https://raw.githubusercontent.com/saidsurucu/palma-mac/main/kur.sh | bash
```

Bu komut otomatik olarak:
- ✅ Homebrew'u kurar (yoksa)
- ✅ Python 3.13 + tkinter'ı kurar
- ✅ Projeyi `~/palma-mac` dizinine indirir
- ✅ `palma` komutunu PATH'e ekler
- ✅ AKIS sürücüsünü kontrol eder
- ✅ Kart bağlantı testini çalıştırır

---

### Manuel Kurulum

macOS sistem Python'u (3.9) Tk 8.5 ile gelir ve GUI düzgün çalışmaz. Homebrew Python 3.13 gereklidir:

```bash
# Homebrew kurulu değilse
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.13 + tkinter
brew install python@3.13 python-tk@3.13
```

### 2. AKIS PKCS#11 Sürücüsü

TÜBİTAK BİLGEM AKIS sürücüsünü indirip kurun:

1. [TÜBİTAK AKIS sürücüsü indirme sayfası](https://eimza.bilgem.tubitak.gov.tr/akis-surucu) adresinden macOS sürücüsünü indirin
2. `.pkg` dosyasını çift tıklayarak kurun
3. Kurulum sonrası sürücü otomatik olarak `/usr/local/lib/libakisp11.dylib` konumuna yerleşir

Doğrulama:
```bash
file /usr/local/lib/libakisp11.dylib
# Beklenen çıktı: Mach-O universal binary with 2 architectures: [x86_64] [arm64]
```

### 3. PALMA macOS Kurulumu

```bash
# Depoyu klonlayın
git clone https://github.com/KULLANICI_ADI/palma-mac.git
cd palma-mac

# Çalıştırılabilir izni verin
chmod +x palma.sh
```

## 🎯 Kullanım

### GUI Modu (önerilen)

```bash
./palma.sh
```

veya doğrudan:

```bash
/opt/homebrew/bin/python3.13 src/__main__.py
```

### Tarayıcı Sunucusu (Headless)

E-imza işlemleri için tarayıcıyla entegre çalışan HTTPS sunucu:

```bash
./palma.sh --server
```

Sunucu `https://localhost:8443` adresinde çalışır.

### Kart Bağlantı Testi

```bash
./palma.sh --test
```

## 🌐 Tarayıcı Entegrasyonu (API)

Sunucu başlatıldığında (`--server` veya GUI içinden) aşağıdaki endpoint'ler kullanılabilir:

| Metod | Endpoint | Açıklama |
|-------|----------|----------|
| GET | `/status` | Sunucu durumu |
| GET | `/readers` | Bağlı okuyucu listesi |
| GET | `/token-info?slot=1` | Kart/token bilgileri |
| GET | `/certificates?slot=1&pin=XXXX` | Sertifika listesi |
| POST | `/verify-pin` | PIN doğrulama |
| POST | `/sign` | İmza işlemi |

### Örnek Kullanım

```bash
# Sunucu durumu
curl -sk https://localhost:8443/status
# {"running": true, "version": "2.9.0-mac"}

# Okuyucu listesi
curl -sk https://localhost:8443/readers
# [{"name": "ACS ACR39U ICC Reader", "slot_id": 1}]

# Token bilgisi
curl -sk "https://localhost:8443/token-info?slot=1"
# {"label": "AKIS_...", "manufacturer": "TUBITAK_UEKAE", ...}

# Sertifikalar (PIN gerekli)
curl -sk "https://localhost:8443/certificates?slot=1&pin=1234"

# PIN doğrulama
curl -sk -X POST -H "Content-Type: application/json" \
  -d '{"slot": 1, "pin": "1234"}' \
  https://localhost:8443/verify-pin
```

> **Not:** İlk çalıştırmada `~/.palma/` dizininde kendinden imzalı SSL sertifikası oluşturulur.
> Tarayıcınız güvenlik uyarısı verebilir — bu normaldir.

## 📁 Proje Yapısı

```
palma-mac/
├── palma.sh                    # Başlatıcı betik
├── README.md
├── src/
│   ├── __main__.py             # Ana giriş noktası
│   ├── core/
│   │   ├── pkcs11_wrapper.py   # PKCS#11 ctypes wrapper
│   │   ├── card_manager.py     # Kart yönetimi
│   │   └── pin_manager.py      # PIN yönetimi
│   ├── gui/
│   │   └── app.py              # tkinter GUI
│   ├── server/
│   │   ├── local_server.py     # HTTPS sunucu (localhost:8443)
│   │   └── cert_generator.py   # SSL sertifika üretici
│   └── services/
│       ├── soap_client.py      # SOAP istemci
│       ├── activation.py       # TÜRKTRUST aktivasyon servisi
│       └── renewal.py          # TÜRKTRUST yenileme servisi
```

## 🔧 Teknik Detaylar

### PKCS#11 Wrapper

- `/usr/local/lib/libakisp11.dylib` sürücüsünü `ctypes` ile yükler
- `C_GetFunctionList` üzerinden tüm PKCS#11 fonksiyonlarına erişir
- ARM64'te struct alignment sorunlarını önlemek için `c_void_p` function table kullanır
- 64-bit `CK_ULONG` desteği

### Tarayıcı Sunucusu

- `https://localhost:8443` üzerinde HTTPS
- CORS başlıkları ile cross-origin desteği
- Thread-safe smart kart erişimi (mutex ile)
- Kendinden imzalı sertifika (`~/.palma/server.pem`)

### Uyumluluk

| Bileşen | Sürüm |
|---------|-------|
| macOS | Sonoma 14+ / Sequoia 15+ (ARM64) |
| Python | 3.13+ (Homebrew) |
| Tk | 9.0+ |
| AKIS sürücü | Universal binary (ARM64 + x86_64) |

## 🐛 Bilinen Sorunlar

1. **macOS sistem Python'u (3.9) ile GUI çalışmaz** — Tk 8.5 widget render sorunları var. Homebrew Python 3.13 kullanın.
2. **TÜRKTRUST aktivasyon servisi** — `as.turktrust.com.tr` SOAP servisi şu anda erişilebilir durumda olmayabilir. Aktif kartlar için bu özellik gerekli değildir.
3. **İlk başlatmada SSL uyarısı** — Kendinden imzalı sertifika kullanıldığı için tarayıcı uyarı verebilir.

## 📄 Lisans

Bu proje topluluk katkısıyla oluşturulmuştur. PALMA, TÜRKTRUST markasıdır.
Yalnızca eğitim ve kişisel kullanım amaçlıdır.
