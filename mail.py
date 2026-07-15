import base64
import email
import imaplib
import mimetypes
import os
import re
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase

from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime

from services.chat_service import get_client, get_gpt_model
from services.mail_content import clean_mail_body, decode_payload, html_to_text, normalize_mail_body


FOLDER_CANDIDATES = {
    "sent": ["[Gmail]/Sent Mail", "Sent", "Sent Items", "INBOX.Sent", "INBOX.Sent Items"],
    "spam": ["[Gmail]/Spam", "Spam", "Junk", "Junk E-mail", "INBOX.Spam", "INBOX.Junk", "INBOX.spam"],
    "trash": ["[Gmail]/Trash", "Trash", "Deleted", "Deleted Items", "INBOX.Trash"],
    "drafts": ["[Gmail]/Drafts", "Drafts", "INBOX.Drafts"],
    "archive": ["[Gmail]/All Mail", "Archive", "Archives", "INBOX.Archive"],
}

RECOVER_SKIP_MARKERS = (
    "\\sent",
    "\\drafts",
    "\\noselect",
    "sieve",
    "dovecot",
)


def _xoauth2_bytes(email, access_token):
    return f"user={email}\x01auth=Bearer {access_token}\x01\x01".encode()


def _imap_login(mail_conn, config):
    if config.get("auth_type") == "oauth":
        mail_conn.authenticate(
            "XOAUTH2",
            lambda _: _xoauth2_bytes(config["email"], config["access_token"]),
        )
        return
    mail_conn.login(config["email"], config["password"])


def _smtp_login(server, config):
    if config.get("auth_type") == "oauth":
        auth_string = base64.b64encode(
            _xoauth2_bytes(config["email"], config["access_token"])
        ).decode()
        code, resp = server.docmd("AUTH", "XOAUTH2 " + auth_string)
        if code != 235:
            raise Exception(f"SMTP OAuth hatası: {resp}")
        return
    server.login(config["email"], config["password"])


def connect_mail(config, folder="INBOX"):
    mail = imaplib.IMAP4_SSL(
        config["imap_server"],
        config.get("imap_port", 993),
    )
    _imap_login(mail, config)
    status, _ = mail.select(folder)
    if status != "OK":
        raise Exception(f"{folder} klasörü açılamadı.")
    return mail


def format_mail_date(date_header):
    if not date_header:
        return ""
    try:
        dt = parsedate_to_datetime(date_header)
        now = datetime.now(dt.tzinfo)
        diff = (now.date() - dt.date()).days
        if diff == 0:
            return dt.strftime("%H:%M")
        if diff < 7:
            days = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
            return days[dt.weekday()]
        return dt.strftime("%d %b")
    except Exception:
        return ""


def decode_mail_header(value):
    if value is None:
        return ""
    decoded = decode_header(value)
    result = ""
    for part, enc in decoded:
        if isinstance(part, bytes):
            result += part.decode(enc if enc else "utf-8", errors="ignore")
        else:
            result += str(part)
    return result


def _is_attachment_part(part):
    disposition = (part.get("Content-Disposition") or "").lower()
    if "attachment" in disposition:
        return True
    if part.get_filename():
        return True
    return False


def _extract_part_text(part):
    payload = part.get_payload(decode=True)
    if not payload:
        return ""

    charset = part.get_content_charset()
    raw = decode_payload(payload, charset)
    if part.get_content_type() == "text/html":
        return html_to_text(raw)
    return raw


def extract_body(msg):
    plain_parts = []
    html_parts = []

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if _is_attachment_part(part):
                continue

            ctype = part.get_content_type()
            if ctype == "text/plain":
                plain_parts.append(_extract_part_text(part))
            elif ctype == "text/html":
                html_parts.append(_extract_part_text(part))
    else:
        ctype = msg.get_content_type()
        text = _extract_part_text(msg)
        if ctype == "text/html":
            html_parts.append(text)
        else:
            plain_parts.append(text)

    plain_text = "\n\n".join(p for p in plain_parts if p.strip())
    html_text = "\n\n".join(p for p in html_parts if p.strip())
    body = normalize_mail_body(plain_text, html_text)
    return clean_mail_body(body)


