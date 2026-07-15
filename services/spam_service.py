import json
import re

from services.chat_service import get_client, get_gpt_model
from services.mail_settings import get_spam_thresholds, parse_sender_list

SPAM_KEYWORDS = [
    "kazandınız", "kazandiniz", "winner", "congratulations", "viagra", "cialis",
    "casino", "lottery", "lotarya", "bitcoin", "kripto para", "earn money",
    "click here", "tıkla", "tikla", "bedava", "free iphone", "nigerian prince",
    "hesabınız askıya", "account suspended", "verify your account",
    "şifreniz sıfırlandı", "password reset", "urgent action", "son şans",
    "limited time", "act now", "unsubscribe", "abonelikten çık",
    "promo code", "discount", "% off", "seks", "dating", "weight loss",
    "kredi kartı", "banka hesabı", "paypal", "invoice attached",
    "ödül", "hediye kartı", "gift card", "reklam", "promosyon",
    "newsletter", "bulk mail", "mass mail",
]

VIRUS_KEYWORDS = [
    "virus", "virüs", "virüsü", "virüs tespit", "virus detected",
    "malware", "trojan", "ransomware", "spyware", "adware",
    "phishing", "oltalama", "oltalama e-posta",
    "zararlı yazılım", "zararli yazilim", "zararlı yazilim",
    "bilgisayarınız enfekte", "bilgisayariniz enfekte",
    "cihazınız enfekte", "cihaziniz enfekte",
    "your computer is infected", "your device is infected",
    "malware detected", "security alert", "güvenlik uyarısı",
    "hesabınız hacklendi", "hesabiniz hacklendi", "account hacked",
    "şüpheli aktivite", "supheli aktivite", "suspicious activity",
    "download attachment", "ek dosyayı açın", "macro enabled",
    "bitcoin wallet", "encrypt your files", "dosyalarınız şifrelendi",
]

FORCED_SPAM_PATTERNS = [
    re.compile(r"\bspam\b", re.I),
    re.compile(r"\bspams\b", re.I),
    re.compile(r"\[(?:spam|junk|phishing|virus|virüs)\]", re.I),
    re.compile(r"^\s*spam\s*[:：\-]", re.I),
    re.compile(r"istenmeyen\s+posta", re.I),
    re.compile(r"gereksiz\s+posta", re.I),
    re.compile(r"junk\s*mail", re.I),
]

SUSPICIOUS_SENDER_PATTERNS = [
    r"no-?reply\d*@",
    r"mailer-daemon",
    r"@[\w-]+\.(xyz|top|club|work|click|link|buzz|icu|rest)$",
]


def _mail_text(mail):
    subject = (mail.get("subject") or "").lower()
    content = (mail.get("content") or "").lower()
    sender = (mail.get("sender") or "").lower()
    return subject, content, sender, f"{subject} {content}"


def _sender_matches_list(sender, entries):
    sender = (sender or "").lower()
    for entry in entries:
        if entry in sender or sender.endswith(entry.lstrip("@")):
            return True
    return False


def is_definite_spam(mail):
    subject, content, _sender, text = _mail_text(mail)

    for pattern in FORCED_SPAM_PATTERNS:
        if pattern.search(subject) or pattern.search(content) or pattern.search(text):
            return True

    for keyword in VIRUS_KEYWORDS:
        if keyword in text:
            return True

    return False


def heuristic_spam_score(mail):
    subject, content, sender, text = _mail_text(mail)

    if is_definite_spam(mail):
        return 100

    score = 0

    for keyword in SPAM_KEYWORDS:
        if keyword in text:
            score += 18

    for keyword in VIRUS_KEYWORDS:
        if keyword in text:
            score += 35

    if re.search(r"\bspam\b", text):
        score += 50

    for pattern in SUSPICIOUS_SENDER_PATTERNS:
        if re.search(pattern, sender):
            score += 15

    if subject and subject == subject.upper() and len(subject) > 12:
        score += 12

    if text.count("!") >= 3 or text.count("$") >= 2:
        score += 10

    if re.search(r"https?://[^\s]+", text) and any(
        w in text for w in ("tıkla", "tikla", "click", "kazan", "ücretsiz", "bedava")
    ):
        score += 20

    return min(score, 100)


def classify_spam_batch(mails, settings=None):
    if not mails:
        return {}

    settings = settings or {}
    thresholds = get_spam_thresholds(settings)
    threshold = thresholds["threshold"]
    uncertain_min = thresholds["uncertain_min"]
    uncertain_fallback = thresholds["uncertain_fallback"]

    trusted = parse_sender_list(settings.get("trusted_senders"))
    blocked = parse_sender_list(settings.get("blocked_senders"))

    scores = {m["id"]: heuristic_spam_score(m) for m in mails}
    result = {}

    for mail in mails:
        sender = mail.get("sender", "")

        if _sender_matches_list(sender, blocked):
            result[mail["id"]] = True
            continue

        if _sender_matches_list(sender, trusted):
            result[mail["id"]] = False
            continue

        if is_definite_spam(mail):
            result[mail["id"]] = True
            continue

        result[mail["id"]] = scores[mail["id"]] >= threshold

    uncertain = [
        m for m in mails
        if not result.get(m["id"])
        and uncertain_min <= scores[m["id"]] < threshold
        and not _sender_matches_list(m.get("sender", ""), trusted)
    ]

    if not uncertain or not settings.get("spam_use_ai", True):
        for m in uncertain:
            result[m["id"]] = scores[m["id"]] >= uncertain_fallback
        return result

    client = get_client()
    if client is None:
        for m in uncertain:
            result[m["id"]] = scores[m["id"]] >= uncertain_fallback
        return result

    items = []
    for m in uncertain[:15]:
        items.append({
            "id": m["id"],
            "sender": m.get("sender", ""),
            "subject": (m.get("subject") or "")[:200],
            "snippet": (m.get("content") or "")[:400],
        })

    prompt = f"""Aşağıdaki e-postaları spam olup olmadığına göre sınıflandır.

Spam sayılır: istenmeyen reklam, dolandırıcılık, sahte ödül/borç uyarısı, şüpheli link, toplu pazarlama, virüs/malware uyarısı, phishing.
Spam değil: iş yazışması, müşteri/tedarikçi, resmi kurum, tanıdık kişi, normal bildirim.

Sadece JSON dizisi döndür, başka metin yazma:
[{{"id":"...","spam":true}}]

E-postalar:
{json.dumps(items, ensure_ascii=False)}"""

    try:
        response = client.chat.completions.create(
            model=get_gpt_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = response.choices[0].message.content or ""
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            for item in parsed:
                mail_id = str(item.get("id", ""))
                if mail_id in result:
                    result[mail_id] = bool(item.get("spam"))
    except Exception:
        for m in uncertain:
            result[m["id"]] = scores[m["id"]] >= uncertain_fallback

    return result


def identify_spam_mails(mails, settings=None):
    if not mails:
        return []

    if settings and not settings.get("auto_spam_filter", True):
        return []

    classification = classify_spam_batch(mails, settings)
    return [m for m in mails if classification.get(m["id"], False)]
