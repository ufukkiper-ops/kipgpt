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

    cleaned = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", "", raw_html)
    cleaned = re.sub(r"(?is)<!--.*?-->", "", cleaned)

    parser = _HTMLTextExtractor()
    try:
        parser.feed(cleaned)
        parser.close()
        text = parser.get_text()
    except Exception:
        text = re.sub(r"<[^>]+>", " ", cleaned)

    return html.unescape(text)


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
        lines.append(line.rstrip())

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)

    return text.strip()


def normalize_mail_body(plain_text="", html_text=""):
    plain = clean_mail_body(plain_text or "")
    html_plain = clean_mail_body(html_to_text(html_text or ""))

    if len(plain) >= 20:
        return plain
    if len(html_plain) >= 10:
        return html_plain
    return plain or html_plain
