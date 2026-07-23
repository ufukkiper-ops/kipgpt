import json
import hashlib
import re

from services.data_paths import ensure_data_dir, users_file_path
DEV_QUICK_USERNAME = "q"
DEV_QUICK_PASSWORD = "q"


def is_dev_quick_login(identifier, password):
    from services.security import allow_dev_quick_login

    if not allow_dev_quick_login():
        return False
    user_key = (identifier or "").strip().lower()
    pass_key = (password or "").strip()
    return user_key == DEV_QUICK_USERNAME and pass_key == DEV_QUICK_PASSWORD


def ensure_dev_quick_mail_accounts():
    """Yalnızca yerel geliştirme. Başka kullanıcılardan şifre kopyalamaz."""
    from services.security import allow_dev_quick_login

    if not allow_dev_quick_login():
        return None

    users = load_users()
    for index, user in enumerate(users):
        if (user.get("email") or "").strip().lower() != DEV_QUICK_USERNAME:
            continue
        user.setdefault("mail_accounts", [])
        user.setdefault("mail_settings", {
            "inbox_fetch_count": 150,
            "auto_spam_filter": False,
            "spam_move_to_folder": False,
            "spam_use_ai": False,
        })
        users[index] = user
        save_users(users)
        return user
    return None


def ensure_dev_quick_user():
    from services.security import allow_dev_quick_login

    if not allow_dev_quick_login():
        return None

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
            return ensure_dev_quick_mail_accounts() or user

    user = {
        "email": DEV_QUICK_USERNAME,
        "username": DEV_QUICK_USERNAME,
        "password": hash_password(DEV_QUICK_PASSWORD),
        "auth_provider": "local",
        "mail_accounts": [],
    }
    users.append(user)
    save_users(users)
    return ensure_dev_quick_mail_accounts() or user


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


def _users_path():
    ensure_data_dir()
    return users_file_path()


def ensure_users_file():
    path = _users_path()
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_users():
    ensure_users_file()
    with open(_users_path(), "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users):
    with open(_users_path(), "w", encoding="utf-8") as f:
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


def create_google_user(email, oauth_tokens, link_mail=False):
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
    if link_mail and oauth_tokens:
        from services.google_auth import _has_gmail_scope
        from services.oauth_mail import upsert_oauth_mail_account

        if _has_gmail_scope(oauth_tokens.get("scopes")):
            upsert_oauth_mail_account(
                email,
                email=email,
                provider_key="google_oauth",
                tokens=oauth_tokens or {},
                label=email,
            )
    return find_user_by_id(email) or user


def link_google_mail_to_user(email, oauth_tokens, link_mail=True):
    users = load_users()
    index = find_user_index_by_email(email)
    if index is None:
        return None

    users[index]["auth_provider"] = "google"
    save_users(users)
    if link_mail and oauth_tokens:
        from services.google_auth import _has_gmail_scope
        from services.oauth_mail import upsert_oauth_mail_account

        if _has_gmail_scope(oauth_tokens.get("scopes")):
            upsert_oauth_mail_account(
                email,
                email=email,
                provider_key="google_oauth",
                tokens=oauth_tokens or {},
                label=email,
            )
    return find_user_by_id(email)
