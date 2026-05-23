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
                sub_val = claims['sub']
                tid_val = claims['tenant_id']

                # 1. Direct Numeric Mapping (Backward compatibility with legacy/symmetric HS256 local tests)
                if str(sub_val).isdigit() and str(tid_val).isdigit():
                    request.state.user = {
                        'user_id': int(sub_val),
                        'tenant_id': int(tid_val),
                        'email': claims['email'],
                        'role': claims.get('role', 'member'),
                        'auth_provider': 'microsoft',
                    }
                # 2. Native Dynamic Microsoft Entra ID GUID/String Mapping and Auto-provisioning
                else:
                    from app.db.session import SessionLocal
                    from sqlalchemy import select
                    from app.models.models import Tenant, User, Role
                    
                    db = SessionLocal()
                    try:
                        tenant_name = str(tid_val)
                        tenant = db.scalar(select(Tenant).where(Tenant.name == tenant_name))
                        if not tenant:
                            tenant = Tenant(name=tenant_name)
                            db.add(tenant)
                            db.commit()
                            db.refresh(tenant)

                        user_sub = str(sub_val)
                        user = db.scalar(select(User).where(User.external_entra_user_id == user_sub))
                        if not user:
                            role_name = claims.get('role', 'member')
                            role = db.scalar(select(Role).where(Role.name == role_name))
                            if not role:
                                role = db.scalar(select(Role).where(Role.name == 'member'))
                            if not role:
                                role = Role(name='member')
                                db.add(role)
                                db.commit(); db.refresh(role)

                            user = User(
                                tenant_id=tenant.id,
                                external_entra_user_id=user_sub,
                                external_entra_tenant_id=tenant_name,
                                email=claims['email'],
                                display_name=claims.get('name', claims['email'].split('@')[0]),
                                role_id=role.id,
                            )
                            db.add(user)
                            db.commit(); db.refresh(user)

                        request.state.user = {
                            'user_id': user.id,
                            'tenant_id': user.tenant_id,
                            'email': user.email,
                            'role': user.role.name if user.role else 'member',
                            'auth_provider': 'microsoft',
                            'external_entra_user_id': user.external_entra_user_id,
                            'external_entra_tenant_id': user.external_entra_tenant_id,
                        }
                    finally:
                        db.close()
            except Exception:
                request.state.user = None

        return await call_next(request)
