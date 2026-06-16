import streamlit as st

from lib import reviews as rv
from lib.auth import is_authorized
from lib.cost import estimate_jpy
from lib.claude_client import (
    analyze_reviews,
    ANALYZE_MAX_TOKENS,
    propose_layouts,
    propose_copy,
    PROPOSE_MAX_TOKENS,
    COPY_MAX_TOKENS,
)
from lib.parsing import parse_layout_proposals, parse_copy_slides, build_copy_draft
from lib.prompts import build_layout_prompt, build_copy_prompt

st.set_page_config(page_title="Amazon クリエイティブ handoff", layout="centered")

# ---- 認証ゲート: Google ログイン (OIDC・st.login) ＋ 許可メール allowlist ----
# secrets.toml の [auth] が必須（未設定だと st.user 参照でエラー）。
# public リポ/アプリでも、ここでログインと allowlist を必ず通すため第三者は使えない。
if not st.user.is_logged_in:
    st.title("Amazon クリエイティブ handoff ツール")
    st.info("社内向けツールです。許可された Google アカウントでログインしてください。")
    st.button("Google でログイン", on_click=st.login)
    st.stop()

email = getattr(st.user, "email", None)
allowed = st.secrets.get("APP_ALLOWED_USERS", [])
if not is_authorized(email, list(allowed)):
    st.error(f"このアカウント（{email}）にはアクセス権がありません。管理者に連絡してください。")
    st.button("別アカウントでログアウト", on_click=st.logout)
    st.stop()

with st.sidebar:
    st.caption(f"ログイン中: {email}")
    st.button("ログアウト", on_click=st.logout)

st.title("Amazon クリエイティブ handoff ツール")
st.caption("商品情報 → 競合レビュー分析 → 構成・レイアウト → コピー →（P3）Codex handoff")

# ---- session_state 初期化 ----
ss = st.session_state
ss.setdefault("product", {})
ss.setdefault("competitor_pains", "")
ss.setdefault("layout", {})                 # 確定構成案 {layoutText, moodMemo, typeLabel, productName}
ss.setdefault("layout_proposals_raw", "")   # 直近の構成案 AI 生テキスト
ss.setdefault("layout_confirmed", False)    # ③ 確定ゲート
ss.setdefault("copy_proposals_raw", "")     # 直近のコピー AI 生テキスト
ss.setdefault("copy_confirmed", False)      # ④ 確定ゲート
ss.setdefault("copy_text", "")              # 確定コピー（手編集テキスト）

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

# ---- ③ 構成・レイアウト案 ----
st.header("③ 構成・レイアウト案")
st.caption(
    "商品情報＋『競合の不満点』から、AI が型（USP型／EPR悩みファースト型）を判断して 3 案提案します。"
    "各案にページ全体の雰囲気メモ1行が付きます。1案を選んで手編集し確定すると ④ に進めます。送信前に概算コストを表示します。"
)

_sys_l, _usr_l = build_layout_prompt(ss["product"], ss.get("competitor_pains", ""))
_yen_l = estimate_jpy(len(_sys_l) + len(_usr_l), PROPOSE_MAX_TOKENS)
st.warning(f"概算コスト：約 {_yen_l} 円（claude-sonnet-4-6・3案提案）")
if st.button("構成案を3案 提案する（課金発生）"):
    key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not key:
        st.error("ANTHROPIC_API_KEY が未設定です（st.secrets を確認）。")
        st.stop()
    with st.spinner("提案を生成中…（数十秒かかる場合があります）"):
        res = propose_layouts(key, ss["product"], ss.get("competitor_pains", ""))
    if res.truncated:
        st.warning("⚠ 出力が上限に達し、途中で切れた可能性があります。")
    ss["layout_proposals_raw"] = res.text
    ss["_layout_choice_prev"] = None  # 新しい提案が来たら選択バッファを作り直す

