from lib import claude_client

class _FakeBlock:
    type = "text"
    def __init__(self, text): self.text = text

class _FakeResp:
    def __init__(self, text, stop_reason="end_turn"):
        self.content = [_FakeBlock(text)]
        self.stop_reason = stop_reason

class _FakeMessages:
    def __init__(self, resp): self._resp = resp; self.called_with = None
    def create(self, **kwargs): self.called_with = kwargs; return self._resp

class _FakeClient:
    def __init__(self, resp): self.messages = _FakeMessages(resp)

def test_analyze_reviews_returns_text_and_uses_model(monkeypatch):
    fake = _FakeClient(_FakeResp("・不満テーマA：3件目安"))
    monkeypatch.setattr(claude_client, "_get_client", lambda key: fake)
    out = claude_client.analyze_reviews("dummy-key", ["遅い", "高い"])
    assert "不満テーマA" in out.text
    assert fake.messages.called_with["model"] == "claude-sonnet-4-6"
    assert fake.messages.called_with["max_tokens"] == 2000

def test_analyze_reviews_flags_truncation(monkeypatch):
    fake = _FakeClient(_FakeResp("途中で切れた", stop_reason="max_tokens"))
    monkeypatch.setattr(claude_client, "_get_client", lambda key: fake)
    out = claude_client.analyze_reviews("k", ["x"])
    assert out.truncated is True


def test_propose_layouts_uses_propose_max_tokens(monkeypatch):
    fake = _FakeClient(_FakeResp("===案1===\n【型】USP型"))
    monkeypatch.setattr(claude_client, "_get_client", lambda key: fake)
    out = claude_client.propose_layouts("k", {"productName": "珪藻土バスマット"}, "遅い")
    assert "案1" in out.text
    assert out.truncated is False
    assert fake.messages.called_with["model"] == "claude-sonnet-4-6"
    assert fake.messages.called_with["max_tokens"] == 8000
    assert "珪藻土バスマット" in fake.messages.called_with["messages"][0]["content"]


def test_propose_copy_uses_copy_max_tokens_and_layout(monkeypatch):
    fake = _FakeClient(_FakeResp("===スライド1：USP===\n[キャッチ]\n- a"))
    monkeypatch.setattr(claude_client, "_get_client", lambda key: fake)
    out = claude_client.propose_copy(
        "k", {"layoutText": "確定構成テキストL", "typeLabel": "USP型"},
        {"productName": "X"}, "",
    )
    assert "スライド1" in out.text
    assert fake.messages.called_with["max_tokens"] == 6000
    assert "確定構成テキストL" in fake.messages.called_with["messages"][0]["content"]


def test_propose_copy_flags_truncation(monkeypatch):
    fake = _FakeClient(_FakeResp("途中で切れた", stop_reason="max_tokens"))
    monkeypatch.setattr(claude_client, "_get_client", lambda key: fake)
    out = claude_client.propose_copy("k", {"layoutText": "L"}, {}, "")
    assert out.truncated is True
