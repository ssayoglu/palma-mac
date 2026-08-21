from dataclasses import dataclass
from typing import Optional
from .soap_client import SOAPClient, SOAPError

@dataclass
class PukSeedResult:
    basarili: bool
    mesaj: str
    puk_seed: Optional[str] = None

@dataclass
class AktivasyonResult:
    basarili: bool
    mesaj: str

@dataclass
class SMSResult:
    basarili: bool
    mesaj: str

@dataclass
class VersiyonInfo:
    basarili: bool
    mesaj: str
    versiyon: Optional[str] = None

class ActivationService:
    """TÜRKTRUST Sertifika Aktivasyon Servisi İstemcisi."""
    
    def __init__(self, endpoint_url: str = 'https://as.turktrust.com.tr/SertifikaAktivasyon/', timeout: int = 30):
        self.client = SOAPClient(
            endpoint_url=endpoint_url, 
            namespace='http://as.turktrust.com.tr/SertifikaAktivasyon/', 
            timeout=timeout
        )

    def puk_seed_al(self, sertifika_seri_no: str) -> PukSeedResult:
        """Aktivasyon işlemi için PUK seed değerini alır."""
        try:
            res = self.client.call('pukSeedAl', {'sertifikaSeriNo': sertifika_seri_no})
            return PukSeedResult(
                basarili=True, 
                mesaj="İşlem başarılı", 
                puk_seed=res.get('pukSeedAlResult') or res.get('return')
            )
        except SOAPError as e:
            return PukSeedResult(basarili=False, mesaj=str(e))

    def sertifika_aktivasyon_bildir(self, sertifika_seri_no: str, aktivasyon_kodu: str) -> AktivasyonResult:
        """Sertifikanın aktivasyon kodu ile aktif edildiğini bildirir."""
        try:
            res = self.client.call('sertifikaAktivasyonBildir', {
                'sertifikaSeriNo': sertifika_seri_no, 
                'aktivasyonKodu': aktivasyon_kodu
            })
            mesaj = str(res.get('sertifikaAktivasyonBildirResult') or res.get('return', 'Başarılı'))
            return AktivasyonResult(basarili=True, mesaj=mesaj)
        except SOAPError as e:
            return AktivasyonResult(basarili=False, mesaj=str(e))

    def sertifika_aktivasyon_bildir_puk(self, sertifika_seri_no: str, puk: str) -> AktivasyonResult:
        """Sertifikanın PUK ile aktif edildiğini bildirir."""
        try:
            res = self.client.call('sertifikaAktivasyonBildirPUK', {
                'sertifikaSeriNo': sertifika_seri_no, 
                'puk': puk
            })
            mesaj = str(res.get('sertifikaAktivasyonBildirPUKResult') or res.get('return', 'Başarılı'))
            return AktivasyonResult(basarili=True, mesaj=mesaj)
        except SOAPError as e:
            return AktivasyonResult(basarili=False, mesaj=str(e))

    def sertifika_aktivasyon_sms_gonder(self, sertifika_seri_no: str, telefon_no: str) -> SMSResult:
        """Aktivasyon için SMS doğrulaması gönderir."""
        try:
            res = self.client.call('sertifikaAktivasyonSMSGonder', {
                'sertifikaSeriNo': sertifika_seri_no, 
                'telefonNo': telefon_no
            })
            mesaj = str(res.get('sertifikaAktivasyonSMSGonderResult') or res.get('return', 'Başarılı'))
            return SMSResult(basarili=True, mesaj=mesaj)
        except SOAPError as e:
            return SMSResult(basarili=False, mesaj=str(e))

    def guncel_versiyon_al(self) -> VersiyonInfo:
        """En güncel PALMA uygulamasının versiyon bilgisini alır."""
        try:
            res = self.client.call('guncelPalmaVersiyonuAl', {})
            return VersiyonInfo(
                basarili=True, 
                mesaj="İşlem başarılı", 
                versiyon=res.get('guncelPalmaVersiyonuAlResult') or res.get('return')
            )
        except SOAPError as e:
            return VersiyonInfo(basarili=False, mesaj=str(e))
