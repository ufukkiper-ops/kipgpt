from services.security import validate_mail_host, validate_mail_port

MAIL_PRESETS = {
    "gmail": {
        "label": "Gmail",
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "hint": "Gmail için Google Hesabı → Güvenlik → Uygulama Şifresi kullanın.",
        "oauth_provider": "google",
    },
    "outlook": {
        "label": "Outlook / Hotmail",
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "hint": "Outlook için Microsoft uygulama şifresi veya hesap şifrenizi kullanın.",
        "oauth_provider": "microsoft",
    },
    "yahoo": {
        "label": "Yahoo Mail",
        "imap_server": "imap.mail.yahoo.com",
        "imap_port": 993,
        "smtp_server": "smtp.mail.yahoo.com",
        "smtp_port": 587,
        "hint": "Yahoo için hesap ayarlarından uygulama şifresi oluşturun.",
        "oauth_provider": "yahoo",
    },
    "custom": {
        "label": "Diğer (Manuel IMAP/SMTP)",
        "imap_server": "",
        "imap_port": 993,
        "smtp_server": "",
        "smtp_port": 587,
        "hint": "IMAP ve SMTP sunucu bilgilerinizi kendiniz girin.",
        "oauth_provider": None,
    },
}

OAUTH_PROVIDER_MAP = {
    "google_oauth": ("gmail", "google"),
    "microsoft_oauth": ("outlook", "microsoft"),
    "yahoo_oauth": ("yahoo", "yahoo"),
}


def resolve_mail_config_from_account(account, owner_user_id=None):
    if not account:
        return None

    email = (account.get("email") or "").strip()
    if not email:
        return None

    provider = account.get("provider", "custom")

    if provider in OAUTH_PROVIDER_MAP:
        preset_key, _ = OAUTH_PROVIDER_MAP[provider]
        preset = MAIL_PRESETS[preset_key]

        if provider == "google_oauth":
            from services.google_auth import get_fresh_access_token
        elif provider == "microsoft_oauth":
            from services.microsoft_auth import get_fresh_access_token
        else:
            from services.yahoo_auth import get_fresh_access_token

        access_token, updated = get_fresh_access_token(account)
        if not access_token:
            return None

        if updated and owner_user_id and account.get("id"):
            from services.mail_accounts import update_account_oauth_tokens
            update_account_oauth_tokens(owner_user_id, account["id"], updated)
            account = {**account, **updated}

        config = {
            "email": email,
            "auth_type": "oauth",
            "provider": provider,
            "access_token": access_token,
            "refresh_token": account.get("refresh_token") or (updated or {}).get("refresh_token") or "",
            "token_expiry": account.get("token_expiry") or (updated or {}).get("token_expiry"),
            "scopes": account.get("scopes") or (updated or {}).get("scopes") or [],
            "imap_server": preset["imap_server"],
            "imap_port": preset["imap_port"],
            "smtp_server": preset["smtp_server"],
            "smtp_port": preset["smtp_port"],
            "account_id": account.get("id"),
            "owner_user_id": owner_user_id,
        }
        if provider == "google_oauth":
            config["mail_backend"] = "gmail_api"
        return config

    password = account.get("password", "").strip()
    if not password:
        return None

    preset = MAIL_PRESETS.get(provider, MAIL_PRESETS["custom"])

    if provider != "custom":
        return {
            "email": email,
            "password": password,
            "auth_type": "password",
            "imap_server": preset["imap_server"],
            "imap_port": preset["imap_port"],
            "smtp_server": preset["smtp_server"],
            "smtp_port": preset["smtp_port"],
            "account_id": account.get("id"),
        }

    imap_server = account.get("imap_server", "").strip()
    smtp_server = account.get("smtp_server", "").strip()
    if not imap_server or not smtp_server:
        return None

    try:
        imap_server = validate_mail_host(imap_server, label="IMAP sunucu")
        smtp_server = validate_mail_host(smtp_server, label="SMTP sunucu")
        imap_port = validate_mail_port(
            account.get("imap_port") or preset["imap_port"],
            default=993,
            label="IMAP port",
        )
        smtp_port = validate_mail_port(
            account.get("smtp_port") or preset["smtp_port"],
            default=587,
            label="SMTP port",
        )
    except ValueError:
        return None

    return {
        "email": email,
        "password": password,
        "auth_type": "password",
        "imap_server": imap_server,
        "imap_port": imap_port,
        "smtp_server": smtp_server,
        "smtp_port": smtp_port,
        "account_id": account.get("id"),
    }


def resolve_mail_config(user):
    from services.mail_accounts import resolve_active_mail_config
    from flask import session

    config, _account = resolve_active_mail_config(user, session)
    return config
