import json
import os
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

ROOT_DIR = Path(__file__).resolve().parent.parent
CLIENT_SECRETS_FILE = ROOT_DIR / "google_client_secret.json"

# Kayıt + Gmail senkronu için gerekli izinler
GMAIL_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://mail.google.com/",
]


def _ensure_insecure_transport():
    if os.getenv("OAUTHLIB_INSECURE_TRANSPORT") is None:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def get_redirect_uri():
    return os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://127.0.0.1:5001/auth/google/callback",
    )


def _client_config_from_env():
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None

    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [get_redirect_uri()],
        }
    }


def _client_config_from_file():
    if not CLIENT_SECRETS_FILE.exists():
        return None

    with open(CLIENT_SECRETS_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_client_config():
    # .env veya google_client_secret.json sonradan eklenebilir
    load_dotenv = None
    try:
        from dotenv import load_dotenv as _load_dotenv
        load_dotenv = _load_dotenv
    except ImportError:
        pass

    if load_dotenv:
        load_dotenv(ROOT_DIR / ".env", override=True)

    return _client_config_from_env() or _client_config_from_file()


def is_google_configured():
    return get_client_config() is not None


def get_google_setup_hint():
    return "Google henüz bağlı değil. Önce Google ayarlarını yapın."


def create_oauth_flow():
    _ensure_insecure_transport()

    config = get_client_config()
    if not config:
        raise RuntimeError(get_google_setup_hint())

    return Flow.from_client_config(
        config,
        scopes=GMAIL_SCOPES,
        redirect_uri=get_redirect_uri(),
    )


def build_authorization_url(action="register", force_account_picker=False):
    flow = create_oauth_flow()
    auth_kwargs = {
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "select_account",
    }
    authorization_url, state = flow.authorization_url(**auth_kwargs)
    return authorization_url, state, flow.code_verifier


def exchange_code_for_credentials(flow, authorization_response):
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
        "scopes": list(credentials.scopes or []),
    }


def credentials_from_user_mail(mail_data):
    if not mail_data or mail_data.get("provider") != "google_oauth":
        return None

    refresh_token = mail_data.get("refresh_token")
    if not refresh_token:
        return None

    config = get_client_config()
    if not config:
        return None

    web = config.get("web", config.get("installed", {}))
    creds = Credentials(
        token=mail_data.get("access_token"),
        refresh_token=refresh_token,
        token_uri=web.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=web.get("client_id"),
        client_secret=web.get("client_secret"),
        scopes=mail_data.get("scopes") or GMAIL_SCOPES,
    )

    if mail_data.get("token_expiry"):
        try:
            creds.expiry = datetime.fromisoformat(mail_data["token_expiry"])
            if creds.expiry.tzinfo is None:
                creds.expiry = creds.expiry.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return creds


def get_fresh_access_token(mail_data):
    creds = credentials_from_user_mail(mail_data)
    if not creds or not creds.token:
        return None, None

    updated = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token or mail_data.get("refresh_token"),
        "token_expiry": creds.expiry.isoformat() if creds.expiry else None,
        "scopes": list(creds.scopes or mail_data.get("scopes") or GMAIL_SCOPES),
    }
    return creds.token, updated


def fetch_google_email(access_token):
    import httpx

    response = httpx.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    email = (data.get("email") or "").strip().lower()
    if not email:
        raise RuntimeError("Google hesabından e-posta alınamadı.")
    return email


def flow_for_callback(state, code_verifier):
    _ensure_insecure_transport()

    config = get_client_config()
    if not config:
        raise RuntimeError(get_google_setup_hint())

    flow = Flow.from_client_config(
        config,
        scopes=GMAIL_SCOPES,
        state=state,
        redirect_uri=get_redirect_uri(),
    )
    flow.code_verifier = code_verifier
    return flow
