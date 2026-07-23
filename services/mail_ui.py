import os

from mail import (
    _fetch_mail_by_uid,
    _mail_id_bytes,
    connect_mail,
    fetch_attachment,
    get_archive,
    get_drafts,
    get_inbox,
    get_sent,
    get_spam,
    get_trash,
    get_folder_mails,
    move_mail_to_folder,
    move_mails_to_folder,
    parse_message,
    recover_all_to_inbox,
    list_folder_uids,
    FOLDER_CANDIDATES,
    has_draft_content,
    save_draft_mail,
    send_new_mail,
    send_reply_mail,
)
from services.chat_service import ask_gpt_mail_reply, get_client
from services.mail_threads import expand_selected_mail_ids, group_mails_by_thread
from services.mail_contacts import remember_contacts_from_fields
from services.file_service import parse_uploaded_attachment
from services.mail_enrich_service import wants_enrichment
from services.file_library_service import load_attachments

FOLDERS = [
    {"id": "inbox", "label": "Gelen Kutusu", "icon": "inbox"},
    {"id": "unread", "label": "Okunmamış", "icon": "mark_email_unread"},
    {"id": "starred", "label": "Yıldızlı", "icon": "star"},
    {"id": "sent", "label": "Gönderilmiş", "icon": "send"},
    {"id": "drafts", "label": "Taslaklar", "icon": "draft"},
    {"id": "spam", "label": "Spam", "icon": "report"},
    {"id": "trash", "label": "Çöp Kutusu", "icon": "delete"},
    {"id": "archive", "label": "Arşiv", "icon": "archive"},
]

FOLDER_LABELS = {
    "inbox": "Gelen Kutusu",
    "unread": "Okunmamış",
    "starred": "Yıldızlı",
    "sent": "Gönderilmiş Postalar",
    "drafts": "Taslaklar",
    "spam": "Spam",
    "trash": "Çöp Kutusu",
    "archive": "Arşiv",
}

FOLDER_IMAP = {
    "inbox": "INBOX",
    "sent": "Sent",
    "spam": "[Gmail]/Spam",
    "trash": "Trash",
    "drafts": "Drafts",
    "archive": "Archive",
}


def load_folder_mails(folder, mail_config, count=20, settings=None, filter_spam=True, search="", user_id=None):
    meta = {}
    settings = settings or {}

    from services.gmail_api import GmailApiError, is_gmail_api_config, list_mails as gmail_list_mails

    if is_gmail_api_config(mail_config):
        try:
            fetch_count = min(count, settings.get("inbox_fetch_count", count)) if folder == "inbox" else count
            mailler = gmail_list_mails(mail_config, folder=folder or "inbox", count=fetch_count, search=search)
            if folder in ("inbox", "sent", "spam", "trash", "archive", "starred", "unread"):
                mailler = group_mails_by_thread(mailler)
            return mailler, meta
        except GmailApiError as exc:
            meta["error"] = str(exc)
            return [], meta
        except Exception as exc:
            meta["error"] = f"Gmail API hatası: {exc}"
            return [], meta

    if folder == "unread":
        fetch_count = min(count, settings.get("inbox_fetch_count", count))
        mailler = get_unread_imap(mail_config, fetch_count)
        return group_mails_by_thread(mailler), meta

    if folder == "inbox":
        fetch_count = min(count, settings.get("inbox_fetch_count", count))
        mailler, spam_moved = get_inbox(
            mail_config,
            fetch_count,
            filter_spam=filter_spam,
            settings={**settings, "inbox_fetch_count": fetch_count},
            user_id=user_id,
        )
        if spam_moved:
            meta["spam_moved"] = spam_moved
        return group_mails_by_thread(mailler), meta

    loaders = {
        "sent": get_sent,
        "spam": get_spam,
        "trash": get_trash,
        "drafts": get_drafts,
        "archive": get_archive,
        "starred": lambda cfg, c=count: get_starred_imap(cfg, c),
    }
    loader = loaders.get(folder, get_inbox)
    result = loader(mail_config, count)
    if isinstance(result, tuple):
        result = result[0]

    if folder in ("inbox", "sent", "spam", "trash", "archive", "starred"):
        result = group_mails_by_thread(result)

    return result, meta


