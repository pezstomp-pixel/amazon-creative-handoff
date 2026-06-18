# Dropbox API v2 薄クライアント（handoff フォルダのアップロード用）。新規依存なし(stdlib)。
# 認証: token_access_type=offline で発行した long-lived refresh_token を st.secrets に保持し、
# /oauth2/token で短命 access_token に都度更新する（spec §9）。
import json
import urllib.error
import urllib.parse
import urllib.request

DBX_TOKEN_URL = "https://api.dropbox.com/oauth2/token"
DBX_UPLOAD_URL = "https://content.dropboxapi.com/2/files/upload"
_TIMEOUT = 30


class DropboxError(Exception):
    pass


def _http_error_detail(e) -> str:
    """HTTPError 本文の先頭を安全に読む（診断用・最大 500 文字）。Dropbox は JSON で理由を返す。"""
    try:
        body = e.read().decode("utf-8", "replace").strip()
    except Exception:
        return ""
    return f" {body[:500]}" if body else ""


def get_access_token(app_key: str, app_secret: str, refresh_token: str) -> str:
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": app_key,
        "client_secret": app_secret,
    }).encode("utf-8")
    req = urllib.request.Request(
        DBX_TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise DropboxError(f"Dropbox token HTTP {e.code}{_http_error_detail(e)}") from e
    if "access_token" not in data:
        raise DropboxError(f"Dropbox token 失敗: {data}")
    return data["access_token"]


def remote_folder_path(base_path: str, folder: str) -> str:
    """base_path と folder を Dropbox 絶対パスへ結合（重複スラッシュを除去）。"""
    return base_path.rstrip("/") + "/" + folder.strip("/")


def _upload_arg(path: str) -> str:
    """files/upload の Dropbox-API-Arg ヘッダ値。json.dumps の既定 ensure_ascii=True で
    日本語を \\uXXXX にエスケープ＝HTTP ヘッダ(latin-1)に安全に載る。"""
    return json.dumps({"path": path, "mode": "overwrite", "autorename": False, "mute": True})


def upload_file(access_token: str, path: str, data: bytes) -> None:
    req = urllib.request.Request(
        DBX_UPLOAD_URL, data=data, method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Dropbox-API-Arg": _upload_arg(path),
            "Content-Type": "application/octet-stream",
        })
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            if resp.getcode() not in (200, 201):
                raise DropboxError(f"Dropbox upload HTTP {resp.getcode()} {path}")
    except urllib.error.HTTPError as e:
        raise DropboxError(f"Dropbox upload HTTP {e.code} {path}{_http_error_detail(e)}") from e


def upload_files(app_key: str, app_secret: str, refresh_token: str,
                 remote_folder: str, files: dict) -> str:
    """{ファイル名: bytes} を remote_folder 配下へ逐次アップロード。アップ先フォルダを返す。"""
    token = get_access_token(app_key, app_secret, refresh_token)
    for name, data in files.items():
        upload_file(token, remote_folder.rstrip("/") + "/" + name, data)
    return remote_folder
