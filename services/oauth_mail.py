"""Mail hesaplarını OAuth ile bağlama (Gmail / Outlook / Yahoo).

OAuth state dosyaya yazılır — Render'da birden fazla gunicorn worker ile uyumlu.

Gmail / Outlook / Yahoo şifresiz (OAuth) giriş ve hesap bağlama varsayılan olarak kapalıdır.
Mevcut OAuth hesaplarının token yenilemesi çalışmaya devam eder.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from services.mail_accounts import (
    ensure_user_mail_accounts,
    persist_mail_accounts,
    set_active_account,
)
from users import find_user_by_id, load_users, save_users

# Gmail / Outlook / Yahoo OAuth ile giriş ve yeni hesap bağlama kapalı.
# Açmak için ortam değişkeni: OAUTH_LOGIN_ENABLED=1
OAUTH_LOGIN_DISABLED_MESSAGE = (
    "Gmail, Outlook ve Yahoo otomatik (OAuth) girişi kapatıldı. "
    "E-posta ve uygulama şifresi ile ekleyin."
)


def is_oauth_login_enabled() -> bool:
    raw = (os.getenv("OAUTH_LOGIN_ENABLED") or "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


OAUTH_PROVIDERS = {
    "google": {
        "provider_key": "google_oauth",
        "label": "Gmail",
        "preset": "gmail",
    },
    "microsoft": {
        "provider_key": "microsoft_oauth",
        "label": "Outlook",
        "preset": "outlook",
    },
    "yahoo": {
        "provider_key": "yahoo_oauth",
        "label": "Yahoo",
        "preset": "yahoo",
    },
}

_STATE_TTL = 15 * 60
_ROOT = Path(__file__).resolve().parent.parent
_STATE_FILE = Path(os.getenv("OAUTH_STATE_FILE") or (_ROOT / "data" / "oauth_states.json"))


def _account_id():
    return f"acc_{uuid.uuid4().hex[:8]}"


def _ensure_state_dir():
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_states() -> dict:
    _ensure_state_dir()
    if not _STATE_FILE.exists():
        return {}
    try:
        with open(_STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_states(states: dict) -> None:
    _ensure_state_dir()
    tmp = _STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(states, f)
    tmp.replace(_STATE_FILE)


def save_oauth_state(state: str, payload: dict) -> None:
    clean_expired_oauth_states()
    states = _load_states()
    data = dict(payload)
    data["exp"] = time.time() + _STATE_TTL
    states[state] = data
    _save_states(states)


def pop_oauth_state(state: str) -> dict | None:
    clean_expired_oauth_states()
    states = _load_states()
    data = states.pop(state, None)
    _save_states(states)
    return data


def clean_expired_oauth_states() -> None:
    now = time.time()
    states = _load_states()
    dead = [key for key, value in states.items() if (value or {}).get("exp", 0) < now]
    if not dead:
        return
    for key in dead:
        states.pop(key, None)
    _save_states(states)


def upsert_oauth_mail_account(user_id: str, *, email: str, provider_key: str, tokens: dict, label: str = ""):
    """Kullanıcıya OAuth mail hesabı ekler veya aynı e-posta için günceller."""
    email = (email or "").strip().lower()
    if not email:
        raise ValueError("E-posta adresi alınamadı.")
    if not tokens.get("refresh_token") and not tokens.get("access_token"):
        raise ValueError("OAuth jetonları eksik.")

    user = find_user_by_id(user_id)
    if not user:
        raise ValueError("Kullanıcı bulunamadı.")

    accounts = ensure_user_mail_accounts(user)
    existing = None
    for account in accounts:
        if (account.get("email") or "").strip().lower() == email:
            existing = account
            break

    account_id = (existing or {}).get("id") or _account_id()
    account = {
        "id": account_id,
        "email": email,
        "label": (label or (existing or {}).get("label") or email).strip(),
        "provider": provider_key,
        "password": "",
        "imap_server": "",
        "smtp_server": "",
        "imap_port": "993",
        "smtp_port": "587",
        "access_token": tokens.get("access_token") or "",
        "refresh_token": tokens.get("refresh_token") or (existing or {}).get("refresh_token") or "",
        "token_expiry": tokens.get("token_expiry"),
        "scopes": tokens.get("scopes") or [],
    }

    if existing:
        accounts = [account if a.get("id") == account_id else a for a in accounts]
    else:
        accounts.append(account)

    persist_mail_accounts(user_id, accounts)
    set_active_account(find_user_by_id(user_id), {}, account_id)
    return account


def attach_oauth_tokens_to_login_user(email: str, oauth_tokens: dict, provider_key: str = "google_oauth"):
    """Google ile giriş/kayıt sonrası mail hesabını da bağlar."""
    email = (email or "").strip().lower()
    users = load_users()
    for index, user in enumerate(users):
        user_email = (user.get("email") or user.get("username") or "").strip().lower()
        if user_email != email:
            continue
        user_id = (user.get("email") or user.get("username") or "").strip()
        users[index]["auth_provider"] = "google" if provider_key == "google_oauth" else user.get("auth_provider", "local")
        save_users(users)
        return upsert_oauth_mail_account(
            user_id,
            email=email,
            provider_key=provider_key,
            tokens=oauth_tokens,
            label=email,
        )
    return None


def clear_user_oauth_tokens(user_id: str, *, revoke: bool = True) -> int:
    """Kullanıcının OAuth mail tokenlarını siler; isteğe bağlı Google revoke."""
    from services.gmail_api import revoke_google_token

    user = find_user_by_id(user_id)
    if not user:
        return 0

    accounts = ensure_user_mail_accounts(user)
    cleared = 0
    updated = []
    for account in accounts:
        provider = account.get("provider") or ""
        if provider.endswith("_oauth") or provider == "google_oauth":
            if revoke and provider == "google_oauth":
                revoke_google_token(account.get("refresh_token") or account.get("access_token") or "")
            account = dict(account)
            account["access_token"] = ""
            account["refresh_token"] = ""
            account["token_expiry"] = None
            account["scopes"] = []
            cleared += 1
        updated.append(account)

    if cleared:
        persist_mail_accounts(user_id, updated)
    return cleared


def oauth_provider_status():
    enabled = is_oauth_login_enabled()
    if not enabled:
        return {
            "google": {
                "configured": False,
                "enabled": False,
                "label": "Gmail",
                "hint": "OAuth kapalı; uygulama şifresi ile ekleyin.",
            },
            "microsoft": {
                "configured": False,
                "enabled": False,
                "label": "Outlook",
                "hint": "OAuth kapalı; uygulama şifresi ile ekleyin.",
            },
            "yahoo": {
                "configured": False,
                "enabled": False,
                "label": "Yahoo",
                "hint": "OAuth kapalı; uygulama şifresi ile ekleyin.",
            },
        }

    from services.google_auth import is_google_configured
    from services.microsoft_auth import is_microsoft_configured
    from services.yahoo_auth import is_yahoo_configured

    return {
        "google": {
            "configured": is_google_configured(),
            "enabled": True,
            "label": "Gmail",
            "hint": "Google hesabınızla şifresiz bağlanır; Gmail API ile senkronize olur.",
        },
        "microsoft": {
            "configured": is_microsoft_configured(),
            "enabled": True,
            "label": "Outlook",
            "hint": "Microsoft hesabınızla şifresiz bağlanır (Outlook / Hotmail / Live).",
        },
        "yahoo": {
            "configured": is_yahoo_configured(),
            "enabled": True,
            "label": "Yahoo",
            "hint": "Yahoo hesabınızla şifresiz bağlanır ve otomatik senkronize olur.",
        },
    }
