import re
from datetime import datetime, timezone

from users import get_user_id, load_users, save_users

MAX_CONTACTS = 80
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+", re.I)
DISPLAY_RE = re.compile(r'^"?([^"<]+)"?\s*<([\w\.-]+@[\w\.-]+\.\w+)>$')


def _now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _find_user_index(users, user_id):
    user_id = (user_id or "").strip()
    for index, user in enumerate(users):
        if get_user_id(user) == user_id:
            return index
    return None


def parse_address(display="", email_fallback=""):
    text = (display or "").strip()
    if not text and email_fallback:
        text = email_fallback.strip()

    match = DISPLAY_RE.match(text)
    if match:
        name = match.group(1).strip()
        email = match.group(2).strip().lower()
        return {"email": email, "name": name or email}

    for email in EMAIL_RE.findall(text):
        return {"email": email.lower(), "name": text or email}

    if email_fallback:
        email = email_fallback.strip().lower()
        if EMAIL_RE.fullmatch(email):
            return {"email": email, "name": text or email}

    return None


def extract_addresses_from_text(text):
    contacts = []
    seen = set()
    for email in EMAIL_RE.findall(text or ""):
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        contacts.append({"email": key, "name": key})
    return contacts


def get_mail_contacts(user):
    if not user:
        return []

    contacts = user.get("mail_contacts") or []
    cleaned = []
    seen = set()

    for item in contacts:
        email = (item.get("email") or "").strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        cleaned.append({
            "email": email,
            "name": (item.get("name") or email).strip(),
            "last_used": item.get("last_used") or "",
        })

    cleaned.sort(key=lambda c: c.get("last_used") or "", reverse=True)
    return cleaned[:MAX_CONTACTS]


def remember_contacts(user, entries, own_email=None):
    if not user or not entries:
        return get_mail_contacts(user)

    own_email = (own_email or user.get("email") or "").strip().lower()
    user_id = get_user_id(user)
    users = load_users()
    index = _find_user_index(users, user_id)
    if index is None:
        return []

    existing = {
        (item.get("email") or "").strip().lower(): item
        for item in users[index].get("mail_contacts") or []
        if item.get("email")
    }

    now = _now_iso()
    for entry in entries:
        email = (entry.get("email") or "").strip().lower()
        if not email or email == own_email:
            continue

        name = (entry.get("name") or email).strip()
        current = existing.get(email, {})
        existing[email] = {
            "email": email,
            "name": name or current.get("name") or email,
            "last_used": now,
        }

    merged = sorted(
        existing.values(),
        key=lambda item: item.get("last_used") or "",
        reverse=True,
    )[:MAX_CONTACTS]

    users[index]["mail_contacts"] = merged
    save_users(users)
    return merged


def remember_contacts_from_mails(user, mailler, own_email=None):
    entries = []
    for mail in mailler or []:
        for message in mail.get("thread_messages") or [mail]:
            parsed = parse_address(
                message.get("sender_display", ""),
                message.get("sender", ""),
            )
            if parsed:
                entries.append(parsed)
    return remember_contacts(user, entries, own_email=own_email)


def remember_contacts_from_fields(user, to_email="", cc_email="", bcc_email="", own_email=None):
    entries = []
    for text in (to_email, cc_email, bcc_email):
        entries.extend(extract_addresses_from_text(text))
    return remember_contacts(user, entries, own_email=own_email)
