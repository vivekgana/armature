"""SPEC-2026-Q2-001 / AC-1, AC-2, AC-3, AC-4 — Authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from app.services.auth_service import authenticate, register, verify_token

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    roles: list[str]


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(req: RegisterRequest) -> UserResponse:
    """AC-1: POST /auth/register creates a new user and returns 201."""
    try:
        user = register(req.email, req.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return UserResponse(id=user.id, email=user.email, roles=user.roles)


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest) -> TokenResponse:
    """AC-2, AC-3: POST /auth/login returns JWT or 401."""
    token = authenticate(req.email, req.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return TokenResponse(access_token=token)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """AC-4: Dependency that validates Bearer token on protected routes."""
    try:
        payload = verify_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return {"id": payload["sub"], "email": payload["email"], "roles": payload["roles"]}
