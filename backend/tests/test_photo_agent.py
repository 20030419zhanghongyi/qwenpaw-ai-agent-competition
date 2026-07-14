"""photo_agent 输出校准测试（不调用 QwenPaw）。"""

from app.agents.photo_agent import _build_prompt, _coerce, _extract_json


def test_traditional_poi_alias_is_canonicalized_for_rag_lookup():
    result = _coerce(
        {
            "description": "画面是薄荷绿色葡式住宅。",
            "candidate_poi": "龍環葡韻（氹仔市政花園）",
            "confidence": 0.88,
        }
    )

    assert result.candidate_poi == "龙环葡韵"
    assert result.confidence == 0.88


def test_macau_alias_is_canonicalized_to_local_poi_name():
    result = _coerce(
        {
            "description": "正门牌匾写着媽祖閣。",
            "candidate_poi": "媽閣廟",
            "confidence": 0.9,
        }
    )

    assert result.candidate_poi == "妈祖阁（妈阁庙）"


def test_non_macau_landmark_is_rejected_and_confidence_is_capped():
    result = _coerce(
        {
            "description": "画面是巴黎的金属铁塔。",
            "candidate_poi": "埃菲尔铁塔",
            "confidence": 0.99,
        }
    )

    assert result.candidate_poi is None
    assert result.confidence <= 0.3


def test_non_scene_chart_cannot_keep_hallucinated_poi():
    result = _coerce(
        {
            "description": "画面是一张柱状图，展示关键词频次。",
            "candidate_poi": "议事亭前地",
            "confidence": 0.7,
        }
    )

    assert result.candidate_poi is None
    assert result.confidence <= 0.1


def test_prompt_requires_visual_evidence_and_canonical_candidate():
    prompt = _build_prompt("C:/Temp/random.jpg", "zh-CN")

    assert "视觉证据" in prompt
    assert "标准名称" in prompt
    assert "非澳门" in prompt


def test_extract_json_repairs_unescaped_quotes_inside_description():
    raw = (
        '```json\n{"description":"浮雕内嵌有"M"徽记",'
        '"candidate_poi":"玫瑰堂","confidence":0.92}\n```'
    )

    obj = _extract_json(raw)

    assert obj is not None
    assert obj["description"] == '浮雕内嵌有"M"徽记'
    assert obj["candidate_poi"] == "玫瑰堂"


def test_visual_evidence_fills_missing_description():
    result = _coerce(
        {
            "candidate_poi": "大三巴牌坊",
            "visual_evidence": ["石质巴洛克教堂立面", "顶部十字架", "空窗拱门"],
            "reasoning": "多项独立特征与大三巴牌坊匹配。",
            "confidence": 0.98,
        }
    )

    assert "教堂立面" in result.description
    assert len(result.description) >= 20


def test_st_dominic_subject_wins_over_senado_ground_pattern():
    result = _coerce(
        {
            "description": (
                "画面主体是鹅黄色巴洛克教堂，白色灰泥装饰，"
                "带有绿色百叶窗和大门，前方为黑白碎石路面。"
            ),
            "candidate_poi": "议事亭前地",
            "confidence": 0.95,
        }
    )

    assert result.candidate_poi == "玫瑰堂"
