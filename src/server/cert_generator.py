import os
import subprocess
from typing import Tuple

def generate_self_signed_cert(cert_path: str, key_path: str, cn: str = 'localhost') -> None:
    """
    Yerel HTTPS sunucusu için kendinden imzalı sertifika (self-signed cert) oluşturur.
    Openssl komutunu kullanarak localhost ve 127.0.0.1 için 10 yıllık sertifika üretir.
    """
    config_path = f"{cert_path}.conf"
    config_content = f"""
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = {cn}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = {cn}
IP.1 = 127.0.0.1
"""
    with open(config_path, "w") as f:
        f.write(config_content)

    try:
        # Generate RSA 2048-bit key and self-signed cert for 3650 days (10 years)
        cmd = [
            "openssl", "req", "-x509", "-nodes", "-days", "3650",
            "-newkey", "rsa:2048",
            "-keyout", key_path,
            "-out", cert_path,
            "-config", config_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        if os.path.exists(config_path):
            os.remove(config_path)

def ensure_server_cert(base_dir: str = '~/.palma') -> Tuple[str, str]:
    """
    Sertifikanın var olduğundan emin olur, yoksa oluşturur.
    Dönüş: (cert_path, key_path)
    """
    expanded_dir = os.path.expanduser(base_dir)
    os.makedirs(expanded_dir, exist_ok=True)
    
    # We store the combined file as .pem, or separate .crt/.key.
    # We will use server.pem as requested and also produce a key file.
    cert_path = os.path.join(expanded_dir, "server.pem")
    key_path = os.path.join(expanded_dir, "server.key")
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        generate_self_signed_cert(cert_path, key_path)
        
    return cert_path, key_path
