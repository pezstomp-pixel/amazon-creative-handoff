from dataclasses import dataclass
from anthropic import Anthropic
from lib.prompts import build_review_analysis_prompt

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
