from app.core.exceptions import AppError

def require_role(user_role: str, allowed_roles: set[str]) -> None:
    if user_role not in allowed_roles:
        raise AppError(code='forbidden', message='Insufficient role permissions', status_code=403)
