import math

PRICE_IN_USD_PER_MTOK = 3.0    # claude-sonnet-4-6 入力 $3 / 1M
PRICE_OUT_USD_PER_MTOK = 15.0  # 出力 $15 / 1M
USD_JPY = 150                  # 概算表示用

def estimate_jpy(input_chars: int, max_out_tokens: int,
                 price_in: float = PRICE_IN_USD_PER_MTOK,
                 price_out: float = PRICE_OUT_USD_PER_MTOK,
                 usd_jpy: int = USD_JPY) -> int:
    """日本語の概算（char*0.7 トークン目安）で円コストを返す。最低 1 円。"""
    in_tok = math.ceil(input_chars * 0.7)
    usd = in_tok / 1e6 * price_in + max_out_tokens / 1e6 * price_out
    return max(1, round(usd * usd_jpy))
