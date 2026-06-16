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


from lib.parsing import CopySlide, parse_copy_slides, build_copy_draft


def test_parse_copy_slides_state_machine():
    raw = (
        "前置き（無視される）\n"
        "===スライド1：USP===\n"
        "[キャッチ]\n- 速く乾く\n- もう濡れない\n"
        "[サブ]\n- 毎朝サラサラ\n"
        "[本文]\n- 珪藻土が水分を吸う\n"
        "===スライド2：比較===\n"
        "[キャッチ]\n- 比べて選ぶ\n"
    )
    slides = parse_copy_slides(raw)
    assert len(slides) == 2
    assert isinstance(slides[0], CopySlide)
    assert slides[0].number == 1
    assert slides[0].role == "USP"
    assert slides[0].options["catch"] == ["速く乾く", "もう濡れない"]
    assert slides[0].options["sub"] == ["毎朝サラサラ"]
    assert slides[0].options["body"] == ["珪藻土が水分を吸う"]
    assert slides[1].number == 2
    assert slides[1].options["catch"] == ["比べて選ぶ"]
    assert slides[1].options["sub"] == []


def test_parse_copy_slides_no_markers_returns_empty():
    assert parse_copy_slides("ただの文章") == []
    assert parse_copy_slides("") == []


def test_build_copy_draft_picks_first_option_per_type():
    slides = parse_copy_slides(
        "===スライド1：USP===\n[キャッチ]\n- A1\n- A2\n[サブ]\n- B1\n[本文]\n- C1\n"
        "===スライド2：比較===\n[キャッチ]\n- D1\n"
    )
    draft = build_copy_draft(slides)
    assert "===スライド1：USP===" in draft
    assert "キャッチ: A1" in draft
    assert "サブ: B1" in draft
    assert "本文: C1" in draft
    assert "===スライド2：比較===" in draft
    assert "キャッチ: D1" in draft
    assert "A2" not in draft  # 先頭案のみ採用（人が手編集で差し替える前提）
