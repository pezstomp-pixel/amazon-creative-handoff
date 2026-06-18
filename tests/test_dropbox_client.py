import json
from lib.dropbox_client import remote_folder_path, _upload_arg


def test_remote_folder_path_joins_and_strips_slashes():
    assert remote_folder_path("/base/", "sub/") == "/base/sub"
    assert remote_folder_path("/a", "b") == "/a/b"
    assert remote_folder_path("/base", "/合同/フォルダ/") == "/base/合同/フォルダ"


def test_upload_arg_is_overwrite_and_ascii_safe():
    # 日本語パスでも Dropbox-API-Arg は ASCII（\uXXXX）でなければ HTTP ヘッダに載らない
    arg_str = _upload_arg("/base/珪藻土バスマット_20260618/ref_A_MAIN.jpg")
    arg_str.encode("ascii")  # 例外が出れば非ASCII混入 = ヘッダ不正
    arg = json.loads(arg_str)
    assert arg["path"] == "/base/珪藻土バスマット_20260618/ref_A_MAIN.jpg"
    assert arg["mode"] == "overwrite"
    assert arg["autorename"] is False
