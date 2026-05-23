from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

PROTECTED_PREFIXES = ('/api/v1/auth', '/api/v1/ingestion', '/api/v1/indexing', '/api/v1/retrieval')

class TenantIsolationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path.startswith(PROTECTED_PREFIXES):
            user = getattr(request.state, 'user', None)
            if not user:
                return JSONResponse(status_code=401, content={'error': {'code': 'unauthorized', 'message': 'Authentication required'}})

            tenant_header = request.headers.get('x-tenant-id')
            if tenant_header:
                matched_id = None
                if tenant_header.isdigit():
                    matched_id = int(tenant_header)
                else:
                    from app.db.session import SessionLocal
                    from sqlalchemy import select
                    from app.models.models import Tenant
                    db = SessionLocal()
                    try:
                        tenant = db.scalar(select(Tenant).where(Tenant.name == tenant_header))
                        if tenant:
                            matched_id = tenant.id
                    finally:
                        db.close()

                if matched_id is None or matched_id != user['tenant_id']:
                    return JSONResponse(status_code=403, content={'error': {'code': 'tenant_forbidden', 'message': 'Cross-tenant request blocked'}})

            request.state.tenant_id = user['tenant_id']
        return await call_next(request)
