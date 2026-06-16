REVIEW_ANALYSIS_SYSTEM = (
    "あなたはAmazon物販のレビュー分析担当です。競合商品の低評価レビューから、"
    "顧客の不満をテーマ別に正確に分類します。原文の転載はせず要約し、"
    "件数は与えられたリスト内の該当数の目安として扱い、憶測で数を作りません。"
)

def build_review_analysis_prompt(reviews: list[str]) -> tuple[str, str]:
    """(system, user) を返す。既存 HTML 版のプロンプトを忠実にポート。"""
    n = len(reviews)
    body = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(reviews))
    user = (
        f"以下は競合商品の低評価（★1〜3中心）レビュー {n} 件です。\n"
        "顧客の不満をテーマ別に分類し、件数が多い順に、日本語のマークダウン箇条書きで簡潔にまとめてください。\n"
        "各テーマに「・不満テーマ：◯件目安 — 代表的な不満の要点（要約）／商品ページで訴求すべき改善方向」を1行で。\n"
        "最後に「最優先で訴求すべき不満トップ3」を箇条書きで添えてください。\n\n"
        "--- レビュー ---\n" + body
    )
    return REVIEW_ANALYSIS_SYSTEM, user
