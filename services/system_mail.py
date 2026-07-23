"""Uygulama sistem mailleri (şifre sıfırlama vb.) — kullanıcı SMTP hesabı değil."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


class SystemMailError(Exception):
    pass


def _smtp_settings() -> dict:
    host = (os.getenv("SMTP_HOST") or "smtp.gmail.com").strip()
    port = int((os.getenv("SMTP_PORT") or "587").strip() or "587")
    user = (os.getenv("SMTP_USER") or "").strip()
    password = (os.getenv("SMTP_PASSWORD") or "").strip()
    from_addr = (os.getenv("SMTP_FROM") or user).strip()
    if not user or not password or not from_addr:
        raise SystemMailError(
            "Sistem e-posta ayarları eksik. "
            "SMTP_USER, SMTP_PASSWORD ve SMTP_FROM değerlerini .env dosyasına ekleyin."
        )
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_addr": from_addr,
    }


def send_system_email(to: str, subject: str, body: str) -> None:
    """Düz metin sistem e-postası gönder. Hata durumunda SystemMailError."""
    to_addr = (to or "").strip()
    if not to_addr:
        raise SystemMailError("Alıcı e-posta boş.")
    cfg = _smtp_settings()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from_addr"]
    msg["To"] = to_addr
    msg.set_content(body)

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)
    except SystemMailError:
        raise
    except smtplib.SMTPAuthenticationError as exc:
        raise SystemMailError(
            "Gmail SMTP girişi reddedildi. Google hesabında 2 adımlı doğrulama açıkken "
            "normal şifre çalışmaz; Google Hesap > Güvenlik > Uygulama şifreleri ile "
            "16 haneli bir uygulama şifresi oluşturup .env içindeki SMTP_PASSWORD alanına yazın."
        ) from exc
    except Exception as exc:
        raise SystemMailError(f"E-posta gönderilemedi: {exc}") from exc
