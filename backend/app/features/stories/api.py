"""HTTP API for the minimal story-route experience."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.contracts import CONFLICT_RESPONSE, NOT_FOUND_RESPONSE, UNPROCESSABLE_RESPONSE
from app.core.security import require_user_id
from app.features.trips.service import InvalidRouteError, RouteNotFoundError
from app.guardrails.runtime import rate_limit

from .content import StoryContentError, StoryNotFoundError
from .engine import InvalidStoryActionError, StoryChapterConflictError
from .future_letter import (
    FutureLetterConflictError,
    FutureLetterNotFoundError,
    FutureLetterUnavailableError,
    future_letter_service,
)
from .models import (
    FutureLetterResponse,
    StoryActionRequest,
    StoryActionResponse,
    StorySessionResponse,
)
from .service import (
    StoryContentVersionError,
    StorySessionNotFoundError,
    StorySessionOwnershipError,
    story_service,
)

story_router = APIRouter(prefix="/api/v1/stories", tags=["stories"])
session_router = APIRouter(prefix="/api/v1/story-sessions", tags=["stories"])


def _raise_http_error(exc: Exception) -> None:
    if isinstance(
        exc,
        (
            StoryNotFoundError,
            StorySessionNotFoundError,
            RouteNotFoundError,
            FutureLetterNotFoundError,
        ),
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(
        exc,
        (
            StoryChapterConflictError,
            StoryContentVersionError,
            FutureLetterConflictError,
        ),
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if isinstance(exc, FutureLetterUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    if isinstance(exc, StorySessionOwnershipError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, (StoryContentError, InvalidStoryActionError, InvalidRouteError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    raise exc


@story_router.get(
    "/{story_id}",
    response_model=dict[str, Any],
    summary="Get public story content",
    responses={**NOT_FOUND_RESPONSE, **UNPROCESSABLE_RESPONSE},
)
def get_story(
    story_id: str,
    language: str = Query(default="zh-CN", description="Story display language"),
) -> dict[str, Any]:
    try:
        return story_service.get_story(story_id, language=language)
    except (StoryNotFoundError, StoryContentError) as exc:
        _raise_http_error(exc)


@story_router.post(
    "/{story_id}/sessions",
    response_model=StorySessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start or resume a story",
    responses={**NOT_FOUND_RESPONSE, **UNPROCESSABLE_RESPONSE},
)
def start_story(
    story_id: str,
    language: str = Query(default="zh-CN", description="Story display language"),
    user_id: str = Depends(require_user_id),
) -> StorySessionResponse:
    try:
        return story_service.start(story_id, user_id, language=language)
    except (StoryNotFoundError, StoryContentError, RouteNotFoundError, InvalidRouteError) as exc:
        _raise_http_error(exc)


@session_router.get(
    "/{session_id}",
    response_model=StorySessionResponse,
    summary="Restore a story session",
    responses={**NOT_FOUND_RESPONSE, **UNPROCESSABLE_RESPONSE},
)
def get_session(
    session_id: str,
    language: str = Query(default="zh-CN", description="Story display language"),
    user_id: str = Depends(require_user_id),
) -> StorySessionResponse:
    try:
        return story_service.get_session(session_id, user_id, language=language)
    except (
        StorySessionNotFoundError,
        StorySessionOwnershipError,
        StoryNotFoundError,
        StoryContentError,
        StoryContentVersionError,
    ) as exc:
        _raise_http_error(exc)


@session_router.post(
    "/{session_id}/actions",
    response_model=StoryActionResponse,
    summary="Apply one story action",
    responses={**NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE, **UNPROCESSABLE_RESPONSE},
)
def act(
    session_id: str,
    request: StoryActionRequest,
    language: str = Query(default="zh-CN", description="Story display language"),
    user_id: str = Depends(require_user_id),
) -> StoryActionResponse:
    try:
        return story_service.act(session_id, user_id, request, language=language)
    except (
        StorySessionNotFoundError,
        StoryNotFoundError,
        StoryContentError,
        InvalidStoryActionError,
        StoryChapterConflictError,
        StoryContentVersionError,
        StorySessionOwnershipError,
    ) as exc:
        _raise_http_error(exc)


@session_router.get(
    "/{session_id}/future-letter",
    response_model=FutureLetterResponse,
    summary="Get the optional Taipa future-letter artwork",
    responses={**NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
)
def get_future_letter(
    session_id: str,
    user_id: str = Depends(require_user_id),
) -> FutureLetterResponse:
    try:
        return future_letter_service.get(session_id, user_id)
    except (
        StorySessionNotFoundError,
        StorySessionOwnershipError,
        StoryContentVersionError,
        FutureLetterNotFoundError,
        FutureLetterConflictError,
    ) as exc:
        _raise_http_error(exc)


@session_router.post(
    "/{session_id}/future-letter",
    response_model=FutureLetterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("expensive"))],
    summary="Generate the optional Taipa future-letter artwork",
    responses={**NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
)
def generate_future_letter(
    session_id: str,
    user_id: str = Depends(require_user_id),
) -> FutureLetterResponse:
    try:
        return future_letter_service.generate(session_id, user_id)
    except (
        StorySessionNotFoundError,
        StorySessionOwnershipError,
        StoryContentVersionError,
        FutureLetterConflictError,
        FutureLetterUnavailableError,
    ) as exc:
        _raise_http_error(exc)


@session_router.get(
    "/{session_id}/future-letter/image",
    summary="Fetch the authenticated Taipa future-letter SVG",
    responses={**NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
)
def future_letter_image(
    session_id: str,
    user_id: str = Depends(require_user_id),
) -> Response:
    try:
        return Response(
            content=future_letter_service.image(session_id, user_id),
            media_type="image/svg+xml",
            headers={"Cache-Control": "private, max-age=86400"},
        )
    except (
        StorySessionNotFoundError,
        StorySessionOwnershipError,
        StoryContentVersionError,
        FutureLetterNotFoundError,
        FutureLetterConflictError,
    ) as exc:
        _raise_http_error(exc)
