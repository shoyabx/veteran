from pydantic import BaseModel, EmailStr

class AuthVerifyResponse(BaseModel):
    user_id: int
    tenant_id: int
    email: EmailStr
    role: str
    auth_provider: str

class ErrorResponse(BaseModel):
    error: dict
