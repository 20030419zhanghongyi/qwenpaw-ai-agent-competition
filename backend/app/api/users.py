from fastapi import APIRouter

from app.models.user import Preference, UserProfile

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# Phase 2 占位：内存返回。Phase 2 末接 Postgres + JWT 后替换。
_INMEMORY: dict[str, UserProfile] = {}


@router.post("")
def create_user(user: UserProfile) -> dict:
    _INMEMORY[user.user_id] = user
    return {"status": "ok", "user_id": user.user_id}


@router.get("/{user_id}")
def get_user(user_id: str) -> dict:
    user = _INMEMORY.get(user_id)
    return {"user": user.model_dump() if user else None}


@router.put("/{user_id}/preferences")
def update_preferences(user_id: str, pref: Preference) -> dict:
    """更新偏好，后续触发路线配对。"""
    if user_id in _INMEMORY:
        _INMEMORY[user_id].preference = pref
    else:
        _INMEMORY[user_id] = UserProfile(user_id=user_id, language=pref.language, preference=pref)
    return {"status": "ok", "user_id": user_id, "preference": pref.model_dump()}
