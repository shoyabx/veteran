from cryptography.fernet import Fernet
from jose import jwt, JWTError
from app.core.config import settings

fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())

def encrypt_secret(raw: str) -> str:
    return fernet.encrypt(raw.encode()).decode()

def decrypt_secret(enc: str) -> str:
    return fernet.decrypt(enc.encode()).decode()

def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise ValueError('invalid_token') from e
