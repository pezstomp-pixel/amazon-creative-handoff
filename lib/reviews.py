import re
import pandas as pd

REVIEW_COL_RE = re.compile(r"レビュー|review|本文|内容|コメント|comment|body|口コミ", re.I)
RATING_COL_RE = re.compile(r"星|評価|rating|star|点数|score", re.I)

MAX_REVIEWS = 400       # 送信レビュー上限（ポート）
MAX_REVIEW_CHARS = 300  # 1レビュー最大文字数（ポート）

# Matches a decimal number like "3.0" — used to prefer the actual rating
# in strings like "5つ星のうち3.0" where the first integer (5) is the scale,
# not the rating. If no decimal is found, fall back to the first integer.
_DECIMAL_RE = re.compile(r"\d+\.\d+")
_INTEGER_RE = re.compile(r"\d+")


def load_table(file, filename: str) -> pd.DataFrame:
    """xlsx/csv を DataFrame で読む（1行目=ヘッダ）。全列を文字列化。"""
    if filename.lower().endswith(".xlsx"):
        df = pd.read_excel(file, engine="openpyxl", dtype=str)
    else:
        df = pd.read_csv(file, dtype=str)
    return df.fillna("")


def detect_columns(headers: list[str]) -> tuple[int, int]:
    """(review_idx, rating_idx) を返す。レビュー列が無ければ 0、星列が無ければ -1。"""
    review_idx = next(
        (i for i, h in enumerate(headers) if REVIEW_COL_RE.search(str(h or ""))), -1
    )
    rating_idx = next(
        (i for i, h in enumerate(headers) if RATING_COL_RE.search(str(h or ""))), -1
    )
    return (review_idx if review_idx >= 0 else 0), rating_idx


def parse_rating(value) -> float | None:
    """星評価を数値化。

    変換ルール:
      '5つ星のうち3.0' → 3.0  (小数を優先: _DECIMAL_RE で "3.0" を先に探す)
      '★★★'           → 3.0  (★の数を数える)
      '4'             → 4.0  (整数フォールバック: _INTEGER_RE)
      ''              → None
      '不明テキスト'   → None

    "5つ星のうち3.0" のような Amazon 形式では最初の数字 "5" はスケール、
    実評価は後続の小数 "3.0" である。そのため _DECIMAL_RE（小数優先）で
    先にマッチを試み、見つからない場合のみ _INTEGER_RE にフォールバックする。
    """
    s = str(value or "").strip()
    if not s:
        return None

    # 優先: 小数点付き数値（例: "3.0" in "5つ星のうち3.0"）
    m = _DECIMAL_RE.search(s)
    if m:
        return float(m.group())

    # 次: ★の数
    stars = s.count("★")
    if stars:
        return float(stars)

    # 最後: 整数（例: "4"）
    m = _INTEGER_RE.search(s)
    if m:
        return float(m.group())

    return None


def collect_low_reviews(
    df: pd.DataFrame,
    review_idx: int,
    rating_idx: int,
    max_reviews: int = MAX_REVIEWS,
    max_chars: int = MAX_REVIEW_CHARS,
) -> list[str]:
    """★1-3（および不明）のレビュー本文を抽出。★4-5 は除外。上限・文字数で切る。"""
    low: list[str] = []
    cols = list(df.columns)
    for _, row in df.iterrows():
        txt = str(row[cols[review_idx]] or "").strip()
        if not txt:
            continue
        if rating_idx >= 0:
            rt = parse_rating(row[cols[rating_idx]])
            if rt is not None and rt > 3:
                continue  # ★4-5 は除外（不明はノイズ回避で残す）
        low.append(txt[:max_chars])
        if len(low) >= max_reviews:
            break
    return low
