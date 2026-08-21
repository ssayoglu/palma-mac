import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import ssl
from typing import Any, Dict

class SOAPError(Exception):
    """SOAP isteklerinde oluşan hatalar için temel istisna sınıfı."""
    pass

class SOAPClient:
    """TÜRKTRUST web servisleri için jenerik SOAP istemcisi."""
    
    def __init__(self, endpoint_url: str, namespace: str, timeout: int = 30):
        self.endpoint_url = endpoint_url
        self.namespace = namespace
        self.timeout = timeout

    def call(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Belirtilen aksiyon ve parametrelerle SOAP çağrısı yapar."""
        # Namespace ayarları
        ns_map = {
            "xmlns:soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
            "xmlns:web": self.namespace
        }
        
        envelope = ET.Element("soapenv:Envelope", ns_map)
        ET.SubElement(envelope, "soapenv:Header")
        body = ET.SubElement(envelope, "soapenv:Body")
        
        operation = ET.SubElement(body, f"web:{action}")
        for k, v in params.items():
            param_elem = ET.SubElement(operation, f"web:{k}")
            param_elem.text = str(v)
            
        xml_data = ET.tostring(envelope, encoding="utf-8", method="xml")
        
        # SOAPAction oluşturma
        soap_action = f"{self.namespace}{action}" if self.namespace.endswith('/') else f"{self.namespace}/{action}"
        
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": soap_action
        }
        
        req = urllib.request.Request(self.endpoint_url, data=xml_data, headers=headers, method="POST")
        
        # Sertifika doğrulaması olmadan HTTPS isteği yap (isteğe bağlı güvenlik ayarı)
        context = ssl._create_unverified_context()
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=context) as response:
                resp_xml = response.read()
        except urllib.error.HTTPError as e:
            resp_xml = e.read()
            if e.code == 404:
                raise SOAPError(f"Servis bulunamadı (HTTP 404). TÜRKTRUST aktivasyon servisi şu anda kullanılamıyor olabilir.") from e
            if e.code != 500:
                raise SOAPError(f"HTTP Hatası: {e.code}") from e
        except urllib.error.URLError as e:
            raise SOAPError(f"Ağ Hatası (Zaman aşımı vb.): {str(e)}") from e
        except Exception as e:
            raise SOAPError(f"Beklenmeyen Hata: {str(e)}") from e
            
        return self._parse_response(resp_xml, action)

    def _parse_response(self, xml_data: bytes, action: str) -> Dict[str, Any]:
        """Gelen XML yanıtını ayrıştırır ve sözlüğe çevirir."""
        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as e:
            raise SOAPError("Geçersiz XML yanıtı alındı") from e
            
        namespaces = {
            'soapenv': 'http://schemas.xmlsoap.org/soap/envelope/',
            'web': self.namespace
        }
        
        body = root.find("soapenv:Body", namespaces)
        if body is None:
            raise SOAPError("SOAP Body bulunamadı")
            
        fault = body.find("soapenv:Fault", namespaces)
        if fault is not None:
            faultstring = fault.findtext("faultstring", default="Bilinmeyen SOAP Hatası", namespaces={'': ''})
            # namespace olmadan faultstring araması
            if not faultstring or faultstring == "Bilinmeyen SOAP Hatası":
                 faultstring_elem = fault.find("faultstring")
                 if faultstring_elem is not None:
                     faultstring = faultstring_elem.text
            raise SOAPError(f"SOAP Hatası: {faultstring}")
            
        response_elem = body.find(f"web:{action}Response", namespaces)
        if response_elem is None:
            # Fallback olarak namespacesiz aramayı dene
            if len(body) > 0:
                response_elem = body[0]
            else:
                return {}
                
        result = {}
        for child in response_elem:
            # child.tag'in içinden sadece tag adını çıkar
            tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            result[tag_name] = child.text
            
        return result
