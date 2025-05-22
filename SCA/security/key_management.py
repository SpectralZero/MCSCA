# security/key_management.py

import logging
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from typing import Tuple

# Configure logger for this module
logger = logging.getLogger('secure_chat.key_management')


def generate_ecdh_keypair() -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
    """
    Generates an Elliptic Curve Diffie-Hellman (ECDH) key pair using the SECP256R1 curve.
    
    ECDH is used for establishing a shared secret between two parties, which can then be used
    to derive symmetric keys for encryption and decryption.
    
    Returns:
        Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]: A tuple containing the
        generated private and public keys.
    
    Raises:
        Exception: If key pair generation fails for any reason.
    """
    try:
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = private_key.public_key()
        #print("Private Key:", private_key)
        #print("Public Key:", public_key)
        logger.info("ECDH key pair generated successfully")
        return private_key, public_key
    except Exception as e:
        logger.error(f"Key pair generation failed: {e}")
        raise e


def derive_shared_key(
    private_key: ec.EllipticCurvePrivateKey,
    peer_public_key_bytes: bytes,
    salt: bytes,
    info: bytes
) -> bytes:
    """
    Derives a shared symmetric key using Elliptic Curve Diffie-Hellman (ECDH) and 
    the HMAC-based Extract-and-Expand Key Derivation Function (HKDF).
    
    This function performs the following steps:
    1. Deserializes the peer's public key from PEM format.
    2. Exchanges keys using ECDH to obtain the shared secret.
    3. Derives a symmetric key from the shared secret using HKDF with the provided salt and info.
    
    Args:
        private_key (ec.EllipticCurvePrivateKey): The user's private ECDH key.
        peer_public_key_bytes (bytes): The peer's public ECDH key in PEM format.
        salt (bytes): A non-secret random value used with HKDF to ensure uniqueness.
        info (bytes): Contextual information for key derivation.
    
    Returns:
        bytes: The derived symmetric key (32 bytes for AES-256).
    
    Raises:
        Exception: If shared key derivation fails due to invalid peer key or other issues.
    """
    try:
        # Deserialize the peer's public key from PEM format
        peer_public_key = serialization.load_pem_public_key(
            peer_public_key_bytes,
            backend=default_backend()
        )

        # Perform ECDH key exchange to obtain the shared secret
        shared_secret = private_key.exchange(ec.ECDH(), peer_public_key)

        # Derive the shared symmetric key using HKDF with SHA-256
        derived_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,       # Derive a 256-bit key for AES-256
            salt=salt,
            info=info,
            backend=default_backend()
        ).derive(shared_secret)

        logger.info("Shared key derived successfully")
        return derived_key
    except Exception as e:
        logger.error(f"Shared key derivation failed: {e}")
        raise
"""
ECDH exchange → 32 bytes of raw shared secret.

HKDF-Extract with a 32 byte salt → mixes in extra randomness.

HKDF-Expand with your info label → namespaces the key and stretches or
shrinks it to the exact length you need (32 bytes for AES-256).
"""
"""
ECDH for Secure Key Exchange: Ensures that only the two parties involved can compute the shared secret.
HKDF for Key Derivation: Adds randomness and ensures the symmetric key is unique and secure.
Error Handling: Logs errors if key generation or derivation fails.

"""