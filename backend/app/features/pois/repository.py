"""SQLAlchemy queries for PostGIS-backed POIs."""

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.db.models import Poi

from .models import NearbyPoiResponse, PoiResponse


class PoiRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_response(record: Poi) -> PoiResponse:
        return PoiResponse(
            poi_id=record.poi_id,
            poi_name=record.poi_name,
            alias=record.alias,
            address=record.address,
            longitude=record.longitude,
            latitude=record.latitude,
            category=record.category,
            source=record.source,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def list_pois(
        self,
        *,
        category: str | None,
        offset: int,
        limit: int,
    ) -> list[PoiResponse]:
        statement = select(Poi).order_by(Poi.poi_id).offset(offset).limit(limit)
        if category:
            statement = statement.where(Poi.category == category)
        return [self._to_response(record) for record in self._session.scalars(statement)]

    def get_poi(self, poi_id: str) -> PoiResponse | None:
        record = self._session.get(Poi, poi_id)
        return self._to_response(record) if record is not None else None

    def nearby(
        self,
        *,
        longitude: float,
        latitude: float,
        radius_m: float,
        limit: int,
    ) -> list[NearbyPoiResponse]:
        point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
        geography = Geography(geometry_type="POINT", srid=4326)
        poi_geography = cast(Poi.location, geography)
        point_geography = cast(point, geography)
        distance = func.ST_Distance(poi_geography, point_geography).label("distance_m")
        statement = (
            select(Poi, distance)
            .where(func.ST_DWithin(poi_geography, point_geography, radius_m))
            .order_by(distance, Poi.poi_id)
            .limit(limit)
        )
        return [
            NearbyPoiResponse(
                **self._to_response(record).model_dump(),
                distance_m=float(distance_m),
            )
            for record, distance_m in self._session.execute(statement)
        ]
