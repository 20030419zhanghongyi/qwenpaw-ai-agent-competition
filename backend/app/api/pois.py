from fastapi import APIRouter, HTTPException

from app.db.data import get_poi, load_pois

router = APIRouter(prefix="/api/v1/pois", tags=["pois"])


@router.get("")
def list_pois() -> list[dict]:
    """全部 POI（地图 marker 与下拉选择用）。"""
    return load_pois()


@router.get("/{poi_id}")
def get_poi_detail(poi_id: str) -> dict:
    poi = get_poi(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail=f"POI not found: {poi_id}")
    return poi
