"""Tests for postcard scene batch checkpoint."""

from app.features.postcards.scene_checkpoint import (
    load_checkpoint,
    mark_research,
    mark_slot,
    research_summary,
    save_checkpoint,
)


def test_checkpoint_research_then_slots(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.features.postcards.scene_checkpoint.scenes_root",
        lambda: tmp_path,
    )
    cp = load_checkpoint()
    mark_research(
        cp,
        poi_id="poi_senado",
        name_zh="议事亭前地",
        has_ref=True,
        landmarks_chars=120,
        sources=["pois.json", "https://example.com/a.jpg"],
    )
    save_checkpoint(cp)
    loaded = load_checkpoint()
    assert loaded["phase"] == "research"
    assert loaded["pois"]["poi_senado"]["has_ref"] is True
    summary = research_summary(loaded)
    assert summary["researched"] == 1
    assert summary["with_ref"] == 1

    mark_slot(loaded, poi_id="poi_senado", slot="morning", status="done")
    save_checkpoint(loaded)
    again = load_checkpoint()
    assert again["phase"] == "generate"
    assert again["pois"]["poi_senado"]["slots"]["morning"] == "done"
