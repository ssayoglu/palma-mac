"""
PALMA macOS — Kart yöneticisi.

PKCS#11 kütüphanesi üzerinden kart okuyucu, slot, sertifika işlemleri.
"""
import ssl
import re
import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from .pkcs11_wrapper import (
    PKCS11Module, PKCS11Error,
    CKA_CLASS, CKA_TOKEN, CKA_LABEL, CKA_VALUE, CKA_ID,
    CKA_CERTIFICATE_TYPE, CKA_SUBJECT, CKA_ISSUER, CKA_SERIAL_NUMBER,
    CKA_MODULUS, CKA_MODULUS_BITS, CKA_PUBLIC_EXPONENT, CKA_KEY_TYPE,
    CKO_CERTIFICATE, CKO_PUBLIC_KEY, CKO_PRIVATE_KEY,
    CKF_TOKEN_PRESENT, CKF_USER_PIN_LOCKED,
)

CKC_X_509 = 0x00000000  # CKC_X_509


@dataclass
class ReaderInfo:
    name: str
    slot_id: int


@dataclass
class SlotInfo:
    slot_id: int
    description: str
    token_present: bool
    hardware_version: str = ""
    firmware_version: str = ""


@dataclass
class TokenInfo:
    label: str
    manufacturer: str
    model: str
    serial_number: str
    max_pin_len: int = 0
    min_pin_len: int = 0
    total_memory: int = 0
    free_memory: int = 0


@dataclass
class CertificateInfo:
    cert_id: bytes
    label: str
    subject: str
    issuer: str
    serial_number: str
    not_before: Optional[datetime.datetime]
    not_after: Optional[datetime.datetime]
    is_expired: bool
    der_encoded: bytes = field(repr=False, default=b"")


class CardManager:
    """Akıllı kart işlemlerini yöneten sınıf."""

    def __init__(self, pkcs11_module: PKCS11Module):
        self.pkcs11 = pkcs11_module

    @contextmanager
    def _session(self, slot_id: int):
        session = self.pkcs11.open_session(slot_id)
        try:
            yield session
        finally:
            try:
                self.pkcs11.close_session(session)
            except Exception:
                pass

    def get_readers(self) -> List[ReaderInfo]:
        readers = []
        for sid in self.pkcs11.get_slot_list(token_present=False):
            info = self.pkcs11.get_slot_info(sid)
            readers.append(ReaderInfo(name=info["description"], slot_id=sid))
        return readers

    def get_slots(self, token_present: bool = True) -> List[SlotInfo]:
        result = []
        for sid in self.pkcs11.get_slot_list(token_present=token_present):
            info = self.pkcs11.get_slot_info(sid)
            result.append(SlotInfo(
                slot_id=sid,
                description=info["description"],
                token_present=info["token_present"],
            ))
        return result

    def get_token_info(self, slot_id: int) -> TokenInfo:
        d = self.pkcs11.get_token_info(slot_id)
        return TokenInfo(
            label=d["label"],
            manufacturer=d["manufacturer"],
            model=d["model"],
            serial_number=d["serial_number"],
            max_pin_len=d.get("max_pin_len", 0),
            min_pin_len=d.get("min_pin_len", 0),
        )

    def is_card_present(self, slot_id: int) -> bool:
        try:
            info = self.pkcs11.get_slot_info(slot_id)
            return info["token_present"]
        except Exception:
            return False

    # ---- Sertifika okuma ----

    def get_certificates(self, slot_id: int,
                         pin: Optional[str] = None) -> List[CertificateInfo]:
        certs = []
        with self._session(slot_id) as session:
            if pin:
                self.pkcs11.login(session, pin)
            try:
                objs = self.pkcs11.find_objects(session, [
                    (CKA_CLASS, CKO_CERTIFICATE),
                ])
                for obj in objs:
                    attrs = self.pkcs11.get_attribute_value(session, obj, [
                        CKA_ID, CKA_LABEL, CKA_VALUE, CKA_SUBJECT, CKA_ISSUER,
                    ])
                    der = attrs.get(CKA_VALUE) or b""
                    cert_id = attrs.get(CKA_ID) or b""
                    label_raw = attrs.get(CKA_LABEL)
                    label = label_raw.decode("utf-8", errors="replace") if label_raw else ""

                    parsed = _parse_x509_der(der) if der else {}

                    certs.append(CertificateInfo(
                        cert_id=cert_id,
                        label=label,
                        subject=parsed.get("subject", ""),
                        issuer=parsed.get("issuer", ""),
                        serial_number=parsed.get("serial", ""),
                        not_before=parsed.get("not_before"),
                        not_after=parsed.get("not_after"),
                        is_expired=parsed.get("is_expired", False),
                        der_encoded=der,
                    ))
            finally:
                if pin:
                    try:
                        self.pkcs11.logout(session)
                    except Exception:
                        pass
        return certs


# ---------- Basit X.509 DER ayrıştırıcı ----------

