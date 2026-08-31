"""用户注册/登录/偏好 请求与响应模型。

复用 app.models.user 的 UserProfile / Preference / SUPPORTED_LANGS，保持与
路线配对、讲解等模块同一份偏好定义。
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.user import Preference, UserProfile


SECURITY_QUESTION_IDS = {
    "childhood_friend",
    "first_school",
    "favorite_place",
    "childhood_nickname",
}


def _validate_security_question(value: str) -> str:
    if value not in SECURITY_QUESTION_IDS:
        raise ValueError("unsupported security question")
    return value


class RegisterRequest(BaseModel):
    """注册：email 和手机至少填一个，密码必填，user_id 由后端自动生成，昵称必填。"""

    email: str | None = None
    phone: str | None = None
    password: str = Field(min_length=6)
    name: str
    language: str = "zh-CN"
    country: str | None = None
    security_question_id: str | None = None
    security_answer: str | None = Field(default=None, min_length=2, max_length=200)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value and value.strip() else None

    @field_validator("security_question_id")
    @classmethod
    def validate_security_question(cls, value: str | None) -> str | None:
        return _validate_security_question(value) if value is not None else None


class LoginRequest(BaseModel):
    """登录：凭 email/phone + 密码换 token。"""

    email: str | None = None
    phone: str | None = None
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value and value.strip() else None


class AuthResponse(BaseModel):
    user_id: str
    email: str | None = None
    phone: str | None = None
    token: str
    user: UserProfile


class LoginResponse(BaseModel):
    user_id: str
    email: str | None = None
    phone: str | None = None
    token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class SecurityQuestionUpdateRequest(BaseModel):
    current_password: str
    security_question_id: str
    security_answer: str = Field(min_length=2, max_length=200)

    @field_validator("security_question_id")
    @classmethod
    def validate_security_question(cls, value: str) -> str:
        return _validate_security_question(value)


class RecoveryQuestionRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class RecoveryQuestionResponse(BaseModel):
    security_question_id: str


class ResetPasswordRequest(RecoveryQuestionRequest):
    security_question_id: str
    security_answer: str = Field(min_length=2, max_length=200)
    new_password: str = Field(min_length=6)

    @field_validator("security_question_id")
    @classmethod
    def validate_security_question(cls, value: str) -> str:
        return _validate_security_question(value)


class SecurityQuestionStatusResponse(BaseModel):
    security_question_id: str | None = None


class UserMutationResponse(BaseModel):
    status: str
    user_id: str


class UserDetailResponse(BaseModel):
    user: UserProfile | None


class PreferenceUpdateResponse(UserMutationResponse):
    preference: Preference


class PreferenceMemoryResponse(BaseModel):
    """A privacy-minimised summary used for cross-session personalisation."""

    user_id: str
    memory: dict[str, Any]


# ── Verification (placeholder — needs cloud email/SMS service) ────────────

class SendVerificationRequest(BaseModel):
    """发送验证码：method = email 或 sms（需云服务支持）。"""

    method: str = "email"  # "email" | "sms"


class VerifyRequest(BaseModel):
    """验证码校验。"""

    code: str


class VerificationStatusResponse(BaseModel):
    status: str  # "unverified" | "pending" | "verified"
