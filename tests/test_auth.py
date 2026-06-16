from lib.auth import is_authorized

def test_empty_allowlist_relies_on_platform():
    assert is_authorized("anyone@example.com", []) is True

def test_allowlist_match_case_insensitive():
    allowed = ["Taro@Example.com"]
    assert is_authorized("taro@example.com", allowed) is True

def test_allowlist_reject():
    allowed = ["taro@example.com"]
    assert is_authorized("intruder@evil.com", allowed) is False

def test_none_email_rejected_when_allowlist_set():
    assert is_authorized(None, ["taro@example.com"]) is False
