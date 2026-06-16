import streamlit as st

from lib import reviews as rv
from lib.auth import is_authorized
from lib.cost import estimate_jpy
from lib.claude_client import analyze_reviews, ANALYZE_MAX_TOKENS

st.set_page_config(page_title="Amazon クリエイティブ handoff", layout="centered")

# ---- 認証ゲート（Community Cloud private が主・アプリ側は defense-in-depth） ----
def _current_email() -> str | None:
    user = getattr(st, "user", None)
    if user is not None:
        try:
            return user.get("email")  # Streamlit 新 API
        except Exception:
            return getattr(user, "email", None)
    return None

allowed = st.secrets.get("APP_ALLOWED_USERS", [])
email = _current_email()
if not is_authorized(email, list(allowed)):
    st.error("このアプリへのアクセス権がありません。管理者に連絡してください。")
    st.stop()

st.title("Amazon クリエイティブ handoff ツール")
st.caption("商品情報 → 競合レビュー分析 →（P2以降）構成/コピー → Codex handoff")

# ---- session_state 初期化 ----
ss = st.session_state
ss.setdefault("product", {})
ss.setdefault("competitor_pains", "")

# ---- ① 商品情報入力 ----
st.header("① 商品情報")
with st.form("product_form"):
    p = ss["product"]
    p["productName"] = st.text_input("商品名", p.get("productName", ""))
    p["category"]    = st.text_input("カテゴリ", p.get("category", ""))
    p["color"]       = st.text_input("色", p.get("color", ""))
    p["material"]    = st.text_input("素材", p.get("material", ""))
    p["size"]        = st.text_input("形状・サイズ", p.get("size", ""))
    p["features"]    = st.text_area("商品の特徴（箇条書きでOK）", p.get("features", ""))
    p["target"]      = st.text_area("ターゲット顧客", p.get("target", ""))
    _TONES = ["", "ミニマル", "ナチュラル", "高級感", "親しみやすい", "都会的"]
    _tone_val = p.get("brandTone", "")
    p["brandTone"]   = st.selectbox(
        "ブランドトーン", _TONES,
        index=_TONES.index(_tone_val) if _tone_val in _TONES else 0,
    )
    p["ng"]          = st.text_area("NG要素（避けたい表現・訴求）", p.get("ng", ""))
    if st.form_submit_button("商品情報を保存"):
        ss["product"] = p
        st.success("保存しました（このセッション内で保持）")

# ---- ② 競合レビュー分析 ----
st.header("② 競合レビュー分析（xlsx / csv）")
st.caption("セラースプライト等の競合レビューをアップ → ★1〜3を Claude が不満テーマ別に分析。送信前に概算コストを表示します。")
up = st.file_uploader("競合レビューファイル", type=["xlsx", "csv"])
if up is not None:
    try:
        df = rv.load_table(up, up.name)
    except Exception as e:
        st.error(f"ファイルを読めませんでした：{e}")
        st.stop()
    headers = list(df.columns)
    d_review, d_rating = rv.detect_columns(headers)
    review_col = st.selectbox("レビュー本文の列", headers, index=d_review)
    rating_options = ["（星評価なし）"] + headers
    rating_sel = st.selectbox(
        "星評価の列", rating_options,
        index=(d_rating + 1) if d_rating >= 0 else 0,
    )
    review_idx = headers.index(review_col)
    rating_idx = headers.index(rating_sel) if rating_sel != "（星評価なし）" else -1

    low = rv.collect_low_reviews(df, review_idx, rating_idx)
    st.info(f"分析対象（★1〜3・不明含む）：{len(low)} 件（上限 {rv.MAX_REVIEWS} 件）")

    if low:
        input_chars = sum(len(t) for t in low) + 400
        yen = estimate_jpy(input_chars, ANALYZE_MAX_TOKENS)
        st.warning(f"概算コスト：約 {yen} 円（claude-sonnet-4-6 / {len(low)} 件送信）")
        if st.button("この内容で分析する（課金発生）"):
            key = st.secrets.get("ANTHROPIC_API_KEY", "")
            if not key:
                st.error("ANTHROPIC_API_KEY が未設定です（st.secrets を確認）。")
                st.stop()
            with st.spinner("分析中…（数十秒かかる場合があります）"):
                result = analyze_reviews(key, low)
            if result.truncated:
                st.warning("⚠ 出力が上限に達し、途中で切れた可能性があります。")
            stamped = f"【競合レビュー分析 / claude-sonnet-4-6 / {len(low)}件】\n{result.text}"
            ss["competitor_pains"] = stamped
            st.success("✓ 分析結果を『競合の不満点』に反映しました。")

# ---- 競合の不満点（②の結果・手編集可・下流工程の入力） ----
st.subheader("競合の不満点（手編集可）")
ss["competitor_pains"] = st.text_area(
    "競合の不満点", ss.get("competitor_pains", ""), height=200,
    label_visibility="collapsed",
)