if ss["layout_proposals_raw"]:
    proposals = parse_layout_proposals(ss["layout_proposals_raw"])
    if not proposals:
        st.error("提案の解析に失敗しました（『===案N===』区切りが見つかりません）。もう一度提案してください。")
    else:
        _labels = [
            f"案{i + 1}（型: {p.type_label or '未記載'} ／ 雰囲気: {p.mood_memo or '未記載'}）"
            for i, p in enumerate(proposals)
        ]
        idx = st.radio(
            "採用する案を選ぶ", range(len(proposals)),
            format_func=lambda i: _labels[i], key="layout_choice",
        )
        # 選択が変わったら編集バッファ（widget key）を選択案で上書きしてから widget を生成する
        if ss.get("_layout_choice_prev") != idx:
            ss["layout_edit"] = proposals[idx].raw_text
            ss["mood_edit"] = proposals[idx].mood_memo
            ss["_layout_choice_prev"] = idx
        st.text_area("構成案テキスト（手編集可）", height=320, key="layout_edit")
        st.text_input("雰囲気メモ（1行・手編集可）", key="mood_edit")
        if st.button("この構成案で確定"):
            ss["layout"] = {
                "layoutText": ss["layout_edit"],
                "moodMemo": ss["mood_edit"],
                "typeLabel": proposals[idx].type_label,
                "productName": ss["product"].get("productName", ""),
            }
            ss["layout_confirmed"] = True
            ss["copy_confirmed"] = False  # 構成を変えたら下流コピーは無効化
            st.success("✓ 構成案を確定しました。④ コピー案に進めます。")

if ss["layout_confirmed"]:
    _lay = ss["layout"]
    st.info(
        f"確定済み構成案 … 型: {_lay.get('typeLabel') or '—'} ／ "
        f"雰囲気メモ: {_lay.get('moodMemo') or '—'}（手編集して再度『確定』すれば上書き）"
    )

# ---- ④ コピー案 ----
st.header("④ コピー案")
if not ss["layout_confirmed"]:
    st.info("先に ③ 構成・レイアウト案を確定してください。確定すると、ここで各スライドのコピーを提案できます。")
else:
    st.caption(
        "確定した構成案の各スライドに載せる『キャッチ／サブ／本文』を種類別に複数案提案します。"
        "下書きを手編集して確定してください。薬機法・景表法の最終確認は人が目視で行います。送信前に概算コストを表示します。"
    )
    _sys_c, _usr_c = build_copy_prompt(ss["layout"], ss["product"], ss.get("competitor_pains", ""))
    _yen_c = estimate_jpy(len(_sys_c) + len(_usr_c), COPY_MAX_TOKENS)
    st.warning(f"概算コスト：約 {_yen_c} 円（claude-sonnet-4-6・コピー提案）")
    if st.button("コピー案を提案する（課金発生）"):
        key = st.secrets.get("ANTHROPIC_API_KEY", "")
        if not key:
            st.error("ANTHROPIC_API_KEY が未設定です（st.secrets を確認）。")
            st.stop()
        with st.spinner("提案を生成中…（数十秒かかる場合があります）"):
            res = propose_copy(key, ss["layout"], ss["product"], ss.get("competitor_pains", ""))
        if res.truncated:
            st.warning("⚠ 出力が上限に達し、途中で切れた可能性があります。")
        ss["copy_proposals_raw"] = res.text
        slides = parse_copy_slides(res.text)
        # 種類別の先頭案を採った下書きを編集欄へプリフィル（パース不能なら生テキスト）
        ss["copy_text"] = build_copy_draft(slides) if slides else res.text

    if ss["copy_proposals_raw"]:
        with st.expander("AI 提案の全文（複数案・参照用）", expanded=False):
            st.text(ss["copy_proposals_raw"])
        st.text_area("確定コピー（種類別の下書きを手編集して確定）", height=400, key="copy_text")
        if st.button("このコピーで確定"):
            ss["copy_confirmed"] = True
            st.success("✓ コピーを確定しました。（⑤ handoff 書き出しは P3 で実装）")

    if ss["copy_confirmed"]:
        st.info("確定済みコピーあり。⑤ handoff 生成（P3）で参照されます。手編集して再度『確定』すれば上書きできます。")
