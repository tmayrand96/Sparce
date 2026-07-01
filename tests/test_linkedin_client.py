import json

from backend.connectors.linkedin_client import LinkedInClient


class MockResponse:
    def __init__(self, payload=None, status_code=200, headers=None, text=""):
        self._payload = payload or {}
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


def test_store_token_persists_to_disk(tmp_path):
    client = LinkedInClient(storage_path=tmp_path / "tokens.json")

    client.store_token("abc123")

    assert client.load_access_token() == "abc123"
    stored = json.loads((tmp_path / "tokens.json").read_text(encoding="utf-8"))
    assert "linkedin" in stored
    assert isinstance(stored["linkedin"], str)


def test_get_profile_uses_stored_token(monkeypatch, tmp_path):
    client = LinkedInClient(storage_path=tmp_path / "tokens.json")
    client.store_token("abc123")

    def fake_get(url, headers=None, timeout=15):
        assert headers["Authorization"] == "Bearer abc123"
        return MockResponse({
            "id": "ABC123",
            "localizedFirstName": "Jane",
            "localizedLastName": "Doe",
        })

    monkeypatch.setattr("backend.connectors.linkedin_client.requests.get", fake_get)

    profile = client.get_profile()

    assert profile["id"] == "ABC123"
    assert profile["firstName"] == "Jane"
    assert profile["lastName"] == "Doe"


def test_validate_scope_returns_true_for_w_member_social(monkeypatch, tmp_path):
    client = LinkedInClient(storage_path=tmp_path / "tokens.json")
    client.store_token("abc123")

    def fake_get(url, headers=None, timeout=15):
        assert headers["Authorization"] == "Bearer abc123"
        return MockResponse({}, headers={"X-OAuth-Scopes": "r_liteprofile,w_member_social"})

    monkeypatch.setattr("backend.connectors.linkedin_client.requests.get", fake_get)

    assert client.validate_scope() is True


def test_post_to_profile_builds_payload(monkeypatch, tmp_path):
    client = LinkedInClient(storage_path=tmp_path / "tokens.json")
    client.store_token("abc123")

    def fake_get(url, headers=None, timeout=15):
        assert headers["Authorization"] == "Bearer abc123"
        return MockResponse({
            "id": "ABC123",
            "localizedFirstName": "Jane",
            "localizedLastName": "Doe",
        })

    def fake_post(url, json=None, headers=None, timeout=15):
        assert url == client.UGC_POST_URL
        assert headers["Authorization"] == "Bearer abc123"
        assert "Source: https://github.com/octocat/demo-repo" in json["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"]
        return MockResponse({"status": "created"}, status_code=201)

    monkeypatch.setattr("backend.connectors.linkedin_client.requests.get", fake_get)
    monkeypatch.setattr("backend.connectors.linkedin_client.requests.post", fake_post)

    result = client.post_to_profile("A summary", "https://github.com/octocat/demo-repo")

    assert result["status"] == "created"