def get_unread_imap(mail_config, count=50):
    """IMAP UNSEEN araması — yalnızca okunmamış mailler."""
    try:
        from mail import connect_mail

        mail = connect_mail(mail_config, "INBOX")
        try:
            status, messages = mail.uid("search", None, "UNSEEN")
            if status != "OK" or not messages or not messages[0]:
                return []
            ids = messages[0].split()
            result = []
            for mail_id in reversed(ids[-count:]):
                try:
                    thread_id, raw, unread = _fetch_mail_by_uid(mail, mail_id, mail_config)
                    if not raw:
                        continue
                    parsed = parse_message(raw, thread_id=thread_id)
                    parsed["id"] = mail_id.decode()
                    parsed["unread"] = True if unread is None else bool(unread)
                    result.append(parsed)
                except Exception:
                    continue
            return result
        finally:
            try:
                mail.logout()
            except Exception:
                pass
    except Exception as e:
        print("UNREAD IMAP HATASI:", e)
        return []


def get_starred_imap(mail_config, count=20):
    """IMAP FLAGGED araması (Outlook/Yahoo vb.)."""
    try:
        from mail import connect_mail

        mail = connect_mail(mail_config, "INBOX")
        try:
            status, messages = mail.uid("search", None, "FLAGGED")
            if status != "OK" or not messages or not messages[0]:
                return []
            ids = messages[0].split()
            result = []
            for mail_id in reversed(ids[-count:]):
                try:
                    thread_id, raw, unread = _fetch_mail_by_uid(mail, mail_id, mail_config)
                    if not raw:
                        continue
                    parsed = parse_message(raw, thread_id=thread_id)
                    parsed["id"] = mail_id.decode()
                    parsed["starred"] = True
                    parsed["unread"] = bool(unread)
                    result.append(parsed)
                except Exception:
                    continue
            return result
        finally:
            try:
                mail.logout()
            except Exception:
                pass
    except Exception as e:
        print("STARRED IMAP HATASI:", e)
        return []


def load_single_mail(folder, mail_config, mail_id):
    from services.gmail_api import GmailApiError, get_mail as gmail_get_mail, is_gmail_api_config

    if is_gmail_api_config(mail_config):
        try:
            return gmail_get_mail(mail_config, str(mail_id))
        except GmailApiError as exc:
            raise RuntimeError(str(exc)) from exc

    imap_folder = get_imap_folder_name(folder, mail_config)
    mail_conn = connect_mail(mail_config, imap_folder)
    try:
        thread_id, raw, unread = _fetch_mail_by_uid(mail_conn, mail_id, mail_config)
        if not raw:
            return None

        parsed = parse_message(raw, thread_id=thread_id)
        parsed["id"] = str(mail_id)
        parsed["unread"] = bool(unread)
        return parsed
    finally:
        try:
            mail_conn.logout()
        except Exception:
            pass


