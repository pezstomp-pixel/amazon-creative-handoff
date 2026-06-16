import re
from dataclasses import dataclass

# 構成案：案の区切りマーカー「===案N===」。前後の = 数は可変。
_LAYOUT_SPLIT_RE = re.compile(r"^=+\s*案\s*\d+\s*=+\s*$", re.M)
# 雰囲気メモ／型：全角【】・半角[]、コロン有無の両対応（app/index.html l.1334 をポート）。
_MOOD_RE = re.compile(r"^[ \t]*[【\[]\s*雰囲気メモ\s*[】\]]\s*[:：]?\s*(.+)$", re.M)
_TYPE_RE = re.compile(r"^[ \t]*[【\[]\s*型\s*[】\]]\s*[:：]?\s*(.+)$", re.M)


@dataclass
class LayoutProposal:
    raw_text: str    # その案の本文（マーカー行は含まない・手編集に使う）
    mood_memo: str   # 雰囲気メモ1行（無ければ空文字）
    type_label: str  # 型ラベル（無ければ空文字）


def parse_layout_proposals(text: str) -> list[LayoutProposal]:
    """AI 返答を「===案N===」で分割し、各案から雰囲気メモ・型を抽出する。
    マーカーが無ければ空リスト（呼び出し側が再提案を促す）。統合提案（構成＋コピー）も
    同じ ===案N=== / 【雰囲気メモ】 / 【型】 マーカーを使うため本関数で分割・抽出できる。"""
    if not text or not _LAYOUT_SPLIT_RE.search(text):
        return []
    # split は先頭にマーカー前テキストを残すので [1:] でマーカー後の本文だけ取る。
    chunks = [c.strip() for c in _LAYOUT_SPLIT_RE.split(text)[1:] if c.strip()]
    out = []
    for chunk in chunks:
        m = _MOOD_RE.search(chunk)
        t = _TYPE_RE.search(chunk)
        out.append(LayoutProposal(
            raw_text=chunk,
            mood_memo=(m.group(1).strip() if m else ""),
            type_label=(t.group(1).strip() if t else ""),
        ))
    return out
