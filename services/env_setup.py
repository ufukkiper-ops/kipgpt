import json
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"
CLIENT_SECRETS_FILE = ROOT_DIR / "google_client_secret.json"


def save_google_credentials(client_id, client_secret, redirect_uri=None):
    client_id = (client_id or "").strip()
    client_secret = (client_secret or "").strip()
    if not client_id or not client_secret:
        raise ValueError("Client ID ve Client Secret gerekli.")

    redirect_uri = redirect_uri or "http://127.0.0.1:5001/auth/google/callback"
    lines = []
    found = {"GOOGLE_CLIENT_ID": False, "GOOGLE_CLIENT_SECRET": False, "GOOGLE_REDIRECT_URI": False}

    if ENV_FILE.exists():
        with open(ENV_FILE, encoding="utf-8") as f:
            for line in f:
                key = line.split("=", 1)[0].strip()
                if key == "GOOGLE_CLIENT_ID":
                    lines.append(f"GOOGLE_CLIENT_ID={client_id}\n")
                    found["GOOGLE_CLIENT_ID"] = True
                elif key == "GOOGLE_CLIENT_SECRET":
                    lines.append(f"GOOGLE_CLIENT_SECRET={client_secret}\n")
                    found["GOOGLE_CLIENT_SECRET"] = True
                elif key == "GOOGLE_REDIRECT_URI":
                    lines.append(f"GOOGLE_REDIRECT_URI={redirect_uri}\n")
                    found["GOOGLE_REDIRECT_URI"] = True
                else:
                    lines.append(line)

    if not found["GOOGLE_CLIENT_ID"]:
        lines.append(f"GOOGLE_CLIENT_ID={client_id}\n")
    if not found["GOOGLE_CLIENT_SECRET"]:
        lines.append(f"GOOGLE_CLIENT_SECRET={client_secret}\n")
    if not found["GOOGLE_REDIRECT_URI"]:
        lines.append(f"GOOGLE_REDIRECT_URI={redirect_uri}\n")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

    os.environ["GOOGLE_CLIENT_ID"] = client_id
    os.environ["GOOGLE_CLIENT_SECRET"] = client_secret
    os.environ["GOOGLE_REDIRECT_URI"] = redirect_uri


def _extract_web_credentials(config):
    web = config.get("web") or config.get("installed") or {}
    client_id = (web.get("client_id") or "").strip()
    client_secret = (web.get("client_secret") or "").strip()
    if not client_id or not client_secret:
        raise ValueError("JSON dosyasında client_id ve client_secret bulunamadı.")
    return client_id, client_secret


def save_google_credentials_from_json(raw_json, redirect_uri=None):
    try:
        config = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Geçersiz JSON dosyası.") from exc

    client_id, client_secret = _extract_web_credentials(config)
    redirect_uri = redirect_uri or "http://127.0.0.1:5001/auth/google/callback"

    with open(CLIENT_SECRETS_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    save_google_credentials(client_id, client_secret, redirect_uri)
    return client_id


def bootstrap_google_credentials():
    if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"):
        return

    if not CLIENT_SECRETS_FILE.exists():
        return

    try:
        raw = CLIENT_SECRETS_FILE.read_text(encoding="utf-8")
        if "BURAYA_CLIENT_ID" in raw:
            return
        save_google_credentials_from_json(raw)
    except Exception:
        pass
