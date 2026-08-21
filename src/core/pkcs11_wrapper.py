"""
PKCS#11 ctypes wrapper — PALMA macOS portu.

libakisp11.dylib üzerinden PKCS#11 (Cryptoki) erişimi sağlar.
C_GetFunctionList ile fonksiyon pointer tablosu alınır,
her çağrı offset üzerinden güvenle yapılır.
"""
import ctypes
import ctypes.util
import os
import sys
from typing import List, Dict, Optional

# ---------- Temel Tipler ----------
CK_BYTE = ctypes.c_ubyte
CK_ULONG = ctypes.c_ulong
CK_BBOOL = CK_BYTE
CK_FLAGS = CK_ULONG
CK_RV = CK_ULONG
CK_SLOT_ID = CK_ULONG
CK_SESSION_HANDLE = CK_ULONG
CK_OBJECT_HANDLE = CK_ULONG
CK_OBJECT_CLASS = CK_ULONG
CK_ATTRIBUTE_TYPE = CK_ULONG
CK_MECHANISM_TYPE = CK_ULONG
CK_USER_TYPE = CK_ULONG
CK_VOID_PTR = ctypes.c_void_p
CK_NOTIFY = ctypes.c_void_p  # callback, kullanılmıyor

CK_TRUE = CK_BBOOL(1)
CK_FALSE = CK_BBOOL(0)

# ---------- Return Codes ----------
CKR_OK                          = 0x00000000
CKR_CANCEL                      = 0x00000001
CKR_HOST_MEMORY                 = 0x00000002
CKR_SLOT_ID_INVALID             = 0x00000003
CKR_GENERAL_ERROR               = 0x00000005
CKR_FUNCTION_FAILED             = 0x00000006
CKR_ARGUMENTS_BAD               = 0x00000007
CKR_ATTRIBUTE_SENSITIVE         = 0x00000011
CKR_ATTRIBUTE_TYPE_INVALID      = 0x00000012
CKR_ATTRIBUTE_VALUE_INVALID     = 0x00000013
CKR_DATA_INVALID                = 0x00000020
CKR_DATA_LEN_RANGE              = 0x00000021
CKR_DEVICE_ERROR                = 0x00000030
CKR_DEVICE_MEMORY               = 0x00000031
CKR_DEVICE_REMOVED              = 0x00000032
CKR_FUNCTION_NOT_SUPPORTED      = 0x00000054
CKR_KEY_HANDLE_INVALID          = 0x00000060
CKR_MECHANISM_INVALID           = 0x00000070
CKR_MECHANISM_PARAM_INVALID     = 0x00000071
CKR_OBJECT_HANDLE_INVALID       = 0x00000082
CKR_OPERATION_ACTIVE            = 0x00000090
CKR_OPERATION_NOT_INITIALIZED   = 0x00000091
CKR_PIN_INCORRECT               = 0x000000A0
CKR_PIN_INVALID                 = 0x000000A1
CKR_PIN_LEN_RANGE               = 0x000000A2
CKR_PIN_EXPIRED                 = 0x000000A3
CKR_PIN_LOCKED                  = 0x000000A4
CKR_SESSION_CLOSED              = 0x000000B0
CKR_SESSION_HANDLE_INVALID      = 0x000000B3
CKR_SESSION_READ_ONLY           = 0x000000B5
CKR_SIGNATURE_INVALID           = 0x000000C0
CKR_SIGNATURE_LEN_RANGE         = 0x000000C1
CKR_TOKEN_NOT_PRESENT           = 0x000000E0
CKR_TOKEN_NOT_RECOGNIZED        = 0x000000E1
CKR_USER_ALREADY_LOGGED_IN      = 0x00000100
CKR_USER_NOT_LOGGED_IN          = 0x00000101
CKR_USER_PIN_NOT_INITIALIZED    = 0x00000102
CKR_BUFFER_TOO_SMALL            = 0x00000150
CKR_CRYPTOKI_NOT_INITIALIZED    = 0x00000190
CKR_CRYPTOKI_ALREADY_INITIALIZED = 0x00000191

