"""HTTP endpoints for Demo trip state."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.contracts import NOT_FOUND_RESPONSE, UNPROCESSABLE_RESPONSE
from app.core.security import require_user_id

from .models import (
    CheckinRequest,
    ClaimGuestTripsRequest,
    ClaimGuestTripsResponse,
    LocationCheckinRequest,
    TripCreateRequest,
    TripProgressResponse,
    TripWithProgressResponse,
)
from .service import (
    InvalidRouteError,
    PoiNotInTripError,
    PoiTooFarError,
    RouteNotFoundError,
    TripNotFoundError,
    trip_service,
)

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])
user_router = APIRouter(prefix="/api/v1/users", tags=["trips"])


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, (TripNotFoundError, RouteNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, (InvalidRouteError, PoiNotInTripError, PoiTooFarError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    raise exc


@router.post(
    "",
    response_model=TripWithProgressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a trip",
    description=(
        "Create a persisted trip from a route template. "
        "Optional stop_poi_ids overrides template nodes with the constructed / adjusted walk order."
    ),
    responses={**NOT_FOUND_RESPONSE, **UNPROCESSABLE_RESPONSE},
)
def create_trip(request: TripCreateRequest) -> TripWithProgressResponse:
    try:
        return trip_service.create_trip(
            request.user_id, request.route_id, request.stop_poi_ids
        )
    except (RouteNotFoundError, InvalidRouteError) as exc:
        _raise_http_error(exc)


@router.get(
    "/{trip_id}",
    response_model=TripWithProgressResponse,
    summary="Get a trip",
    responses=NOT_FOUND_RESPONSE,
)
def get_trip(trip_id: str) -> TripWithProgressResponse:
    try:
        return trip_service.get_trip(trip_id)
    except TripNotFoundError as exc:
        _raise_http_error(exc)


@user_router.get(
    "/{user_id}/current-trip",
    response_model=TripWithProgressResponse,
    summary="Get the user's current trip",
    responses=NOT_FOUND_RESPONSE,
)
def get_current_trip(user_id: str) -> TripWithProgressResponse:
    try:
        return trip_service.get_current_trip(user_id)
    except TripNotFoundError as exc:
        _raise_http_error(exc)


@user_router.post(
    "/me/claim-guest-trips",
    response_model=ClaimGuestTripsResponse,
    summary="Move local guest trips into the authenticated account",
)
def claim_guest_trips(
    request: ClaimGuestTripsRequest,
    user_id: str = Depends(require_user_id),
) -> ClaimGuestTripsResponse:
    try:
        claimed = trip_service.claim_guest_trips(request.guest_user_id, user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return ClaimGuestTripsResponse(claimed_trips=claimed)


@router.post(
    "/{trip_id}/checkins",
    response_model=TripWithProgressResponse,
    summary="Check in at a trip stop",
    responses={**NOT_FOUND_RESPONSE, **UNPROCESSABLE_RESPONSE},
)
def check_in(trip_id: str, request: CheckinRequest) -> TripWithProgressResponse:
    try:
        return trip_service.check_in(trip_id, request.poi_id)
    except (TripNotFoundError, PoiNotInTripError) as exc:
        _raise_http_error(exc)


@router.post(
    "/{trip_id}/location-checkins",
    response_model=TripWithProgressResponse,
    summary="Check in after a current GPS proximity check",
    responses={**NOT_FOUND_RESPONSE, **UNPROCESSABLE_RESPONSE},
)
def check_in_at_location(
    trip_id: str, request: LocationCheckinRequest
) -> TripWithProgressResponse:
    try:
        return trip_service.check_in_at_location(
            trip_id,
            request.poi_id,
            longitude=request.longitude,
            latitude=request.latitude,
            radius_m=request.radius_m,
            accuracy_m=request.accuracy_m,
        )
    except (TripNotFoundError, PoiNotInTripError, PoiTooFarError) as exc:
        _raise_http_error(exc)


@router.get(
    "/{trip_id}/progress",
    response_model=TripProgressResponse,
    summary="Get trip progress",
    responses=NOT_FOUND_RESPONSE,
)
def get_progress(trip_id: str) -> TripProgressResponse:
    try:
        progress = trip_service.get_progress(trip_id)
        return TripProgressResponse.model_validate(progress.model_dump())
    except TripNotFoundError as exc:
        _raise_http_error(exc)
