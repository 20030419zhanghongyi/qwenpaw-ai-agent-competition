"""REST endpoints for database-backed POIs."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.contracts import NOT_FOUND_RESPONSE, UNPROCESSABLE_RESPONSE
from app.db.session import get_db

from .models import NearbyPoiResponse, PoiResponse
from .service import PoiNotFoundError, PoiService

router = APIRouter(prefix="/api/v1/pois", tags=["pois"])


@router.get(
    "",
    response_model=list[PoiResponse],
    summary="List POIs",
    description="List canonical POIs stored in PostgreSQL, optionally filtered by category.",
    responses=UNPROCESSABLE_RESPONSE,
)
def list_pois(
    database: Annotated[Session, Depends(get_db)],
    category: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=1000),
) -> list[PoiResponse]:
    return PoiService(database).list_pois(category=category, offset=offset, limit=limit)


@router.get(
    "/nearby",
    response_model=list[NearbyPoiResponse],
    summary="Find nearby POIs",
    description="Use PostGIS geography distance to find canonical POIs within a radius.",
    responses=UNPROCESSABLE_RESPONSE,
)
def nearby_pois(
    database: Annotated[Session, Depends(get_db)],
    longitude: float = Query(ge=-180, le=180),
    latitude: float = Query(ge=-90, le=90),
    radius_m: float = Query(default=1000, gt=0, le=100_000),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[NearbyPoiResponse]:
    return PoiService(database).nearby(
        longitude=longitude,
        latitude=latitude,
        radius_m=radius_m,
        limit=limit,
    )


@router.get(
    "/{poi_id}",
    response_model=PoiResponse,
    summary="Get a POI",
    responses=NOT_FOUND_RESPONSE,
)
def get_poi_detail(
    poi_id: str,
    database: Annotated[Session, Depends(get_db)],
) -> PoiResponse:
    try:
        return PoiService(database).get_poi(poi_id)
    except PoiNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
