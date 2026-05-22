import uuid
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger('request')

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        correlation_id = request.headers.get('x-correlation-id', str(uuid.uuid4()))
        request.state.correlation_id = correlation_id
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            f'{request.method} {request.url.path} {response.status_code} {duration_ms}ms',
            extra={'correlation_id': correlation_id},
        )
        response.headers['x-correlation-id'] = correlation_id
        return response