def _parse_x509_der(der: bytes) -> Dict[str, Any]:
    """DER-encoded X.509 sertifikasından temel bilgileri çıkar (standard lib)."""
    result: Dict[str, Any] = {}

    try:
        pem = ssl.DER_cert_to_PEM_cert(der)
        # Python 3.9 ssl modülü ile sertifika ayrıştırma sınırlı.
        # Temel bilgiler DER'den offset arayarak çıkarılabilir.

        # DER içindeki okunabilir stringleri çıkar
        text = der.decode("latin-1", errors="replace")

        # E-posta
        email_m = re.search(r'[\w.-]+@[\w.-]+\.\w{2,}', text)
        if email_m:
            result["email"] = email_m.group(0)

        # TC Kimlik No (11 haneli)
        tckn_m = re.search(r'\b([1-9]\d{10})\b', text)
        if tckn_m:
            result["tc_kimlik_no"] = tckn_m.group(1)

        # OID'ler sonrası common name vs. çıkarmak için basit heuristik
        # CN, O, OU gibi alanlar genellikle OID (0x55 0x04 0x03=CN, 0x04 0x0A=O) sonrası gelir
        def _extract_name_component(data: bytes, oid_suffix: int) -> Optional[str]:
            oid = bytes([0x55, 0x04, oid_suffix])
            idx = 0
            while True:
                pos = data.find(oid, idx)
                if pos == -1:
                    return None
                # OID'den sonra: tag (1 byte) + length (1 byte) + string
                str_start = pos + len(oid)
                if str_start + 2 >= len(data):
                    return None
                tag = data[str_start]
                slen = data[str_start + 1]
                if slen > 0 and str_start + 2 + slen <= len(data):
                    val = data[str_start + 2: str_start + 2 + slen]
                    try:
                        return val.decode('utf-8', errors='replace')
                    except Exception:
                        return val.decode('latin-1', errors='replace')
                idx = pos + 1

        # X.509 yapısında issuer ve subject tekrarlanır, ilk issuer sonra subject gelir
        # Basitleştirme: tüm CN'leri bul
        cns = []
        idx = 0
        oid_cn = bytes([0x55, 0x04, 0x03])
        while True:
            pos = der.find(oid_cn, idx)
            if pos == -1:
                break
            str_start = pos + 3
            if str_start + 2 < len(der):
                slen = der[str_start + 1]
                if 0 < slen < 128 and str_start + 2 + slen <= len(der):
                    val = der[str_start + 2: str_start + 2 + slen]
                    cns.append(val.decode('utf-8', errors='replace'))
            idx = pos + 1

        # Tipik olarak: issuer CN, sonra subject CN
        if len(cns) >= 2:
            result["issuer"] = cns[0]
            result["subject"] = cns[1]
        elif len(cns) == 1:
            result["subject"] = cns[0]
            result["issuer"] = cns[0]

        # Seri numarası: DER yapısı:
        # SEQUENCE(Certificate) > SEQUENCE(TBSCertificate) > [0]version(opsiyonel) > INTEGER(serialNumber)
        serial = _extract_serial_number(der)
        if serial:
            result["serial"] = serial

        # Geçerlilik tarihleri: UTCTime (0x17) veya GeneralizedTime (0x18)
        dates = []
        for tag in [0x17, 0x18]:
            idx = 0
            while True:
                pos = der.find(bytes([tag]), idx)
                if pos == -1:
                    break
                if pos + 2 < len(der):
                    dlen = der[pos + 1]
                    if 10 <= dlen <= 20 and pos + 2 + dlen <= len(der):
                        date_str = der[pos + 2: pos + 2 + dlen].decode('ascii', errors='replace')
                        dt = _parse_asn1_time(date_str, tag)
                        if dt:
                            dates.append(dt)
                idx = pos + 1
                if len(dates) >= 2:
                    break
            if len(dates) >= 2:
                break

        if len(dates) >= 2:
            result["not_before"] = dates[0]
            result["not_after"] = dates[1]
            result["is_expired"] = datetime.datetime.utcnow() > dates[1]
        elif len(dates) == 1:
            result["not_before"] = dates[0]

    except Exception:
        pass

    return result


def _parse_asn1_time(s: str, tag: int) -> Optional[datetime.datetime]:
    """UTCTime (0x17) veya GeneralizedTime (0x18) parse."""
    try:
        s = s.rstrip("Z").rstrip()
        if tag == 0x17:  # UTCTime: YYMMDDHHMMSSZ
            if len(s) >= 12:
                return datetime.datetime.strptime(s[:12], "%y%m%d%H%M%S")
            elif len(s) >= 10:
                return datetime.datetime.strptime(s[:10], "%y%m%d%H%M")
        elif tag == 0x18:  # GeneralizedTime: YYYYMMDDHHMMSSZ
            if len(s) >= 14:
                return datetime.datetime.strptime(s[:14], "%Y%m%d%H%M%S")
    except Exception:
        pass
    return None


def _read_der_length(der: bytes, offset: int):
    """DER length field'ını oku. (değer, yeni offset) döner."""
    if offset >= len(der):
        return 0, offset
    b = der[offset]
    if b < 0x80:
        return b, offset + 1
    n_bytes = b & 0x7f
    if n_bytes == 0 or offset + 1 + n_bytes > len(der):
        return 0, offset + 1
    length = int.from_bytes(der[offset + 1: offset + 1 + n_bytes], 'big')
    return length, offset + 1 + n_bytes


def _extract_serial_number(der: bytes) -> Optional[str]:
    """X.509 DER sertifikasından seri numarasını çıkar."""
    try:
        if len(der) < 10 or der[0] != 0x30:
            return None
        # Dış SEQUENCE (Certificate)
        _, pos = _read_der_length(der, 1)
        # İç SEQUENCE (TBSCertificate)
        if der[pos] != 0x30:
            return None
        _, pos = _read_der_length(der, pos + 1)
        # version [0] EXPLICIT opsiyonel
        if pos < len(der) and der[pos] == 0xa0:
            vlen, vpos = _read_der_length(der, pos + 1)
            pos = vpos + vlen
        # serialNumber INTEGER (tag=0x02)
        if pos < len(der) and der[pos] == 0x02:
            slen, spos = _read_der_length(der, pos + 1)
            serial_bytes = der[spos: spos + slen]
            # Hex string olarak döndür (başındaki 00 padding'i kaldır)
            serial_hex = serial_bytes.hex()
            if serial_hex.startswith("00") and len(serial_hex) > 2:
                serial_hex = serial_hex[2:]
            return serial_hex
    except Exception:
        pass
    return None

