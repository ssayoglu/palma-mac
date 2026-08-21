import os
import json
import ssl
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from .cert_generator import ensure_server_cert

# Log dosyasının yolunu ayarla
LOG_DIR = os.path.expanduser("~/Library/Logs/PalmaMac")
logger = logging.getLogger("PalmaLocalServer")
logger.setLevel(logging.INFO)
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    _fh = logging.FileHandler(os.path.join(LOG_DIR, "server.log"))
    _fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(_fh)
except OSError:
    pass  # Log dizini oluşturulamazsa sessizce devam et

class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info("%s - - [%s] %s\n" % (self.client_address[0], self.log_date_time_string(), format%args))

    def _send_cors_headers(self):
        """CORS başlıklarını ekler"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_response(self, status_code, payload=None):
        self.send_response(status_code)
        self._send_cors_headers()
        if payload is not None:
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        else:
            self.end_headers()

    def do_OPTIONS(self):
        """CORS preflight isteklerini işler"""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """GET isteklerini işler"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query = parse_qs(parsed_path.query)

        if path == "/status":
            self._send_response(200, {"running": True, "version": "2.9.0-mac"})
            return

        server = self.server.palma_server

        if path == "/readers":
            try:
                with server.lock:
                    readers = server.card_manager.get_readers()
                result = [{"name": r.name, "slot_id": r.slot_id} for r in readers]
                self._send_response(200, result)
            except Exception as e:
                logger.error(f"Error in /readers: {e}")
                self._send_response(500, {"error": str(e)})
            return

        if path == "/certificates":
            pin = query.get("pin", [""])[0]
            slot_id = int(query.get("slot", ["1"])[0])
            try:
                with server.lock:
                    certs = server.card_manager.get_certificates(slot_id, pin=pin or None)
                result = [{
                    "label": c.label,
                    "subject": c.subject,
                    "issuer": c.issuer,
                    "serial_number": c.serial_number,
                    "not_after": c.not_after.isoformat() if c.not_after else None,
                    "is_expired": c.is_expired,
                } for c in certs]
                self._send_response(200, result)
            except Exception as e:
                logger.error(f"Error in /certificates: {e}")
                self._send_response(500, {"error": str(e)})
            return
            
        if path == "/token-info":
            slot_id = int(query.get("slot", ["1"])[0])
            try:
                with server.lock:
                    info = server.card_manager.get_token_info(slot_id)
                result = {
                    "label": info.label,
                    "manufacturer": info.manufacturer,
                    "model": info.model,
                    "serial_number": info.serial_number,
                }
                self._send_response(200, result)
            except Exception as e:
                logger.error(f"Error in /token-info: {e}")
                self._send_response(500, {"error": str(e)})
            return

        self._send_response(404, {"error": "Endpoint not found"})

    def do_POST(self):
        """POST isteklerini işler"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode('utf-8')) if body else {}
        except json.JSONDecodeError:
            self._send_response(400, {"error": "Invalid JSON body"})
            return

        server = self.server.palma_server

        if path == "/sign":
            try:
                with server.lock:
                    res = server.card_manager.sign(data) if hasattr(server.card_manager, "sign") else {"signature": ""}
                self._send_response(200, res)
            except Exception as e:
                logger.error(f"Error in /sign: {e}")
                self._send_response(500, {"error": str(e)})
            return

        if path == "/verify-pin":
            try:
                pin = data.get("pin", "")
                slot_id = data.get("slot", 1)
                with server.lock:
                    res = server.pin_manager.verify_pin(slot_id, pin)
                self._send_response(200, {
                    "success": res.success,
                    "remaining_attempts": res.remaining_attempts,
                    "error_message": res.error_message,
                })
            except Exception as e:
                logger.error(f"Error in /verify-pin: {e}")
                self._send_response(500, {"error": str(e)})
            return

        self._send_response(404, {"error": "Endpoint not found"})


class PalmaLocalServer:
    def __init__(self, card_manager, pin_manager, host='127.0.0.1', port=8443):
        self.card_manager = card_manager
        self.pin_manager = pin_manager
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        
        # Smart kart işlemlerini serileştirmek için kilit (thread-safe)
        self.lock = threading.Lock()

    def start(self):
        """Sunucuyu arka plan iş parçacığında başlatır"""
        if self.is_running():
            return
            
        cert_path, key_path = ensure_server_cert()
        
        self.server = HTTPServer((self.host, self.port), RequestHandler)
        self.server.palma_server = self
        
        # HTTPS ayarları (SSL context)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        logger.info(f"Palma local server started on https://{self.host}:{self.port}")

    def stop(self):
        """Sunucuyu durdurur"""
        if self.server:
            logger.info("Stopping Palma local server...")
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None
            logger.info("Server stopped.")

    def is_running(self) -> bool:
        """Sunucunun çalışıp çalışmadığını kontrol eder"""
        return self.server is not None and self.thread is not None and self.thread.is_alive()
