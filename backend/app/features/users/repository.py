"""PostgreSQL 持久化：用户 + 偏好。

偏好以整体 JSON 存 users.preference（迁移 20260714_01），避免逐字段映射 ORM；
top-level language 与 preference.language 保持同步，方便其它模块直接读 user.language。
"""

from collections.abc import Callable
from datetime import datetime, timezone
from threading import RLock

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User as UserRecord
from app.db.session import SessionLocal
from app.models.user import Preference, UserProfile


class SqlAlchemyUserRepository:
    """用户表 CRUD，对外暴露既有 UserProfile 领域模型。"""

    def __init__(self, session_factory: Callable[[], Session] = SessionLocal) -> None:
        self._session_factory = session_factory
        self._created_user_ids: set[str] = set()
        self._created_ids_lock = RLock()

    @staticmethod
    def _to_domain(record: UserRecord) -> UserProfile:
        preference: Preference | None = None
        if record.preference:
            try:
                preference = Preference(**record.preference)
            except Exception:
                preference = None
        return UserProfile(
            user_id=record.id,
            email=record.email,
            phone=record.phone,
            name=record.name,
            language=record.language or "zh-CN",
            country=record.country,
            verification_status=record.verification_status or "unverified",
            preference=preference,
            preference_memory=record.preference_memory,
        )

    def get(self, user_id: str) -> UserProfile | None:
        with self._session_factory() as session:
            record = session.get(UserRecord, user_id)
            return self._to_domain(record) if record is not None else None

    def _get_raw(self, user_id: str) -> UserRecord | None:
        """Return raw ORM record (needed for password_hash access)."""
        with self._session_factory() as session:
            return session.get(UserRecord, user_id)

    def find_by_email(self, email: str) -> UserProfile | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(UserRecord).where(UserRecord.email == email)
            )
            return self._to_domain(record) if record is not None else None

    def find_by_phone(self, phone: str) -> UserProfile | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(UserRecord).where(UserRecord.phone == phone)
            )
            return self._to_domain(record) if record is not None else None

    def exists_by_email(self, email: str) -> bool:
        return self.find_by_email(email) is not None

    def exists(self, user_id: str) -> bool:
        with self._session_factory() as session:
            return session.get(UserRecord, user_id) is not None

    def create(self, user_id: str, name: str, language: str, email: str | None = None, phone: str | None = None, country: str | None = None, password_hash: str | None = None) -> UserProfile:
        with self._session_factory() as session:
            record = UserRecord(
                id=user_id,
                email=email,
                phone=phone,
                name=name,
                language=language,
                country=country,
                password_hash=password_hash,
                interests=[],
                preference_memory=_empty_memory(),
            )
            session.add(record)
            session.commit()
            result = self._to_domain(record)
        with self._created_ids_lock:
            self._created_user_ids.add(user_id)
        return result

    def upsert_preference(self, user_id: str, preference: Preference) -> UserProfile:
        """写偏好；用户不存在则顺带创建（保留旧 PUT /preferences 的 upsert 语义）。"""
        pref_dict = preference.model_dump()
        with self._session_factory() as session:
            record = session.get(UserRecord, user_id)
            created = record is None
            if record is None:
                record = UserRecord(
                    id=user_id,
                    email=f"auto_{user_id}@placeholder.local",
                    name="未命名用户",
                    interests=[],
                    preference_memory=_empty_memory(),
                )
                session.add(record)
            record.preference = pref_dict
            record.language = preference.language  # 顶层语言与偏好同步
            record.preference_memory = _record_preference(record.preference_memory, preference)
            session.commit()
            result = self._to_domain(record)
        if created:
            with self._created_ids_lock:
                self._created_user_ids.add(user_id)
        return result

    def get_preference_memory(self, user_id: str) -> dict:
        with self._session_factory() as session:
            record = session.get(UserRecord, user_id)
            return dict(record.preference_memory or _empty_memory()) if record else _empty_memory()

    def record_trip_memory(self, user_id: str, route_id: str) -> None:
        with self._session_factory() as session:
            record = session.get(UserRecord, user_id)
            if record is None:
                return
            memory = dict(record.preference_memory or _empty_memory())
            routes = list(memory.get("route_history") or [])
            routes.append({"route_id": route_id, "created_at": _now_iso()})
            memory["route_history"] = routes[-12:]
            memory["updated_at"] = _now_iso()
            record.preference_memory = memory
            session.commit()

    def record_feedback_memory(
        self, user_id: str, trip_id: str, rating: int, walking_comfortable: bool | None
    ) -> None:
        with self._session_factory() as session:
            record = session.get(UserRecord, user_id)
            if record is None:
                return
            memory = dict(record.preference_memory or _empty_memory())
            feedback = dict(memory.get("feedback_by_trip") or {})
            feedback[trip_id] = {"rating": rating, "walking_comfortable": walking_comfortable}
            memory["feedback_by_trip"] = feedback
            memory["updated_at"] = _now_iso()
            record.preference_memory = memory
            session.commit()

    def list_all(self) -> list[UserProfile]:
        with self._session_factory() as session:
            records = session.scalars(select(UserRecord).order_by(UserRecord.created_at.desc())).all()
            return [self._to_domain(record) for record in records]

    def delete(self, user_id: str) -> bool:
        with self._session_factory() as session:
            record = session.get(UserRecord, user_id)
            if record is None:
                return False
            session.delete(record)
            session.commit()
        with self._created_ids_lock:
            self._created_user_ids.discard(user_id)
        return True

    def clear(self) -> None:
        """仅删除本 repository 进程内创建的用户行（测试清理用）。"""
        with self._created_ids_lock:
            ids = set(self._created_user_ids)
            self._created_user_ids.clear()
        if not ids:
            return
        with self._session_factory() as session:
            for user_id in ids:
                record = session.get(UserRecord, user_id)
                if record is not None:
                    session.delete(record)
            session.commit()


user_repository = SqlAlchemyUserRepository()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_memory() -> dict:
    return {
        "version": 1,
        "updated_at": None,
        "preference_updates": 0,
        "signal_counts": {"themes": {}, "interests": {}, "physical": {}, "durations": {}, "languages": {}},
        "latest_preference": {},
        "route_history": [],
        "feedback_by_trip": {},
    }


def _increment(counts: dict, values: list[str]) -> None:
    for value in values:
        if value:
            counts[value] = int(counts.get(value, 0)) + 1


def _record_preference(memory: dict | None, preference: Preference) -> dict:
    result = dict(memory or _empty_memory())
    signal_counts = dict(result.get("signal_counts") or {})
    for key, values in {
        "themes": preference.themes,
        "interests": preference.interests,
        "physical": preference.physical,
        "durations": [preference.duration],
        "languages": [preference.language],
    }.items():
        counts = dict(signal_counts.get(key) or {})
        _increment(counts, values)
        signal_counts[key] = counts
    result["signal_counts"] = signal_counts
    result["preference_updates"] = int(result.get("preference_updates", 0)) + 1
    result["latest_preference"] = preference.model_dump(exclude={"travel_date"})
    result["updated_at"] = _now_iso()
    return result
