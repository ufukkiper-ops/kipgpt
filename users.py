import json
import os
import hashlib
import re

USERS_FILE = "users.json"
DEV_QUICK_USERNAME = "q"
DEV_QUICK_PASSWORD = "q"
DEV_QUICK_MAIL_TARGETS = (
    "ufukkiper@pamecarbon.com",
    "info@pamecarbon.com",
)
DEV_QUICK_MAIL_IDS = {
    "ufukkiper@pamecarbon.com": "dev_ufuk_pame",
    "info@pamecarbon.com": "dev_info_pame",
}


def is_dev_quick_login(identifier, password):
    user_key = (identifier or "").strip().lower()
    pass_key = (password or "").strip()
    return user_key == DEV_QUICK_USERNAME and pass_key == DEV_QUICK_PASSWORD


def _find_mail_account_source(email):
    target = (email or "").strip().lower()
    for user in load_users():
        for account in user.get("mail_accounts") or []:
            if (account.get("email") or "").strip().lower() == target and account.get("password"):
                return dict(account)

        legacy = user.get("mail") or {}
        user_email = (user.get("email") or user.get("username") or "").strip().lower()
        if user_email == target and legacy.get("password"):
            return {
                "email": target,
                "label": legacy.get("label") or target,
                "provider": legacy.get("provider", "custom"),
                "password": legacy.get("password", ""),
                "imap_server": legacy.get("imap_server", "mail.pamecarbon.com"),
                "smtp_server": legacy.get("smtp_server", "mail.pamecarbon.com"),
                "imap_port": str(legacy.get("imap_port") or 993),
                "smtp_port": str(legacy.get("smtp_port") or 587),
            }
    return None


def ensure_dev_quick_mail_accounts():
    users = load_users()
    q_index = None
    for index, user in enumerate(users):
        if (user.get("email") or "").strip().lower() == DEV_QUICK_USERNAME:
            q_index = index
            break

    if q_index is None:
        return ensure_dev_quick_user()

    q_user = users[q_index]
    accounts = []

    for target in DEV_QUICK_MAIL_TARGETS:
        source = _find_mail_account_source(target)
        if not source:
            continue

        accounts.append({
            "id": DEV_QUICK_MAIL_IDS.get(target, f"dev_{target.split('@')[0]}"),
            "email": target,
            "label": source.get("label") or target,
            "provider": source.get("provider", "custom"),
            "password": source.get("password", ""),
            "imap_server": source.get("imap_server", "mail.pamecarbon.com"),
            "smtp_server": source.get("smtp_server", "mail.pamecarbon.com"),
            "imap_port": str(source.get("imap_port") or 993),
            "smtp_port": str(source.get("smtp_port") or 587),
        })

    if accounts:
        q_user["mail_accounts"] = accounts
        active = q_user.get("active_mail_account")
        if not active or not any(a["id"] == active for a in accounts):
            q_user["active_mail_account"] = accounts[0]["id"]

    for user in users:
        if (user.get("email") or "").strip().lower() == "ufukkiper@pamecarbon.com":
            if user.get("mail_settings"):
                q_user["mail_settings"] = dict(user["mail_settings"])
            break
    else:
        q_user.setdefault("mail_settings", {
            "inbox_fetch_count": 150,
            "auto_spam_filter": False,
            "spam_move_to_folder": False,
            "spam_use_ai": False,
        })

    users[q_index] = q_user
    save_users(users)
    return q_user


def ensure_dev_quick_user():
    users = load_users()
    for index, user in enumerate(users):
        email = (user.get("email") or "").strip().lower()
        username = (user.get("username") or "").strip().lower()
        if email == DEV_QUICK_USERNAME or username == DEV_QUICK_USERNAME:
            user["email"] = user.get("email") or DEV_QUICK_USERNAME
            user["username"] = DEV_QUICK_USERNAME
            user["password"] = hash_password(DEV_QUICK_PASSWORD)
            user.setdefault("auth_provider", "local")
            user.setdefault("mail_accounts", [])
            users[index] = user
            save_users(users)
            return ensure_dev_quick_mail_accounts()

    user = {
        "email": DEV_QUICK_USERNAME,
        "username": DEV_QUICK_USERNAME,
        "password": hash_password(DEV_QUICK_PASSWORD),
        "auth_provider": "local",
        "mail_accounts": [],
    }
    users.append(user)
    save_users(users)
    return ensure_dev_quick_mail_accounts()


def authenticate_local_user(identifier, password):
    if is_dev_quick_login(identifier, password):
        ensure_dev_quick_user()
        return find_user_by_id(DEV_QUICK_USERNAME)

    user = find_user(identifier)
    if not user:
        return None
    if user.get("auth_provider") == "google" and not user.get("password"):
        return None
    if not check_password(password, user.get("password")):
        return None
    return user


def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_users():
    ensure_users_file()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def check_password(password, hashed):
    if not hashed:
        return False
    return hash_password(password) == hashed


def is_valid_email(email):
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email))


def get_user_id(user):
    return (user.get("email") or user.get("username") or "").strip()


def find_user(identifier):
    identifier = (identifier or "").strip().lower()
    for user in load_users():
        email = (user.get("email") or "").strip().lower()
        username = (user.get("username") or "").strip().lower()
        if identifier == email or identifier == username:
            return user
    return None


def find_user_by_id(user_id):
    user_id = (user_id or "").strip()
    for user in load_users():
        if get_user_id(user) == user_id:
            return user
    return None


def find_user_index_by_email(email):
    email = email.strip().lower()
    for index, user in enumerate(load_users()):
        if (user.get("email") or "").strip().lower() == email:
            return index
    return None


def email_exists(email):
    return find_user_index_by_email(email) is not None


def update_user_mail_tokens(email, token_data):
    users = load_users()
    index = find_user_index_by_email(email)
    if index is None:
        return False

    mail = users[index].setdefault("mail", {})
    mail.update(token_data)
    users[index]["mail"] = mail
    save_users(users)
    return True


def create_google_user(email, oauth_tokens):
    users = load_users()
    user = {
        "email": email,
        "username": email,
        "password": "",
        "auth_provider": "google",
        "mail_accounts": [],
    }
    users.append(user)
    save_users(users)
    return user


def link_google_mail_to_user(email, oauth_tokens):
    users = load_users()
    index = find_user_index_by_email(email)
    if index is None:
        return None

    users[index]["auth_provider"] = "google"
    save_users(users)
    return users[index]
