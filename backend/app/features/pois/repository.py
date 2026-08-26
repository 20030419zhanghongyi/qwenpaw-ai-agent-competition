"""SQLAlchemy queries for PostGIS-backed POIs."""

from geoalchemy2 import Geography
from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Poi

from .models import NearbyPoiResponse, PoiResponse
from .knowledge import get_poi_summary

# Route templates and existing clients still expose these stable business IDs.
# The mapping is identifier compatibility only; all POI content is read from PostgreSQL.
LEGACY_POI_IDS = {
    "poi_ama": "poi_0011",
    "poi_carmo": "poi_0098",
    "poi_cathedral": "poi_0054",
    "poi_coloane_chapel": "poi_0234",
    "poi_coloane_pier": "poi_0238",
    "poi_dom_pedro_v": "poi_0051",
    "poi_eanes_square": "poi_0241",
    "poi_fatong": "poi_0018",
    "poi_florindo": "poi_0016",
    "poi_holy_house_mercy": "poi_0055",
    "poi_ho_tung_library": "poi_0129",
    "poi_leal_senado": "poi_0056",
    "poi_lilau": "poi_0017",
    "poi_lou_kau": "poi_0057",
    "poi_mandarin_house": "poi_0015",
    "poi_moorish_barracks": "poi_0170",
    "poi_mount_fortress": "poi_0003",
    "poi_na_tcha": "poi_0049",
    "poi_old_city_walls": "poi_0133",
    "poi_paixao": "poi_0002",
    "poi_rua_cunha": "poi_0008",
    "poi_ruins_st_paul": "poi_0001",
    "poi_senado": "poi_0004",
    "poi_st_augustine": "poi_0053",
    "poi_st_dominic": "poi_0009",
    "poi_st_joseph": "poi_0052",
    "poi_st_lawrence": "poi_0050",
    "poi_sv_lazaro": "poi_0030",
    "poi_taipa_houses": "poi_0012",
    "poi_xiahuan": "poi_0168",
}


def canonical_poi_id(poi_id: str) -> str:
    return LEGACY_POI_IDS.get(poi_id, poi_id)


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
            **get_poi_summary(record.poi_id),
        )

    def list_pois(
        self,
        *,
        category: str | None,
        query: str | None,
        offset: int,
        limit: int,
    ) -> list[PoiResponse]:
        statement = select(Poi).order_by(Poi.poi_id).offset(offset).limit(limit)
        if category:
            statement = statement.where(Poi.category == category)
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(or_(Poi.poi_name.ilike(pattern), Poi.alias.ilike(pattern)))
        return [self._to_response(record) for record in self._session.scalars(statement)]

    @staticmethod
    def _database_id(poi_id: str) -> str:
        return canonical_poi_id(poi_id)

    def get_by_id(self, poi_id: str) -> PoiResponse | None:
        record = self._session.get(Poi, self._database_id(poi_id))
        return self._to_response(record) if record is not None else None

    def get_by_ids(self, poi_ids: list[str]) -> dict[str, PoiResponse]:
        requested_ids = list(dict.fromkeys(poi_ids))
        database_ids = {poi_id: self._database_id(poi_id) for poi_id in requested_ids}
        records = self._session.scalars(
            select(Poi).where(Poi.poi_id.in_(set(database_ids.values())))
        ).all()
        records_by_id = {record.poi_id: self._to_response(record) for record in records}
        return {
            requested_id: records_by_id[database_id]
            for requested_id, database_id in database_ids.items()
            if database_id in records_by_id
        }

    def exists(self, poi_id: str) -> bool:
        return self._session.get(Poi, self._database_id(poi_id)) is not None

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
