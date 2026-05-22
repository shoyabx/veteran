from app.core.exceptions import AppError

def assert_tenant_access(request_tenant_id: int, resource_tenant_id: int) -> None:
    if request_tenant_id != resource_tenant_id:
        raise AppError(code='tenant_forbidden', message='Cross-tenant access blocked', status_code=403)
