import json
from pathlib import Path

from backend.connectors.storage import TokenStorage, TokenStorageError


def test_token_storage_saves_and_loads_token(tmp_path):
    storage_file = tmp_path / "tokens.json"
    storage = TokenStorage(storage_path=storage_file)

    storage.save_token("github", "secret-abc123")

    raw = json.loads(storage_file.read_text(encoding="utf-8"))
    assert "github" in raw
    assert isinstance(raw["github"], str)
    assert storage.load_token("github") == "secret-abc123"


def test_token_storage_clears_token(tmp_path):
    storage_file = tmp_path / "tokens.json"
    storage = TokenStorage(storage_path=storage_file)

    storage.save_token("linkedin", "secret-xyz789")
    assert storage.load_token("linkedin") == "secret-xyz789"

    storage.clear_token("linkedin")
    assert storage.load_token("linkedin") is None


def test_token_storage_raises_for_invalid_provider():
    storage = TokenStorage(storage_path=Path("/tmp/tokens.json"))

    try:
        storage.save_token("", "token")
        assert False, "Expected TokenStorageError for empty provider"
    except TokenStorageError:
        pass
