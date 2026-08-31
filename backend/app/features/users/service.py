"""用户注册/登录/查询/偏好 业务规则。"""

import time
from random import randint

from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import SUPPORTED_LANGS, Preference, UserProfile

from .repository import SqlAlchemyUserRepository, user_repository


class UserAlreadyExistsError(LookupError):
    pass


class EmailAlreadyExistsError(UserAlreadyExistsError):
    pass


class PhoneAlreadyExistsError(UserAlreadyExistsError):
    pass


class UserNotFoundError(LookupError):
    pass


class IncorrectPasswordError(LookupError):
    pass


class EmailOrPhoneRequiredError(ValueError):
    pass


class InvalidLanguageError(ValueError):
    pass


class InvalidSecurityQuestionError(ValueError):
    pass


class RecoveryUnavailableError(LookupError):
    pass


class IncorrectSecurityAnswerError(ValueError):
    pass


def _normalize_security_answer(answer: str) -> str:
    return " ".join(answer.strip().casefold().split())


def _new_user_id() -> str:
    """生成纯数字用户 ID（类似 QQ 号）：时间戳后 10 位 + 4 位随机数。"""
    ts_part = str(int(time.time() * 1000))[-10:]
    rand_part = f"{randint(0, 9999):04d}"
    return f"{ts_part}{rand_part}"


class UserService:
    def __init__(self, repository: SqlAlchemyUserRepository) -> None:
        self._repository = repository

    def register(self, name: str, language: str, password: str, email: str | None = None, phone: str | None = None, country: str | None = None, security_question_id: str | None = None, security_answer: str | None = None) -> tuple[UserProfile, str]:
        if language not in SUPPORTED_LANGS:
            raise InvalidLanguageError(f"language must be one of {SUPPORTED_LANGS}, got {language!r}")
        if not email and not phone:
            raise EmailOrPhoneRequiredError("email or phone is required")
        if email and self._repository.exists_by_email(email):
            raise EmailAlreadyExistsError("email already registered")
        if phone and self._repository.find_by_phone(phone):
            raise PhoneAlreadyExistsError("phone already registered")
        if bool(security_question_id) != bool(security_answer and security_answer.strip()):
            raise InvalidSecurityQuestionError(
                "security question and answer must be provided together"
            )
        uid = _new_user_id()
        password_hash = hash_password(password)
        security_answer_hash = (
            hash_password(_normalize_security_answer(security_answer))
            if security_answer
            else None
        )
        try:
            user = self._repository.create(
                uid,
                name,
                language,
                email=email,
                phone=phone,
                country=country,
                password_hash=password_hash,
                security_question_id=security_question_id,
                security_answer_hash=security_answer_hash,
            )
        except IntegrityError as exc:
            # The database unique constraints are the final guard if two registrations race.
            if email and self._repository.exists_by_email(email):
                raise EmailAlreadyExistsError("email already registered") from exc
            if phone and self._repository.find_by_phone(phone):
                raise PhoneAlreadyExistsError("phone already registered") from exc
            raise
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

    def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        raw = self._repository._get_raw(user_id)
        if raw is None:
            raise UserNotFoundError(user_id)
        if raw.password_hash is None or not verify_password(current_password, raw.password_hash):
            raise IncorrectPasswordError("incorrect password")
        self._repository.update_password(user_id, hash_password(new_password))

    def get_security_question(self, user_id: str) -> str | None:
        raw = self._repository._get_raw(user_id)
        if raw is None:
            raise UserNotFoundError(user_id)
        return raw.security_question_id

    def update_security_question(
        self, user_id: str, current_password: str, question_id: str, answer: str
    ) -> None:
        raw = self._repository._get_raw(user_id)
        if raw is None:
            raise UserNotFoundError(user_id)
        if raw.password_hash is None or not verify_password(current_password, raw.password_hash):
            raise IncorrectPasswordError("incorrect password")
        answer_hash = hash_password(_normalize_security_answer(answer))
        self._repository.update_security_question(user_id, question_id, answer_hash)

    def get_recovery_question(self, email: str) -> str:
        user = self._repository.find_by_email(email)
        if user is None:
            raise RecoveryUnavailableError("recovery unavailable")
        raw = self._repository._get_raw(user.user_id)
        if raw is None or not raw.security_question_id or not raw.security_answer_hash:
            raise RecoveryUnavailableError("recovery unavailable")
        return raw.security_question_id

    def reset_password_with_security_answer(
        self, email: str, question_id: str, answer: str, new_password: str
    ) -> None:
        user = self._repository.find_by_email(email)
        if user is None:
            raise RecoveryUnavailableError("recovery unavailable")
        raw = self._repository._get_raw(user.user_id)
        if raw is None or not raw.security_question_id or not raw.security_answer_hash:
            raise RecoveryUnavailableError("recovery unavailable")
        answer_matches = verify_password(
            _normalize_security_answer(answer), raw.security_answer_hash
        )
        if raw.security_question_id != question_id or not answer_matches:
            raise IncorrectSecurityAnswerError("invalid recovery answer")
        self._repository.update_password(user.user_id, hash_password(new_password))

    def get_preference_memory(self, user_id: str) -> dict:
        return self._repository.get_preference_memory(user_id)

    def update_preference(self, user_id: str, preference: Preference) -> UserProfile:
        if preference.language not in SUPPORTED_LANGS:
            raise InvalidLanguageError(f"language must be one of {SUPPORTED_LANGS}")
        return self._repository.upsert_preference(user_id, preference)


user_service = UserService(user_repository)
