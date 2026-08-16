"""
Handles LinkedIn OAuth. Normally called by setup.py, not run directly.

Reads LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET from environment
variables (set by setup.py) rather than hardcoded values, so nothing
sensitive ever needs to sit in a tracked file.
"""

import http.server
import json
import os
import urllib.parse
import webbrowser
from datetime import datetime, timezone
import requests

CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")

REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "openid profile w_member_social"
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"

received_code = {}


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            received_code["code"] = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Success! You can close this tab and return to the terminal.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code received.")

    def log_message(self, format, *args):
        pass


def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET must be set.")
        print("Run setup.py instead of this file directly.")
        return

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    print("Opening browser for LinkedIn login/consent...")
    print(f"If it doesn't open automatically, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = http.server.HTTPServer(("localhost", 8080), CallbackHandler)
    print("Waiting for LinkedIn to redirect back to localhost:8080 ...")
    server.handle_request()

    if "code" not in received_code:
        print("Did not receive an authorization code. Try again.")
        return

    code = received_code["code"]

    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    token_data = resp.json()
    access_token = token_data["access_token"]

    userinfo_resp = requests.get(
        USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
    )
    userinfo_resp.raise_for_status()
    member_id = userinfo_resp.json()["sub"]
    author_urn = f"urn:li:person:{member_id}"

    token_data["author_urn"] = author_urn
    token_data["authorized_at"] = datetime.now(timezone.utc).isoformat()
    with open("tokens.json", "w") as f:
        json.dump(token_data, f, indent=2)

    print("\nSuccess! Saved to tokens.json")
    print(f"Your author URN: {author_urn}")


if __name__ == "__main__":
    main()
