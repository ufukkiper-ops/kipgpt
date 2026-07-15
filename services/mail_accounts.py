import uuid

from services.mail_config import resolve_mail_config_from_account
from users import is_valid_email, load_users, save_users


def _account_id():
    return f"acc_{uuid.uuid4().hex[:8]}"


def _normalize_account(raw, fallback_email=""):
    email = (raw.get("email") or fallback_email or "").strip().lower()
    if not email:
        return None

    account = {
        "id": raw.get("id") or _account_id(),
        "email": email,
        "label": (raw.get("label") or email).strip(),
        "provider": raw.get("provider", "custom"),
        "password": raw.get("password", ""),
        "imap_server": raw.get("imap_server", ""),
        "smtp_server": raw.get("smtp_server", ""),
        "imap_port": str(raw.get("imap_port") or 993),
        "smtp_port": str(raw.get("smtp_port") or 587),
    }

    for key in ("access_token", "refresh_token", "token_expiry", "scopes"):
        if raw.get(key):
            account[key] = raw[key]

    return account


def get_user_mail_accounts(user):
    if not user:
        return []

    if "mail_accounts" in user:
        accounts = user.get("mail_accounts") or []
        return [a for a in (_normalize_account(item) for item in accounts) if a]

    legacy = user.get("mail") or {}
    email = (user.get("email") or user.get("username") or "").strip().lower()
    if not legacy.get("password") and legacy.get("provider") != "google_oauth":
        if not legacy.get("refresh_token"):
            return []

    if not legacy or not email:
        return []

    return [_normalize_account({**legacy, "email": email, "id": "primary", "label": email})]


def persist_mail_accounts(user_id, accounts):
    users = load_users()
    for index, user in enumerate(users):
        if (user.get("email") or user.get("username") or "").strip() == user_id:
            users[index]["mail_accounts"] = accounts
            if accounts and not users[index].get("active_mail_account"):
                users[index]["active_mail_account"] = accounts[0]["id"]
            save_users(users)
            return True
    return False


def ensure_user_mail_accounts(user):
    user_id = (user.get("email") or user.get("username") or "").strip()
    accounts = get_user_mail_accounts(user)
    if user.get("mail_accounts"):
        return accounts

    if accounts:
        persist_mail_accounts(user_id, accounts)
    return accounts


def list_accounts_for_ui(user):
    accounts = ensure_user_mail_accounts(user)
    return [
        {
            "id": a["id"],
            "email": a["email"],
            "label": a.get("label") or a["email"],
            "provider": a.get("provider", "custom"),
        }
        for a in accounts
    ]


def get_account_by_id(user, account_id):
    accounts = ensure_user_mail_accounts(user)
    for account in accounts:
        if account["id"] == account_id:
            return account
    return accounts[0] if accounts else None


def get_active_account_id(user, session):
    accounts = ensure_user_mail_accounts(user)
    if not accounts:
        return None

    account_id = session.get("mail_account_id") or user.get("active_mail_account")
    if account_id and any(a["id"] == account_id for a in accounts):
        return account_id

    return accounts[0]["id"]


def set_active_account(user, session, account_id):
    accounts = ensure_user_mail_accounts(user)
    if not any(a["id"] == account_id for a in accounts):
        return False

    session["mail_account_id"] = account_id
    user_id = (user.get("email") or user.get("username") or "").strip()

    users = load_users()
    for index, item in enumerate(users):
        if (item.get("email") or item.get("username") or "").strip() == user_id:
            users[index]["active_mail_account"] = account_id
            save_users(users)
            return True
    return False


def resolve_active_mail_config(user, session, account_id=None):
    if not user:
        return None, None

    accounts = ensure_user_mail_accounts(user)
    if not accounts:
        return None, None

    owner_user_id = (user.get("email") or user.get("username") or "").strip()
    active_id = account_id or get_active_account_id(user, session)
    account = get_account_by_id(user, active_id)
    if not account:
        return None, None

    config = resolve_mail_config_from_account(account, owner_user_id)
    return config, account


def build_account_from_form(form):
    email = form.get("account_email", "").strip().lower()
    label = form.get("account_label", "").strip()
    provider = form.get("mail_provider", "gmail").strip()
    mail_password = form.get("mail_password", "").strip()
    imap_server = form.get("imap_server", "").strip()
    smtp_server = form.get("smtp_server", "").strip()
    imap_port = form.get("imap_port", "993").strip()
    smtp_port = form.get("smtp_port", "587").strip()

    if not email:
        raise ValueError("E-posta adresi gerekli.")
    if not is_valid_email(email):
        raise ValueError("Geçerli bir e-posta adresi girin.")
    if not mail_password:
        raise ValueError("E-posta şifresi veya uygulama şifresi gerekli.")
    if provider == "custom" and (not imap_server or not smtp_server):
        raise ValueError("Özel sağlayıcı için IMAP ve SMTP sunucularını girin.")

    return _normalize_account({
        "id": _account_id(),
        "email": email,
        "label": label or email,
        "provider": provider,
        "password": mail_password,
        "imap_server": imap_server,
        "smtp_server": smtp_server,
        "imap_port": imap_port,
        "smtp_port": smtp_port,
    })


def add_mail_account(user, form):
    user_id = (user.get("email") or user.get("username") or "").strip()
    accounts = ensure_user_mail_accounts(user)
    new_account = build_account_from_form(form)

    for account in accounts:
        if account["email"] == new_account["email"]:
            raise ValueError("Bu e-posta adresi zaten ekli.")

    accounts.append(new_account)
    persist_mail_accounts(user_id, accounts)
    return new_account


def remove_mail_account(user, account_id):
    user_id = (user.get("email") or user.get("username") or "").strip()
    accounts = ensure_user_mail_accounts(user)

    if len(accounts) <= 1:
        raise ValueError("Son mail hesabı silinemez.")

    accounts = [a for a in accounts if a["id"] != account_id]
    persist_mail_accounts(user_id, accounts)
    return accounts[0]["id"]


def update_account_oauth_tokens(user_id, account_id, token_data):
    users = load_users()
    for index, user in enumerate(users):
        if (user.get("email") or user.get("username") or "").strip() != user_id:
            continue

        accounts = ensure_user_mail_accounts(user)
        updated = False
        for acc_index, account in enumerate(accounts):
            if account["id"] == account_id:
                accounts[acc_index].update(token_data)
                updated = True
                break

        if updated:
            users[index]["mail_accounts"] = accounts
            save_users(users)
            return True
    return False
