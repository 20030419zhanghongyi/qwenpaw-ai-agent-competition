"""REST endpoints for database-backed POIs."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.contracts import NOT_FOUND_RESPONSE, UNPROCESSABLE_RESPONSE
from app.db.session import get_db

from .models import NearbyPoiResponse, PoiResponse
from .service import PoiNotFoundError, PoiService
from .knowledge import get_knowledge_subgraph, get_operational_metadata

router = APIRouter(prefix="/api/v1/pois", tags=["pois"])


@router.get("/knowledge-graph", summary="Get the cultural knowledge subgraph for POIs")
def knowledge_graph(poi_ids: str = "") -> dict:
    return get_knowledge_subgraph([item for item in poi_ids.split(",") if item])


@router.get("/opening-hours", summary="Get fixed, source-verified opening schedules")
def opening_hours(poi_ids: str = "", language: str = "zh-CN") -> dict:
    """Return the versioned backend registry; this endpoint performs no live scraping."""
    return get_operational_metadata(
        [item for item in poi_ids.split(",") if item],
        language,
    )


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
    q: str | None = Query(default=None, min_length=1, max_length=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=1000),
) -> list[PoiResponse]:
    return PoiService(database).list_pois(category=category, query=q, offset=offset, limit=limit)


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
