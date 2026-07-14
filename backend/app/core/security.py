"""极简 JWT 鉴权：签发 / 校验访问令牌。

仅做 token 编解码（不碰数据库），DB 侧「当前用户」解析放 features/users，
避免 core 反向依赖业务模块。密钥/算法/有效期来自 settings（.env）。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

# Bearer 方案：auto_error=False 让依赖自行决定 401 时机与文案。
_bearer_scheme = HTTPBearer(auto_error=False)


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
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """FastAPI 依赖：从 Bearer token 解出 user_id；缺失/无效 → 401。"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")
    return user_id
