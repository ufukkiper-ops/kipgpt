from users import load_users, save_users

DEFAULT_MAIL_SETTINGS = {
    "auto_spam_filter": False,
    "spam_sensitivity": "normal",
    "spam_threshold": 70,
    "spam_move_to_folder": False,
    "spam_use_ai": False,
    "trusted_senders": "",
    "blocked_senders": "",
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

    settings["auto_spam_filter"] = _coerce_bool(settings.get("auto_spam_filter"), True)
    settings["spam_move_to_folder"] = _coerce_bool(settings.get("spam_move_to_folder"), True)
    settings["spam_use_ai"] = _coerce_bool(settings.get("spam_use_ai"), True)

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
    return settings


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
            users[index]["mail_settings"] = settings
            save_users(users)
            return get_mail_settings(users[index])

    raise ValueError("Kullanıcı bulunamadı.")
