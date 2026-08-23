"""用户注册/登录/查询/偏好 HTTP 端点（F1）。

- POST /register  注册（email + 昵称 + 国家 + 语言 → 自动生成 user_id + JWT）
- POST /login     登录（email → JWT）
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
    PreferenceMemoryResponse,
    RegisterRequest,
    SendVerificationRequest,
    UserDetailResponse,
    VerificationStatusResponse,
    VerifyRequest,
)
from .service import (
    EmailOrPhoneRequiredError,
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
    summary="Register a user by email and issue a JWT",
    responses={**CONFLICT_RESPONSE, **UNPROCESSABLE_RESPONSE},
)
def register(request: RegisterRequest) -> AuthResponse:
    try:
        user, token = user_service.register(
            request.name, request.language, request.password,
            email=request.email, phone=request.phone, country=request.country,
        )
    except EmailOrPhoneRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidLanguageError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return AuthResponse(
        user_id=user.user_id, email=user.email, phone=user.phone,
        token=token, user=user,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login: exchange email or phone for a JWT",
    responses=NOT_FOUND_RESPONSE,
)
def login(request: LoginRequest) -> LoginResponse:
    try:
        user, token = user_service.login(request.password, email=request.email, phone=request.phone)
    except EmailOrPhoneRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LoginResponse(
        user_id=user.user_id, email=user.email, phone=user.phone,
        token=token,
    )


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


@router.get(
    "/{user_id}/preference-memory",
    response_model=PreferenceMemoryResponse,
    summary="Get the user's structured long-term preference memory",
)
def get_preference_memory(user_id: str) -> PreferenceMemoryResponse:
    return PreferenceMemoryResponse(user_id=user_id, memory=user_service.get_preference_memory(user_id))


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


# ── Verification endpoints (placeholder — requires cloud email/SMS service) ─

NOT_IMPLEMENTED_DETAIL = (
    "Verification requires a cloud email/SMS service (e.g. SendGrid, Twilio, Alibaba Cloud SMS). "
    "This endpoint is a placeholder. Set up a cloud provider and implement the service layer to enable."
)


@router.post(
    "/me/send-verification",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Send verification code via email or SMS (placeholder)",
)
def send_verification(
    request: SendVerificationRequest,
    user_id: str = Depends(require_user_id),
) -> dict:
    """发送验证码到用户邮箱或手机。

    当前为占位端点。实现需要：
    1. 云邮件/SMS 服务（SendGrid / Twilio / 阿里云短信）
    2. 生成随机验证码 → 哈希存入 users.verification_code
    3. 设置 users.verification_expires_at（如 +10 分钟）
    4. 调用云服务发送验证码
    5. 更新 users.verification_status = "pending"
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=NOT_IMPLEMENTED_DETAIL,
    )


@router.post(
    "/me/verify",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="Verify a code sent to email or phone (placeholder)",
)
def verify_code(
    request: VerifyRequest,
    user_id: str = Depends(require_user_id),
) -> dict:
    """校验用户提交的验证码。

    当前为占位端点。实现需要：
    1. 从 DB 读取 verification_code 和 verification_expires_at
    2. 比对用户提交的 code 与存储的哈希值
    3. 检查是否过期
    4. 匹配成功 → users.verification_status = "verified"
    5. 清除 verification_code / verification_expires_at
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=NOT_IMPLEMENTED_DETAIL,
    )


@router.get(
    "/me/verification-status",
    response_model=VerificationStatusResponse,
    summary="Get current verification status",
)
def get_verification_status(
    user_id: str = Depends(require_user_id),
) -> VerificationStatusResponse:
    """查询当前用户的验证状态。"""
    user = user_service.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return VerificationStatusResponse(status=user.verification_status)
