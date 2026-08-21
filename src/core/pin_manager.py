from dataclasses import dataclass
from typing import Optional
from contextlib import contextmanager

from .pkcs11_wrapper import PKCS11Module

@dataclass
class PINVerifyResult:
    success: bool
    remaining_attempts: Optional[int] = None
    error_message: Optional[str] = None

@dataclass
class PINChangeResult:
    success: bool
    error_message: Optional[str] = None

@dataclass
class PINInfo:
    min_length: int
    max_length: int
    remaining_attempts: Optional[int]
    is_locked: bool

class PINManager:
    """PIN yönetimi işlemlerini gerçekleştiren sınıf."""

    def __init__(self, pkcs11_module: PKCS11Module):
        self.pkcs11 = pkcs11_module

    @contextmanager
    def _session(self, slot_id: int):
        """Güvenli oturum yönetimi (Context Manager)"""
        session_handle = None
        try:
            session_handle = self.pkcs11.open_session(slot_id)
            yield session_handle
        finally:
            if session_handle is not None:
                try:
                    self.pkcs11.close_session(session_handle)
                except Exception:
                    pass

    def _parse_error(self, e: Exception) -> str:
        """PKCS#11 hatalarını kullanıcı dostu mesajlara çevirir."""
        error_msg = str(e)
        if 'CKR_PIN_INCORRECT' in error_msg:
            return 'PIN hatalı'
        elif 'CKR_PIN_LOCKED' in error_msg:
            return 'PIN kilitlendi'
        elif 'CKR_PIN_EXPIRED' in error_msg:
            return 'PIN süresi doldu'
        elif 'CKR_PIN_LEN_RANGE' in error_msg:
            return 'PIN uzunluğu geçersiz'
        elif 'CKR_TOKEN_NOT_PRESENT' in error_msg:
            return 'Kart takılı değil'
        return f"Bilinmeyen hata: {error_msg}"

    def verify_pin(self, slot_id: int, pin: str) -> PINVerifyResult:
        """Kullanıcı PIN kodunu doğrular."""
        try:
            with self._session(slot_id) as session:
                self.pkcs11.login(session, pin)
                self.pkcs11.logout(session)
                return PINVerifyResult(success=True)
        except Exception as e:
            err_msg = self._parse_error(e)
            
            # Kalan deneme sayısını almak için token bilgisini okuyabiliriz
            remaining = None
            try:
                # Bazı tokenlar CKA_ veya token_info içinde kalan hakkı dönebilir, 
                # Standart PKCS11'de kalan deneme hakkı spesifik extensionlar olmadan zor alınır, 
                # fakat eğer firmware destekliyorsa token info'da olabilir. (Varsayılan Null)
                pass
            except Exception:
                pass
                
            return PINVerifyResult(
                success=False,
                remaining_attempts=remaining,
                error_message=err_msg
            )

    def change_pin(self, slot_id: int, old_pin: str, new_pin: str) -> PINChangeResult:
        """Kartın PIN kodunu değiştirir."""
        try:
            with self._session(slot_id) as session:
                self.pkcs11.login(session, old_pin)
                try:
                    self.pkcs11.set_pin(session, old_pin, new_pin)
                finally:
                    try:
                        self.pkcs11.logout(session)
                    except Exception:
                        pass
                return PINChangeResult(success=True)
        except Exception as e:
            return PINChangeResult(
                success=False,
                error_message=self._parse_error(e)
            )

    def get_pin_info(self, slot_id: int) -> PINInfo:
        """PIN kuralları ve durumunu getirir."""
        try:
            info = self.pkcs11.get_token_info(slot_id)

            is_locked = info.get("user_pin_locked", False)

            return PINInfo(
                min_length=info.get("min_pin_len", 4),
                max_length=info.get("max_pin_len", 8),
                remaining_attempts=None,  # Standart P11'de doğrudan bulunmaz
                is_locked=is_locked,
            )
        except Exception as e:
            return PINInfo(min_length=0, max_length=0, remaining_attempts=None, is_locked=False)

    def is_pin_locked(self, slot_id: int) -> bool:
        """PIN kodunun kilitli olup olmadığını kontrol eder."""
        info = self.get_pin_info(slot_id)
        return info.is_locked

