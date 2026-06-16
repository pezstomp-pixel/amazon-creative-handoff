from lib.prompts import build_review_analysis_prompt

def test_review_prompt_contains_count_and_rules():
    system, user = build_review_analysis_prompt(["遅い", "壊れた", "高い"])
    assert "レビュー分析担当" in system
    assert "憶測で数を作りません" in system
    assert "3 件" in user
    assert "最優先で訴求すべき不満トップ3" in user
    assert "1. 遅い" in user
    assert "3. 高い" in user

def test_review_prompt_empty_list():
    system, user = build_review_analysis_prompt([])
    assert "0 件" in user
