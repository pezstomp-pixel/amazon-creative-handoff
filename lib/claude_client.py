from dataclasses import dataclass
from anthropic import Anthropic
from lib.prompts import build_review_analysis_prompt, build_creative_prompt

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
    r = _generate(api_key, system, user, ANALYZE_MAX_TOKENS)
    return AnalyzeResult(text=r.text, truncated=r.truncated)


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


COMBINED_MAX_TOKENS = 12000  # 2案フル（構成＋キャッチ/サブ/本文 厚め）が途中で切れない余裕。
# 非ストリーミングで >~16000 は SDK がタイムアウト保護で弾くため 12000 に設定。


def propose_creative(api_key: str, product: dict, competitor_pains: str) -> GenResult:
    """③ 構成＋コピー案を2案、一度に生成（生テキスト＋truncated）。パースは lib.parsing。"""
    system, user = build_creative_prompt(product, competitor_pains)
    return _generate(api_key, system, user, COMBINED_MAX_TOKENS)
