import json
import os
import requests
from pathlib import Path
from typing import Dict, Optional


class GitHubOAuthError(Exception):
    """Custom exception for GitHub OAuth connector failures."""
    pass


class GitHubOAuthHandler:
    """Handles GitHub OAuth token exchange and repository metadata retrieval."""

    AUTH_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    API_BASE_URL = "https://api.github.com"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> None:
        self.client_id = client_id or os.getenv("GITHUB_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GITHUB_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("GITHUB_REDIRECT_URI")
        self.storage_path = Path(os.getenv("SPARCE_TOKEN_STORE_PATH", Path(__file__).resolve().parents[1] / ".sparce_tokens.json"))
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

    def store_access_token(self, access_token: str) -> None:
        """Persist the access token securely to a local JSON storage file."""
        if not access_token:
            raise GitHubOAuthError("Access token is required for storage.")

        tokens = self._read_tokens()
        tokens["github"] = {"access_token": access_token}
        self._write_tokens(tokens)

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
        except ValueError:
            raise GitHubOAuthError("Unexpected non-JSON response from GitHub token endpoint.")

        token = data.get("access_token")
        if not token:
            raise GitHubOAuthError(f"GitHub token exchange failed: {data}")

        return token

    def get_repo_metadata(self, access_token: str, owner: str, repo: str) -> Dict[str, str]:
        """Fetch repository metadata from GitHub using the access token."""
        if not access_token:
            raise GitHubOAuthError("Access token is required to fetch repository metadata.")

        url = f"{self.API_BASE_URL}/repos/{owner}/{repo}"
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=15,
        )

        if response.status_code != 200:
            raise GitHubOAuthError(
                f"Failed to fetch repository metadata: {response.status_code} {response.text}"
            )

        payload = response.json()
        return {
            "full_name": payload.get("full_name", ""),
            "description": payload.get("description", ""),
            "html_url": payload.get("html_url", ""),
            "default_branch": payload.get("default_branch", ""),
        }

    def list_user_repositories(self, access_token: str) -> Dict[str, str]:
        """Return a simplified list of repositories for the authenticated GitHub user."""
        url = f"{self.API_BASE_URL}/user/repos"
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
            params={"per_page": 100},
            timeout=15,
        )

        if response.status_code != 200:
            raise GitHubOAuthError(
                f"Failed to list repositories: {response.status_code} {response.text}"
            )

        repos = response.json()
        return {repo["full_name"]: repo["html_url"] for repo in repos}
