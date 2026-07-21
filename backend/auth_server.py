import os
from flask import Flask, request, redirect

try:
    from .connectors.github_oauth import GitHubOAuthHandler
    from .connectors.linkedin_client import LinkedInClient
except ImportError:
    from backend.connectors.github_oauth import GitHubOAuthHandler
    from backend.connectors.linkedin_client import LinkedInClient

app = Flask(__name__)

# Retrieve keys securely from your local .env file
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")

# Replace this with your active Localtunnel base address (e.g., https://xyz.loca.lt)
# DO NOT include a trailing slash
BASE_URL = os.getenv("BASE_URL", "https://legendary-spoon-r4x977g775j4hp7xq-5000.app.github.dev")

github_handler = GitHubOAuthHandler(
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    redirect_uri=f"{BASE_URL}/github-callback",
)
linkedin_client = LinkedInClient(
    client_id=LINKEDIN_CLIENT_ID,
    client_secret=LINKEDIN_CLIENT_SECRET,
    redirect_uri=f"{BASE_URL}/linkedin-callback",
)


@app.route("/")
def home():
    """Kick off the authorization loop by sending the user to GitHub."""
    if not GITHUB_CLIENT_ID:
        return "Error: GITHUB_CLIENT_ID missing from .env configuration.", 500

    return redirect(github_handler.build_authorization_url())


@app.route("/github-callback")
def github_callback():
    """Exchange the GitHub authorization code for a token and continue to LinkedIn."""
    code = request.args.get("code")
    if not code:
        return "Failed to grab authorization code from GitHub.", 400

    try:
        github_token = github_handler.exchange_code_for_token(code)
    except Exception as exc:
        return f"GitHub token exchange failed: {exc}", 400

    github_handler.store_access_token(github_token)
    return redirect(linkedin_client.build_authorization_url())


@app.route("/linkedin-callback")
def linkedin_callback():
    """Exchange the LinkedIn authorization code for a token and finalize the flow."""
    code = request.args.get("code")
    if not code:
        return "Failed to grab authorization code from LinkedIn.", 400

    try:
        linkedin_token = linkedin_client.exchange_code_for_token(code)
    except Exception as exc:
        return f"LinkedIn token exchange failed: {exc}", 400

    linkedin_client.store_access_token(linkedin_token)
    return "<h3>Success! GitHub and LinkedIn accounts are now connected via Sparce.</h3>"


if __name__ == "__main__":
    app.run(port=5000)