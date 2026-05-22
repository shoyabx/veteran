from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.exceptions import register_exception_handlers
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.ingestion import router as ingestion_router
from app.api.indexing import router as indexing_router
from app.api.retrieval import router as retrieval_router
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.auth import AuthMiddleware
from app.middleware.tenant import TenantIsolationMiddleware

configure_logging()

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
register_exception_handlers(app)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(TenantIsolationMiddleware)

app.include_router(health_router, prefix='/api/v1')
app.include_router(auth_router, prefix='/api/v1')
app.include_router(ingestion_router, prefix='/api/v1')
app.include_router(indexing_router, prefix='/api/v1')
app.include_router(retrieval_router, prefix='/api/v1')