def _iter_attachment_parts(msg):
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue

        filename = decode_mail_header(part.get_filename())
        disposition = (part.get("Content-Disposition") or "").lower()
        if not filename:
            if "attachment" not in disposition:
                continue
            mime = part.get_content_type() or "application/octet-stream"
            ext = mimetypes.guess_extension(mime.split(";")[0].strip()) or ".bin"
            filename = "ek" + ext

        mime = part.get_content_type() or "application/octet-stream"
        payload = part.get_payload(decode=True) or b""
        yield filename, mime, payload


def extract_attachments(msg):
    attachments = []

    for index, (filename, mime, payload) in enumerate(_iter_attachment_parts(msg)):
        is_image = mime.startswith("image/")
        preview = None
        if is_image and len(payload) < 800000:
            preview = f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}"

        attachments.append({
            "index": index,
            "filename": filename,
            "mime": mime,
            "size": len(payload),
            "is_image": is_image,
            "preview": preview,
        })

    return attachments


def _normalize_message_id(value):
    value = (value or "").strip().lower()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1]
    return value


def _extract_reference_ids(msg):
    refs = []

    def add(value):
        norm = _normalize_message_id(value)
        if norm and norm not in refs:
            refs.append(norm)

    add(msg.get("Message-ID"))

    for header_name in ("References", "In-Reply-To"):
        header = msg.get(header_name)
        if not header:
            continue
        header_text = str(header)
        for token in re.findall(r"<[^>]+>", header_text):
            add(token)
        for token in header_text.split():
            if token.startswith("<") and token.endswith(">"):
                continue
            add(token)

    return refs


def _parse_date_ts(date_header):
    if not date_header:
        return 0
    try:
        return parsedate_to_datetime(date_header).timestamp()
    except Exception:
        return 0


def parse_message(raw, thread_id=None):
    msg = email.message_from_bytes(raw)
    subject = decode_mail_header(msg.get("Subject"))
    sender_display = decode_mail_header(msg.get("From"))
    match = re.search(r"[\w\.-]+@[\w\.-]+", sender_display)
    sender = match.group(0) if match else sender_display
    reference_ids = _extract_reference_ids(msg)
    in_reply_to = _normalize_message_id(msg.get("In-Reply-To"))

    return {
        "subject": subject,
        "sender_display": sender_display,
        "sender": sender,
        "date": format_mail_date(msg.get("Date")),
        "date_ts": _parse_date_ts(msg.get("Date")),
        "content": extract_body(msg),
        "attachments": extract_attachments(msg),
        "thread_id": thread_id or "",
        "message_id": _normalize_message_id(msg.get("Message-ID")),
        "in_reply_to": in_reply_to,
        "reference_ids": reference_ids,
    }


def _mail_id_bytes(mail_id):
    if isinstance(mail_id, bytes):
        return mail_id
    return str(mail_id).encode()


def _is_gmail_config(config):
    server = (config.get("imap_server") or "").lower()
    return "gmail.com" in server or "googlemail.com" in server


def _extract_rfc822_from_fetch(msg_data):
    if not msg_data:
        return None

    for part in msg_data:
        if part is None:
            continue
        if isinstance(part, tuple):
            if len(part) >= 2 and isinstance(part[1], bytes) and len(part[1]) > 20:
                return part[1]
            _, body = _parse_uid_fetch_item(part)
            if body:
                return body
        elif isinstance(part, bytes):
            if len(part) > 100 and not part.strip().startswith(b"("):
                return part

    if msg_data[0]:
        _, body = _parse_uid_fetch_item(msg_data[0])
        return body

    return None


def _fetch_mail_by_uid(mail, mail_id, config):
    uid = _mail_id_bytes(mail_id)
    _, msg_data = mail.uid("fetch", uid, "(RFC822)")
    raw = _extract_rfc822_from_fetch(msg_data)
    if not raw:
        return None, None

    thread_id = _fetch_gmail_thread_id(mail, uid) if _is_gmail_config(config) else None
    return thread_id, raw


