from lib.handoff import RefImage, ref_filename, folder_name, build_handoff_md


def test_ref_filename_format():
    assert ref_filename("B071FSRQGF", "MAIN") == "ref_B071FSRQGF_MAIN.jpg"
    assert ref_filename("B07", "PT01") == "ref_B07_PT01.jpg"


def test_folder_name_sanitizes_and_appends_stamp():
    assert folder_name("珪藻土バスマット", "20260618_1530") == "珪藻土バスマット_20260618_1530"
    # パス区切り・禁止文字は _ に置換
    assert folder_name("珪藻土/バス:マット", "20260618_1530") == "珪藻土_バス_マット_20260618_1530"
    # 空商品名は product にフォールバック
    assert folder_name("", "20260618_1530") == "product_20260618_1530"
    assert folder_name("   ", "x") == "product_x"


def test_build_handoff_md_includes_all_sections():
    md = build_handoff_md(
        product={"productName": "珪藻土バスマット", "features": "速乾", "category": "バス用品"},
        competitor_pains="乾きが遅いという不満",
        creative={"text": "## スライド1：USP\n[キャッチ]\n- 速く乾く",
                  "moodMemo": "清潔・信頼感", "typeLabel": "USP型"},
        ref_images=[RefImage(asin="B071FSRQGF", variant="MAIN",
                             filename="ref_B071FSRQGF_MAIN.jpg", data=b"")],
    )
    assert "珪藻土バスマット" in md
    assert "速乾" in md
    assert "乾きが遅いという不満" in md
    assert "清潔・信頼感" in md
    assert "USP型" in md
    assert "## スライド1：USP" in md
    assert "ref_B071FSRQGF_MAIN.jpg" in md
    assert "B071FSRQGF" in md
    assert "文字なし" in md          # 背景要件
    assert "1:1" in md              # 比率要件
    assert "A+" in md               # A+ 非取得の注記


def test_build_handoff_md_handles_empty_refs_and_missing_fields():
    md = build_handoff_md(
        product={"productName": "X"},
        competitor_pains="",
        creative={"text": "", "moodMemo": "", "typeLabel": ""},
        ref_images=[],
    )
    assert "X" in md
    assert "（参考画像なし）" in md
    assert "（入力なし）" in md


import io
import zipfile
from lib.handoff import build_zip


def test_build_zip_contains_all_files_with_bytes():
    data = build_zip({"handoff.md": "こんにちは".encode("utf-8"),
                      "ref_A_MAIN.jpg": b"\xff\xd8\xff"})
    zf = zipfile.ZipFile(io.BytesIO(data))
    assert set(zf.namelist()) == {"handoff.md", "ref_A_MAIN.jpg"}
    assert zf.read("handoff.md").decode("utf-8") == "こんにちは"
    assert zf.read("ref_A_MAIN.jpg") == b"\xff\xd8\xff"


def test_build_zip_empty_dict_is_valid_empty_archive():
    zf = zipfile.ZipFile(io.BytesIO(build_zip({})))
    assert zf.namelist() == []