def mail_content_preview(content, limit=400):
    text = (content or "").replace("\r", "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def filter_mails(mailler, search):
    if not search:
        return mailler

    s = search.lower()
    return [
        m for m in mailler
        if (
            s in m.get("subject", "").lower()
            or s in m.get("sender", "").lower()
            or s in m.get("content", "").lower()
        )
    ]


def load_mail_css(app_root):
    css_path = os.path.join(app_root, "static", "css", "mail.css")
    with open(css_path, encoding="utf-8") as f:
        return f.read()


def _parse_mail_ids(form):
    ids = []
    bulk = (form.get("mail_ids") or "").strip()
    if bulk:
        ids.extend(part.strip() for part in bulk.split(",") if part.strip())

    single = (form.get("mail_id") or "").strip()
    if single and single not in ids:
        ids.append(single)

    return ids


def _move_mails_to_inbox(form, mail_config, source_folder_key):
    mail_ids = _parse_mail_ids(form)
    if not mail_ids:
        raise ValueError("Mail seçilmedi.")

    source_folder = form.get("source_folder", source_folder_key).strip()
    imap_source = get_imap_folder_name(source_folder, mail_config)
    folder_mails = get_folder_mails(mail_config, imap_source, count=200)
    expanded_ids = expand_selected_mail_ids(folder_mails, mail_ids)

    selected = {
        str(mid).strip()
        for mid in (expanded_ids or mail_ids)
        if str(mid).strip()
    }
    senders = []
    for mail in folder_mails:
        mail_id = str(mail.get("id") or "").strip()
        thread_ids = {str(tid).strip() for tid in (mail.get("thread_ids") or []) if str(tid).strip()}
        if mail_id in selected or (thread_ids & selected):
            sender = (mail.get("sender") or mail.get("sender_display") or "").strip()
            if sender:
                senders.append(sender)

    moved, errors = move_mails_to_folder(
        mail_config,
        imap_source,
        expanded_ids,
        ["INBOX"],
        expand_threads=True,
    )

    if moved == 0:
        raise Exception(errors[0] if errors else "Mail taşınamadı.")

    message_ids = []
    for mail in folder_mails:
        mail_id = str(mail.get("id") or "").strip()
        thread_ids = {str(tid).strip() for tid in (mail.get("thread_ids") or []) if str(tid).strip()}
        if mail_id in selected or (thread_ids & selected):
            msgid = str(mail.get("message_id") or "").strip()
            if msgid:
                message_ids.append(msgid)
            if mail_id:
                message_ids.append(mail_id)

    return moved, errors, senders, message_ids


def generate_ai_mail_reply(
    sender,
    subject,
    content,
    user_instruction="",
    current_draft="",
    revize_notu="",
    user=None,
    enrich=None,
):
    client = get_client()
    if client is None:
        raise RuntimeError("Sunucuda OPENAI_API_KEY ayarlı değil.")

    instruction = (revize_notu or user_instruction or "").strip()
    should_enrich = enrich if enrich is not None else wants_enrichment(instruction)

    if should_enrich:
        from services.mail_enrich_service import generate_enriched_mail

        return generate_enriched_mail(
            user,
            mode="reply",
            sender=sender,
            subject=subject,
            content=content,
            user_instruction=user_instruction,
            current_draft=current_draft,
            revize_notu=revize_notu,
        )

    if revize_notu:
        prompt = f"""KULLANICI İPUCU / TALİMAT (ÖNCELİKLİ):
{revize_notu}

Bu ipucu doğrultusunda aşağıdaki taslağı güncelle. İpucundaki istekler mutlaka uygulansın.

Gelen Mail:
Kimden: {sender}
Konu: {subject}
İçerik:
{content}

Mevcut Taslak (kullanıcı elle düzenlemiş olabilir):
{current_draft}

Güncellenmiş taslağı yaz. Sadece gönderilecek yanıt metnini döndür."""
    elif user_instruction:
        prompt = f"""KULLANICI İPUCU / TALİMAT (ÖNCELİKLİ):
{user_instruction}

Bu ipucu doğrultusunda aşağıdaki maile yanıt yaz. İpucundaki ton, uzunluk, içerik ve istekler mutlaka yansısın.

Gelen Mail:
Kimden: {sender}
Konu: {subject}
İçerik:
{content}

Sadece gönderilecek yanıt metnini yaz."""
    else:
        prompt = f"""Gelen Mail:
Kimden: {sender}
Konu: {subject}
İçerik:
{content}

Bu maile profesyonel, kibar ve çözüm odaklı bir Türkçe yanıt yaz. Sadece gönderilecek yanıt metnini yaz."""

    return {
        "body": ask_gpt_mail_reply(prompt),
        "html_body": "",
        "library_attachments": [],
        "library_file_ids": [],
    }


def generate_ai_new_mail(
    to_email="",
    subject="",
    user_instruction="",
    current_draft="",
    revize_notu="",
    user=None,
    enrich=None,
):
    client = get_client()
    if client is None:
        raise RuntimeError("Sunucuda OPENAI_API_KEY ayarlı değil.")

    to_email = (to_email or "").strip()
    subject = (subject or "").strip()
    user_instruction = (user_instruction or "").strip()
    current_draft = (current_draft or "").strip()
    revize_notu = (revize_notu or "").strip()
    instruction = (revize_notu or user_instruction or "").strip()
    should_enrich = enrich if enrich is not None else wants_enrichment(instruction)

    if should_enrich:
        from services.mail_enrich_service import generate_enriched_mail

        return generate_enriched_mail(
            user,
            mode="compose",
            to_email=to_email,
            subject=subject,
            user_instruction=user_instruction,
            current_draft=current_draft,
            revize_notu=revize_notu,
        )

    if revize_notu:
        prompt = f"""KULLANICI İPUCU / TALİMAT (ÖNCELİKLİ):
{revize_notu}

Bu ipucu doğrultusunda aşağıdaki yeni e-posta taslağını güncelle.

Alıcı: {to_email or "(belirtilmedi)"}
Konu: {subject or "(belirtilmedi)"}

Mevcut Taslak:
{current_draft or "(boş)"}

Güncellenmiş e-posta gövdesini yaz. Sadece gönderilecek metni döndür; konu satırı veya açıklama ekleme."""
    elif user_instruction:
        prompt = f"""KULLANICI İPUCU / TALİMAT (ÖNCELİKLİ):
{user_instruction}

Bu ipucu doğrultusunda yeni bir e-posta yaz. Ton, uzunluk ve istekler mutlaka yansısın.

Alıcı: {to_email or "(belirtilmedi)"}
Konu: {subject or "(belirtilmedi)"}

Sadece gönderilecek e-posta gövdesini yaz. Konu satırı veya açıklama ekleme."""
    else:
        prompt = f"""Yeni bir profesyonel Türkçe e-posta yaz.

Alıcı: {to_email or "(belirtilmedi)"}
Konu: {subject or "(belirtilmedi)"}

Kısa, kibar ve net bir gövde metni yaz. Sadece gönderilecek metni döndür."""

    return {
        "body": ask_gpt_mail_reply(prompt),
        "html_body": "",
        "library_attachments": [],
        "library_file_ids": [],
    }


def _normalize_ai_result(result):
    if isinstance(result, dict):
        body = (result.get("body") or result.get("draft") or "").strip()
        return {
            "body": body,
            "html_body": (result.get("html_body") or "").strip(),
            "library_attachments": result.get("library_attachments") or [],
            "library_file_ids": result.get("library_file_ids") or [],
            "table": result.get("table"),
            "chart": result.get("chart"),
        }
    return {
        "body": str(result or "").strip(),
        "html_body": "",
        "library_attachments": [],
        "library_file_ids": [],
        "table": None,
        "chart": None,
    }


def _collect_outgoing_attachments(form, files, user):
    attachments = []
    if files:
        uploaded = parse_uploaded_attachment(files.get("attachment"))
        if uploaded:
            attachments.append(uploaded)

    library_ids = form.getlist("library_file_ids") if hasattr(form, "getlist") else []
    if not library_ids:
        raw = (form.get("library_file_ids") or "").strip()
        if raw:
            library_ids = [part.strip() for part in raw.split(",") if part.strip()]

    if user and library_ids:
        attachments.extend(load_attachments(user, library_ids))

    return attachments


def save_outgoing_draft(mail_config, *, to_email="", subject="", body="", cc="", bcc="", html_body="", attachments=None):
    """Boş değilse IMAP taslak kaydeder. Dönüş: (saved: bool, message: str)."""
    attachments = attachments or []
    if not has_draft_content(to_email, subject, body, cc, bcc, html_body, attachments):
        return False, "Kaydedilecek içerik yok."
    save_draft_mail(
        mail_config,
        to_email=to_email,
        subject=subject,
        body=body,
        attachments=attachments or None,
        cc=cc,
        bcc=bcc,
        html_body=html_body or None,
    )
    return True, "Taslak kaydedildi."


def handle_mail_action(form, mail_config, files=None, user=None):
    islem = form.get("islem")
    sender = form.get("sender", "")
    subject = form.get("subject", "")
    content = form.get("content", "")
    mail_id = form.get("mail_id", "")
    user_instruction = form.get("user_instruction", "").strip()
    current_draft = form.get("current_draft", "").strip()
    revize_notu = form.get("revize_notu", "").strip()

    error = ""
    success_message = ""
    ai_yaniti = ""
    secilen_mail = {}
    ai_meta = {}

    if islem == "olustur":
        try:
            result = _normalize_ai_result(
                generate_ai_mail_reply(
                    sender,
                    subject,
                    content,
                    user_instruction=user_instruction,
                    user=user,
                )
            )
            ai_yaniti = result["body"]
            ai_meta = result
            reply_to = (form.get("to_email") or sender or "").strip()
            reply_cc = (form.get("cc_email") or "").strip()
            reply_bcc = (form.get("bcc_email") or "").strip()
            reply_all = (form.get("reply_all") or "").strip() in {"1", "true", "on", "yes"}
            secilen_mail = {
                "id": mail_id,
                "sender": sender,
                "subject": subject,
                "content": content,
                "to_email": reply_to,
                "cc_email": reply_cc,
                "bcc_email": reply_bcc,
                "reply_all": reply_all,
                "to_emails": [p.strip() for p in reply_to.split(",") if p.strip()],
                "cc_emails": [p.strip() for p in reply_cc.split(",") if p.strip()],
            }
        except Exception as e:
            error = f"Yanıt oluşturulurken hata: {str(e)}"

    elif islem == "revize_et":
        try:
            result = _normalize_ai_result(
                generate_ai_mail_reply(
                    sender,
                    subject,
                    content,
                    current_draft=current_draft,
                    revize_notu=revize_notu,
                    user=user,
                )
            )
            ai_yaniti = result["body"]
            ai_meta = result
            reply_to = (form.get("to_email") or sender or "").strip()
            reply_cc = (form.get("cc_email") or "").strip()
            reply_bcc = (form.get("bcc_email") or "").strip()
            reply_all = (form.get("reply_all") or "").strip() in {"1", "true", "on", "yes"}
            secilen_mail = {
                "id": mail_id,
                "sender": sender,
                "subject": subject,
                "content": content,
                "to_email": reply_to,
                "cc_email": reply_cc,
                "bcc_email": reply_bcc,
                "reply_all": reply_all,
                "to_emails": [p.strip() for p in reply_to.split(",") if p.strip()],
                "cc_emails": [p.strip() for p in reply_cc.split(",") if p.strip()],
            }
        except Exception as e:
            error = f"Taslak yeniden düzenlenirken hata: {str(e)}"

    elif islem == "spam":
        mail_id = form.get("mail_id", "").strip()
        source_folder = form.get("source_folder", "inbox").strip()
        try:
            if not mail_id:
                raise ValueError("Mail seçilmedi.")
            imap_source = get_imap_folder_name(source_folder, mail_config)
            move_mail_to_folder(
                mail_config,
                imap_source,
                mail_id,
                FOLDER_CANDIDATES["spam"],
            )
            success_message = "Mail spam klasörüne taşındı."
        except Exception as e:
            error = f"Spam klasörüne taşınamadı: {str(e)}"

    elif islem == "spam_cikar":
        try:
            moved, errors, senders, restore_ids = _move_mails_to_inbox(form, mail_config, "spam")
            trusted_added = []
            if user:
                from services.mail_settings import add_spam_exempt_ids, add_trusted_senders

                user_id = (user.get("email") or user.get("username") or "").strip()
                if senders:
                    trusted_added = add_trusted_senders(user_id, senders)
                if restore_ids:
                    add_spam_exempt_ids(user_id, restore_ids)
            if moved == 1:
                success_message = "Mail spam klasöründen çıkarıldı ve gelen kutusuna taşındı."
            else:
                success_message = f"{moved} mail spam klasöründen çıkarıldı ve gelen kutusuna taşındı."
            if trusted_added:
                success_message += (
                    f" Bundan sonra {', '.join(trusted_added)} adresinden gelen mailler "
                    "otomatik spam'e düşmeyecek."
                )
            if errors:
                success_message += f" ({len(errors)} mail taşınamadı.)"
        except Exception as e:
            error = f"Spam'dan çıkarılamadı: {str(e)}"

    elif islem == "cop_kurtar":
        try:
            moved, errors, _senders, _restore_ids = _move_mails_to_inbox(form, mail_config, "trash")
            if moved == 1:
                success_message = "Mail çöp kutusundan geri alındı ve gelen kutusuna taşındı."
            else:
                success_message = f"{moved} mail çöp kutusundan geri alındı ve gelen kutusuna taşındı."
            if errors:
                success_message += f" ({len(errors)} mail taşınamadı.)"
        except Exception as e:
            error = f"Çöp kutusundan geri alınamadı: {str(e)}"

    elif islem == "tumunu_geri_al":
        try:
            result = recover_all_to_inbox(mail_config)
            spam_count = result.get("spam_restored", 0)
            trash_count = result.get("trash_restored", 0)
            archive_count = result.get("archive_restored", 0)
            other_count = result.get("other_restored", 0)
            total = spam_count + trash_count + archive_count + other_count
            inbox_total = len(list_folder_uids(mail_config, "INBOX"))
            if total == 0:
                success_message = (
                    f"Geri alınacak mail bulunamadı. Gelen kutusunda şu an {inbox_total} mail var."
                )
            else:
                success_message = (
                    f"{total} mail gelen kutusuna geri alındı "
                    f"(spam: {spam_count}, çöp: {trash_count}, arşiv: {archive_count}, diğer: {other_count}). "
                    f"Gelen kutusu toplam: {inbox_total}"
                )
            errors = result.get("errors") or []
            if errors and total > 0:
                success_message += f" ({len(errors)} mail taşınamadı.)"
        except Exception as e:
            error = f"Geri alma başarısız: {str(e)}"

    elif islem == "gonder":
        final_reply = form.get("final_reply", "")
        html_body = (form.get("html_body") or "").strip()
        to_email = (form.get("to_email") or sender or "").strip()
        cc_email = form.get("cc_email", "").strip()
        bcc_email = form.get("bcc_email", "").strip()
        try:
            if not to_email:
                raise ValueError("Alıcı e-posta adresi gerekli.")
            attachments = _collect_outgoing_attachments(form, files, user)
            send_reply_mail(
                mail_config,
                to_email=to_email,
                subject=f"Re: {subject}",
                body=final_reply,
                attachments=attachments or None,
                cc=cc_email,
                bcc=bcc_email,
                html_body=html_body or None,
            )
            if user:
                remember_contacts_from_fields(
                    user,
                    to_email=to_email,
                    cc_email=cc_email,
                    bcc_email=bcc_email,
                    own_email=mail_config.get("email"),
                )
            success_message = f"{to_email} adresine yanıt başarıyla postalandı!"
            if attachments:
                names = ", ".join(a["filename"] for a in attachments)
                success_message += f" (Ek: {names})"
        except Exception as e:
            error = f"E-posta gönderilirken hata oluştu: {str(e)}"

    elif islem == "yeni_gonder":
        to_email = form.get("to_email", "").strip()
        cc_email = form.get("cc_email", "").strip()
        bcc_email = form.get("bcc_email", "").strip()
        new_subject = form.get("new_subject", "").strip()
        new_body = form.get("new_body", "").strip()
        html_body = (form.get("html_body") or "").strip()
        try:
            if not to_email:
                raise ValueError("Alıcı e-posta adresi gerekli.")
            attachments = _collect_outgoing_attachments(form, files, user)
            send_new_mail(
                mail_config,
                to_email=to_email,
                subject=new_subject,
                body=new_body,
                attachments=attachments or None,
                cc=cc_email,
                bcc=bcc_email,
                html_body=html_body or None,
            )
            if user:
                remember_contacts_from_fields(
                    user,
                    to_email=to_email,
                    cc_email=cc_email,
                    bcc_email=bcc_email,
                    own_email=mail_config.get("email"),
                )
            success_message = f"{to_email} adresine mail gönderildi!"
            if attachments:
                names = ", ".join(a["filename"] for a in attachments)
                success_message += f" (Ek: {names})"
        except Exception as e:
            error = f"E-posta gönderilirken hata oluştu: {str(e)}"

    elif islem == "taslak_kaydet":
        to_email = form.get("to_email", "").strip()
        cc_email = form.get("cc_email", "").strip()
        bcc_email = form.get("bcc_email", "").strip()
        new_subject = (form.get("new_subject") or form.get("subject") or "").strip()
        new_body = (form.get("new_body") or form.get("final_reply") or form.get("body") or "").strip()
        html_body = (form.get("html_body") or "").strip()
        try:
            attachments = _collect_outgoing_attachments(form, files, user)
            if not has_draft_content(
                to_email, new_subject, new_body, cc_email, bcc_email, html_body, attachments
            ):
                success_message = ""
            else:
                save_draft_mail(
                    mail_config,
                    to_email=to_email,
                    subject=new_subject,
                    body=new_body,
                    attachments=attachments or None,
                    cc=cc_email,
                    bcc=bcc_email,
                    html_body=html_body or None,
                )
                success_message = "Taslak kaydedildi."
        except Exception as e:
            error = f"Taslak kaydedilirken hata oluştu: {str(e)}"

    return error, success_message, ai_yaniti, secilen_mail, ai_meta


def get_imap_folder_name(folder, mail_config=None):
    if mail_config and folder in FOLDER_CANDIDATES:
        from mail import resolve_folder_name
        resolved = resolve_folder_name(mail_config, FOLDER_CANDIDATES[folder])
        if resolved:
            return resolved
    return FOLDER_IMAP.get(folder, "INBOX")


def download_mail_attachment(mail_config, folder, mail_id, index):
    from services.gmail_api import (
        GmailApiError,
        download_attachment as gmail_download_attachment,
        is_gmail_api_config,
    )

    if is_gmail_api_config(mail_config):
        try:
            return gmail_download_attachment(mail_config, str(mail_id), int(index))
        except GmailApiError as exc:
            raise RuntimeError(str(exc)) from exc

    imap_folder = get_imap_folder_name(folder, mail_config)
    return fetch_attachment(mail_config, imap_folder, mail_id, index)