# ---------- Object Classes ----------
CKO_DATA        = 0x00000000
CKO_CERTIFICATE = 0x00000001
CKO_PUBLIC_KEY  = 0x00000002
CKO_PRIVATE_KEY = 0x00000003
CKO_SECRET_KEY  = 0x00000004

# ---------- Attribute Types ----------
CKA_CLASS               = 0x00000000
CKA_TOKEN               = 0x00000001
CKA_PRIVATE             = 0x00000002
CKA_LABEL               = 0x00000003
CKA_VALUE               = 0x00000011
CKA_CERTIFICATE_TYPE    = 0x00000080
CKA_ISSUER              = 0x00000081
CKA_SERIAL_NUMBER       = 0x00000082
CKA_SUBJECT             = 0x00000101
CKA_ID                  = 0x00000102
CKA_MODULUS             = 0x00000120
CKA_MODULUS_BITS        = 0x00000121
CKA_PUBLIC_EXPONENT     = 0x00000122
CKA_KEY_TYPE            = 0x00000100

# ---------- Mechanism Types ----------
CKM_RSA_PKCS            = 0x00000001
CKM_RSA_PKCS_OAEP       = 0x00000009
CKM_SHA1_RSA_PKCS       = 0x00000006
CKM_SHA256_RSA_PKCS     = 0x00000040
CKM_SHA384_RSA_PKCS     = 0x00000041
CKM_SHA512_RSA_PKCS     = 0x00000042

# ---------- User Types ----------
CKU_SO   = 0
CKU_USER = 1

# ---------- Flags ----------
CKF_TOKEN_PRESENT    = 0x00000001
CKF_RW_SESSION       = 0x00000002
CKF_SERIAL_SESSION   = 0x00000004
CKF_LOGIN_REQUIRED   = 0x00000004  # token info flag
CKF_USER_PIN_LOCKED  = 0x00040000
CKF_USER_PIN_TO_BE_CHANGED = 0x00080000

# ---------- Structures (platform-native alignment — _pack_ YOKTUR) ----------

class CK_VERSION(ctypes.Structure):
    _fields_ = [("major", CK_BYTE), ("minor", CK_BYTE)]

class CK_SLOT_INFO(ctypes.Structure):
    _fields_ = [
        ("slotDescription", CK_BYTE * 64),
        ("manufacturerID", CK_BYTE * 32),
        ("flags", CK_FLAGS),
        ("hardwareVersion", CK_VERSION),
        ("firmwareVersion", CK_VERSION),
    ]

class CK_TOKEN_INFO(ctypes.Structure):
    _fields_ = [
        ("label", CK_BYTE * 32),
        ("manufacturerID", CK_BYTE * 32),
        ("model", CK_BYTE * 16),
        ("serialNumber", CK_BYTE * 16),
        ("flags", CK_FLAGS),
        ("ulMaxSessionCount", CK_ULONG),
        ("ulSessionCount", CK_ULONG),
        ("ulMaxRwSessionCount", CK_ULONG),
        ("ulRwSessionCount", CK_ULONG),
        ("ulMaxPinLen", CK_ULONG),
        ("ulMinPinLen", CK_ULONG),
        ("ulTotalPublicMemory", CK_ULONG),
        ("ulFreePublicMemory", CK_ULONG),
        ("ulTotalPrivateMemory", CK_ULONG),
        ("ulFreePrivateMemory", CK_ULONG),
        ("hardwareVersion", CK_VERSION),
        ("firmwareVersion", CK_VERSION),
        ("utcTime", CK_BYTE * 16),
    ]

class CK_ATTRIBUTE(ctypes.Structure):
    _fields_ = [
        ("type", CK_ATTRIBUTE_TYPE),
        ("pValue", CK_VOID_PTR),
        ("ulValueLen", CK_ULONG),
    ]

