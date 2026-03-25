from flask import Blueprint, redirect, request, url_for, session, current_app
from google_auth_oauthlib.flow import Flow
import google.oauth2.credentials
import googleapiclient.discovery
import os

auth_bp = Blueprint("auth", __name__)

# Scope for basic profile + email
SCOPES = ["https://www.googleapis.com/auth/userinfo.email", "openid", "https://www.googleapis.com/auth/userinfo.profile"]

@auth_bp.route("/login")
def login():
    flow = Flow.from_client_secrets_file(
        os.getenv("GOOGLE_CLIENT_SECRET_JSON", "credentials.json"),
        scopes=SCOPES,
        redirect_uri=url_for("auth.callback", _external=True)
    )
    authorization_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
    session["state"] = state
    return redirect(authorization_url)

@auth_bp.route("/callback")
def callback():
    flow = Flow.from_client_secrets_file(
        os.getenv("GOOGLE_CLIENT_SECRET_JSON", "credentials.json"),
        scopes=SCOPES,
        state=session["state"],
        redirect_uri=url_for("auth.callback", _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    session["credentials"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes
    }

    # Extract user info (optional)
    oauth2 = googleapiclient.discovery.build("oauth2", "v2", credentials=creds)
    user_info = oauth2.userinfo().get().execute()
    session["user_email"] = user_info.get("email")

    return redirect(url_for("index"))

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
