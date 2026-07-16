"""用户注册/登录/查询/偏好 HTTP 端点（F1）。

- POST /register  注册（落库 + 签发 JWT）
- POST /login     极简登录（user_id → JWT）
- GET  /me        Bearer token → 当前用户
- GET  /{user_id} 查询用户（落库）
- PUT  /{user_id}/preferences  更新偏好（落库，整体 JSON）

注意：/me 必须在 /{user_id} 之前声明，否则会被当成 user_id="me"。
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.contracts import CONFLICT_RESPONSE, NOT_FOUND_RESPONSE, UNPROCESSABLE_RESPONSE
from app.core.security import require_user_id
from app.models.user import Preference

from .models import (
    AuthResponse,
    LoginRequest,
    LoginResponse,
    PreferenceUpdateResponse,
    RegisterRequest,
    UserDetailResponse,
)
from .service import (
    InvalidLanguageError,
    UserAlreadyExistsError,
    UserNotFoundError,
    user_service,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user and issue a JWT",
    responses={**CONFLICT_RESPONSE, **UNPROCESSABLE_RESPONSE},
)
def register(request: RegisterRequest) -> AuthResponse:
    try:
        user, token = user_service.register(request.user_id, request.name, request.language)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"user {exc} already exists") from exc
    except InvalidLanguageError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return AuthResponse(user_id=user.user_id, token=token, user=user)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Minimal login: exchange user_id for a JWT",
    responses=NOT_FOUND_RESPONSE,
)
def login(request: LoginRequest) -> LoginResponse:
    try:
        user, token = user_service.login(request.user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"user {exc} not found") from exc
    return LoginResponse(user_id=user.user_id, token=token)


@router.get(
    "/me",
    response_model=UserDetailResponse,
    summary="Get the current user from the Bearer token",
    responses={**NOT_FOUND_RESPONSE, 401: {"description": "Missing or invalid bearer token."}},
)
def me(user_id: str = Depends(require_user_id)) -> UserDetailResponse:
    user = user_service.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return UserDetailResponse(user=user)


@router.get(
    "/{user_id}",
    response_model=UserDetailResponse,
    summary="Get a user by id",
    responses=NOT_FOUND_RESPONSE,
)
def get_user(user_id: str) -> UserDetailResponse:
    user = user_service.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"user {user_id} not found")
    return UserDetailResponse(user=user)


@router.put(
    "/{user_id}/preferences",
    response_model=PreferenceUpdateResponse,
    summary="Update user preferences (persisted)",
    responses=UNPROCESSABLE_RESPONSE,
)
def update_preferences(user_id: str, pref: Preference) -> PreferenceUpdateResponse:
    try:
        user_service.update_preference(user_id, pref)
    except InvalidLanguageError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return PreferenceUpdateResponse(status="ok", user_id=user_id, preference=pref)