def list_folder_uids(config, folder):
    mail = connect_mail(config, folder)
    status, messages = mail.uid("search", None, "ALL")
    if status != "OK" or not messages or not messages[0]:
        mail.logout()
        return []

    ids = [uid.decode() for uid in messages[0].split()]
    mail.logout()
    return ids


def list_imap_folders(config):
    mail = imaplib.IMAP4_SSL(
        config["imap_server"],
        config.get("imap_port", 993),
    )
    _imap_login(mail, config)
    status, folders = mail.list()
    mail.logout()

    if status != "OK" or not folders:
        return []

    names = []
    for entry in folders:
        if not entry:
            continue
        line = entry.decode("utf-8", errors="ignore")
        match = re.search(r'"([^"]+)"\s*$', line)
        if not match:
            match = re.search(r'\s([^ ]+)\s*$', line)
        if match:
            names.append(match.group(1))
    return names


def recover_all_to_inbox(config):
    results = {
        "spam_restored": 0,
        "trash_restored": 0,
        "archive_restored": 0,
        "other_restored": 0,
        "errors": [],
        "folders_checked": [],
    }

    def _restore_folder(folder_name, result_key):
        mail_ids = list_folder_uids(config, folder_name)
        if not mail_ids:
            return
        moved, errors = move_mails_to_folder(
            config,
            folder_name,
            mail_ids,
            ["INBOX"],
            expand_threads=False,
        )
        results[result_key] += moved
        results["errors"].extend(errors)

    for folder_name in list_imap_folders(config):
        lowered = folder_name.lower()
        results["folders_checked"].append(folder_name)

        if lowered == "inbox":
            continue
        if any(marker in lowered for marker in RECOVER_SKIP_MARKERS):
            continue
        if "sent" in lowered or "draft" in lowered:
            continue

        if any(key in lowered for key in ("spam", "junk")):
            _restore_folder(folder_name, "spam_restored")
        elif any(key in lowered for key in ("trash", "deleted")):
            _restore_folder(folder_name, "trash_restored")
        elif "archive" in lowered:
            _restore_folder(folder_name, "archive_restored")
        else:
            _restore_folder(folder_name, "other_restored")

    return results


def _parse_uid_fetch_item(item):
    if not item:
        return None, None

    header = item[0]
    if isinstance(header, bytes):
        header = header.decode("utf-8", errors="ignore")
    elif isinstance(header, tuple):
        header = header[0].decode("utf-8", errors="ignore") if isinstance(header[0], bytes) else str(header[0])

    thread_match = re.search(r"X-GM-THRID (\d+)", header or "")
    thread_id = thread_match.group(1) if thread_match else None

    raw = item[1]
    if isinstance(raw, tuple):
        raw = raw[1] if len(raw) > 1 else raw[0]
    if isinstance(raw, int):
        return thread_id, None

    return thread_id, raw


def _fetch_gmail_thread_id(mail_conn, mail_id):
    try:
        _, data = mail_conn.uid("fetch", _mail_id_bytes(mail_id), "(X-GM-THRID)")
        if not data or not data[0]:
            return None
        header = data[0]
        if isinstance(header, tuple):
            header = header[0]
        if isinstance(header, bytes):
            header = header.decode("utf-8", errors="ignore")
        match = re.search(r"X-GM-THRID (\d+)", header)
        return match.group(1) if match else None
    except Exception:
        return None


def _expand_thread_uids_in_folder(mail_conn, mail_ids):
    expanded = []
    seen = set()
    seen_threads = set()

    for mail_id in mail_ids:
        uid = str(mail_id).strip()
        if not uid:
            continue

        thread_id = _fetch_gmail_thread_id(mail_conn, uid)
        if thread_id and thread_id not in seen_threads:
            seen_threads.add(thread_id)
            try:
                status, data = mail_conn.uid("search", None, f"X-GM-THRID {thread_id}")
                if status == "OK" and data and data[0]:
                    for found_uid in data[0].split():
                        found = found_uid.decode()
                        if found not in seen:
                            seen.add(found)
                            expanded.append(found)
                    continue
            except Exception:
                pass

        if uid not in seen:
            seen.add(uid)
            expanded.append(uid)

    return expanded


