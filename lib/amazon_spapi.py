# Amazon SP-API (Catalog Items v2022-04-01) 薄クライアント（handoff 用に必要分のみ vendor）。
# 2023-10-02 以降 SigV4/IAM 不要・LWA access token のみ。新規依存なし(stdlib urllib)。
# vendor 元: D:\business\06_programmer\bmc_input\amazon_spapi.py（token/throttle/catalog_get/
#   get_catalog_item/定数/SpApiError を移植）。collect_all_images は _pick_image の全variant版。
# download_image_bytes は enrich_reference.py _download_image を「bytes 返却」に変更して移植。
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

LWA_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
SPAPI_HOST = "https://sellingpartnerapi-fe.amazon.com"  # Far East (JP)
MARKETPLACE_JP = "A1VC38T7YXB528"
_TIMEOUT = 20

# getCatalogItem は ~2rps 制限。プロセス内で最低間隔を空け、429 は指数バックオフで再試行する。
_CATALOG_MIN_INTERVAL = 0.6   # ~1.6rps（制限に余裕）
_CATALOG_MAX_ATTEMPTS = 4
_CATALOG_BACKOFF_BASE = 1.0
_last_catalog_ts = 0.0


class SpApiError(Exception):
    pass


def _read_json(resp) -> dict:
    return json.loads(resp.read().decode("utf-8"))


def get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode("utf-8")
    req = urllib.request.Request(
        LWA_TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            code = resp.getcode()
            data = _read_json(resp)
    except urllib.error.HTTPError as e:
        raise SpApiError(f"LWA token HTTP {e.code}") from e
    if code != 200 or "access_token" not in data:
        raise SpApiError(f"LWA token 失敗: {data}")
    return data["access_token"]


def _throttle_catalog() -> None:
    """getCatalogItem 呼び出し間隔を最低 _CATALOG_MIN_INTERVAL 秒空ける（プロセス内・逐次前提）。"""
    global _last_catalog_ts
    wait = _CATALOG_MIN_INTERVAL - (time.monotonic() - _last_catalog_ts)
    if wait > 0:
        time.sleep(wait)
    _last_catalog_ts = time.monotonic()


def _catalog_get(url: str, access_token: str, *, what: str) -> dict:
    """Catalog API 共通 GET。throttle＋429指数バックオフ。what はエラーメッセージ用。"""
    req = urllib.request.Request(url, headers={"x-amz-access-token": access_token}, method="GET")
    for attempt in range(_CATALOG_MAX_ATTEMPTS):
        _throttle_catalog()
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                if resp.getcode() != 200:
                    raise SpApiError(f"Catalog HTTP {resp.getcode()} {what}")
                return _read_json(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < _CATALOG_MAX_ATTEMPTS - 1:
                time.sleep(_CATALOG_BACKOFF_BASE * (2 ** attempt))
                continue
            raise SpApiError(f"Catalog HTTP {e.code} {what}") from e
    raise SpApiError(f"Catalog 429 リトライ上限 {what}")  # 保険（通常到達しない）


def get_catalog_item(asin: str, access_token: str, marketplace: str = MARKETPLACE_JP) -> dict:
    qs = urllib.parse.urlencode({
        "marketplaceIds": marketplace,
        "includedData": "images,summaries",
    })
    url = f"{SPAPI_HOST}/catalog/2022-04-01/items/{asin}?{qs}"
    return _catalog_get(url, access_token, what=f"asin={asin}")


def collect_all_images(images_block, marketplace: str = MARKETPLACE_JP) -> list:
    """images ブロックから variant ごとに最大解像度1枚を選び [(variant, link)] を返す。
    MAIN を先頭、その後 variant 名（PT01, PT02, ...）昇順。link/variant 欠落は無視。
    指定 marketplace のブロックが無ければ空リスト。"""
    for block in images_block or []:
        if block.get("marketplaceId") != marketplace:
            continue
        best_by_variant: dict[str, dict] = {}
        for img in block.get("images") or []:
            variant = img.get("variant")
            link = img.get("link")
            if not variant or not link:
                continue
            cur = best_by_variant.get(variant)
            if cur is None or img.get("width", 0) > cur.get("width", 0):
                best_by_variant[variant] = img
        if not best_by_variant:
            return []
        def _key(v: str):
            return (0, "") if v == "MAIN" else (1, v)
        return [(v, best_by_variant[v]["link"]) for v in sorted(best_by_variant, key=_key)]
    return []


def download_image_bytes(url: str) -> bytes:
    """画像 URL の実体を bytes で取得（CORS 非該当・User-Agent 付き）。
    enrich_reference.py _download_image を Path 書き込み → bytes 返却に変更して移植。"""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.read()
