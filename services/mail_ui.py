import os

from mail import (
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
    recover_all_to_inbox,
    list_folder_uids,
    FOLDER_CANDIDATES,
    send_new_mail,
    send_reply_mail,
)
from services.chat_service import ask_gpt_mail_reply, get_client
from services.mail_threads import expand_selected_mail_ids, group_mails_by_thread
from services.mail_contacts import remember_contacts_from_fields
from services.file_service import parse_uploaded_attachment

FOLDERS = [
    {"id": "inbox", "label": "Gelen Kutusu", "icon": "inbox"},
    {"id": "starred", "label": "Yıldızlı", "icon": "star"},
    {"id": "sent", "label": "Gönderilmiş", "icon": "send"},
    {"id": "drafts", "label": "Taslaklar", "icon": "draft"},
    {"id": "spam", "label": "Spam", "icon": "report"},
    {"id": "trash", "label": "Çöp Kutusu", "icon": "delete"},
    {"id": "archive", "label": "Arşiv", "icon": "archive"},
]

FOLDER_LABELS = {
    "inbox": "Gelen Kutusu",
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


def load_folder_mails(folder, mail_config, count=20, settings=None):
    meta = {}
    settings = settings or {}

    if folder == "inbox":
        fetch_count = settings.get("inbox_fetch_count", count)
        mailler, spam_moved = get_inbox(
            mail_config,
            fetch_count,
            filter_spam=True,
            settings=settings,
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
        "starred": lambda cfg, c=count: [],
    }
    loader = loaders.get(folder, get_inbox)
    result = loader(mail_config, count)
    if isinstance(result, tuple):
        result = result[0]

    if folder in ("inbox", "sent", "spam", "trash", "archive"):
        result = group_mails_by_thread(result)

    return result, meta


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

    moved, errors = move_mails_to_folder(
        mail_config,
        imap_source,
        expanded_ids,
        ["INBOX"],
        expand_threads=True,
    )

    if moved == 0:
        raise Exception(errors[0] if errors else "Mail taşınamadı.")

    return moved, errors


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

    if islem == "olustur":
        client = get_client()
        if client is None:
            error = "Sunucuda OPENAI_API_KEY ayarlı değil."
        else:
            try:
                if user_instruction:
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
                ai_yaniti = ask_gpt_mail_reply(prompt)
                secilen_mail = {
                    "id": mail_id,
                    "sender": sender,
                    "subject": subject,
                    "content": content,
                }
            except Exception as e:
                error = f"Yanıt oluşturulurken hata: {str(e)}"

    elif islem == "revize_et":
        client = get_client()
        if client is None:
            error = "Sunucuda OPENAI_API_KEY ayarlı değil."
        else:
            try:
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
                ai_yaniti = ask_gpt_mail_reply(prompt)
                secilen_mail = {
                    "id": mail_id,
                    "sender": sender,
                    "subject": subject,
                    "content": content,
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
            moved, errors = _move_mails_to_inbox(form, mail_config, "spam")
            if moved == 1:
                success_message = "Mail spam klasöründen çıkarıldı ve gelen kutusuna taşındı."
            else:
                success_message = f"{moved} mail spam klasöründen çıkarıldı ve gelen kutusuna taşındı."
            if errors:
                success_message += f" ({len(errors)} mail taşınamadı.)"
        except Exception as e:
            error = f"Spam'dan çıkarılamadı: {str(e)}"

    elif islem == "cop_kurtar":
        try:
            moved, errors = _move_mails_to_inbox(form, mail_config, "trash")
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
        cc_email = form.get("cc_email", "").strip()
        bcc_email = form.get("bcc_email", "").strip()
        try:
            attachment = None
            if files:
                attachment = parse_uploaded_attachment(files.get("attachment"))
            send_reply_mail(
                mail_config,
                to_email=sender,
                subject=f"Re: {subject}",
                body=final_reply,
                attachments=[attachment] if attachment else None,
                cc=cc_email,
                bcc=bcc_email,
            )
            if user:
                remember_contacts_from_fields(
                    user,
                    to_email=sender,
                    cc_email=cc_email,
                    bcc_email=bcc_email,
                    own_email=mail_config.get("email"),
                )
            success_message = f"{sender} adresine yanıt başarıyla postalandı!"
            if attachment:
                success_message += f" (Ek: {attachment['filename']})"
        except Exception as e:
            error = f"E-posta gönderilirken hata oluştu: {str(e)}"

    elif islem == "yeni_gonder":
        to_email = form.get("to_email", "").strip()
        cc_email = form.get("cc_email", "").strip()
        bcc_email = form.get("bcc_email", "").strip()
        new_subject = form.get("new_subject", "").strip()
        new_body = form.get("new_body", "").strip()
        try:
            if not to_email:
                raise ValueError("Alıcı e-posta adresi gerekli.")
            attachment = None
            if files:
                attachment = parse_uploaded_attachment(files.get("attachment"))
            send_new_mail(
                mail_config,
                to_email=to_email,
                subject=new_subject,
                body=new_body,
                attachments=[attachment] if attachment else None,
                cc=cc_email,
                bcc=bcc_email,
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
            if attachment:
                success_message += f" (Ek: {attachment['filename']})"
        except Exception as e:
            error = f"E-posta gönderilirken hata oluştu: {str(e)}"

    return error, success_message, ai_yaniti, secilen_mail


def get_imap_folder_name(folder, mail_config=None):
    if mail_config and folder in FOLDER_CANDIDATES:
        from mail import resolve_folder_name
        resolved = resolve_folder_name(mail_config, FOLDER_CANDIDATES[folder])
        if resolved:
            return resolved
    return FOLDER_IMAP.get(folder, "INBOX")


def download_mail_attachment(mail_config, folder, mail_id, index):
    imap_folder = get_imap_folder_name(folder, mail_config)
    return fetch_attachment(mail_config, imap_folder, mail_id, index)
