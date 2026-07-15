import html
import re
from html.parser import HTMLParser


CHARSET_CANDIDATES = (
    "utf-8",
    "utf-8-sig",
    "iso-8859-9",
    "windows-1254",
    "cp1254",
    "iso-8859-1",
    "windows-1252",
    "cp1252",
    "latin-1",
)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip_depth += 1
            return
        if tag == "br":
            self._parts.append("\n")
        elif tag == "p":
            self._parts.append("\n\n")
        elif tag == "li":
            self._parts.append("\n- ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in ("p", "div", "tr", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._parts.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        self._parts.append(data)

    def get_text(self):
        return "".join(self._parts)


def decode_payload(payload, declared_charset=None):
    if not payload:
        return ""

    candidates = []
    if declared_charset:
        candidates.append(declared_charset.replace("ascii", "utf-8"))
    candidates.extend(CHARSET_CANDIDATES)

    seen = set()
    ordered = []
    for enc in candidates:
        key = enc.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(enc)

    best_text = ""
    best_score = -1

    for enc in ordered:
        try:
            text = payload.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue

        replacement_ratio = text.count("\ufffd") / max(len(text), 1)
        control_ratio = sum(1 for c in text if ord(c) < 32 and c not in "\n\r\t") / max(len(text), 1)
        mojibake_hits = len(re.findall(r"[ÃÂâ€]", text))
        score = len(text) - (replacement_ratio * 1000) - (control_ratio * 500) - (mojibake_hits * 2)

        if score > best_score:
            best_score = score
            best_text = text

    if best_text:
        return best_text

    return payload.decode("utf-8", errors="replace")


def html_to_text(raw_html):
    if not raw_html:
        return ""

    cleaned = re.sub(r"(?is)<(script|style|noscript|head)[^>]*>.*?</\1>", "", raw_html)
    cleaned = re.sub(r"(?is)<!--.*?-->", "", cleaned)

    def _replace_link(match):
        href = (match.group(1) or "").strip()
        label = re.sub(r"<[^>]+>", " ", match.group(2) or "")
        label = re.sub(r"\s+", " ", html.unescape(label)).strip()
        if not label:
            return href
        generic = re.match(
            r"^(click here|here|link|online|view|read more|buraya|tıklayın|tiklayin|gidiniz|burayi)$",
            label,
            re.I,
        )
        if generic and href:
            return f"{label}: {href}"
        return label

    cleaned = re.sub(
        r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        _replace_link,
        cleaned,
    )

    parser = _HTMLTextExtractor()
    try:
        parser.feed(cleaned)
        parser.close()
        text = parser.get_text()
    except Exception:
        text = re.sub(r"<[^>]+>", " ", cleaned)

    return html.unescape(text)


PLAIN_STUB_PATTERNS = [
    re.compile(r"e-?posta.{0,30}okuyam", re.I),
    re.compile(r"alıcınız.{0,30}okuyam", re.I),
    re.compile(r"cannot read this (e-?)?mail", re.I),
    re.compile(r"email client.{0,40}(cannot|can't|unable)", re.I),
    re.compile(r"view (this |the )?(email|message).{0,20}(browser|online)", re.I),
    re.compile(r"having trouble viewing", re.I),
    re.compile(r"online görmek", re.I),
    re.compile(r"buraya gidiniz", re.I),
    re.compile(r"display\.php", re.I),
    re.compile(r"jetplatform\.com", re.I),
    re.compile(r"mailchimp\.com/view", re.I),
    re.compile(r"list-manage\.com", re.I),
    re.compile(r"click here to view", re.I),
    re.compile(r"view in (browser|your browser)", re.I),
]

BOILERPLATE_LINE_PATTERNS = [
    re.compile(r"^https?://\S+$", re.I),
    re.compile(r"^mailto:\S+$", re.I),
    re.compile(r"^destekleniyor\.?$", re.I),
    re.compile(r"^supported by\b", re.I),
    re.compile(r"^unsubscribe\b", re.I),
    re.compile(r"^abonelikten çık", re.I),
    re.compile(r"^bu tip e-postalar", re.I),
    re.compile(r"^e-posta alıcınız", re.I),
    re.compile(r"^online görmek için", re.I),
]


def is_plain_text_stub(text):
    if not text:
        return False

    stripped = text.strip()
    if len(stripped) < 10:
        return False

    for pattern in PLAIN_STUB_PATTERNS:
        if pattern.search(stripped):
            return True

    urls = re.findall(r"https?://\S+", stripped)
    without_urls = re.sub(r"https?://\S+", " ", stripped)
    meaningful = re.sub(r"\s+", " ", without_urls).strip()
    lower = stripped.lower()

    if urls and len(meaningful) < 160:
        markers = (
            "okuyam",
            "view",
            "online",
            "browser",
            "display",
            "unsubscribe",
            "desteklen",
            "buraya",
            "gidiniz",
            "supported",
        )
        if any(marker in lower for marker in markers):
            return True

    return False


def _body_quality_score(text):
    if not text:
        return 0

    stripped = text.strip()
    if not stripped:
        return 0

    score = len(stripped)
    urls = len(re.findall(r"https?://", stripped))
    words = len(re.findall(r"\b[\wçğıöşüÇĞİÖŞÜ]{3,}\b", stripped, re.I))
    score += words * 8
    score -= urls * 25

    if is_plain_text_stub(stripped):
        score -= 500

    return score


def _strip_boilerplate_lines(text):
    if not text:
        return ""

    kept = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            kept.append("")
            continue
        if any(pattern.search(stripped) for pattern in BOILERPLATE_LINE_PATTERNS):
            continue
        kept.append(line.rstrip())

    return "\n".join(kept)


def fix_mojibake(text):
    if not text:
        return text

    if re.search(r"[ÃÂâ€]", text):
        try:
            fixed = text.encode("latin-1").decode("utf-8")
            if fixed.count("\ufffd") <= text.count("Ã"):
                text = fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    replacements = {
        "â€™": "'",
        "â€˜": "'",
        "â€œ": '"',
        "â€\x9d": '"',
        "â€”": "—",
        "â€“": "–",
        "Â ": " ",
        "Â·": "·",
        "Â©": "©",
        "Â®": "®",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return text


def clean_mail_body(text):
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = fix_mojibake(text)
    text = html.unescape(text)

    text = text.replace("\u00a0", " ")
    text = text.replace("\u00ad", "")
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", text)

    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if re.match(r"^--[=A-Za-z0-9_\-]{8,}--?$", stripped):
            continue
        if re.match(r"^Content-(Type|Transfer-Encoding|Disposition):", stripped, re.I):
            continue
        if re.match(r"^[A-Za-z0-9+/]{60,}={0,2}$", stripped):
            continue
        if any(pattern.search(stripped) for pattern in BOILERPLATE_LINE_PATTERNS):
            continue
        lines.append(line.rstrip())

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)

    return text.strip()


def normalize_mail_body(plain_text="", html_text=""):
    plain = clean_mail_body(plain_text or "")
    html_plain = clean_mail_body(html_to_text(html_text or "")) if html_text else ""
    plain = _strip_boilerplate_lines(plain)
    html_plain = _strip_boilerplate_lines(html_plain)
    plain = clean_mail_body(plain)
    html_plain = clean_mail_body(html_plain)

    plain_stub = is_plain_text_stub(plain)

    if plain_stub and html_plain:
        return html_plain

    plain_score = _body_quality_score(plain)
    html_score = _body_quality_score(html_plain)

    if html_plain and html_score > plain_score:
        return html_plain

    if plain and not plain_stub:
        return plain

    return html_plain or plain
