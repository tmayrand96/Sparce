import json

from backend.connectors.github_oauth import GitHubOAuthHandler


class MockResponse:
    def __init__(self, payload=None, status_code=200, headers=None):
        self._payload = payload or {}
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self._payload


def test_store_token_persists_to_disk(tmp_path):
    handler = GitHubOAuthHandler(storage_path=tmp_path / "tokens.json")

    handler.store_token("abc123")

    stored = json.loads((tmp_path / "tokens.json").read_text(encoding="utf-8"))
    assert stored["github"]["access_token"] == "abc123"


def test_get_user_repos_uses_stored_token(monkeypatch, tmp_path):
    handler = GitHubOAuthHandler(storage_path=tmp_path / "tokens.json")
    handler.store_token("abc123")

    def fake_get(url, headers=None, timeout=15, params=None):
        assert headers["Authorization"] == "Bearer abc123"
        return MockResponse([
            {
                "name": "demo-repo",
                "full_name": "octocat/demo-repo",
                "html_url": "https://github.com/octocat/demo-repo",
                "private": False,
            }
        ])

    monkeypatch.setattr("backend.connectors.github_oauth.requests.get", fake_get)

    repos = handler.get_user_repos()

    assert repos[0]["full_name"] == "octocat/demo-repo"


def test_fetch_repo_content_decodes_base64(monkeypatch, tmp_path):
    handler = GitHubOAuthHandler(storage_path=tmp_path / "tokens.json")
    handler.store_token("abc123")

    def fake_get(url, headers=None, timeout=15):
        assert headers["Authorization"] == "Bearer abc123"
        return MockResponse(
            {
                "path": "README.md",
                "name": "README.md",
                "content": "SGVsbG8gV29ybGQ=",
                "encoding": "base64",
            }
        )

    monkeypatch.setattr("backend.connectors.github_oauth.requests.get", fake_get)

    content = handler.fetch_repo_content("octocat", "demo-repo", "README.md")

    assert content["content"] == "Hello World"


def test_validate_scope_returns_true_for_repo_scope(monkeypatch, tmp_path):
    handler = GitHubOAuthHandler(storage_path=tmp_path / "tokens.json")
    handler.store_token("abc123")

    def fake_get(url, headers=None, timeout=15):
        assert headers["Authorization"] == "Bearer abc123"
        return MockResponse({}, headers={"X-OAuth-Scopes": "repo, user"})

    monkeypatch.setattr("backend.connectors.github_oauth.requests.get", fake_get)

    assert handler.validate_scope() is True
