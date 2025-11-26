"""PII encryption utilities using Fernet symmetric encryption."""

from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from core.config import config


def get_fernet() -> Fernet:
    """Get Fernet instance with encryption key from config."""
    key = config.ENCRYPTION_KEY
    if not key:
        raise ValueError("ENCRYPTION_KEY not configured")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_pii(plaintext: Optional[str]) -> Optional[str]:
    """
    Encrypt PII data.

    Args:
        plaintext: The plain text to encrypt

    Returns:
        Base64-encoded encrypted string, or None if input is None/empty
    """
    if not plaintext:
        return None

    fernet = get_fernet()
    encrypted = fernet.encrypt(plaintext.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_pii(ciphertext: Optional[str]) -> Optional[str]:
    """
    Decrypt PII data.

    Args:
        ciphertext: The encrypted text to decrypt

    Returns:
        Decrypted plain text, or None if input is None/empty

    Raises:
        InvalidToken: If the ciphertext is invalid or tampered
    """
    if not ciphertext:
        return None

    fernet = get_fernet()
    try:
        decrypted = fernet.decrypt(ciphertext.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        # Log this in production - indicates data tampering or key mismatch
        raise ValueError("Failed to decrypt data - invalid token or key mismatch")


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    Use this to generate a key for ENCRYPTION_KEY config.

    Returns:
        A new Fernet key as a string
    """
    return Fernet.generate_key().decode("utf-8")
