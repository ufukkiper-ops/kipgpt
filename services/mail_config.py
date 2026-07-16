from services.google_auth import get_fresh_access_token
from services.security import validate_mail_host, validate_mail_port

MAIL_PRESETS = {
    "gmail": {
        "label": "Gmail",
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "hint": "Gmail'de 2 adımlı doğrulama açık olmalı ve Uygulama Şifresi kullanın.",
    },
    "outlook": {
        "label": "Outlook / Hotmail",
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
        "hint": "Microsoft hesabınızın e-posta ve şifresini veya uygulama şifresini kullanın.",
    },
    "yahoo": {
        "label": "Yahoo Mail",
        "imap_server": "imap.mail.yahoo.com",
        "imap_port": 993,
        "smtp_server": "smtp.mail.yahoo.com",
        "smtp_port": 587,
        "hint": "Yahoo hesabınız için uygulama şifresi oluşturmanız gerekebilir.",
    },
    "custom": {
        "label": "Diğer (Manuel IMAP/SMTP)",
        "imap_server": "",
        "imap_port": 993,
        "smtp_server": "",
        "smtp_port": 587,
        "hint": "IMAP ve SMTP sunucu bilgilerinizi kendiniz girin.",
    },
}


def resolve_mail_config_from_account(account, owner_user_id=None):
    if not account:
        return None

    email = (account.get("email") or "").strip()
    if not email:
        return None

    provider = account.get("provider", "custom")

    if provider == "google_oauth":
        access_token, updated = get_fresh_access_token(account)
        if not access_token:
            return None

        if updated and owner_user_id and account.get("id"):
            from services.mail_accounts import update_account_oauth_tokens
            update_account_oauth_tokens(owner_user_id, account["id"], updated)

        preset = MAIL_PRESETS["gmail"]
        return {
            "email": email,
            "auth_type": "oauth",
            "access_token": access_token,
            "imap_server": preset["imap_server"],
            "imap_port": preset["imap_port"],
            "smtp_server": preset["smtp_server"],
            "smtp_port": preset["smtp_port"],
            "account_id": account.get("id"),
        }

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
