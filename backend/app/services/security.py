from cryptography.fernet import Fernet
from jose import jwt, JWTError
from app.core.config import settings

fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())

def encrypt_secret(raw: str) -> str:
    return fernet.encrypt(raw.encode()).decode()

def decrypt_secret(enc: str) -> str:
    return fernet.decrypt(enc.encode()).decode()

_JWKS_CACHE: dict = {}
_JWKS_CACHE_EXPIRY: float = 0.0

def get_microsoft_jwks() -> dict:
    global _JWKS_CACHE, _JWKS_CACHE_EXPIRY
    import time
    now = time.time()
    if not _JWKS_CACHE or now > _JWKS_CACHE_EXPIRY:
        try:
            # Discover and retrieve dynamic JWKS from Microsoft's public keys endpoint
            resp = httpx.get('https://login.microsoftonline.com/common/discovery/v2.0/keys', timeout=5.0)
            if resp.status_code == 200:
                _JWKS_CACHE = resp.json()
                _JWKS_CACHE_EXPIRY = now + 86400  # Cache keys for 24 hours
        except Exception as e:
            if not _JWKS_CACHE:
                raise ValueError('jwks_retrieval_failed') from e
    return _JWKS_CACHE

def decode_jwt(token: str) -> dict:
    try:
        headers = jwt.get_unverified_header(token)
    except Exception as e:
        raise ValueError('invalid_token_header') from e

    alg = headers.get('alg', 'HS256')
    if alg == 'HS256':
        try:
            return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        except JWTError as e:
            raise ValueError('invalid_token_signature') from e

    elif alg == 'RS256':
        kid = headers.get('kid')
        if not kid:
            raise ValueError('missing_kid_header')

        jwks = get_microsoft_jwks()
        public_key = None
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                public_key = key
                break

        if not public_key:
            raise ValueError('matching_jwk_not_found')

        try:
            # We skip 'iss' verification in Jose's native decode so we can dynamically check for multiple Entra ID issuer formats
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=[settings.AZURE_CLIENT_ID, '00000003-0000-0000-c000-000000000000'],
                options={'verify_aud': True, 'verify_iss': False, 'verify_exp': True}
            )
        except JWTError as e:
            raise ValueError(f'rs256_token_validation_failed:{str(e)}') from e

        iss = decoded.get('iss', '')
        # Issuer validation: Must contain standard Entra ID domains
        if 'login.microsoftonline.com' not in iss and 'sts.windows.net' not in iss:
            raise ValueError('invalid_issuer')

        # Normalize claims for downstream processing
        return {
            'sub': decoded.get('oid') or decoded.get('sub'),
            'tenant_id': decoded.get('tid') or decoded.get('tenant_id') or 'default',
            'email': decoded.get('email') or decoded.get('upn') or decoded.get('unique_name') or 'unknown@entra.local',
            'role': decoded.get('role') or (decoded.get('roles', ['member'])[0] if decoded.get('roles') else 'member'),
            'auth_provider': 'microsoft',
        }
    else:
        raise ValueError(f'unsupported_algorithm:{alg}')
