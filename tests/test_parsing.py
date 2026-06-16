from lib.parsing import LayoutProposal, parse_layout_proposals


def test_parse_layout_proposals_splits_and_extracts():
    raw = (
        "前置きの文章（マーカー前は捨てる）\n"
        "===案1===\n"
        "【雰囲気メモ】清潔・信頼感\n"
        "【型】USP型\n"
        "## スライド1：USP\n- a\n"
        "===案2===\n"
        "【雰囲気メモ】力強い・実用的\n"
        "【型】EPR悩みファースト型\n"
        "## スライド1：悩み\n- b\n"
    )
    ps = parse_layout_proposals(raw)
    assert len(ps) == 2
    assert isinstance(ps[0], LayoutProposal)
    assert ps[0].mood_memo == "清潔・信頼感"
    assert ps[0].type_label == "USP型"
    assert "## スライド1：USP" in ps[0].raw_text
    assert "前置き" not in ps[0].raw_text
    assert ps[1].mood_memo == "力強い・実用的"
    assert ps[1].type_label == "EPR悩みファースト型"


def test_parse_layout_proposals_no_markers_returns_empty():
    assert parse_layout_proposals("マーカーのない文章") == []
    assert parse_layout_proposals("") == []


def test_parse_layout_proposals_missing_mood_is_empty_string():
    raw = "===案1===\n【型】USP型\n## スライド1\n- a\n"
    ps = parse_layout_proposals(raw)
    assert len(ps) == 1
    assert ps[0].mood_memo == ""
    assert ps[0].type_label == "USP型"


def test_parse_layout_proposals_bracket_variants():
    # 全角【】でも半角[]でも、コロン有無でも拾える
    raw = "===案1===\n[雰囲気メモ]: 上品・洗練\n[型] USP型\n- x\n"
    ps = parse_layout_proposals(raw)
    assert ps[0].mood_memo == "上品・洗練"
    assert ps[0].type_label == "USP型"


