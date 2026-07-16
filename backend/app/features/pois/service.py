"""POI query application service."""

from sqlalchemy.orm import Session

from .models import NearbyPoiResponse, PoiResponse
from .repository import PoiRepository


class PoiNotFoundError(LookupError):
    pass


class PoiService:
    def __init__(self, session: Session) -> None:
        self._repository = PoiRepository(session)

    def list_pois(
        self,
        *,
        category: str | None,
        query: str | None,
        offset: int,
        limit: int,
    ) -> list[PoiResponse]:
        return self._repository.list_pois(category=category, query=query, offset=offset, limit=limit)

    def get_poi(self, poi_id: str) -> PoiResponse:
        poi = self._repository.get_by_id(poi_id)
        if poi is None:
            raise PoiNotFoundError(f"POI not found: {poi_id}")
        return poi

    def nearby(
        self,
        *,
        longitude: float,
        latitude: float,
        radius_m: float,
        limit: int,
    ) -> list[NearbyPoiResponse]:
        return self._repository.nearby(
            longitude=longitude,
            latitude=latitude,
            radius_m=radius_m,
            limit=limit,
        )
