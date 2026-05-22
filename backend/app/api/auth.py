from fastapi import APIRouter, Request
from app.schemas.auth import AuthVerifyResponse

router = APIRouter(prefix='/auth', tags=['auth'])

@router.get('/verify', response_model=AuthVerifyResponse)
def verify(request: Request):
    user = request.state.user
    return AuthVerifyResponse(**user)
