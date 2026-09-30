"""Auth routes: signup and login, both returning an access token."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_auth_service
from app.api.schemas import LoginRequest, SignupRequest, TokenResponse
from app.services.auth import AuthService, EmailTaken, InvalidCredentials

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest, svc: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    try:
        _, token = await svc.signup(body.email, body.password, body.topics)
    except EmailTaken as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="email already registered"
        ) from exc
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, svc: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    try:
        token = await svc.login(body.email, body.password)
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
        ) from exc
    return TokenResponse(access_token=token)
