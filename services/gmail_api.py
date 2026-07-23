"""Gmail API istemcisi (resmi google-api-python-client).

Google OAuth ile bağlı hesaplarda IMAP yerine Gmail API kullanır:
listeleme, detay, gönder, taslak, yıldızlı, okunmamış, spam, çöp, arama.
"""

from __future__ import annotations

import base64
import email
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime

from mail import (
    decode_mail_header,
    extract_attachments,
    extract_body,
    format_mail_date,
    parse_message,
    _extract_address_list,
    _normalize_message_id,
    _parse_date_ts,
    _extract_reference_ids,
)

FOLDER_QUERIES = {
    "inbox": "in:inbox",
    "starred": "is:starred",
    "unread": "is:unread",
    "sent": "in:sent",
    "drafts": "in:drafts",
    "spam": "in:spam",
    "trash": "in:trash",
    "archive": "in:archive OR -in:inbox -in:sent -in:drafts -in:spam -in:trash",
}


class GmailApiError(Exception):
    """Kullanıcıya gösterilebilir Gmail API hatası."""

    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


def is_gmail_api_config(config) -> bool:
    if not config:
        return False
    if config.get("mail_backend") == "gmail_api":
        return True
    return config.get("provider") == "google_oauth" and bool(config.get("access_token"))


def _user_friendly_error(exc: Exception) -> str:
    text = str(exc or "").strip()
    lower = text.lower()
    if "invalid_grant" in lower or "token" in lower and "expired" in lower:
        return (
            "Google oturumu süresi doldu veya iptal edildi. "
            "Mail → Hesap Ekle → Gmail ile tekrar bağlayın."
        )
    if "insufficient" in lower or "403" in lower:
        return "Gmail izni yetersiz. Gmail hesabını yeniden bağlayıp tüm izinleri onaylayın."
    if "404" in lower or "not found" in lower:
        return "İstenen mail bulunamadı veya silinmiş olabilir."
    if "quota" in lower or "rate" in lower:
        return "Gmail API kotası aşıldı. Birkaç dakika sonra tekrar deneyin."
    if not text:
        return "Gmail işlemi başarısız oldu. Lütfen tekrar deneyin."
    return f"Gmail hatası: {text[:240]}"


def build_gmail_service(config):
    """Credentials + Gmail API v1 service döndürür; gerekirse token yeniler."""
    from googleapiclient.discovery import build
    from services.google_auth import credentials_from_user_mail, get_fresh_access_token

    mail_data = {
        "provider": "google_oauth",
        "access_token": config.get("access_token"),
        "refresh_token": config.get("refresh_token"),
        "token_expiry": config.get("token_expiry"),
        "scopes": config.get("scopes"),
    }
    creds = credentials_from_user_mail(mail_data)
    if not creds:
        # Yalnızca access_token varsa dene
        token, updated = get_fresh_access_token(mail_data)
        if not token:
            raise GmailApiError(
                "Gmail bağlantısı geçersiz. Hesabı yeniden bağlayın."
            )
        if updated:
            config.update({
                "access_token": updated.get("access_token") or token,
                "refresh_token": updated.get("refresh_token") or config.get("refresh_token"),
                "token_expiry": updated.get("token_expiry"),
                "scopes": updated.get("scopes") or config.get("scopes"),
            })
            mail_data.update(updated)
            mail_data["access_token"] = token
        creds = credentials_from_user_mail(mail_data)
        if not creds:
            raise GmailApiError("Gmail kimlik bilgileri oluşturulamadı.")

    # Yenilenen token'ı config'e yaz
    if creds.token:
        config["access_token"] = creds.token
    if creds.refresh_token:
        config["refresh_token"] = creds.refresh_token
    if creds.expiry:
        from services.google_auth import _naive_utc_expiry

        expiry = _naive_utc_expiry(creds.expiry)
        config["token_expiry"] = expiry.isoformat() if expiry else None

    try:
        return build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception as exc:
        raise GmailApiError(_user_friendly_error(exc)) from exc


def _headers_map(payload) -> dict:
    headers = {}
    for item in (payload or {}).get("headers") or []:
        name = (item.get("name") or "").lower()
        if name:
            headers[name] = item.get("value") or ""
    return headers


