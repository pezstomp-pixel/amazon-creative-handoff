import pandas as pd
from lib.reviews import detect_columns, parse_rating, collect_low_reviews

def test_detect_columns():
    headers = ["日付", "星評価", "レビュー本文", "名前"]
    review_idx, rating_idx = detect_columns(headers)
    assert review_idx == 2
    assert rating_idx == 1

def test_detect_columns_defaults_when_missing():
    headers = ["colA", "colB"]
    review_idx, rating_idx = detect_columns(headers)
    assert review_idx == 0
    assert rating_idx == -1

def test_parse_rating_variants():
    assert parse_rating("5つ星のうち3.0") == 3.0
    assert parse_rating("★★★") == 3.0
    assert parse_rating("4") == 4.0
    assert parse_rating("") is None
    assert parse_rating("コメント") is None

def test_collect_low_reviews_filters_and_caps():
    df = pd.DataFrame({
        "rating": ["5", "3", "1", "4", ""],
        "text":   ["良い", "普通に不満", "壊れた", "満足", "不明だが不満"],
    })
    low = collect_low_reviews(df, review_idx=1, rating_idx=0, max_reviews=10, max_chars=300)
    assert "普通に不満" in low
    assert "壊れた" in low
    assert "不明だが不満" in low
    assert "良い" not in low
    assert "満足" not in low

def test_collect_low_reviews_truncates_and_limits():
    df = pd.DataFrame({"text": ["あ" * 500, "い" * 10, "う" * 10]})
    low = collect_low_reviews(df, review_idx=0, rating_idx=-1, max_reviews=2, max_chars=300)
    assert len(low) == 2
    assert len(low[0]) == 300
