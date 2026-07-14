"""PostgreSQL 持久化：用户 + 偏好。

偏好以整体 JSON 存 users.preference（迁移 20260714_01），避免逐字段映射 ORM；
top-level language 与 preference.language 保持同步，方便其它模块直接读 user.language。
"""

from collections.abc import Callable
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
            name=record.name,
            language=record.language or "zh-CN",
            preference=preference,
        )

    def get(self, user_id: str) -> UserProfile | None:
        with self._session_factory() as session:
            record = session.get(UserRecord, user_id)
            return self._to_domain(record) if record is not None else None

    def exists(self, user_id: str) -> bool:
        with self._session_factory() as session:
            return session.get(UserRecord, user_id) is not None

    def create(self, user_id: str, name: str | None, language: str) -> UserProfile:
        with self._session_factory() as session:
            record = UserRecord(
                id=user_id,
                name=name,
                language=language,
                interests=[],
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
                record = UserRecord(id=user_id, interests=[])
                session.add(record)
            record.preference = pref_dict
            record.language = preference.language  # 顶层语言与偏好同步
            session.commit()
            result = self._to_domain(record)
        if created:
            with self._created_ids_lock:
                self._created_user_ids.add(user_id)
        return result

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
