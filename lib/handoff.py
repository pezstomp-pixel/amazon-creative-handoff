import io
import re
import zipfile
from dataclasses import dataclass

_UNSAFE = re.compile(r'[\\/:*?"<>|]+')


@dataclass
class RefImage:
    asin: str
    variant: str
    filename: str
    data: bytes


def ref_filename(asin: str, variant: str) -> str:
    """参考画像の同梱ファイル名（spec §4 データフロー: ref_<asin>_<variant>.jpg）。"""
    return f"ref_{asin}_{variant}.jpg"


def folder_name(product_name: str, stamp: str) -> str:
    """出力フォルダ名 <商品名>_<JST日時>。禁止文字は _ に、空名は product に。"""
    base = _UNSAFE.sub("_", (product_name or "").strip()) or "product"
    return f"{base}_{stamp}"


def _g(d: dict, key: str) -> str:
    return str((d or {}).get(key, "") or "").strip()


def build_handoff_md(product: dict, competitor_pains: str,
                     creative: dict, ref_images: list) -> str:
    """確定データ → Codex 添付用 handoff.md（spec §4.1/§4.3）。"""
    pains = (competitor_pains or "").strip()
    lines: list[str] = []
    lines.append("# Codex handoff（背景／使用シーン画像 制作指示）")
    lines.append("")
    lines.append("このフォルダは Amazon 商品ページ用の背景／使用シーン画像を Codex で生成するための指示書です。")
    lines.append("**文字入れ・実物商品の合成は人間が Photoshop で行います。Codex は文字なし・実物なしの背景／使用シーンのみを生成してください。**")

    lines.append("\n## 1. 商品基本情報")
    lines.append("- 商品名: " + (_g(product, "productName") or "(未入力)"))
    for label, key in (("カテゴリ", "category"), ("色", "color"), ("素材", "material"),
                       ("形状・サイズ", "size"), ("ターゲット顧客", "target"),
                       ("ブランドトーン", "brandTone"), ("NG要素", "ng")):
        val = _g(product, key)
        if val:
            lines.append(f"- {label}: {val}")
    feats = _g(product, "features")
    if feats:
        lines.append("- 特徴:\n" + feats)

    lines.append("\n## 2. 差別化軸（競合の不満点）")
    lines.append(pains if pains else "（入力なし）")

    lines.append("\n## 3. 確定した構成・コピー案")
    lines.append("- 型: " + (_g(creative, "typeLabel") or "—"))
    lines.append("- 雰囲気メモ（トーン＆マナー）: " + (_g(creative, "moodMemo") or "—"))
    lines.append("")
    lines.append(_g(creative, "text") or "(構成・コピー案なし)")

    lines.append("\n## 4. 画像に求める要件（資料ではなく“広告”として作る）")
    lines.append("### 4-0. 共通（A版・B版の両方に適用）")
    lines.append("- 用途は「広告クリエイティブ（ad creative）」。infographic／資料・スライド調にはしない。")
    lines.append("- 1画像1メッセージ（要素を詰め込まない・3秒で1訴求）。写真（使用シーン・素材感・寸法）を主役にする。")
    lines.append("- 雰囲気メモのトーン＆マナーに沿う。各スライドの役割・意図に合わせる。")
    lines.append("- 出力比率は縦長 2:3（横1200×縦1800px・Amazonサブ画像前提・スマホ画面占有率優先）。最重要の差別化要素を上部に置く。")
    lines.append("\n### 4-1. 各スライドにつき次の2版を出力してください（比較・使い分け用）")
    lines.append("**【A版＝文字なし・実物なし（既定／Photoshop 用）】**")
    lines.append("- 文字入れ・実物商品の合成は人が Photoshop で行う前提。Codex は文字なし・実物なしの背景／使用シーンのみを生成する。")
    lines.append("- 確定コピーは余白・構図設計の参考にとどめ、画像には文字を入れない。")
    lines.append("**【B版＝文字あり・1枚完成（検証用）】**")
    lines.append("- 確定コピーを画像内に焼き込んだ完成版も併せて出力する（A版との比較・歩留まり検証用）。")
    lines.append("- 文字の鉄則：短く・大きく・中央寄せ・太ゴシック・シンプル背景。最低24pt相当・背景と文字の明度差を大きく（白背景に黄色はNG）。")
    lines.append("- 確定文字は \"引用符\" で囲んで逐語で描画し、余計な文字を足さない。日本語フォントは Noto Sans JP 等を明示し、プロンプトに「Japanese」と明記する（CJK統合で中国語字形になるのを防ぐ）。")
    lines.append("- 日本語の文字描画は Gemini 3 Pro Image（Nano Banana Pro）が安定。GPT Image 系は漢字が崩れやすいので確定コピーの焼き込みには非推奨。")
    lines.append("- ※B版はあくまで検証用。実物商品の合成・薬機法/景表法の最終チェックは人が行う（A版＋Photoshop が安全な既定経路）。")

    lines.append("\n## 5. 同梱の参考画像（競合 ASIN のメイン／サブ画像）")
    if ref_images:
        lines.append("構図・余白・雰囲気の参考用です。模倣・転載はしないでください。")
        seen_asins = []
        for r in ref_images:
            lines.append(f"- {r.filename}（ASIN: {r.asin} / variant: {r.variant}）")
            if r.asin not in seen_asins:
                seen_asins.append(r.asin)
        lines.append("\n出典（Amazon 商品ページ）:")
        for asin in seen_asins:
            lines.append(f"- {asin}: https://www.amazon.co.jp/dp/{asin}")
    else:
        lines.append("（参考画像なし）")
    lines.append("\n> 注: Amazon の A+（商品紹介コンテンツ）画像はカタログ外のため取得していません。"
                 "競合 ASIN のカタログ露出枚数は商品により差があります。")

    return "\n".join(lines)


def build_zip(files: dict) -> bytes:
    """{ファイル名: bytes} を ZIP（bytes）にまとめる。ブラウザ DL 用。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()
