import re

from users import load_users, save_users

DEFAULT_MAIL_SETTINGS = {
    "auto_spam_filter": False,
    "spam_sensitivity": "normal",
    "spam_threshold": 70,
    "spam_move_to_folder": False,
    "spam_use_ai": False,
    "trusted_senders": "",
    "blocked_senders": "",
    "spam_exempt_ids": "",
    "inbox_fetch_count": 150,
}

SENSITIVITY_PRESETS = {
    "low": {
        "label": "Düşük",
        "threshold": 85,
        "uncertain_min": 40,
        "uncertain_fallback": 65,
        "hint": "Az mail spam sayılır; önemli mailler gelen kutusunda kalır.",
    },
    "normal": {
        "label": "Normal",
        "threshold": 70,
        "uncertain_min": 25,
        "uncertain_fallback": 50,
        "hint": "Dengeli filtreleme (Thunderbird varsayılanına benzer).",
    },
    "high": {
        "label": "Yüksek",
        "threshold": 55,
        "uncertain_min": 15,
        "uncertain_fallback": 40,
        "hint": "Daha agresif filtre; daha çok mail spam klasörüne gider.",
    },
    "custom": {
        "label": "Özel",
        "threshold": 70,
        "uncertain_min": 20,
        "uncertain_fallback": 50,
        "hint": "Eşik değerini kendiniz belirleyin (0-100).",
    },
}


def _coerce_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).lower() in ("1", "true", "on", "yes", "evet")


def get_mail_settings(user):
    raw = (user or {}).get("mail_settings") or {}
    settings = {**DEFAULT_MAIL_SETTINGS, **raw}

    # Varsayılan: otomatik spam taşıma kapalı (her girişte yeniden spam olmasın)
    settings["auto_spam_filter"] = _coerce_bool(settings.get("auto_spam_filter"), False)
    settings["spam_move_to_folder"] = _coerce_bool(settings.get("spam_move_to_folder"), False)
    settings["spam_use_ai"] = _coerce_bool(settings.get("spam_use_ai"), False)

    sensitivity = settings.get("spam_sensitivity", "normal")
    if sensitivity not in SENSITIVITY_PRESETS:
        sensitivity = "normal"
    settings["spam_sensitivity"] = sensitivity

    try:
        settings["spam_threshold"] = max(0, min(100, int(settings.get("spam_threshold", 70))))
    except (TypeError, ValueError):
        settings["spam_threshold"] = 70

    try:
        count = int(settings.get("inbox_fetch_count", 20))
        settings["inbox_fetch_count"] = max(5, min(200, count))
    except (TypeError, ValueError):
        settings["inbox_fetch_count"] = 20

    settings["trusted_senders"] = str(settings.get("trusted_senders") or "")
    settings["blocked_senders"] = str(settings.get("blocked_senders") or "")
    settings["spam_exempt_ids"] = str(settings.get("spam_exempt_ids") or "")
    return settings


def parse_id_list(text):
    items = []
    for part in re.split(r"[\s,;]+", str(text or "")):
        value = part.strip()
        if value:
            items.append(value)
    return items


def add_spam_exempt_ids(user_id, mail_ids):
    """Bir kez işlenen / spam'dan çıkarılan mailleri tekrar otomatik spam'e alma."""
    user_id = (user_id or "").strip()
    ids = []
    for mail_id in mail_ids or []:
        value = str(mail_id or "").strip()
        if value and value not in ids:
            ids.append(value)
    if not user_id or not ids:
        return []

    users = load_users()
    added = []
    for index, user in enumerate(users):
        if (user.get("email") or user.get("username") or "").strip() != user_id:
            continue

        raw = dict(user.get("mail_settings") or {})
        existing = parse_id_list(raw.get("spam_exempt_ids"))
        for mail_id in ids:
            if mail_id not in existing:
                existing.append(mail_id)
                added.append(mail_id)
        # Liste şişmesin
        if len(existing) > 2000:
            existing = existing[-2000:]
        raw["spam_exempt_ids"] = "\n".join(existing)
        users[index]["mail_settings"] = raw
        save_users(users)
        return added

    return []


