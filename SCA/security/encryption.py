# security/encryption.py

import os
import threading
import logging
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidTag

# Configure logger for this module
logger = logging.getLogger('secure_chat.encryption')

# Global variables for IV generation to ensure uniqueness
_iv_counter = int.from_bytes(os.urandom(4), 'big')
_iv_lock = threading.Lock()

def _get_unique_iv() -> bytes:
    """
    Generates a unique 12-byte Initialization Vector (IV) for AES-GCM encryption.
    
    The IV consists of:
    - 4 bytes from an incrementing counter to ensure uniqueness across sessions.
    - 8 bytes of random data to add unpredictability.
    
    Returns:
        bytes: A unique 12-byte IV.
    """
    global _iv_counter
    with _iv_lock:
        _iv_counter += 1
        counter_bytes = _iv_counter.to_bytes(4, 'big')  # 4-byte counter in big-endian
    random_bytes = os.urandom(8)  # 8 bytes of random data
    return counter_bytes + random_bytes  # Total IV length: 12 bytes

def encrypt_message(key: bytes, plaintext: str) -> bytes:
    """
    Encrypts a plaintext message using AES-256 in Galois/Counter Mode (GCM).
    
    AES-GCM provides both confidentiality and integrity for the encrypted data.
    
    Args:
        key (bytes): A 32-byte (256-bit) symmetric encryption key.
        plaintext (str): The message to be encrypted.
    
    Returns:
        bytes: The encrypted message containing IV, authentication tag, and ciphertext.                #jamal >>   12(4,8)+16+axv32     
    
    Raises:
        Exception: If encryption fails for any reason.
    """
    try:
        # Generate a unique IV for this encryption operation
        iv = _get_unique_iv()
        
        # Initialize the AES-GCM cipher
        encryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(iv),
            backend=default_backend()
        ).encryptor()
        
        # Encrypt the plaintext
        ciphertext = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()
        
        # Concatenate IV, Tag, and Ciphertext for transmission/storage
        encrypted_message = iv + encryptor.tag + ciphertext  # Total length: 12 + 16 + len(ciphertext)
        
        #logger.debug(f"Encryption successful. IV: {iv.hex()}, Tag: {encryptor.tag.hex()}, Ciphertext: {ciphertext.hex()}")
        return encrypted_message
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise

def decrypt_message(key: bytes, encrypted_message: bytes) -> str:
    """ 

        This function validates the integrity of the message using the authentication tag 
        and ensures that the encrypted message contains the necessary components for decryption.
        encrypted_message (bytes): The encrypted message containing the Initialization Vector (IV),
        authentication tag, and ciphertext. The IV is expected to be 12 bytes, the tag 16 bytes,
        nd the remainder is the ciphertext.
        str or None: The decrypted plaintext message as a UTF-8 string if decryption is successful.
        Returns None if the decryption fails due to an invalid authentication tag, corrupted data,
        or any other error.

    """
    """

    Decrypts an encrypted message using AES-256 in Galois/Counter Mode (GCM).
    
    Validates the integrity of the message using the authentication tag.
    
    Args:
        key (bytes): A 32-byte (256-bit) symmetric encryption key.
        encrypted_message (bytes): The encrypted message containing IV, authentication tag, and ciphertext.
    
    Returns:
        str or None: The decrypted plaintext message if successful; otherwise, None.

    """
    try:
        # Ensure the encrypted message is long enough to contain IV and Tag
        if len(encrypted_message) < 28:
            logger.error("Encrypted message is too short to contain IV and Tag.")
            return None

        # Extract IV (12 bytes), Tag (16 bytes), and Ciphertext
        iv = encrypted_message[:12]
        tag = encrypted_message[12:28]
        ciphertext = encrypted_message[28:]              #      abcdefghijklmnopqrstuvwxyz1234

        # Initialize the AES-GCM cipher for decryption with the extracted IV and Tag
        decryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(iv, tag),
            backend=default_backend()
        ).decryptor()

        # Decrypt the ciphertext
        decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Decode the decrypted bytes to a UTF-8 string
        decrypted_message = decrypted_padded.decode('utf-8')
        
        
        return decrypted_message
    except InvalidTag:
        # The authentication tag does not match; the message has been tampered with or corrupted
        logger.error("Invalid authentication tag. Decryption failed.")
        logger.debug("Invalid authentication tag (expected if non-ciphertext frame)") 
        return None
    except Exception as e:
        # Catch-all for any other exceptions during decryption
        logger.error(f"Decryption failed: {e}")
        return None


"""
1. AES-GCM Encryption: Provides both confidentiality (hides the data) and integrity (ensures the data hasn’t been altered).
2. Thread Safety: Ensures the IV is unique even when multiple threads are running.
3. Error Logging: Logs detailed errors for debugging if encryption or decryption fails.
4. Secure Key Handling: Requires a 32-byte key, ensuring strong encryption.

"""