def _decode_body_data(data: str) -> bytes:
    if not data:
        return b""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _collect_parts(payload, parts_out):
    if not payload:
        return
    body = payload.get("body") or {}
    data = body.get("data")
    mime = (payload.get("mimeType") or "").lower()
    filename = payload.get("filename") or ""
    if data:
        parts_out.append({
            "mime": mime,
            "filename": filename,
            "data": _decode_body_data(data),
            "attachment_id": body.get("attachmentId"),
        })
    for child in payload.get("parts") or []:
        _collect_parts(child, parts_out)


def _raw_rfc822_from_message(service, message_id: str) -> bytes:
    result = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="raw")
        .execute()
    )
    raw = result.get("raw") or ""
    return _decode_body_data(raw)


def _message_to_mail_dict(service, msg_meta: dict, *, full: bool = False) -> dict:
    msg_id = msg_meta.get("id") or ""
    thread_id = msg_meta.get("threadId") or ""
    label_ids = set(msg_meta.get("labelIds") or [])

    if full or not msg_meta.get("payload"):
        raw = _raw_rfc822_from_message(service, msg_id)
        parsed = parse_message(raw, thread_id=thread_id)
    else:
        # metadata-only fallback (list view may use this path rarely)
        headers = _headers_map(msg_meta.get("payload") or {})
        subject = decode_mail_header(headers.get("subject"))
        sender_display, sender_emails = _extract_address_list(headers.get("from"))
        to_display, to_emails = _extract_address_list(headers.get("to"))
        cc_display, cc_emails = _extract_address_list(headers.get("cc"))
        date_hdr = headers.get("date")
        snippet = msg_meta.get("snippet") or ""
        parsed = {
            "subject": subject,
            "sender_display": sender_display,
            "sender": sender_emails[0] if sender_emails else sender_display,
            "to": to_display,
            "to_emails": to_emails,
            "cc": cc_display,
            "cc_emails": cc_emails,
            "date": format_mail_date(date_hdr),
            "date_ts": _parse_date_ts(date_hdr),
            "content": snippet,
            "attachments": [],
            "thread_id": thread_id,
            "message_id": _normalize_message_id(headers.get("message-id")),
            "in_reply_to": _normalize_message_id(headers.get("in-reply-to")),
            "reference_ids": [],
        }

    parsed["id"] = msg_id
    parsed["thread_id"] = thread_id or parsed.get("thread_id") or ""
    parsed["unread"] = "UNREAD" in label_ids
    parsed["starred"] = "STARRED" in label_ids
    parsed["label_ids"] = list(label_ids)
    return parsed


def list_mails(config, folder: str = "inbox", count: int = 20, search: str = ""):
    try:
        service = build_gmail_service(config)
        base_q = FOLDER_QUERIES.get(folder) or FOLDER_QUERIES["inbox"]
        query = base_q
        search = (search or "").strip()
        if search:
            # Kullanıcı Gmail arama sözdizimi de yazabilir
            if any(token in search.lower() for token in ("from:", "to:", "subject:", "after:", "before:", "is:", "in:", "label:")):
                query = f"({base_q}) ({search})"
            else:
                # Serbest metin → gönderen/konu/gövde
                safe = search.replace('"', "")
                query = f'({base_q}) (from:{safe} OR subject:{safe} OR "{safe}")'

        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=min(max(count, 1), 100))
            .execute()
        )
        items = response.get("messages") or []
        result = []
        for item in items:
            try:
                full = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=item["id"],
                        format="raw",
                    )
                    .execute()
                )
                raw = _decode_body_data(full.get("raw") or "")
                parsed = parse_message(raw, thread_id=full.get("threadId") or item.get("threadId"))
                parsed["id"] = item["id"]
                labels = set(full.get("labelIds") or [])
                parsed["unread"] = "UNREAD" in labels
                parsed["starred"] = "STARRED" in labels
                parsed["label_ids"] = list(labels)
                result.append(parsed)
            except Exception as exc:
                print("GMAIL LIST ITEM HATASI:", exc)
                continue
        return result
    except GmailApiError:
        raise
    except Exception as exc:
        raise GmailApiError(_user_friendly_error(exc)) from exc


def get_mail(config, mail_id: str):
    try:
        service = build_gmail_service(config)
        full = (
            service.users()
            .messages()
            .get(userId="me", id=mail_id, format="raw")
            .execute()
        )
        raw = _decode_body_data(full.get("raw") or "")
        parsed = parse_message(raw, thread_id=full.get("threadId"))
        parsed["id"] = mail_id
        labels = set(full.get("labelIds") or [])
        parsed["unread"] = "UNREAD" in labels
        parsed["starred"] = "STARRED" in labels
        parsed["label_ids"] = list(labels)
        return parsed
    except GmailApiError:
        raise
    except Exception as exc:
        raise GmailApiError(_user_friendly_error(exc)) from exc