class CK_MECHANISM(ctypes.Structure):
    _fields_ = [
        ("mechanism", CK_MECHANISM_TYPE),
        ("pParameter", CK_VOID_PTR),
        ("ulParameterLen", CK_ULONG),
    ]

# CK_FUNCTION_LIST: version (2 bytes) + padding + N function pointers.
# Offset'ler platform hizalamasına bağlıdır.
# Güvenli yol: struct tanımlamak yerine, pointer aritmetiğiyle okumak.
# Ama daha basit yol: function pointer'ları tümüyle c_void_p olarak tanımlamak,
# sonra CFUNCTYPE ile cast etmek.

# PKCS#11 v2.20 function list sırası (68 fonksiyon):
_FUNC_NAMES = [
    "C_Initialize", "C_Finalize", "C_GetInfo", "C_GetFunctionList",
    "C_GetSlotList", "C_GetSlotInfo", "C_GetTokenInfo",
    "C_GetMechanismList", "C_GetMechanismInfo",
    "C_InitToken", "C_InitPIN", "C_SetPIN",
    "C_OpenSession", "C_CloseSession", "C_CloseAllSessions",
    "C_GetSessionInfo", "C_GetOperationState", "C_SetOperationState",
    "C_Login", "C_Logout",
    "C_CreateObject", "C_CopyObject", "C_DestroyObject",
    "C_GetObjectSize", "C_GetAttributeValue", "C_SetAttributeValue",
    "C_FindObjectsInit", "C_FindObjects", "C_FindObjectsFinal",
    "C_EncryptInit", "C_Encrypt", "C_EncryptUpdate", "C_EncryptFinal",
    "C_DecryptInit", "C_Decrypt", "C_DecryptUpdate", "C_DecryptFinal",
    "C_DigestInit", "C_Digest", "C_DigestUpdate", "C_DigestKey", "C_DigestFinal",
    "C_SignInit", "C_Sign", "C_SignUpdate", "C_SignFinal",
    "C_SignRecoverInit", "C_SignRecover",
    "C_VerifyInit", "C_Verify", "C_VerifyUpdate", "C_VerifyFinal",
    "C_VerifyRecoverInit", "C_VerifyRecover",
    "C_DigestEncryptUpdate", "C_DecryptDigestUpdate",
    "C_SignEncryptUpdate", "C_DecryptVerifyUpdate",
    "C_GenerateKey", "C_GenerateKeyPair",
    "C_WrapKey", "C_UnwrapKey", "C_DeriveKey",
    "C_SeedRandom", "C_GenerateRandom",
    "C_GetFunctionStatus", "C_CancelFunction", "C_WaitForSlotEvent",
]

class _FuncList(ctypes.Structure):
    """CK_FUNCTION_LIST: CK_VERSION + 68 function pointers (hepsi c_void_p)."""
    _fields_ = [("version", CK_VERSION)] + \
               [(name, ctypes.c_void_p) for name in _FUNC_NAMES]


# ---------- Hata sınıfı ----------

class PKCS11Error(Exception):
    _MSGS = {
        CKR_CANCEL: "İşlem iptal edildi",
        CKR_HOST_MEMORY: "Bellek yetersiz",
        CKR_SLOT_ID_INVALID: "Geçersiz slot",
        CKR_GENERAL_ERROR: "Genel hata",
        CKR_FUNCTION_FAILED: "İşlev başarısız",
        CKR_ARGUMENTS_BAD: "Geçersiz argüman",
        CKR_DEVICE_ERROR: "Cihaz hatası",
        CKR_DEVICE_REMOVED: "Kart çıkarıldı",
        CKR_PIN_INCORRECT: "PIN hatalı",
        CKR_PIN_INVALID: "Geçersiz PIN",
        CKR_PIN_LEN_RANGE: "PIN uzunluğu geçersiz",
        CKR_PIN_EXPIRED: "PIN süresi doldu",
        CKR_PIN_LOCKED: "PIN kilitli",
        CKR_TOKEN_NOT_PRESENT: "Kart takılı değil",
        CKR_TOKEN_NOT_RECOGNIZED: "Kart tanınmadı",
        CKR_USER_ALREADY_LOGGED_IN: "Zaten giriş yapılmış",
        CKR_USER_NOT_LOGGED_IN: "Giriş yapılmamış",
        CKR_USER_PIN_NOT_INITIALIZED: "PIN tanımlanmamış",
        CKR_CRYPTOKI_NOT_INITIALIZED: "Kütüphane başlatılmamış",
        CKR_CRYPTOKI_ALREADY_INITIALIZED: "Kütüphane zaten başlatılmış",
        CKR_BUFFER_TOO_SMALL: "Tampon çok küçük",
        CKR_SESSION_HANDLE_INVALID: "Geçersiz oturum",
        CKR_SIGNATURE_INVALID: "Geçersiz imza",
    }

    def __init__(self, rv: int):
        self.rv = rv
        msg = self._MSGS.get(rv, f"PKCS#11 hata kodu: 0x{rv:08X}")
        super().__init__(msg)


