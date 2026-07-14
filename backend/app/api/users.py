"""Demo user preference endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.models.user import Preference, UserProfile

router = APIRouter(prefix="/api/v1/users", tags=["users"])
_INMEMORY: dict[str, UserProfile] = {}


class UserMutationResponse(BaseModel):
    status: str
    user_id: str


class UserDetailResponse(BaseModel):
    user: UserProfile | None


class PreferenceUpdateResponse(UserMutationResponse):
    preference: Preference


@router.post("", response_model=UserMutationResponse, summary="Create a demo user")
def create_user(user: UserProfile) -> UserMutationResponse:
    _INMEMORY[user.user_id] = user
    return UserMutationResponse(status="ok", user_id=user.user_id)


@router.get(
    "/{user_id}", response_model=UserDetailResponse, summary="Get a demo user"
)
def get_user(user_id: str) -> UserDetailResponse:
    return UserDetailResponse(user=_INMEMORY.get(user_id))


@router.put(
    "/{user_id}/preferences",
    response_model=PreferenceUpdateResponse,
    summary="Update demo user preferences",
)
def update_preferences(user_id: str, pref: Preference) -> PreferenceUpdateResponse:
    if user_id in _INMEMORY:
        _INMEMORY[user_id].preference = pref
    else:
        _INMEMORY[user_id] = UserProfile(
            user_id=user_id,
            language=pref.language,
            preference=pref,
        )
    return PreferenceUpdateResponse(status="ok", user_id=user_id, preference=pref)
