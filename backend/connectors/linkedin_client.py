import json
import os
import requests
from pathlib import Path
from typing import Dict, Optional


class LinkedInClientError(Exception):
    """Custom exception for LinkedIn connector failures."""
    pass


class LinkedInClient:
    """Handles LinkedIn OpenID authentication and social post creation."""

    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    PROFILE_URL = "https://api.linkedin.com/v2/me"
    UGC_POST_URL = "https://api.linkedin.com/v2/ugcPosts"

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> None:
        self.client_id = client_id or os.getenv("LINKEDIN_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("LINKEDIN_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("LINKEDIN_REDIRECT_URI")
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
        """Persist the LinkedIn access token securely to a local JSON storage file."""
        if not access_token:
            raise LinkedInClientError("Access token is required for storage.")

        tokens = self._read_tokens()
        tokens["linkedin"] = {"access_token": access_token}
        self._write_tokens(tokens)

    def load_access_token(self) -> Optional[str]:
        """Load the stored LinkedIn access token, if present."""
        tokens = self._read_tokens()
        provider_tokens = tokens.get("linkedin", {})
        return provider_tokens.get("access_token")

    def clear_access_token(self) -> None:
        """Remove the persisted LinkedIn token."""
        tokens = self._read_tokens()
        tokens.pop("linkedin", None)
        self._write_tokens(tokens)

    def build_authorization_url(self, scope: str = "openid profile w_member_social") -> str:
        """Return a LinkedIn authorization URL for OpenID and post permissions."""
        if not self.redirect_uri:
            raise LinkedInClientError("Redirect URI is required to build the authorization URL.")
        if not self.client_id:
            raise LinkedInClientError("LinkedIn client ID is required to build the authorization URL.")

        return (
            f"{self.AUTH_URL}?response_type=code"
            f"&client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope={scope}"
        )

    def exchange_code_for_token(self, code: str) -> str:
        """Exchange the authorization code for a LinkedIn access token."""
        if not code:
            raise LinkedInClientError("Authorization code is required for token exchange.")
        if not self.client_id or not self.client_secret:
            raise LinkedInClientError("LinkedIn client ID and secret must be configured before exchanging the code.")

        response = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )

        try:
            data = response.json()
        except ValueError:
            raise LinkedInClientError("Unexpected non-JSON response from LinkedIn token endpoint.")

        token = data.get("access_token")
        if not token:
            raise LinkedInClientError(f"LinkedIn token exchange failed: {data}")

        return token

    def get_authorized_profile(self, access_token: str) -> Dict[str, str]:
        """Fetch the authenticated user's LinkedIn profile data."""
        if not access_token:
            raise LinkedInClientError("Access token is required to fetch the LinkedIn profile.")

        response = requests.get(
            self.PROFILE_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=15,
        )

        if response.status_code != 200:
            raise LinkedInClientError(
                f"Failed to fetch LinkedIn profile: {response.status_code} {response.text}"
            )

        payload = response.json()
        return {
            "id": payload.get("id", ""),
            "firstName": payload.get("localizedFirstName", ""),
            "lastName": payload.get("localizedLastName", ""),
        }

    def create_ugc_post(self, access_token: str, author_urn: str, text: str) -> Dict[str, str]:
        """Create a LinkedIn UGC post on behalf of the authorized member."""
        if not access_token:
            raise LinkedInClientError("Access token is required to create a LinkedIn post.")
        if not author_urn:
            raise LinkedInClientError("Author URN is required to create a LinkedIn post.")
        if not text:
            raise LinkedInClientError("Post text cannot be empty.")

        body = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "CONNECTIONS"},
        }

        response = requests.post(
            self.UGC_POST_URL,
            json=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            timeout=15,
        )

        if response.status_code not in (201, 202):
            raise LinkedInClientError(
                f"Failed to create LinkedIn post: {response.status_code} {response.text}"
            )

        return response.json()
