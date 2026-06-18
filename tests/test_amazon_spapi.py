from lib.amazon_spapi import collect_all_images, MARKETPLACE_JP


def _block(images):
    return [{"marketplaceId": MARKETPLACE_JP, "images": images}]


def test_collect_all_images_picks_max_res_per_variant():
    out = collect_all_images(_block([
        {"variant": "MAIN", "link": "main_500", "width": 500, "height": 500},
        {"variant": "MAIN", "link": "main_1000", "width": 1000, "height": 1000},
        {"variant": "PT01", "link": "pt01_1000", "width": 1000, "height": 1000},
    ]))
    assert out == [("MAIN", "main_1000"), ("PT01", "pt01_1000")]


def test_collect_all_images_main_first_then_variant_sorted():
    out = collect_all_images(_block([
        {"variant": "PT02", "link": "b", "width": 1000},
        {"variant": "MAIN", "link": "m", "width": 1000},
        {"variant": "PT01", "link": "a", "width": 1000},
    ]))
    assert [v for v, _ in out] == ["MAIN", "PT01", "PT02"]


def test_collect_all_images_skips_entries_without_link_or_variant():
    out = collect_all_images(_block([
        {"variant": "MAIN", "width": 1000},          # link 無し → 無視
        {"link": "x", "width": 1000},                 # variant 無し → 無視
        {"variant": "PT01", "link": "ok", "width": 800},
    ]))
    assert out == [("PT01", "ok")]


def test_collect_all_images_other_marketplace_and_empty_return_empty():
    assert collect_all_images([]) == []
    assert collect_all_images(None) == []
    assert collect_all_images([{"marketplaceId": "OTHER",
        "images": [{"variant": "MAIN", "link": "x", "width": 1}]}]) == []
