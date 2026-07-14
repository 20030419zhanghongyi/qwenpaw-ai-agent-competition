"""用户注册/登录/偏好 请求与响应模型。

复用 app.models.user 的 UserProfile / Preference / SUPPORTED_LANGS，保持与
路线配对、讲解等模块同一份偏好定义。
"""

from pydantic import BaseModel

from app.models.user import Preference, UserProfile


class RegisterRequest(BaseModel):
    """注册：user_id 不填则后端生成（u_ 前缀）；语言默认简中。"""

    user_id: str | None = None
    name: str | None = None
    language: str = "zh-CN"


class LoginRequest(BaseModel):
    """极简登录：凭 user_id 换 token（demo 阶段不设密码，见 AI 伦理「最小必要」）。"""

    user_id: str


class AuthResponse(BaseModel):
    user_id: str
    token: str
    user: UserProfile


class LoginResponse(BaseModel):
    user_id: str
    token: str


class UserMutationResponse(BaseModel):
    status: str
    user_id: str


class UserDetailResponse(BaseModel):
    user: UserProfile | None


class PreferenceUpdateResponse(UserMutationResponse):
    preference: Preference
