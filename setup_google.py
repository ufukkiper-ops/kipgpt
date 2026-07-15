#!/usr/bin/env python3
"""Google OAuth bir kez kurulumu. Çalıştırın: py setup_google.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from services.env_setup import save_google_credentials, save_google_credentials_from_json
from services.google_auth import get_redirect_uri

JSON_FILE = ROOT / "google_client_secret.json"


def main():
    print("Kip Asistan — Google tek tıkla kayıt kurulumu (bir kez)\n")

    if JSON_FILE.exists():
        raw = JSON_FILE.read_text(encoding="utf-8")
        if "BURAYA_CLIENT_ID" not in raw:
            save_google_credentials_from_json(raw, get_redirect_uri())
            print("google_client_secret.json bulundu ve kaydedildi.")
            print("Tamam! http://127.0.0.1:5001/register adresinden Google ile kayıt olun.")
            return

    print("Google Cloud Console → Credentials → OAuth client ID → Web application")
    print(f"Redirect URI: {get_redirect_uri()}\n")

    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Hata: Client ID ve Secret gerekli.")
        sys.exit(1)

    save_google_credentials(client_id, client_secret, get_redirect_uri())
    print("\nTamam! Uygulamayı yeniden başlatın.")
    print("Kayıt: http://127.0.0.1:5001/register → Google ile Kayıt Ol")


if __name__ == "__main__":
    main()
