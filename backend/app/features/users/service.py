"""用户注册/登录/查询/偏好 业务规则。"""

from uuid import uuid4

from app.core.security import create_access_token
from app.models.user import SUPPORTED_LANGS, Preference, UserProfile

from .repository import SqlAlchemyUserRepository, user_repository


class UserAlreadyExistsError(LookupError):
    pass


class UserNotFoundError(LookupError):
    pass


class InvalidLanguageError(ValueError):
    pass


def _new_user_id() -> str:
    return f"u_{uuid4().hex[:16]}"


class UserService:
    def __init__(self, repository: SqlAlchemyUserRepository) -> None:
        self._repository = repository

    def register(self, user_id: str | None, name: str | None, language: str) -> tuple[UserProfile, str]:
        if language not in SUPPORTED_LANGS:
            raise InvalidLanguageError(f"language must be one of {SUPPORTED_LANGS}, got {language!r}")
        uid = user_id or _new_user_id()
        if self._repository.exists(uid):
            raise UserAlreadyExistsError(uid)
        user = self._repository.create(uid, name, language)
        token = create_access_token(uid)
        return user, token

    def login(self, user_id: str) -> tuple[UserProfile, str]:
        user = self._repository.get(user_id)
        if user is None:
            raise UserNotFoundError(user_id)
        token = create_access_token(user_id)
        return user, token

    def get(self, user_id: str) -> UserProfile | None:
        return self._repository.get(user_id)

    def update_preference(self, user_id: str, preference: Preference) -> UserProfile:
        if preference.language not in SUPPORTED_LANGS:
            raise InvalidLanguageError(f"language must be one of {SUPPORTED_LANGS}")
        return self._repository.upsert_preference(user_id, preference)


user_service = UserService(user_repository)
