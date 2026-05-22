from jose import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def mk_token(sub: int, tenant_id: int, email: str, role='member'):
    return jwt.encode(
        {'sub': str(sub), 'tenant_id': tenant_id, 'email': email, 'role': role, 'auth_provider': 'microsoft'},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

def test_health_live():
    r = client.get('/api/v1/health/live')
    assert r.status_code == 200

def test_unauthorized_verify():
    r = client.get('/api/v1/auth/verify')
    assert r.status_code == 401

def test_authorized_verify():
    token = mk_token(1, 101, 'user@example.com')
    r = client.get('/api/v1/auth/verify', headers={'authorization': f'Bearer {token}'})
    assert r.status_code == 200
    assert r.json()['tenant_id'] == 101

def test_cross_tenant_blocked():
    token = mk_token(1, 101, 'user@example.com')
    r = client.get('/api/v1/auth/verify', headers={'authorization': f'Bearer {token}', 'x-tenant-id': '202'})
    assert r.status_code == 403
