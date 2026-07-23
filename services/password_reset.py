"""Şifre sıfırlama doğrulama kodları."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from typing import Any

from services.data_paths import password_resets_file_path
from services.system_mail import SystemMailError, send_system_email
from users import find_user

CODE_TTL_SEC = 10 * 60
RATE_LIMIT_SEC = 60
MAX_ATTEMPTS = 5

GENERIC_SENT = (
    "Bu e-posta kayıtlıysa doğrulama kodu gönderildi. "
    "Gelen kutunuzu (ve spam klasörünü) kontrol edin."
)


def _now() -> float:
    return time.time()


def _load() -> dict[str, Any]:
    path = password_resets_file_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict[str, Any]) -> None:
    path = password_resets_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _is_google_only(user: dict) -> bool:
    return user.get("auth_provider") == "google" and not user.get("password")


def request_reset_code(email: str) -> tuple[bool, str]:
    """Kod üretir ve mail atar. (ok, message)."""
    email = (email or "").strip().lower()
    if not email:
        return False, "E-posta adresi gerekli."

    user = find_user(email)
    if not user:
        return True, GENERIC_SENT
    if _is_google_only(user):
        return False, (
            "Bu hesap Google ile oluşturulmuş. "
            "Şifre sıfırlama yerine Google ile giriş yapın."
        )

    store = _load()
    existing = store.get(email) or {}
    last_sent = float(existing.get("sent_at") or 0)
    if last_sent and (_now() - last_sent) < RATE_LIMIT_SEC:
        wait = int(RATE_LIMIT_SEC - (_now() - last_sent)) + 1
        return False, f"Lütfen {wait} saniye sonra tekrar deneyin."

    code = f"{secrets.randbelow(1_000_000):06d}"
    store[email] = {
        "code_hash": _hash_code(code),
        "expires_at": _now() + CODE_TTL_SEC,
        "sent_at": _now(),
        "attempts": 0,
        "verified": False,
    }
    _save(store)

    body = (
        "KipGPT şifre sıfırlama kodunuz:\n\n"
        f"  {code}\n\n"
        "Bu kod 10 dakika geçerlidir. "
        "Bu isteği siz yapmadıysanız bu iletiyi yok sayın.\n"
    )
    try:
        send_system_email(
            email,
            "KipGPT şifre sıfırlama kodu",
            body,
        )
    except SystemMailError as exc:
        store.pop(email, None)
        _save(store)
        return False, str(exc)

    return True, GENERIC_SENT


def verify_reset_code(email: str, code: str) -> tuple[bool, str]:
    email = (email or "").strip().lower()
    code = (code or "").strip()
    if not email or not code:
        return False, "E-posta ve doğrulama kodu gerekli."

    store = _load()
    entry = store.get(email)
    if not entry:
        return False, "Geçersiz veya süresi dolmuş kod."

    if float(entry.get("expires_at") or 0) < _now():
        store.pop(email, None)
        _save(store)
        return False, "Kodun süresi dolmuş. Yeni kod isteyin."

    attempts = int(entry.get("attempts") or 0)
    if attempts >= MAX_ATTEMPTS:
        store.pop(email, None)
        _save(store)
        return False, "Çok fazla hatalı deneme. Yeni kod isteyin."

    if _hash_code(code) != entry.get("code_hash"):
        entry["attempts"] = attempts + 1
        store[email] = entry
        _save(store)
        left = MAX_ATTEMPTS - entry["attempts"]
        return False, f"Kod hatalı. Kalan deneme: {left}."

    entry["verified"] = True
    entry["verified_at"] = _now()
    store[email] = entry
    _save(store)
    return True, "Kod doğrulandı."


def is_reset_verified(email: str) -> bool:
    email = (email or "").strip().lower()
    entry = _load().get(email) or {}
    if not entry.get("verified"):
        return False
    if float(entry.get("expires_at") or 0) < _now():
        return False
    return True


def clear_reset(email: str) -> None:
    email = (email or "").strip().lower()
    store = _load()
    if email in store:
        store.pop(email, None)
        _save(store)
