import os
from flask import Flask, request, redirect
import requests

app = Flask(__name__)

# Retrieve keys securely from your local .env file
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("os.getenv("GITHUB_CLIENT_SECRET")")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")

# Replace this with your active Localtunnel base address (e.g., https://xyz.loca.lt)
# DO NOT include a trailing slash
BASE_URL = "https://legendary-spoon-r4x977g775j4hp7xq-5000.app.github.dev"

@app.route('/')
def home():
    """Step 1: Kick off the authorization loop by sending you to GitHub."""
    if not GITHUB_CLIENT_ID:
        return "Error: GITHUB_CLIENT_ID missing from .env configuration."
        
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={BASE_URL}/github-callback"
        f"&scope=repo,user"
    )
    return redirect(github_auth_url)

@app.route('/github-callback')
def github_callback():
    """Step 2: Catch GitHub's code, swap it for a token, then pass you to LinkedIn."""
    code = request.args.get('code')
    if not code:
        return "Failed to grab authorization code from GitHub.", 400

    # Exchange temporary code for permanent GitHub Access Token
    token_response = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code
        },
        headers={"Accept": "application/json"}
    ).json()

    github_token = token_response.get("access_token")
    if not github_token:
        return f"GitHub token exchange failed: {token_response}", 400

    # TODO: Securely save github_token to a database session or local securely tracked file

    # Forward immediately to LinkedIn to grant posting access
    linkedin_auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={BASE_URL}/linkedin-callback"
        f"&scope=w_member_social,openid,profile"
    )
    return redirect(linkedin_auth_url)

@app.route('/linkedin-callback')
def linkedin_callback():
    """Step 3: Catch LinkedIn's code and finalize the dual token handshake."""
    code = request.args.get('code')
    if not code:
        return "Failed to grab authorization code from LinkedIn.", 400

    # Exchange temporary code for permanent LinkedIn Access Token
    token_response = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": LINKEDIN_CLIENT_ID,
            "client_secret": LINKEDIN_CLIENT_SECRET,
            "redirect_uri": f"{BASE_URL}/linkedin-callback"
        }
    ).json()

    linkedin_token = token_response.get("access_token")
    if not linkedin_token:
        return f"LinkedIn token exchange failed: {token_response}", 400

    # TODO: Securely save linkedin_token 

    return "<h3>Success! GitHub and LinkedIn accounts are now connected via Sparce.</h3>"

if __name__ == '__main__':
    # Fires up the local server listening on port 5000
    app.run(port=5000)