def _uid_move_or_copy(mail_conn, mail_id, dest_folder):
    mid = _mail_id_bytes(mail_id)

    try:
        status, _ = mail_conn.uid("MOVE", mid, dest_folder)
        if status == "OK":
            return True
    except Exception:
        pass

    status, _ = mail_conn.uid("copy", mid, dest_folder)
    if status != "OK":
        return False

    mail_conn.uid("store", mid, "+FLAGS", "\\Deleted")
    return True


def resolve_folder_name(config, candidates):
    mail = imaplib.IMAP4_SSL(
        config["imap_server"],
        config.get("imap_port", 993),
    )
    _imap_login(mail, config)

    for folder in candidates:
        status, _ = mail.select(folder, readonly=True)
        if status == "OK":
            mail.close()
            mail.logout()
            return folder

    mail.logout()
    return None


def move_mail_to_folder(config, source_folder, mail_id, dest_candidates):
    moved, errors = move_mails_to_folder(config, source_folder, [mail_id], dest_candidates)
    if moved == 0:
        raise Exception(errors[0] if errors else "Mail taşınamadı.")
    return resolve_folder_name(config, dest_candidates)


def move_mails_to_folder(config, source_folder, mail_ids, dest_candidates, expand_threads=True):
    dest_folder = resolve_folder_name(config, dest_candidates)
    if not dest_folder:
        raise Exception("Hedef klasör bulunamadı.")

    unique_ids = []
    seen = set()
    for mail_id in mail_ids:
        key = str(mail_id).strip()
        if key and key not in seen:
            seen.add(key)
            unique_ids.append(key)

    if not unique_ids:
        raise Exception("Taşınacak mail bulunamadı.")

    mail = connect_mail(config, source_folder)

    if expand_threads and _is_gmail_config(config):
        unique_ids = _expand_thread_uids_in_folder(mail, unique_ids)

    unique_ids.sort(key=lambda value: int(value), reverse=True)

    moved = 0
    errors = []

    for mail_id in unique_ids:
        try:
            if _uid_move_or_copy(mail, mail_id, dest_folder):
                moved += 1
            else:
                errors.append(f"Mail taşınamadı: {mail_id}")
        except Exception as e:
            errors.append(f"{mail_id}: {e}")

    if moved:
        try:
            mail.expunge()
        except Exception:
            pass

    mail.logout()
    return moved, errors


def filter_spam_from_inbox(config, mailler, settings=None):
    from services.spam_service import identify_spam_mails

    settings = settings or {}
    if not settings.get("auto_spam_filter", True):
        return mailler, 0

    spam_mails = identify_spam_mails(mailler, settings)
    if not spam_mails:
        return mailler, 0

    if not settings.get("spam_move_to_folder", True):
        spam_ids = {m["id"] for m in spam_mails}
        clean = [m for m in mailler if m["id"] not in spam_ids]
        return clean, 0

    moved = 0
    try:
        moved, errors = move_mails_to_folder(
            config,
            "INBOX",
            [item["id"] for item in spam_mails],
            FOLDER_CANDIDATES["spam"],
            expand_threads=False,
        )
        for err in errors:
            print("SPAM TAŞIMA HATASI:", err)
    except Exception as e:
        print("SPAM TAŞIMA HATASI:", e)

    spam_ids = {m["id"] for m in spam_mails}
    clean = [m for m in mailler if m["id"] not in spam_ids]
    return clean, moved


