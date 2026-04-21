import os
from cryptography.fernet import Fernet, InvalidToken

_raw_key = os.getenv("CUENTAS_SECRET_KEY", "")
_fernet = None

if _raw_key:
    try:
        _fernet = Fernet(_raw_key.encode())
    except Exception as e:
        print(f"[crypto] CUENTAS_SECRET_KEY inválida: {e}")


def encrypt(plaintext: str) -> str:
    if not _fernet or not plaintext:
        return plaintext
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    if not _fernet or not ciphertext:
        return ciphertext
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        return ciphertext  # Texto plano legado — devuelve tal cual
