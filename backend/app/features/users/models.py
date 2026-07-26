"""用户注册/登录/偏好 请求与响应模型。

复用 app.models.user 的 UserProfile / Preference / SUPPORTED_LANGS，保持与
路线配对、讲解等模块同一份偏好定义。
"""

from pydantic import BaseModel

from app.models.user import Preference, UserProfile


class RegisterRequest(BaseModel):
    """注册：email 和手机至少填一个，密码必填，user_id 由后端自动生成，昵称必填。"""

    email: str | None = None
    phone: str | None = None
    password: str
    name: str
    language: str = "zh-CN"
    country: str | None = None


class LoginRequest(BaseModel):
    """登录：凭 email/phone + 密码换 token。"""

    email: str | None = None
    phone: str | None = None
    password: str


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


class UserMutationResponse(BaseModel):
    status: str
    user_id: str


class UserDetailResponse(BaseModel):
    user: UserProfile | None


class PreferenceUpdateResponse(UserMutationResponse):
    preference: Preference


# ── Verification (placeholder — needs cloud email/SMS service) ────────────

class SendVerificationRequest(BaseModel):
    """发送验证码：method = email 或 sms（需云服务支持）。"""

    method: str = "email"  # "email" | "sms"


class VerifyRequest(BaseModel):
    """验证码校验。"""

    code: str


class VerificationStatusResponse(BaseModel):
    status: str  # "unverified" | "pending" | "verified"