def get_spam_thresholds(settings):
    settings = get_mail_settings({"mail_settings": settings}) if "auto_spam_filter" not in settings else settings
    sensitivity = settings["spam_sensitivity"]
    preset = SENSITIVITY_PRESETS.get(sensitivity, SENSITIVITY_PRESETS["normal"])

    if sensitivity == "custom":
        threshold = settings["spam_threshold"]
        uncertain_min = max(10, threshold - 30)
        uncertain_fallback = max(uncertain_min + 5, threshold - 15)
    else:
        threshold = preset["threshold"]
        uncertain_min = preset["uncertain_min"]
        uncertain_fallback = preset["uncertain_fallback"]

    return {
        "threshold": threshold,
        "uncertain_min": uncertain_min,
        "uncertain_fallback": uncertain_fallback,
    }


def parse_sender_list(text):
    items = []
    for line in (text or "").splitlines():
        value = line.strip().lower()
        if value:
            items.append(value)
    return items


def normalize_sender_email(sender: str) -> str:
    """Display name / From satırından e-posta adresini çıkarır."""
    import re

    text = (sender or "").strip().lower()
    if not text:
        return ""
    match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", text)
    return (match.group(0) if match else text).strip().lower()


def add_trusted_senders(user_id, senders):
    """Spam Değil sonrası gönderenleri güvenilir listeye ekler; engelli listeden çıkarır."""
    user_id = (user_id or "").strip()
    emails = []
    for sender in senders or []:
        email = normalize_sender_email(sender)
        if email and email not in emails:
            emails.append(email)
    if not user_id or not emails:
        return []

    users = load_users()
    added = []
    for index, user in enumerate(users):
        if (user.get("email") or user.get("username") or "").strip() != user_id:
            continue

        raw = dict(user.get("mail_settings") or {})
        trusted = parse_sender_list(raw.get("trusted_senders"))
        blocked = parse_sender_list(raw.get("blocked_senders"))

        for email in emails:
            if email not in trusted:
                trusted.append(email)
                added.append(email)
            blocked = [
                entry
                for entry in blocked
                if entry != email and email not in entry and entry not in email
            ]

        raw["trusted_senders"] = "\n".join(trusted)
        raw["blocked_senders"] = "\n".join(blocked)
        users[index]["mail_settings"] = raw
        save_users(users)
        return added

    return []


def save_mail_settings(user_id, form):
    sensitivity = form.get("spam_sensitivity", "normal").strip()
    if sensitivity not in SENSITIVITY_PRESETS:
        sensitivity = "normal"

    try:
        threshold = max(0, min(100, int(form.get("spam_threshold", "70"))))
    except ValueError:
        threshold = 70

    try:
        fetch_count = max(5, min(200, int(form.get("inbox_fetch_count", "20"))))
    except ValueError:
        fetch_count = 20

    settings = {
        "auto_spam_filter": _coerce_bool(form.get("auto_spam_filter")),
        "spam_sensitivity": sensitivity,
        "spam_threshold": threshold,
        "spam_move_to_folder": _coerce_bool(form.get("spam_move_to_folder")),
        "spam_use_ai": _coerce_bool(form.get("spam_use_ai")),
        "trusted_senders": form.get("trusted_senders", "").strip(),
        "blocked_senders": form.get("blocked_senders", "").strip(),
        "inbox_fetch_count": fetch_count,
    }

    users = load_users()
    for index, user in enumerate(users):
        if (user.get("email") or user.get("username") or "").strip() == user_id:
            existing = dict(user.get("mail_settings") or {})
            # Formda olmayan kalıcı alanları koru (spam exempt vb.)
            if "spam_exempt_ids" in existing and "spam_exempt_ids" not in settings:
                settings["spam_exempt_ids"] = existing.get("spam_exempt_ids") or ""
            users[index]["mail_settings"] = settings
            save_users(users)
            return get_mail_settings(users[index])

    raise ValueError("Kullanıcı bulunamadı.")
