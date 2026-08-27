from app.features.pois.knowledge import (
    get_knowledge_subgraph,
    get_operational_metadata,
    get_poi_summary,
)
from app.features.routes import transit_live


def test_priority_poi_hours_are_source_attributed():
    result = get_operational_metadata(["poi_0003", "poi_0011", "poi_missing"], "en")

    assert result["status"] == "verified-schedule"
    assert result["coverage"] == {"requested": 3, "verified": 2}
    assert all(entry["source"]["url"].startswith("https://") for entry in result["entries"])


def test_opening_hours_registry_is_loaded_once():
    from app.features.pois import knowledge

    knowledge._records.cache_clear()
    first = knowledge._records()
    second = knowledge._records()

    assert first is second
    assert knowledge._records.cache_info().hits == 1


def test_poi_summary_comes_from_fixed_backend_content():
    summary = get_poi_summary("poi_0002")

    assert summary["summary_zh_cn"]
    assert "短巷" in summary["summary_zh_cn"]


def test_knowledge_graph_returns_requested_relationships():
    result = get_knowledge_subgraph(["poi_0001", "poi_0003"])

    assert {node["poi_id"] for node in result["nodes"]} == {"poi_0001", "poi_0003"}
    assert any(edge["target_poi_id"] == "poi_0003" for edge in result["edges"])


def test_bus_operations_reports_live_changes(monkeypatch):
    monkeypatch.setattr(
        transit_live,
        "_post",
        lambda path, params: {
            "header": "000",
            "data": {
                "routeList": [
                    {"routeName": "3", "routeChange": "1", "direction": "0", "color": "Orange"}
                ]
            },
        }
        if "RouteAndCompany" in path
        else None,
    )
    transit_live._cache.clear()

    result = transit_live.get_bus_operations(routes=[], language="en")

    assert result["status"] == "live"
    assert result["alerts"][0]["route"] == "3"
    assert result["source"]["url"].startswith("https://bis.dsat.gov.mo")
