"""极简 JWT 鉴权 + bcrypt 密码：签发 / 校验访问令牌 + 密码哈希。

仅做 token 编解码和密码哈希（不碰数据库），DB 侧「当前用户」解析放 features/users，
避免 core 反向依赖业务模块。密钥/算法/有效期来自 settings（.env）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

# Bearer 方案：auto_error=False 让依赖自行决定 401 时机与文案。
_bearer_scheme = HTTPBearer(auto_error=False)
AUTH_COOKIE_NAME = "macau_storywalk_session"


def _request_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    # An explicitly supplied, valid token identifies the intended API caller.
    # Browser requests restored from an HttpOnly session may still carry a
    # stale in-memory marker, so only let a valid Bearer token override cookie auth.
    if credentials is not None and credentials.scheme.lower() == "bearer":
        if decode_access_token(credentials.credentials) is not None:
            return credentials.credentials
    cookie_token = request.cookies.get(AUTH_COOKIE_NAME)
    if cookie_token:
        return cookie_token
    if credentials is not None and credentials.scheme.lower() == "bearer":
        return credentials.credentials
    return None


def create_access_token(user_id: str) -> str:
    """为 user_id 签发 JWT（HS256，有效期 jwt_expire_minutes，默认 7 天）。"""
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=settings.jwt_expire_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_access_token(token: str) -> str | None:
    """校验并返回 user_id；任何错误（过期/篡改/格式）一律返回 None。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) and sub else None


def require_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """FastAPI dependency: resolve a user from the session cookie or Bearer token."""
    token = _request_token(request, credentials)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing session")
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")
    return user_id


def optional_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str | None:
    """Return the authenticated user when supplied, while allowing guest requests."""
    token = _request_token(request, credentials)
    if token is None:
        return None
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")
    return user_id


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
