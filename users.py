import json
import os
import hashlib
import re

USERS_FILE = "users.json"


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
