from pathlib import Path

from app.agents.photo_agent import PhotoRecognition
from app.eval import scoring
from app.eval.runner import run_photo_case


def test_score_photo_positive_accepts_poi_alias_and_visual_evidence():
    case = {
        "expect": {
            "candidate_any": ["大三巴牌坊", "Ruins of St. Paul's"],
            "description_keywords_any": ["石质", "拱门"],
            "description_min_len": 10,
            "confidence_min": 0.7,
        }
    }
    response = {
        "description": "画面是一座石质教堂立面，可见多层拱门。",
        "candidate_poi": "澳门大三巴牌坊（Ruins of St. Paul's）",
        "confidence": 0.91,
        "source": "agent",
    }

    result = scoring.score_photo_case(case, response)

    assert result["score"] == 1.0
    assert result["passed"] == result["total"] == 4


def test_score_photo_negative_penalizes_hard_guess():
    case = {
        "expect": {
            "candidate_null": True,
            "description_keywords_any": ["图表"],
            "description_min_len": 5,
            "confidence_max": 0.3,
        }
    }
    response = {
        "description": "画面是一张项目图表。",
        "candidate_poi": "议事亭前地",
        "confidence": 0.8,
        "source": "agent",
    }

    result = scoring.score_photo_case(case, response)

    assert result["score"] == 0.5
    assert {c["name"] for c in result["checks"] if not c["passed"]} == {
        "candidate_null",
        "confidence_max",
    }


def test_run_photo_case_hides_ground_truth_filename(monkeypatch):
    seen_path: Path | None = None

    def fake_recognize(image_path: str, *, language: str):
        nonlocal seen_path
        seen_path = Path(image_path)
        assert seen_path.is_file()
        assert seen_path.name != "style_reference_gantt.jpg"
        assert language == "zh-CN"
        return PhotoRecognition(description="项目甘特图", candidate_poi=None, confidence=0.0)

    monkeypatch.setattr("app.eval.runner.photo_agent.recognize", fake_recognize)
    result = run_photo_case({
        "context": {"image_path": "assets/style_reference_gantt.jpg"},
    })

    assert result["source"] == "agent"
    assert result["candidate_poi"] is None
    assert seen_path is not None and not seen_path.exists()


def test_aggregate_includes_photo_category():
    aggregate = scoring.aggregate([{"category": "photo", "score": 0.75}])

    assert aggregate["overall"] == 0.75
    assert aggregate["by_category"]["photo"] == 0.75
