"""Uygulama güvenlik yardımcıları: secret kontrolü, kimlik bilgisi şifreleme, SSRF koruması."""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import os
import socket
import time
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken

ENC_PREFIX = "enc:v1:"
DEFAULT_INSECURE_SECRET = "gizli123"
_SECRET_FIELDS = ("password", "access_token", "refresh_token")


def is_production() -> bool:
    if os.getenv("RENDER"):
        return True
    env = (os.getenv("FLASK_ENV") or os.getenv("ENV") or "").strip().lower()
    return env in {"production", "prod"}


def allow_dev_quick_login() -> bool:
    """q/q ve hesap kopyalama yalnızca açık yerel geliştirmede."""
    if is_production():
        return False
    flag = (os.getenv("ALLOW_DEV_QUICK_LOGIN") or "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return True
    # Yerel varsayılan: kapalı (güvenlik). Açmak için ALLOW_DEV_QUICK_LOGIN=1
    return False


def resolve_flask_secret_key() -> str:
    import secrets as secrets_mod

    secret = (os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY") or "").strip()
    if is_production():
        if not secret or secret == DEFAULT_INSECURE_SECRET:
            # Deploy'u düşürmemek için geçici anahtar; Render Environment'a kalıcı değer koyun.
            ephemeral = secrets_mod.token_urlsafe(48)
            print(
                "WARNING: FLASK_SECRET_KEY missing or insecure (gizli123). "
                "Using ephemeral key. Set a strong FLASK_SECRET_KEY in Render Environment.",
                flush=True,
            )
            return ephemeral
        return secret
    return secret or DEFAULT_INSECURE_SECRET


def _fernet() -> Fernet:
    material = (
        (os.getenv("MAIL_CREDENTIALS_KEY") or "").strip()
        or (os.getenv("FLASK_SECRET_KEY") or "").strip()
        or DEFAULT_INSECURE_SECRET
    )
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if text.startswith(ENC_PREFIX):
        return text
    token = _fernet().encrypt(text.encode("utf-8")).decode("ascii")
    return f"{ENC_PREFIX}{token}"


def decrypt_secret(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if not text.startswith(ENC_PREFIX):
        return text
    token = text[len(ENC_PREFIX) :]
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def encrypt_account_secrets(account: dict) -> dict:
    if not account:
        return account
    out = dict(account)
    for key in _SECRET_FIELDS:
        if out.get(key):
            out[key] = encrypt_secret(str(out[key]))
    return out


def decrypt_account_secrets(account: dict) -> dict:
    if not account:
        return account
    out = dict(account)
    for key in _SECRET_FIELDS:
        if out.get(key):
            out[key] = decrypt_secret(str(out[key]))
    return out


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_mail_host(host: str, *, label: str = "Sunucu") -> str:
    """Özel IMAP/SMTP hedeflerinde SSRF'yi engelle."""
    raw = (host or "").strip()
    if not raw:
        raise ValueError(f"{label} gerekli.")

    cleaned = raw
    if "://" in cleaned:
        parsed = urlparse(cleaned)
        cleaned = parsed.hostname or ""
    cleaned = cleaned.split("/")[0].split("@")[-1].strip().strip("[]")
    if ":" in cleaned and cleaned.count(":") == 1 and not cleaned.startswith("["):
        # host:port
        cleaned = cleaned.split(":", 1)[0]

    if not cleaned:
        raise ValueError(f"Geçersiz {label.lower()}.")

    lowered = cleaned.lower()
    if lowered in {"localhost", "metadata", "metadata.google.internal"}:
        raise ValueError(f"{label} güvenlik nedeniyle reddedildi.")
    if lowered.endswith(".local") or lowered.endswith(".internal"):
        raise ValueError(f"{label} güvenlik nedeniyle reddedildi.")

    try:
        as_ip = ipaddress.ip_address(cleaned)
        if _is_blocked_ip(as_ip):
            raise ValueError(f"{label} güvenlik nedeniyle reddedildi.")
        return cleaned
    except ValueError as exc:
        if "güvenlik nedeniyle" in str(exc):
            raise

    try:
        infos = socket.getaddrinfo(cleaned, None)
    except socket.gaierror as exc:
        raise ValueError(f"{label} çözümlenemedi.") from exc

    if not infos:
        raise ValueError(f"{label} çözümlenemedi.")

    for info in infos:
        ip_str = info[4][0]
        try:
            if _is_blocked_ip(ipaddress.ip_address(ip_str)):
                raise ValueError(f"{label} güvenlik nedeniyle reddedildi.")
        except ValueError as exc:
            if "güvenlik nedeniyle" in str(exc):
                raise

    return cleaned


def validate_mail_port(port_value, *, default: int, label: str = "Port") -> int:
    try:
        port = int(port_value or default)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Geçersiz {label.lower()}.") from exc
    if port < 1 or port > 65535:
        raise ValueError(f"Geçersiz {label.lower()}.")
    # Yaygın mail portları + genel TLS
    allowed = {25, 465, 587, 993, 995, 143, 110, 2525}
    if port not in allowed:
        raise ValueError(f"{label} izin verilen mail portlarından biri olmalı.")
    return port


class SlidingWindowRateLimiter:
    def __init__(self):
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        now = time.time()
        bucket = [t for t in self._hits.get(key, []) if now - t < window_seconds]
        if len(bucket) >= limit:
            raise ValueError("Çok fazla deneme. Lütfen biraz sonra tekrar deneyin.")
        bucket.append(now)
        self._hits[key] = bucket


mail_account_add_limiter = SlidingWindowRateLimiter()
