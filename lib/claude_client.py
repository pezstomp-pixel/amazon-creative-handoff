from dataclasses import dataclass
from anthropic import Anthropic
from lib.prompts import build_review_analysis_prompt, build_layout_prompt, build_copy_prompt

MODEL = "claude-sonnet-4-6"
ANALYZE_MAX_TOKENS = 2000

@dataclass
class AnalyzeResult:
    text: str
    truncated: bool

def _get_client(api_key: str) -> Anthropic:
    return Anthropic(api_key=api_key)

def analyze_reviews(api_key: str, reviews: list[str]) -> AnalyzeResult:
    system, user = build_review_analysis_prompt(reviews)
    client = _get_client(api_key)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=ANALYZE_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    truncated = getattr(resp, "stop_reason", None) == "max_tokens"
    return AnalyzeResult(text=text, truncated=truncated)


PROPOSE_MAX_TOKENS = 8000  # 構成案3案フル（EPR6枚等）が途中で切れない余裕（旧版から）
COPY_MAX_TOKENS = 6000     # スライド×3種×3案前後を賄う上限（旧版から）


@dataclass
class GenResult:
    text: str
    truncated: bool


def _generate(api_key: str, system: str, user: str, max_tokens: int) -> GenResult:
    client = _get_client(api_key)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    truncated = getattr(resp, "stop_reason", None) == "max_tokens"
    return GenResult(text=text, truncated=truncated)


def propose_layouts(api_key: str, product: dict, competitor_pains: str) -> GenResult:
    """③ 構成・レイアウト案を3案生成（生テキスト＋truncated）。パースは lib.parsing。"""
    system, user = build_layout_prompt(product, competitor_pains)
    return _generate(api_key, system, user, PROPOSE_MAX_TOKENS)


def propose_copy(api_key: str, layout: dict, product: dict, competitor_pains: str) -> GenResult:
    """④ コピー案を生成（生テキスト＋truncated）。パースは lib.parsing。"""
    system, user = build_copy_prompt(layout, product, competitor_pains)
    return _generate(api_key, system, user, COPY_MAX_TOKENS)