def get_folder_mails(config, folder="INBOX", count=20):
    mail = connect_mail(config, folder)
    try:
        status, messages = mail.uid("search", None, "ALL")
        if status != "OK":
            return []

        ids = messages[0].split()
        result = []

        for mail_id in reversed(ids[-count:]):
            try:
                thread_id, raw = _fetch_mail_by_uid(mail, mail_id, config)
                if not raw:
                    continue

                parsed = parse_message(raw, thread_id=thread_id)
                parsed["id"] = mail_id.decode()
                result.append(parsed)
            except Exception as e:
                print("MAIL HATASI:", e)

        return result
    finally:
        try:
            mail.logout()
        except Exception:
            pass


def get_first_available_folder(config, folder_names, count=20):
    for folder in folder_names:
        try:
            return get_folder_mails(config, folder, count)
        except Exception:
            pass
    return []


def get_inbox(config, count=20, filter_spam=True, settings=None):
    settings = settings or {}
    display_count = settings.get("inbox_fetch_count", count)
    sweep_count = max(display_count, 50)

    mailler = get_folder_mails(config, "INBOX", sweep_count)
    if not filter_spam:
        return mailler[:display_count], 0

    clean, moved = filter_spam_from_inbox(config, mailler, settings)
    return clean[:display_count], moved


def get_sent(config, count=20):
    return get_first_available_folder(config, FOLDER_CANDIDATES["sent"], count)


def get_spam(config, count=100):
    return get_first_available_folder(config, FOLDER_CANDIDATES["spam"], count)


def get_trash(config, count=100):
    return get_first_available_folder(config, FOLDER_CANDIDATES["trash"], count)


def get_drafts(config, count=20):
    return get_first_available_folder(config, FOLDER_CANDIDATES["drafts"], count)


def get_archive(config, count=20):
    return get_first_available_folder(config, FOLDER_CANDIDATES["archive"], count)


def fetch_attachment(config, folder, mail_id, index):
    mail = connect_mail(config, folder)
    try:
        _, raw = _fetch_mail_by_uid(mail, mail_id, config)
        if not raw:
            raise FileNotFoundError("Mail bulunamadı.")

        msg = email.message_from_bytes(raw)
        attachments = list(_iter_attachment_parts(msg))
        if index < 0 or index >= len(attachments):
            raise FileNotFoundError("Ek bulunamadı.")

        return attachments[index]
    finally:
        mail.logout()


def send_reply_mail(config, to_email, subject, body, attachments=None, cc=None, bcc=None):
    return _send_mail(config, to_email, subject, body, attachments, cc=cc, bcc=bcc)


def send_new_mail(config, to_email, subject, body, attachments=None, cc=None, bcc=None):
    return _send_mail(config, to_email, subject, body, attachments, cc=cc, bcc=bcc)


def _parse_recipient_list(value):
    if not value:
        return []
    return [
        part.strip()
        for part in re.split(r"[;,]+", str(value))
        if part.strip()
    ]


def _attach_files(msg, attachments):
    for attachment in attachments or []:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment["data"])
        encoders.encode_base64(part)
        filename = attachment.get("filename", "ek")
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)


def _send_mail(config, to_email, subject, body, attachments=None, cc=None, bcc=None):
    to_list = _parse_recipient_list(to_email)
    cc_list = _parse_recipient_list(cc)
    bcc_list = _parse_recipient_list(bcc)

    if not to_list:
        raise ValueError("Alıcı e-posta adresi gerekli.")

    msg = MIMEMultipart()
    msg["From"] = config["email"]
    msg["To"] = ", ".join(to_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    _attach_files(msg, attachments)

    recipients = list(dict.fromkeys(to_list + cc_list + bcc_list))

    server = smtplib.SMTP(config["smtp_server"], config.get("smtp_port", 587))
    server.starttls()
    _smtp_login(server, config)
    server.sendmail(config["email"], recipients, msg.as_string())
    server.quit()
    return True


def analyze_mail(text):
    client = get_client()
    if client is None:
        raise Exception("OPENAI_API_KEY bulunamadı.")

    prompt = f"""Aşağıdaki e-postayı analiz et.

1. Kısa özet
2. Önem derecesi
3. Yapılması gerekenler
4. Profesyonel cevap önerisi

Mail:

{text}
"""
    response = client.chat.completions.create(
        model=get_gpt_model(),
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
