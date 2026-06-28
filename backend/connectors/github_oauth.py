import base64
import json
import os
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional


class GitHubOAuthError(Exception):
    """Custom exception for GitHub OAuth connector failures."""
    pass


class GitHubOAuthHandler:
    """Handles GitHub OAuth token exchange and repository content retrieval."""

    AUTH_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    API_BASE_URL = "https://api.github.com"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        storage_path: Optional[Path] = None,
    ) -> None:
        self.client_id = client_id or os.getenv("GITHUB_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GITHUB_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("GITHUB_REDIRECT_URI")
        if storage_path is None:
            env_path = os.getenv("SPARCE_TOKEN_STORE_PATH")
            self.storage_path = Path(env_path) if env_path else Path(__file__).resolve().parents[1] / ".sparce_tokens.json"
        else:
            self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_tokens(self) -> Dict[str, Dict[str, str]]:
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

    def _write_tokens(self, tokens: Dict[str, Dict[str, str]]) -> None:
        with self.storage_path.open("w", encoding="utf-8") as handle:
            json.dump(tokens, handle, indent=2)

        try:
            os.chmod(self.storage_path, 0o600)
        except OSError:
            pass

    def load_access_token(self) -> Optional[str]:
        """Load the stored GitHub access token, if present."""
        tokens = self._read_tokens()
        provider_tokens = tokens.get("github", {})
        return provider_tokens.get("access_token")

    def clear_access_token(self) -> None:
        """Remove the persisted GitHub token."""
        tokens = self._read_tokens()
        tokens.pop("github", None)
        self._write_tokens(tokens)

    def build_authorization_url(self, scope: str = "repo,user") -> str:
        """Return a GitHub user authorization URL."""
        if not self.redirect_uri:
            raise GitHubOAuthError("Redirect URI is required to build the authorization URL.")
        if not self.client_id:
            raise GitHubOAuthError("GitHub client ID is required to build the authorization URL.")

        return (
            f"{self.AUTH_URL}?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope={scope}"
        )

    def exchange_code_for_token(self, code: str) -> str:
        """Exchange an OAuth code for a GitHub access token."""
        if not code:
            raise GitHubOAuthError("Authorization code is required for token exchange.")
        if not self.client_id or not self.client_secret:
            raise GitHubOAuthError("GitHub client ID and secret must be configured before exchanging the code.")

        response = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "redirect_uri": self.redirect_uri,
            },
            headers={"Accept": "application/json"},
            timeout=15,
        )

        try:
            data = response.json()
        except ValueError as exc:
            raise GitHubOAuthError("Unexpected non-JSON response from GitHub token endpoint.") from exc

        token = data.get("access_token")
        if not token:
            raise GitHubOAuthError(f"GitHub token exchange failed: {data}")

        return token

    def store_token(self, token: str) -> None:
        """Persist an access token securely to a local JSON storage file."""
        if not token:
            raise GitHubOAuthError("Access token is required for storage.")

        tokens = self._read_tokens()
        tokens["github"] = {"access_token": token}
        self._write_tokens(tokens)

    def store_access_token(self, access_token: str) -> None:
        """Backward-compatible alias for storing a GitHub access token."""
        self.store_token(access_token)

    def get_user_repos(self) -> List[Dict[str, Any]]:
        """List the authenticated user's repositories."""
        token = self.load_access_token()
        if not token:
            raise GitHubOAuthError("Access token is required to list repositories.")

        response = requests.get(
            f"{self.API_BASE_URL}/user/repos",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            params={"per_page": 100},
            timeout=15,
        )

        if response.status_code != 200:
            raise GitHubOAuthError(f"Failed to list repositories: {response.status_code} {response.text}")

        payload = response.json()
        if not isinstance(payload, list):
            return []

        return payload

    def fetch_repo_content(self, owner: str, repo: str, path: str) -> Dict[str, Any]:
        """Retrieve the contents of a repository file."""
        token = self.load_access_token()
        if not token:
            raise GitHubOAuthError("Access token is required to fetch repository content.")

        response = requests.get(
            f"{self.API_BASE_URL}/repos/{owner}/{repo}/contents/{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=15,
        )
        if response.status_code != 200:
            raise GitHubOAuthError(f"Failed to fetch repository content: {response.status_code} {response.text}")

        payload = response.json()
        content = payload.get("content", "")
        if payload.get("encoding") == "base64":
            try:
                content = base64.b64decode(content).decode("utf-8")
            except (ValueError, UnicodeDecodeError):
                content = payload.get("content", "")

        return {
            "path": payload.get("path", path),
            "name": payload.get("name", path),
            "content": content,
        }

    def validate_scope(self) -> bool:
        """Ensure the GitHub token includes the repo scope."""
        token = self.load_access_token()
        if not token:
            raise GitHubOAuthError("Access token is required to validate scopes.")

        response = requests.get(
            f"{self.API_BASE_URL}/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=15,
        )
        if response.status_code != 200:
            raise GitHubOAuthError(f"Failed to validate scopes: {response.status_code} {response.text}")

        scopes = response.headers.get("X-OAuth-Scopes", "")
        return any(scope.strip() == "repo" for scope in scopes.split(","))

    def get_repo_metadata(self, access_token: str, owner: str, repo: str) -> Dict[str, str]:
        """Fetch repository metadata from GitHub using the access token."""
        if not access_token:
            raise GitHubOAuthError("Access token is required to fetch repository metadata.")

        response = requests.get(
            f"{self.API_BASE_URL}/repos/{owner}/{repo}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=15,
        )

        if response.status_code != 200:
            raise GitHubOAuthError(f"Failed to fetch repository metadata: {response.status_code} {response.text}")

        payload = response.json()
        return {
            "full_name": payload.get("full_name", ""),
            "description": payload.get("description", ""),
            "html_url": payload.get("html_url", ""),
            "default_branch": payload.get("default_branch", ""),
        }

