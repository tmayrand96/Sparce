import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken


class TokenStorageError(Exception):
    """Raised when token storage cannot be accessed or decrypted."""


class TokenStorage:
    """Encrypted token persistence for provider credentials."""

    DEFAULT_FILENAME = ".sparce_tokens.json"
    DEFAULT_KEY_FILENAME = ".sparce_tokens.key"

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        encryption_key: Optional[str] = None,
    ) -> None:
        env_path = os.getenv("SPARCE_TOKEN_STORE_PATH")
        self.storage_path = Path(storage_path) if storage_path else Path(env_path) if env_path else Path(__file__).resolve().parents[1] / self.DEFAULT_FILENAME
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        env_key = encryption_key or os.getenv("SPARCE_TOKEN_ENCRYPTION_KEY")
        self.key_path = self.storage_path.parent / self.DEFAULT_KEY_FILENAME
        self._key = self._load_or_create_key(env_key)

    def save_token(self, provider: str, token: str) -> None:
        if not provider:
            raise TokenStorageError("Provider name is required to save a token.")
        if not token:
            raise TokenStorageError("Token value is required to save a token.")

        tokens = self._read_tokens()
        tokens[provider.lower()] = self._encrypt_value(token)
        self._write_tokens(tokens)

    def load_token(self, provider: str) -> Optional[str]:
        if not provider:
            raise TokenStorageError("Provider name is required to load a token.")

        tokens = self._read_tokens()
        encrypted_token = tokens.get(provider.lower())
        if not encrypted_token:
            return None

        return self._decrypt_value(encrypted_token)

    def clear_token(self, provider: str) -> None:
        if not provider:
            raise TokenStorageError("Provider name is required to clear a token.")

        tokens = self._read_tokens()
        tokens.pop(provider.lower(), None)
        self._write_tokens(tokens)

    def _encrypt_value(self, value: str) -> str:
        return self._get_fernet().encrypt(value.encode("utf-8")).decode("utf-8")

    def _decrypt_value(self, ciphertext: str) -> str:
        try:
            plaintext = self._get_fernet().decrypt(ciphertext.encode("utf-8"))
        except InvalidToken as exc:
            raise TokenStorageError("Stored token could not be decrypted.") from exc

        return plaintext.decode("utf-8")

    def _read_tokens(self) -> Dict[str, Any]:
        if not self.storage_path.exists():
            return {}

        try:
            with self.storage_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return {}

        if not isinstance(data, dict):
            return {}

        return data

    def _write_tokens(self, tokens: Dict[str, Any]) -> None:
        temp_path = self.storage_path.with_suffix(self.storage_path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(tokens, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())

        temp_path.replace(self.storage_path)

        try:
            os.chmod(self.storage_path, 0o600)
        except OSError:
            pass

    def _load_or_create_key(self, env_key: Optional[str]) -> bytes:
        if env_key:
            key_bytes = env_key.encode("utf-8")
            try:
                return Fernet(key_bytes).encrypt(b"test") and key_bytes
            except (ValueError, TypeError):
                raise TokenStorageError(
                    "SPARCE_TOKEN_ENCRYPTION_KEY must be a valid Fernet key."
                )

        if self.key_path.exists():
            try:
                return self.key_path.read_bytes()
            except OSError as exc:
                raise TokenStorageError("Failed to read the token storage key file.") from exc

        key = Fernet.generate_key()
        try:
            self.key_path.write_bytes(key)
            os.chmod(self.key_path, 0o600)
        except OSError:
            pass

        return key

    def _get_fernet(self) -> Fernet:
        return Fernet(self._key)
