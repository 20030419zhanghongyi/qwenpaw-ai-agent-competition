"""用户注册/登录/查询/偏好 业务规则。"""

import time
from random import randint

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import SUPPORTED_LANGS, Preference, UserProfile

from .repository import SqlAlchemyUserRepository, user_repository


class UserAlreadyExistsError(LookupError):
    pass


class UserNotFoundError(LookupError):
    pass


class IncorrectPasswordError(LookupError):
    pass


class EmailOrPhoneRequiredError(ValueError):
    pass


class InvalidLanguageError(ValueError):
    pass


def _new_user_id() -> str:
    """生成纯数字用户 ID（类似 QQ 号）：时间戳后 10 位 + 4 位随机数。"""
    ts_part = str(int(time.time() * 1000))[-10:]
    rand_part = f"{randint(0, 9999):04d}"
    return f"{ts_part}{rand_part}"


class UserService:
    def __init__(self, repository: SqlAlchemyUserRepository) -> None:
        self._repository = repository

    def register(self, name: str, language: str, password: str, email: str | None = None, phone: str | None = None, country: str | None = None) -> tuple[UserProfile, str]:
        if language not in SUPPORTED_LANGS:
            raise InvalidLanguageError(f"language must be one of {SUPPORTED_LANGS}, got {language!r}")
        if not email and not phone:
            raise EmailOrPhoneRequiredError("email or phone is required")
        if email and self._repository.exists_by_email(email):
            raise UserAlreadyExistsError(f"email {email} already registered")
        if phone and self._repository.find_by_phone(phone):
            raise UserAlreadyExistsError(f"phone {phone} already registered")
        uid = _new_user_id()
        password_hash = hash_password(password)
        user = self._repository.create(uid, name, language, email=email, phone=phone, country=country, password_hash=password_hash)
        token = create_access_token(uid)
        return user, token

    def login(self, password: str, email: str | None = None, phone: str | None = None) -> tuple[UserProfile, str]:
        if not email and not phone:
            raise EmailOrPhoneRequiredError("email or phone is required")
        user = None
        if email:
            user = self._repository.find_by_email(email)
        if user is None and phone:
            user = self._repository.find_by_phone(phone)
        if user is None:
            raise UserNotFoundError(email or phone or "unknown")
        # Verify password — need raw record for the hash
        raw = self._repository._get_raw(user.user_id)
        if raw is None or raw.password_hash is None or not verify_password(password, raw.password_hash):
            raise IncorrectPasswordError("incorrect password")
        token = create_access_token(user.user_id)
        return user, token

    def get(self, user_id: str) -> UserProfile | None:
        return self._repository.get(user_id)

    def get_preference_memory(self, user_id: str) -> dict:
        return self._repository.get_preference_memory(user_id)

    def update_preference(self, user_id: str, preference: Preference) -> UserProfile:
        if preference.language not in SUPPORTED_LANGS:
            raise InvalidLanguageError(f"language must be one of {SUPPORTED_LANGS}")
        return self._repository.upsert_preference(user_id, preference)


user_service = UserService(user_repository)
