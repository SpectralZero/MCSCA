import os
import ssl
import datetime
import ipaddress
import socket
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import datetime

# Dynamically determine the directory of this script (ensures portability across different systems)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_DIR = os.path.join(BASE_DIR, "cert")

def ensure_cert_in_cert_dir(cert_filename="server_cert.pem", key_filename="server_key.pem"):
    """
    Ensures that the SSL certificate and key exist in the designated certificate directory.
    If they do not exist, a new self-signed certificate is generated.

    Returns:
        Tuple[str, str]: Paths to the certificate and key files.
    """
    cert_path = os.path.join(CERT_DIR, cert_filename)
    key_path = os.path.join(CERT_DIR, key_filename)

    # Debugging output to indicate where certificates are being checked
    print("\n")
    print(f" Checking certificate directory: {CERT_DIR}")

    # Ensure the directory exists, create it if necessary
    if not os.path.exists(CERT_DIR):
        os.makedirs(CERT_DIR)
        print(f" Created certificate directory: {CERT_DIR}")

    # If certificate or key is missing, generate new ones
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        try:
            host_name = socket.gethostname()
            local_ip  = socket.gethostbyname(host_name)
        except Exception:
            local_ip = "127.0.0.1"

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            local_ip = sock.getsockname()[0]
        except Exception:
            local_ip = "127.0.0.1"
        finally:
            sock.close()    
        print("  Certificates not found. Generating new ones...")
        generate_self_signed_cert(cert_path, key_path, ip=local_ip)
    else:
        print(f" Certificates already exist: {cert_path}, {key_path}")

    return cert_path, key_path

def configure_tls_context(certfile, keyfile, purpose, cafile=None):
    """
    Configures a TLS context using the provided certificate and key files.

    Args:
        certfile (str): Path to the SSL certificate file.
        keyfile (str): Path to the private key file.
        purpose (ssl.Purpose): The intended use of the SSL context (SERVER_AUTH or CLIENT_AUTH).
        cafile (str, optional): Path to the CA file for verifying certificates (default is None).

    Returns:
        ssl.SSLContext: Configured TLS context.
    """
    try:
        # ── Client side ───────────────────────────────────────────────
        if purpose == ssl.Purpose.SERVER_AUTH:
            ctx = ssl.create_default_context(purpose)
            if cafile:
                ctx.load_verify_locations(cafile=cafile)
                ctx.verify_mode = ssl.CERT_REQUIRED
            else:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

        # ── Server side ───────────────────────────────────────────────
        else:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile, keyfile)
            ctx.verify_mode = ssl.CERT_OPTIONAL     # ready for mTLS later

        # ── Hardening common to both roles ────────────────────────────
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        ctx.options |= ssl.OP_NO_COMPRESSION

        #ctx.keylog_filename = os.path.expanduser("C:/Users/RTX/Desktop/sslkeys.log")  to decrypt with wireshark (tls) 

        # Try to pin TLS‑1.3 cipher suites if the API is present
        try:
            if hasattr(ctx, "set_ciphersuites"):     # OpenSSL ≥ 3.0
                ctx.set_ciphersuites(
                    "TLS_AES_256_GCM_SHA384:"
                    "TLS_CHACHA20_POLY1305_SHA256"
                )
        except ssl.SSLError as err:
            # Fall back silently; runtime doesn’t support our filter
            print("  Cipher-suite pinning skipped:", err)

        return ctx

    except Exception as e:
        raise RuntimeError(f"Failed to configure TLS context: {e}")

def generate_self_signed_cert(cert_path, key_path,ip):
    """
    Generates a self-signed SSL certificate and saves it to the specified paths.

    Args:
        cert_path (str): Path where the certificate should be saved.
        key_path (str): Path where the private key should be saved.
    """
    """
        What is an X.509 certificate?

        X.509 is a standard format for public key certificates, digital documents that securely associate cryptographic key pairs with identities such as websites, individuals, or organizations. RFC 5280 profiles the X.509 v3 certificate, the X.509 v2 certificate revocation list (CRL), and describes an algorithm for X.509 certificate path validation.
        What are X.509 certificates used for?

        Common applications of X.509 certificates include SSL/TLS and HTTPS for authenticated and encrypted web browsing, signed and encrypted email via the S/MIME protocol, code signing, document signing, client authentication, and government-issued electronic ID.

    """
    try:
        # Generate an RSA private key
        key = rsa.generate_private_key(
            public_exponent=65537,  # Standard value for security
            key_size=2048,  # 2048-bit key size (secure and efficient)
            backend=default_backend()
        )

        # Define the subject and issuer (same for a self-signed certificate)
        subject = issuer = x509.Name([
            x509.NameAttribute(x509.NameOID.COMMON_NAME, u'localhost')
        ])

        san_list = [
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address(ip))
        ]
        # Create the self-signed certificate
        cert_builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())  # Generate a unique serial number
            .not_valid_before(datetime.datetime.utcnow())  # Certificate starts being valid immediately
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))  # Valid for 1 year
            .add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False
            )
        )
        cert = cert_builder.sign(key, hashes.SHA256(), default_backend())

        # Save the private key to the specified path
        with open(key_path, "wb") as key_file:
            key_file.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),  # No password protection
                )
            )

        # Save the self-signed certificate to the specified path
        with open(cert_path, "wb") as cert_file:
            cert_file.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f" Self-signed certificate created at: {cert_path}")
        print(f" Private key saved at: {key_path}")

    except Exception as e:
        print(f" Error generating self-signed certificate: {e}")
