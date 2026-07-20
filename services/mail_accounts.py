import uuid

from services.mail_config import resolve_mail_config_from_account
from services.security import (
    decrypt_account_secrets,
    encrypt_account_secrets,
    validate_mail_host,
    validate_mail_port,
)
from users import is_valid_email, load_users, save_users

MAX_MAIL_ACCOUNTS_PER_USER = 10


def _account_id():
    return f"acc_{uuid.uuid4().hex[:8]}"


def _normalize_account(raw, fallback_email=""):
    email = (raw.get("email") or fallback_email or "").strip().lower()
    if not email:
        return None

    decrypted = decrypt_account_secrets(raw)
    account = {
        "id": raw.get("id") or _account_id(),
        "email": email,
        "label": (raw.get("label") or email).strip(),
        "provider": raw.get("provider", "custom"),
        "password": decrypted.get("password", ""),
        "imap_server": raw.get("imap_server", ""),
        "smtp_server": raw.get("smtp_server", ""),
        "imap_port": str(raw.get("imap_port") or 993),
        "smtp_port": str(raw.get("smtp_port") or 587),
    }

    for key in ("access_token", "refresh_token", "token_expiry", "scopes"):
        if decrypted.get(key) or raw.get(key):
            account[key] = decrypted.get(key, raw.get(key))

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
    sealed = [encrypt_account_secrets(dict(a)) for a in accounts]
    for index, user in enumerate(users):
        if (user.get("email") or user.get("username") or "").strip() == user_id:
            users[index]["mail_accounts"] = sealed
            if sealed:
                active = users[index].get("active_mail_account")
                if not active or not any(a.get("id") == active for a in sealed):
                    users[index]["active_mail_account"] = sealed[0]["id"]
            else:
                users[index]["active_mail_account"] = ""
                # Eski tek-hesap alanını da temizle; yoksa hesap geri gelebilir
                if "mail" in users[index]:
                    users[index]["mail"] = {}
            save_users(users)
            return True
    return False


def ensure_user_mail_accounts(user):
    user_id = (user.get("email") or user.get("username") or "").strip()
    accounts = get_user_mail_accounts(user)
    if "mail_accounts" in (user or {}):
        # Eski düz metin kayıtları şifreli forma geçir
        needs_seal = False
        for raw in user.get("mail_accounts") or []:
            pwd = (raw.get("password") or "")
            if pwd and not str(pwd).startswith("enc:v1:"):
                needs_seal = True
                break
            refresh = (raw.get("refresh_token") or "")
            if refresh and not str(refresh).startswith("enc:v1:"):
                needs_seal = True
                break
        if needs_seal and accounts:
            persist_mail_accounts(user_id, accounts)
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
    if not accounts:
        return None
    if not account_id:
        return accounts[0]
    for account in accounts:
        if account["id"] == account_id:
            return account
    return None


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
    account_id = (account_id or "").strip()
    user_id = (user.get("email") or user.get("username") or "").strip()

    if not account_id:
        session.pop("mail_account_id", None)
        users = load_users()
        for index, item in enumerate(users):
            if (item.get("email") or item.get("username") or "").strip() == user_id:
                users[index]["active_mail_account"] = ""
                save_users(users)
                return True
        return False

    if not any(a["id"] == account_id for a in accounts):
        return False

    session["mail_account_id"] = account_id

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
    if account_id:
        account = get_account_by_id(user, account_id)
        if not account:
            return None, None
    else:
        active_id = get_active_account_id(user, session)
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
    if provider == "custom":
        if not imap_server or not smtp_server:
            raise ValueError("Özel sağlayıcı için IMAP ve SMTP sunucularını girin.")
        imap_server = validate_mail_host(imap_server, label="IMAP sunucu")
        smtp_server = validate_mail_host(smtp_server, label="SMTP sunucu")
        imap_port = str(validate_mail_port(imap_port, default=993, label="IMAP port"))
        smtp_port = str(validate_mail_port(smtp_port, default=587, label="SMTP port"))

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


def verify_mail_account_login(account):
    """IMAP ile kimlik doğrulaması yapmadan hesabı kaydetme."""
    from mail import connect_mail

    config = resolve_mail_config_from_account(account)
    if not config:
        raise ValueError("Mail yapılandırması geçersiz.")
    mail = connect_mail(config, "INBOX")
    try:
        mail.logout()
    except Exception:
        pass


def add_mail_account(user, form):
    user_id = (user.get("email") or user.get("username") or "").strip()
    accounts = ensure_user_mail_accounts(user)
    if len(accounts) >= MAX_MAIL_ACCOUNTS_PER_USER:
        raise ValueError(f"En fazla {MAX_MAIL_ACCOUNTS_PER_USER} mail hesabı eklenebilir.")

    new_account = build_account_from_form(form)

    for account in accounts:
        if account["email"] == new_account["email"]:
            raise ValueError("Bu e-posta adresi zaten ekli.")

    try:
        verify_mail_account_login(new_account)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Mail girişi başarısız: {exc}") from exc

    accounts.append(new_account)
    persist_mail_accounts(user_id, accounts)
    return new_account


class _MappingForm:
    """dict tabanlı form benzeri sarmalayıcı (mobil API için)."""

    def __init__(self, data):
        self._data = data or {}

    def get(self, key, default=""):
        value = self._data.get(key, default)
        if value is None:
            return default
        return str(value)


def add_mail_account_from_data(user, data):
    return add_mail_account(user, _MappingForm(data))


def remove_mail_account(user, account_id):
    user_id = (user.get("email") or user.get("username") or "").strip()
    accounts = ensure_user_mail_accounts(user)
    account_id = (account_id or "").strip()
    if not account_id:
        raise ValueError("Silinecek hesap seçilmedi.")

    remaining = [a for a in accounts if a["id"] != account_id]
    if len(remaining) == len(accounts):
        raise ValueError("Mail hesabı bulunamadı veya zaten silinmiş.")

    persist_mail_accounts(user_id, remaining)
    return remaining[0]["id"] if remaining else ""


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
            users[index]["mail_accounts"] = [encrypt_account_secrets(dict(a)) for a in accounts]
            save_users(users)
            return True
    return False