# ---------- Yardımcılar ----------

def _cfunc(ptr, restype, *argtypes):
    """c_void_p → çağrılabilir CFUNCTYPE."""
    if not ptr:
        return None
    ft = ctypes.CFUNCTYPE(restype, *argtypes)
    return ft(ptr)

def _bytes_from_arr(arr) -> str:
    """CK_BYTE dizisini sondaki boşlukları temizleyerek str'ye çevir."""
    return bytes(arr).rstrip(b'\x00').rstrip().decode('utf-8', errors='replace')


# ---------- PKCS11Module ----------

class PKCS11Module:
    """
    PKCS#11 kütüphanesi sarmalayıcı.

    Kullanım:
        mod = PKCS11Module()       # libakisp11.dylib yükle
        mod.initialize()
        slots = mod.get_slot_list()
        ...
        mod.finalize()
    """

    # Kütüphane arama yolları
    _LIB_PATHS = [
        "/usr/local/lib/libakisp11.dylib",
        "/Library/Java/Extensions/libakisp11.dylib",
        "/opt/homebrew/lib/libakisp11.dylib",
        "/usr/lib/libakisp11.dylib",
    ]

    def __init__(self, library_path: Optional[str] = None):
        self._lib = None
        self._fl: Optional[_FuncList] = None
        self._initialized = False

        paths = [library_path] if library_path else []
        paths.extend(self._LIB_PATHS)

        for p in paths:
            if p and os.path.isfile(p):
                try:
                    self._lib = ctypes.cdll.LoadLibrary(p)
                    break
                except OSError:
                    continue

        if not self._lib:
            raise FileNotFoundError(
                "libakisp11.dylib bulunamadı. "
                "AKİS kart sürücüsünün kurulu olduğundan emin olun."
            )

        # C_GetFunctionList çağrısı
        proto = ctypes.CFUNCTYPE(CK_RV, ctypes.POINTER(ctypes.POINTER(_FuncList)))
        c_get_fl = proto(("C_GetFunctionList", self._lib))

        fl_ptr = ctypes.POINTER(_FuncList)()
        rv = c_get_fl(ctypes.byref(fl_ptr))
        if rv != CKR_OK:
            raise PKCS11Error(rv)
        self._fl = fl_ptr.contents

    # ---- iç yardımcılar ----

    def _ck(self, rv: int):
        if rv != CKR_OK:
            raise PKCS11Error(rv)

    def _call(self, name: str, restype, argtypes, *args):
        """Function list'ten fonksiyon çağır."""
        ptr = getattr(self._fl, name)
        fn = _cfunc(ptr, restype, *argtypes)
        if fn is None:
            raise PKCS11Error(CKR_FUNCTION_FAILED)
        return fn(*args)

    # ---- Genel ----

    def initialize(self):
        rv = self._call("C_Initialize", CK_RV, [CK_VOID_PTR], None)
        if rv not in (CKR_OK, CKR_CRYPTOKI_ALREADY_INITIALIZED):
            self._ck(rv)
        self._initialized = True

    def finalize(self):
        if self._initialized:
            rv = self._call("C_Finalize", CK_RV, [CK_VOID_PTR], None)
            self._ck(rv)
            self._initialized = False

    # ---- Slot / Token ----

    def get_slot_list(self, token_present: bool = True) -> List[int]:
        present = CK_BBOOL(1 if token_present else 0)
        count = CK_ULONG(0)

        rv = self._call("C_GetSlotList", CK_RV,
                         [CK_BBOOL, ctypes.POINTER(CK_SLOT_ID), ctypes.POINTER(CK_ULONG)],
                         present, None, ctypes.byref(count))
        self._ck(rv)

        if count.value == 0:
            return []

        buf = (CK_SLOT_ID * count.value)()
        rv = self._call("C_GetSlotList", CK_RV,
                         [CK_BBOOL, ctypes.POINTER(CK_SLOT_ID), ctypes.POINTER(CK_ULONG)],
                         present, buf, ctypes.byref(count))
        self._ck(rv)
        return list(buf[:count.value])

    def get_slot_info(self, slot_id: int) -> dict:
        info = CK_SLOT_INFO()
        rv = self._call("C_GetSlotInfo", CK_RV,
                         [CK_SLOT_ID, ctypes.POINTER(CK_SLOT_INFO)],
                         CK_SLOT_ID(slot_id), ctypes.byref(info))
        self._ck(rv)
        return {
            "description": _bytes_from_arr(info.slotDescription),
            "manufacturer": _bytes_from_arr(info.manufacturerID),
            "flags": info.flags,
            "token_present": bool(info.flags & CKF_TOKEN_PRESENT),
        }

    def get_token_info(self, slot_id: int) -> dict:
        info = CK_TOKEN_INFO()
        rv = self._call("C_GetTokenInfo", CK_RV,
                         [CK_SLOT_ID, ctypes.POINTER(CK_TOKEN_INFO)],
                         CK_SLOT_ID(slot_id), ctypes.byref(info))
        self._ck(rv)
        return {
            "label": _bytes_from_arr(info.label),
            "manufacturer": _bytes_from_arr(info.manufacturerID),
            "model": _bytes_from_arr(info.model),
            "serial_number": _bytes_from_arr(info.serialNumber),
            "flags": info.flags,
            "max_pin_len": info.ulMaxPinLen,
            "min_pin_len": info.ulMinPinLen,
            "login_required": bool(info.flags & CKF_LOGIN_REQUIRED),
            "user_pin_locked": bool(info.flags & CKF_USER_PIN_LOCKED),
        }

    # ---- Session ----

    def open_session(self, slot_id: int,
                     flags: int = CKF_SERIAL_SESSION | CKF_RW_SESSION) -> int:
        handle = CK_SESSION_HANDLE(0)
        rv = self._call("C_OpenSession", CK_RV,
                         [CK_SLOT_ID, CK_FLAGS, CK_VOID_PTR, CK_VOID_PTR,
                          ctypes.POINTER(CK_SESSION_HANDLE)],
                         CK_SLOT_ID(slot_id), CK_FLAGS(flags),
                         None, None, ctypes.byref(handle))
        self._ck(rv)
        return handle.value

    def close_session(self, session: int):
        rv = self._call("C_CloseSession", CK_RV,
                         [CK_SESSION_HANDLE],
                         CK_SESSION_HANDLE(session))
        self._ck(rv)

    def login(self, session: int, pin: str, user_type: int = CKU_USER):
        pin_bytes = pin.encode('utf-8')
        pin_buf = ctypes.create_string_buffer(pin_bytes)
        rv = self._call("C_Login", CK_RV,
                         [CK_SESSION_HANDLE, CK_USER_TYPE,
                          ctypes.POINTER(CK_BYTE), CK_ULONG],
                         CK_SESSION_HANDLE(session), CK_USER_TYPE(user_type),
                         ctypes.cast(pin_buf, ctypes.POINTER(CK_BYTE)),
                         CK_ULONG(len(pin_bytes)))
        self._ck(rv)

    def logout(self, session: int):
        rv = self._call("C_Logout", CK_RV,
                         [CK_SESSION_HANDLE],
                         CK_SESSION_HANDLE(session))
        self._ck(rv)

    def set_pin(self, session: int, old_pin: str, new_pin: str):
        old_b = old_pin.encode('utf-8')
        new_b = new_pin.encode('utf-8')
        old_buf = ctypes.create_string_buffer(old_b)
        new_buf = ctypes.create_string_buffer(new_b)
        rv = self._call("C_SetPIN", CK_RV,
                         [CK_SESSION_HANDLE,
                          ctypes.POINTER(CK_BYTE), CK_ULONG,
                          ctypes.POINTER(CK_BYTE), CK_ULONG],
                         CK_SESSION_HANDLE(session),
                         ctypes.cast(old_buf, ctypes.POINTER(CK_BYTE)),
                         CK_ULONG(len(old_b)),
                         ctypes.cast(new_buf, ctypes.POINTER(CK_BYTE)),
                         CK_ULONG(len(new_b)))
        self._ck(rv)

    # ---- Object search ----

    def find_objects(self, session: int,
                     template: List[tuple]) -> List[int]:
        """
        template: [(CKA_xxx, value), ...] — value bytes veya int.
        """
        n = len(template)
        attrs = (CK_ATTRIBUTE * n)()
        # ctypes nesnelerin referanslarını tutmak için
        _refs = []

        for i, (attr_type, val) in enumerate(template):
            attrs[i].type = CK_ATTRIBUTE_TYPE(attr_type)
            if isinstance(val, int):
                v = CK_ULONG(val)
                _refs.append(v)
                attrs[i].pValue = ctypes.cast(ctypes.pointer(v), CK_VOID_PTR)
                attrs[i].ulValueLen = CK_ULONG(ctypes.sizeof(CK_ULONG))
            elif isinstance(val, (bytes, bytearray)):
                buf = ctypes.create_string_buffer(val)
                _refs.append(buf)
                attrs[i].pValue = ctypes.cast(buf, CK_VOID_PTR)
                attrs[i].ulValueLen = CK_ULONG(len(val))
            elif isinstance(val, bool):
                v = CK_BBOOL(1 if val else 0)
                _refs.append(v)
                attrs[i].pValue = ctypes.cast(ctypes.pointer(v), CK_VOID_PTR)
                attrs[i].ulValueLen = CK_ULONG(1)

        rv = self._call("C_FindObjectsInit", CK_RV,
                         [CK_SESSION_HANDLE, ctypes.POINTER(CK_ATTRIBUTE), CK_ULONG],
                         CK_SESSION_HANDLE(session), attrs, CK_ULONG(n))
        self._ck(rv)

        objects = []
        batch = (CK_OBJECT_HANDLE * 32)()
        found = CK_ULONG(0)

        while True:
            rv = self._call("C_FindObjects", CK_RV,
                             [CK_SESSION_HANDLE, ctypes.POINTER(CK_OBJECT_HANDLE),
                              CK_ULONG, ctypes.POINTER(CK_ULONG)],
                             CK_SESSION_HANDLE(session), batch,
                             CK_ULONG(32), ctypes.byref(found))
            self._ck(rv)
            if found.value == 0:
                break
            objects.extend(batch[i] for i in range(found.value))

        rv = self._call("C_FindObjectsFinal", CK_RV,
                         [CK_SESSION_HANDLE],
                         CK_SESSION_HANDLE(session))
        self._ck(rv)
        return objects

    def get_attribute_value(self, session: int, obj: int,
                            attr_types: List[int]) -> Dict[int, Optional[bytes]]:
        """
        Nesne özniteliklerini oku. Dönen dict: {CKA_xxx: bytes | None}.
        """
        n = len(attr_types)
        # İlk çağrı: boyutları al
        attrs = (CK_ATTRIBUTE * n)()
        for i, at in enumerate(attr_types):
            attrs[i].type = CK_ATTRIBUTE_TYPE(at)
            attrs[i].pValue = None
            attrs[i].ulValueLen = CK_ULONG(0)

        rv = self._call("C_GetAttributeValue", CK_RV,
                         [CK_SESSION_HANDLE, CK_OBJECT_HANDLE,
                          ctypes.POINTER(CK_ATTRIBUTE), CK_ULONG],
                         CK_SESSION_HANDLE(session), CK_OBJECT_HANDLE(obj),
                         attrs, CK_ULONG(n))
        # ATTRIBUTE_SENSITIVE veya TYPE_INVALID bazı alanlar için döner — devam et
        if rv not in (CKR_OK, CKR_ATTRIBUTE_SENSITIVE, CKR_ATTRIBUTE_TYPE_INVALID):
            self._ck(rv)

        result: Dict[int, Optional[bytes]] = {}
        bufs = []
        for i in range(n):
            sz = attrs[i].ulValueLen
            at = attr_types[i]
            # -1 (CK_UNAVAILABLE_INFORMATION) veya 0 ise bu öznitelik yok
            if sz == CK_ULONG(-1).value or sz == 0:
                result[at] = None
                continue
            buf = ctypes.create_string_buffer(sz)
            bufs.append(buf)
            attrs[i].pValue = ctypes.cast(buf, CK_VOID_PTR)

        # İkinci çağrı: değerleri al
        rv = self._call("C_GetAttributeValue", CK_RV,
                         [CK_SESSION_HANDLE, CK_OBJECT_HANDLE,
                          ctypes.POINTER(CK_ATTRIBUTE), CK_ULONG],
                         CK_SESSION_HANDLE(session), CK_OBJECT_HANDLE(obj),
                         attrs, CK_ULONG(n))
        if rv not in (CKR_OK, CKR_ATTRIBUTE_SENSITIVE, CKR_ATTRIBUTE_TYPE_INVALID):
            self._ck(rv)

        for i in range(n):
            at = attr_types[i]
            if at in result:
                continue
            sz = attrs[i].ulValueLen
            if attrs[i].pValue and sz > 0 and sz != CK_ULONG(-1).value:
                result[at] = ctypes.string_at(attrs[i].pValue, sz)
            else:
                result[at] = None

        return result

    # ---- İmzalama ----

    def sign_init(self, session: int, mechanism_type: int, key_handle: int):
        mech = CK_MECHANISM()
        mech.mechanism = CK_MECHANISM_TYPE(mechanism_type)
        mech.pParameter = None
        mech.ulParameterLen = CK_ULONG(0)

        rv = self._call("C_SignInit", CK_RV,
                         [CK_SESSION_HANDLE, ctypes.POINTER(CK_MECHANISM),
                          CK_OBJECT_HANDLE],
                         CK_SESSION_HANDLE(session), ctypes.byref(mech),
                         CK_OBJECT_HANDLE(key_handle))
        self._ck(rv)

    def sign(self, session: int, data: bytes) -> bytes:
        data_buf = ctypes.create_string_buffer(data)
        sig_len = CK_ULONG(512)  # RSA 4096 max
        sig_buf = ctypes.create_string_buffer(512)

        rv = self._call("C_Sign", CK_RV,
                         [CK_SESSION_HANDLE,
                          ctypes.POINTER(CK_BYTE), CK_ULONG,
                          ctypes.POINTER(CK_BYTE), ctypes.POINTER(CK_ULONG)],
                         CK_SESSION_HANDLE(session),
                         ctypes.cast(data_buf, ctypes.POINTER(CK_BYTE)),
                         CK_ULONG(len(data)),
                         ctypes.cast(sig_buf, ctypes.POINTER(CK_BYTE)),
                         ctypes.byref(sig_len))
        self._ck(rv)
        return sig_buf.raw[:sig_len.value]