def _build_mime(config, to_email, subject, body, cc=None, bcc=None, html_body=None, attachments=None):
    from mail import _build_mail_message

    msg, to_list, cc_list, bcc_list = _build_mail_message(
        config,
        to_email=to_email,
        subject=subject,
        body=body,
        attachments=attachments,
        cc=cc,
        bcc=bcc,
        html_body=html_body,
        require_to=bool(str(to_email or "").strip()),
    )
    return msg, to_list, cc_list, bcc_list


def send_mail(config, to_email, subject, body, attachments=None, cc=None, bcc=None, html_body=None):
    try:
        service = build_gmail_service(config)
        msg, to_list, *_ = _build_mime(
            config, to_email, subject, body, cc=cc, bcc=bcc, html_body=html_body, attachments=attachments
        )
        if not to_list:
            raise GmailApiError("Alıcı e-posta adresi gerekli.")
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except GmailApiError:
        raise
    except Exception as exc:
        raise GmailApiError(_user_friendly_error(exc)) from exc


def create_draft(config, to_email="", subject="", body="", attachments=None, cc=None, bcc=None, html_body=None):
    try:
        service = build_gmail_service(config)
        msg, *_ = _build_mime(
            config,
            to_email=to_email or "",
            subject=subject or "(Konu yok)",
            body=body or "",
            cc=cc,
            bcc=bcc,
            html_body=html_body,
            attachments=attachments,
        )
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}},
        ).execute()
        return True
    except GmailApiError:
        raise
    except Exception as exc:
        raise GmailApiError(_user_friendly_error(exc)) from exc


def mark_mails_as_read(config, mail_ids):
    """Gmail API: UNREAD etiketini kaldır."""
    ids = [str(mid).strip() for mid in (mail_ids or []) if str(mid).strip()]
    if not ids:
        return 0
    try:
        service = build_gmail_service(config)
        marked = 0
        for mail_id in ids:
            try:
                service.users().messages().modify(
                    userId="me",
                    id=mail_id,
                    body={"removeLabelIds": ["UNREAD"]},
                ).execute()
                marked += 1
            except Exception:
                continue
        return marked
    except GmailApiError:
        raise
    except Exception as exc:
        raise GmailApiError(_user_friendly_error(exc)) from exc


def mark_mails_as_unread(config, mail_ids):
    """Gmail API: UNREAD etiketi ekle."""
    ids = [str(mid).strip() for mid in (mail_ids or []) if str(mid).strip()]
    if not ids:
        return 0
    try:
        service = build_gmail_service(config)
        marked = 0
        for mail_id in ids:
            try:
                service.users().messages().modify(
                    userId="me",
                    id=mail_id,
                    body={"addLabelIds": ["UNREAD"]},
                ).execute()
                marked += 1
            except Exception:
                continue
        return marked
    except GmailApiError:
        raise
    except Exception as exc:
        raise GmailApiError(_user_friendly_error(exc)) from exc


def download_attachment(config, mail_id: str, index: int):
    try:
        service = build_gmail_service(config)
        full = (
            service.users()
            .messages()
            .get(userId="me", id=mail_id, format="full")
            .execute()
        )
        parts = []
        _collect_parts(full.get("payload") or {}, parts)
        attachments = [p for p in parts if p.get("filename") or p.get("attachment_id")]
        # Prefer named attachments
        named = [p for p in attachments if p.get("filename")]
        pool = named or attachments
        if index < 0 or index >= len(pool):
            raise GmailApiError("Ek bulunamadı.")
        part = pool[index]
        data = part.get("data") or b""
        if part.get("attachment_id") and not data:
            att = (
                service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=mail_id, id=part["attachment_id"])
                .execute()
            )
            data = _decode_body_data(att.get("data") or "")
        filename = part.get("filename") or f"ek-{index + 1}"
        mime = part.get("mime") or "application/octet-stream"
        return filename, mime, data
    except GmailApiError:
        raise
    except Exception as exc:
        raise GmailApiError(_user_friendly_error(exc)) from exc


def revoke_google_token(token: str) -> bool:
    if not token:
        return False
    try:
        import httpx

        httpx.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        return True
    except Exception:
        return False
