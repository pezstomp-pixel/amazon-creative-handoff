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

from lib.prompts import WIN_PATTERNS


def test_win_patterns_has_core_sections():
    assert "勝ちパターン指針メモ" in WIN_PATTERNS
    assert "§5 法務" in WIN_PATTERNS
    assert "EPR" in WIN_PATTERNS


from lib.prompts import build_creative_prompt


def test_creative_prompt_combines_structure_and_copy():
    system, user = build_creative_prompt(
        {"productName": "珪藻土バスマット", "features": "速乾", "brandTone": "ナチュラル"},
        "乾きが遅いという不満",
    )
    assert "勝ちパターン指針メモ" in system
    assert "コピー" in system
    assert "ハルシネーション禁止" in system
    assert "§5" in system
    assert "珪藻土バスマット" in user
    assert "ナチュラル" in user
    assert "乾きが遅いという不満" in user
    assert "構成・コピー案を必ず2案" in user
    assert "===案1===" in user
    assert "【雰囲気メモ】" in user
    assert "## スライド1" in user
    assert "[キャッチ]" in user
    assert "[サブ]" in user
    assert "[本文]" in user


def test_creative_prompt_pain_fallback_when_empty():
    system, user = build_creative_prompt({"productName": "X"}, "")
    assert "（入力なし）" in user
    assert "でっち上げない" in user
