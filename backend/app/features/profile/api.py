"""HTTP endpoints for the personal profile MVP."""

from typing import NoReturn

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.contracts import CONFLICT_RESPONSE, NOT_FOUND_RESPONSE, UNPROCESSABLE_RESPONSE
from app.features.trips.models import TripStatus

from .models import (
    FavoritePoiResponse,
    HistoryTripResponse,
    TripFeedback,
    TripFeedbackRequest,
)
from .service import (
    FeedbackNotFoundError,
    PoiNotFoundError,
    TripNotCompletedError,
    TripNotFoundError,
    TripUserMismatchError,
    profile_service,
)

user_router = APIRouter(prefix="/api/v1/users", tags=["profile"])
trip_router = APIRouter(prefix="/api/v1/trips", tags=["profile"])


def _raise_http_error(exc: Exception) -> NoReturn:
    if isinstance(exc, (PoiNotFoundError, TripNotFoundError, FeedbackNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, TripUserMismatchError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if isinstance(exc, TripNotCompletedError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@user_router.get(
    "/{user_id}/trips",
    response_model=list[HistoryTripResponse],
    summary="List trip history",
    responses=UNPROCESSABLE_RESPONSE,
)
def list_trip_history(
    user_id: str,
    status_filter: TripStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[HistoryTripResponse]:
    return profile_service.list_trip_history(user_id, status_filter, limit)


@user_router.post(
    "/{user_id}/favorites/pois/{poi_id}",
    response_model=FavoritePoiResponse,
    summary="Add a favorite POI",
    responses=NOT_FOUND_RESPONSE,
)
def add_favorite(user_id: str, poi_id: str, response: Response) -> FavoritePoiResponse:
    try:
        favorite, created = profile_service.add_favorite(user_id, poi_id)
    except PoiNotFoundError as exc:
        _raise_http_error(exc)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return favorite


@user_router.delete(
    "/{user_id}/favorites/pois/{poi_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a favorite POI",
)
def remove_favorite(user_id: str, poi_id: str) -> Response:
    profile_service.remove_favorite(user_id, poi_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@user_router.get(
    "/{user_id}/favorites/pois",
    response_model=list[FavoritePoiResponse],
    summary="List favorite POIs",
)
def list_favorites(user_id: str) -> list[FavoritePoiResponse]:
    return profile_service.list_favorites(user_id)


@trip_router.post(
    "/{trip_id}/feedback",
    response_model=TripFeedback,
    summary="Create or update trip feedback",
    responses={
        **NOT_FOUND_RESPONSE,
        **CONFLICT_RESPONSE,
        **UNPROCESSABLE_RESPONSE,
        403: {"description": "The trip belongs to a different user."},
    },
)
def upsert_feedback(
    trip_id: str,
    request: TripFeedbackRequest,
    response: Response,
) -> TripFeedback:
    try:
        feedback, created = profile_service.upsert_feedback(trip_id, request)
    except (TripNotFoundError, TripUserMismatchError, TripNotCompletedError) as exc:
        _raise_http_error(exc)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return feedback


@trip_router.get(
    "/{trip_id}/feedback",
    response_model=TripFeedback,
    summary="Get trip feedback",
    responses=NOT_FOUND_RESPONSE,
)
def get_feedback(trip_id: str) -> TripFeedback:
    try:
        return profile_service.get_feedback(trip_id)
    except (TripNotFoundError, FeedbackNotFoundError) as exc:
        _raise_http_error(exc)
