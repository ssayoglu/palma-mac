import base64
from dataclasses import dataclass
from typing import Optional
from .soap_client import SOAPClient, SOAPError

@dataclass
class YenilemeKontrolResult:
    basarili: bool
    mesaj: str
    yenilenebilir: bool = False

@dataclass
class OnayKontrolResult:
    basarili: bool
    mesaj: str

@dataclass
class YenilemeResult:
    basarili: bool
    mesaj: str

class RenewalService:
    """TÜRKTRUST Online Yenileme Servisi İstemcisi."""
    
    def __init__(self, endpoint_url: str = 'http://ws.platan.turktrust.com/PalmaWSPlatan/', timeout: int = 30):
        self.client = SOAPClient(
            endpoint_url=endpoint_url, 
            namespace='http://ws.platan.turktrust.com/PalmaWSPlatan/', 
            timeout=timeout
        )

    def is_yenilenebilir(self, sertifika_seri_no: str) -> YenilemeKontrolResult:
        """Sertifikanın yenilenebilir olup olmadığını kontrol eder."""
        try:
            res = self.client.call('isYenilenebilir', {'sertifikaSeriNo': sertifika_seri_no})
            val = str(res.get('isYenilenebilirResult') or res.get('return', 'false')).strip().lower()
            return YenilemeKontrolResult(
                basarili=True, 
                mesaj="Sorgu başarılı", 
                yenilenebilir=(val == 'true' or val == '1')
            )
        except SOAPError as e:
            return YenilemeKontrolResult(basarili=False, mesaj=str(e))

    def onay_kodu_kontrol(self, sertifika_seri_no: str, onay_kodu: str) -> OnayKontrolResult:
        """Yenileme onayı için gönderilen kodu kontrol eder."""
        try:
            res = self.client.call('onayKoduKontrol', {
                'sertifikaSeriNo': sertifika_seri_no, 
                'onayKodu': onay_kodu
            })
            mesaj = str(res.get('onayKoduKontrolResult') or res.get('return', 'Başarılı'))
            return OnayKontrolResult(basarili=True, mesaj=mesaj)
        except SOAPError as e:
            return OnayKontrolResult(basarili=False, mesaj=str(e))

    def sertifika_yenile(self, sertifika_seri_no: str, csr: bytes) -> YenilemeResult:
        """Sertifika yenileme işlemini başlatır."""
        try:
            csr_b64 = base64.b64encode(csr).decode('utf-8')
            res = self.client.call('sertifikaYenile', {
                'sertifikaSeriNo': sertifika_seri_no, 
                'csr': csr_b64
            })
            mesaj = str(res.get('sertifikaYenileResult') or res.get('return', 'Başarılı'))
            return YenilemeResult(basarili=True, mesaj=mesaj)
        except SOAPError as e:
            return YenilemeResult(basarili=False, mesaj=str(e))

    def yenilenmis_sertifika_getir(self, sertifika_seri_no: str) -> Optional[bytes]:
        """Yenilenmiş sertifikayı çeker."""
        try:
            res = self.client.call('yenilenmisSertifikaGetir', {'sertifikaSeriNo': sertifika_seri_no})
            cert_b64 = res.get('yenilenmisSertifikaGetirResult') or res.get('return')
            if cert_b64:
                return base64.b64decode(cert_b64)
            return None
        except SOAPError:
            return None

    def adres_getir(self) -> Optional[str]:
        """Adres bilgisini alır."""
        try:
            res = self.client.call('adresGetir', {})
            return res.get('adresGetirResult') or res.get('return')
        except SOAPError:
            return None
