from starlette.middleware.base import BaseHTTPMiddleware
from app.services.security import decode_jwt

PUBLIC_PATHS = {'/api/v1/health/live', '/api/v1/health/ready'}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.user = None
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1].strip()
            try:
                claims = decode_jwt(token)
                request.state.user = {
                    'user_id': int(claims['sub']),
                    'tenant_id': int(claims['tenant_id']),
                    'email': claims['email'],
                    'role': claims.get('role', 'member'),
                    'auth_provider': claims.get('auth_provider', 'microsoft'),
                }
            except Exception:
                request.state.user = None

        return await call_next(request)
