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
    マーカーが無ければ空リスト（呼び出し側が再提案を促す）。"""
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


# コピー案：スライド区切り「===スライドN：役割===」／種類見出し [キャッチ]/[サブ]/[本文]／
# 案行「- …」を状態機械で読む（app/index.html l.1523-1524・1707-1723 をポート）。
_SLIDE_RE = re.compile(r"^=+\s*スライド\s*(\d+)\s*[:：]?\s*(.*?)\s*=+\s*$")
_TYPE_HDR_RE = re.compile(r"^\[\s*(キャッチ|サブ|本文)\s*\]\s*$")
_OPT_RE = re.compile(r"^-\s+(.+?)\s*$")
_TYPE_KEY = {"キャッチ": "catch", "サブ": "sub", "本文": "body"}
_TYPE_LABEL = {"catch": "キャッチ", "sub": "サブ", "body": "本文"}


@dataclass
class CopySlide:
    number: int
    role: str
    options: dict[str, list[str]]  # {"catch": [...], "sub": [...], "body": [...]}


def parse_copy_slides(text: str) -> list[CopySlide]:
    """AI 返答をスライド単位 → 種類単位 → 案リストにパースする。
    スライドマーカーが無ければ空リスト。"""
    slides: list[CopySlide] = []
    cur = None
    cur_type = None
    for line in (text or "").splitlines():
        ms = _SLIDE_RE.match(line)
        if ms:
            cur = CopySlide(number=int(ms.group(1)), role=ms.group(2).strip(),
                            options={"catch": [], "sub": [], "body": []})
            slides.append(cur)
            cur_type = None
            continue
        if cur is None:
            continue  # 最初のスライドマーカー前は無視
        mt = _TYPE_HDR_RE.match(line)
        if mt:
            cur_type = _TYPE_KEY[mt.group(1)]
            continue
        mo = _OPT_RE.match(line)
        if mo and cur_type:
            cur.options[cur_type].append(mo.group(1).strip())
    return slides


def build_copy_draft(slides: list[CopySlide]) -> str:
    """各スライド×種類の先頭案だけを採った『確定コピー』下書きを作る。
    人はこのテキストを手編集して確定する（種類別の手編集を簡素に実現）。"""
    out = []
    for s in slides:
        # 役割が空（AIが「===スライドN===」のように省略）の場合は余計なコロンを出さない。
        out.append(f"===スライド{s.number}：{s.role}===" if s.role else f"===スライド{s.number}===")
        for key in ("catch", "sub", "body"):
            opts = s.options.get(key, [])
            if opts:
                out.append(f"{_TYPE_LABEL[key]}: {opts[0]}")
        out.append("")
    return "\n".join(out).strip()
