from flask import Blueprint, current_app, jsonify, request, send_file
from io import BytesIO

from services.api_auth import create_api_token, require_api_user
from services.mail_accounts import list_accounts_for_ui, resolve_active_mail_config
from services.mail_settings import get_mail_settings
from services.mail_ui import (
    FOLDERS,
    download_mail_attachment,
    filter_mails,
    generate_ai_mail_reply,
    generate_ai_new_mail,
    load_folder_mails,
    load_single_mail,
    mail_content_preview,
    _normalize_ai_result,
)
from services.translate_service import resolve_lang, supported_languages, translate_mail_content
from mail import send_new_mail, send_reply_mail
from services.chat_service import (
    analyze_uploaded_file,
    generate_chat_response,
    generate_chat_title,
    get_client,
)
from storage import load_data, next_chat_id, save_data
from users import (
    authenticate_local_user,
    email_exists,
    find_user_by_id,
    get_user_id,
    hash_password,
    is_valid_email,
)

mobile_api_bp = Blueprint("mobile_api", __name__, url_prefix="/api/v1")


def _user_chat_data(user_id):
    data = load_data()
    if user_id not in data or not isinstance(data[user_id], dict):
        data[user_id] = {
            "active_chat": "chat1",
            "chats": {"chat1": []},
            "chat_titles": {},
        }
        save_data(data)
    return data


def _serialize_message(message):
    item = {
        "role": message.get("role", "user"),
        "content": message.get("content", ""),
    }
    file_meta = message.get("file")
    if file_meta:
        item["file"] = {
            "name": file_meta.get("name", ""),
            "type": file_meta.get("type", "other"),
            "icon": file_meta.get("icon", ""),
        }
    return item


def _serialize_mail(mail, for_list=False):
    attachments = []
    for att in mail.get("attachments") or []:
        attachments.append({
            "index": att.get("index", 0),
            "filename": att.get("filename", ""),
            "mime": att.get("mime", ""),
            "size": att.get("size", 0),
            "is_image": bool(att.get("is_image")),
        })

    content = mail.get("content", "")
    if for_list:
        content = mail_content_preview(content)

    return {
        "id": mail.get("id", ""),
        "subject": mail.get("subject", ""),
        "sender": mail.get("sender", ""),
        "sender_display": mail.get("sender_display", ""),
        "date": mail.get("date", ""),
        "content": content,
        "attachments": attachments,
        "thread_count": mail.get("thread_count", 1),
        "starred": bool(mail.get("starred")),
    }


def _mail_context(user):
    mail_config, active_account = resolve_active_mail_config(user, {})
    settings = get_mail_settings(user)
    return mail_config, active_account, settings


@mobile_api_bp.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Auth-Token"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


@mobile_api_bp.route("/<path:_path>", methods=["OPTIONS"])
def cors_preflight(_path):
    return "", 204


@mobile_api_bp.route("/login", methods=["POST"])
def api_login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = (payload.get("password") or "").strip()

    user = authenticate_local_user(email, password)
    if not user:
        return jsonify({"error": "E-posta veya şifre hatalı."}), 401

    user_id = get_user_id(user)
    token = create_api_token(current_app.secret_key, user_id)
    return jsonify({
        "token": token,
        "user": {
            "email": user_id,
            "auth_provider": user.get("auth_provider", "local"),
        },
    })


@mobile_api_bp.route("/register", methods=["POST"])
def api_register():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = (payload.get("password") or "").strip()

    if not email or not password:
        return jsonify({"error": "E-posta ve şifre gerekli."}), 400
    if not is_valid_email(email):
        return jsonify({"error": "Geçerli bir e-posta adresi girin."}), 400
    if email_exists(email):
        return jsonify({"error": "Bu e-posta zaten kayıtlı."}), 409

    from users import load_users, save_users

    users = load_users()
    users.append({
        "email": email,
        "username": email,
        "password": hash_password(password),
        "auth_provider": "local",
        "mail_accounts": [],
    })
    save_users(users)

    data = load_data()
    data[email] = {
        "active_chat": "chat1",
        "chats": {"chat1": []},
        "chat_titles": {},
    }
    save_data(data)

    token = create_api_token(current_app.secret_key, email)
    return jsonify({
        "token": token,
        "user": {"email": email, "auth_provider": "local"},
    }), 201


@mobile_api_bp.route("/me", methods=["GET"])
@require_api_user
def api_me(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

    accounts = list_accounts_for_ui(user)
    return jsonify({
        "email": user_id,
        "auth_provider": user.get("auth_provider", "local"),
        "mail_accounts": accounts,
    })


@mobile_api_bp.route("/chats", methods=["GET"])
@require_api_user
def api_list_chats(user_id):
    data = _user_chat_data(user_id)
    user_data = data[user_id]
    chats = user_data.get("chats", {})
    titles = user_data.get("chat_titles", {})
    active = user_data.get("active_chat", "chat1")

    items = []
    for chat_id, messages in chats.items():
        last = messages[-1]["content"][:80] if messages else ""
        items.append({
            "id": chat_id,
            "title": titles.get(chat_id, "Yeni Sohbet"),
            "preview": last,
            "message_count": len(messages),
            "active": chat_id == active,
        })

    items.sort(key=lambda item: int(item["id"].replace("chat", "") or 0), reverse=True)
    return jsonify({"active_chat": active, "chats": items})


@mobile_api_bp.route("/chats", methods=["POST"])
@require_api_user
def api_new_chat(user_id):
    data = _user_chat_data(user_id)
    chats = data[user_id].setdefault("chats", {"chat1": []})
    new_id = next_chat_id(chats)
    chats[new_id] = []
    data[user_id]["active_chat"] = new_id
    save_data(data)
    return jsonify({"id": new_id, "title": "Yeni Sohbet"}), 201


@mobile_api_bp.route("/chats/<chat_id>/activate", methods=["PUT"])
@require_api_user
def api_activate_chat(user_id, chat_id):
    data = _user_chat_data(user_id)
    if chat_id not in data[user_id].get("chats", {}):
        return jsonify({"error": "Sohbet bulunamadı."}), 404
    data[user_id]["active_chat"] = chat_id
    save_data(data)
    return jsonify({"active_chat": chat_id})


@mobile_api_bp.route("/chats/<chat_id>/messages", methods=["GET"])
@require_api_user
def api_chat_messages(user_id, chat_id):
    data = _user_chat_data(user_id)
    messages = data[user_id].get("chats", {}).get(chat_id)
    if messages is None:
        return jsonify({"error": "Sohbet bulunamadı."}), 404
    return jsonify({
        "chat_id": chat_id,
        "title": data[user_id].get("chat_titles", {}).get(chat_id, "Yeni Sohbet"),
        "messages": [_serialize_message(m) for m in messages],
    })


@mobile_api_bp.route("/chats/<chat_id>/messages", methods=["POST"])
@require_api_user
def api_send_message(user_id, chat_id):
    if get_client() is None:
        return jsonify({"error": "Sunucuda OPENAI_API_KEY ayarlı değil."}), 400

    data = _user_chat_data(user_id)
    chats = data[user_id].setdefault("chats", {})
    if chat_id not in chats:
        return jsonify({"error": "Sohbet bulunamadı."}), 404

    gecmis = chats[chat_id]
    titles = data[user_id].setdefault("chat_titles", {})
    uploaded = request.files.get("file") or request.files.get("image")
    has_file = bool(uploaded and uploaded.filename)

    if has_file:
        payload_text = (
            request.form.get("text")
            or request.form.get("soru")
            or ""
        ).strip()
        prompt = payload_text or "Bu dosyayı detaylı analiz et ve Türkçe yorumla."
        try:
            answer, file_meta = analyze_uploaded_file(uploaded, prompt)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": f"Dosya analizi hatası: {e}"}), 500

        user_message = {
            "role": "user",
            "content": payload_text or f"[DOSYA] {file_meta['name']}",
            "file": file_meta,
        }
        if file_meta.get("preview"):
            user_message["image"] = file_meta["preview"]

        gecmis.append(user_message)
        gecmis.append({"role": "assistant", "content": answer})

        if chat_id not in titles:
            titles[chat_id] = file_meta["name"][:30]
    else:
        payload = request.get_json(silent=True) or {}
        text = (
            payload.get("text")
            or request.form.get("text")
            or request.form.get("soru")
            or ""
        ).strip()
        if not text:
            return jsonify({"error": "Mesaj boş olamaz."}), 400

        gecmis.append({"role": "user", "content": text})
        try:
            answer = generate_chat_response([
                {"role": m["role"], "content": m["content"]}
                for m in gecmis
            ])
        except Exception as e:
            return jsonify({"error": f"AI hatası: {e}"}), 500

        gecmis.append({"role": "assistant", "content": answer})
        if chat_id not in titles:
            try:
                titles[chat_id] = generate_chat_title(text)
            except Exception:
                titles[chat_id] = text[:30]

    data[user_id]["active_chat"] = chat_id
    save_data(data)

    response = {
        "answer": answer,
        "chat_title": titles.get(chat_id, "Yeni Sohbet"),
        "messages": [_serialize_message(m) for m in gecmis[-2:]],
    }
    last_user = gecmis[-2] if len(gecmis) >= 2 else None
    if last_user and last_user.get("file"):
        response["file"] = {
            "name": last_user["file"].get("name", ""),
            "type": last_user["file"].get("type", "other"),
            "icon": last_user["file"].get("icon", ""),
        }
    return jsonify(response)


@mobile_api_bp.route("/chats/<chat_id>", methods=["DELETE"])
@require_api_user
def api_clear_chat(user_id, chat_id):
    data = _user_chat_data(user_id)
    chats = data[user_id].get("chats", {})
    if chat_id not in chats:
        return jsonify({"error": "Sohbet bulunamadı."}), 404
    chats[chat_id] = []
    save_data(data)
    return jsonify({"cleared": True})


@mobile_api_bp.route("/mail/folders", methods=["GET"])
@require_api_user
def api_mail_folders(user_id):
    return jsonify({"folders": FOLDERS})


@mobile_api_bp.route("/mail", methods=["GET"])
@require_api_user
def api_mail_list(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

    mail_config, active_account, settings = _mail_context(user)
    if not mail_config:
        return jsonify({"error": "Mail hesabı bağlı değil. Web üzerinden mail hesabı ekleyin."}), 400

    folder = (request.args.get("folder") or "inbox").strip()
    search = (request.args.get("search") or "").strip()
    mobile_count = 35

    try:
        mailler, meta = load_folder_mails(
            folder,
            mail_config,
            count=mobile_count,
            settings=settings,
            filter_spam=True,
        )
        mailler = filter_mails(mailler, search)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "folder": folder,
        "account": active_account.get("email") if active_account else "",
        "mails": [_serialize_mail(m, for_list=True) for m in mailler],
        "meta": meta,
    })


@mobile_api_bp.route("/mail/detail", methods=["GET"])
@require_api_user
def api_mail_detail(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

    mail_config, active_account, _settings = _mail_context(user)
    if not mail_config:
        return jsonify({"error": "Mail hesabı bağlı değil."}), 400

    mail_id = (request.args.get("mail_id") or "").strip()
    folder = (request.args.get("folder") or "inbox").strip()
    if not mail_id:
        return jsonify({"error": "mail_id gerekli."}), 400

    try:
        mail = load_single_mail(folder, mail_config, mail_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not mail:
        return jsonify({"error": "Mail bulunamadı."}), 404

    return jsonify(_serialize_mail(mail))


@mobile_api_bp.route("/mail/attachment", methods=["GET"])
@require_api_user
def api_mail_attachment(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

    mail_config, _ = resolve_active_mail_config(user, {})
    if not mail_config:
        return jsonify({"error": "Mail hesabı bağlı değil."}), 400

    mail_id = request.args.get("mail_id", "")
    folder = request.args.get("folder", "inbox")
    try:
        index = int(request.args.get("index", "0"))
    except ValueError:
        return jsonify({"error": "Geçersiz ek numarası."}), 400

    try:
        filename, mime, data = download_mail_attachment(
            mail_config, folder, mail_id, index
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 404

    return send_file(
        BytesIO(data),
        mimetype=mime,
        as_attachment=True,
        download_name=filename,
    )


@mobile_api_bp.route("/mail/translate", methods=["POST"])
@require_api_user
def api_mail_translate(user_id):
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    target_lang = (payload.get("target_lang") or "").strip().lower()

    if not text:
        return jsonify({"error": "Çevrilecek içerik yok."}), 400

    code, _label = resolve_lang(target_lang)
    if not code:
        return jsonify({"error": "Geçersiz dil."}), 400

    try:
        translated = translate_mail_content(text, code)
        return jsonify({"translated": translated, "target_lang": code})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mobile_api_bp.route("/mail/languages", methods=["GET"])
@require_api_user
def api_mail_languages(user_id):
    return jsonify({"languages": supported_languages()})


@mobile_api_bp.route("/mail/ai-reply", methods=["POST"])
@require_api_user
def api_mail_ai_reply(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

    mail_config, _active_account, _settings = _mail_context(user)
    if not mail_config:
        return jsonify({"error": "Mail hesabı bağlı değil."}), 400

    payload = request.get_json(silent=True) or {}
    mail_id = (payload.get("mail_id") or "").strip()
    folder = (payload.get("folder") or "inbox").strip()
    sender = (payload.get("sender") or "").strip()
    subject = (payload.get("subject") or "").strip()
    content = (payload.get("content") or "").strip()
    user_instruction = (payload.get("user_instruction") or "").strip()
    current_draft = (payload.get("current_draft") or "").strip()
    revize_notu = (payload.get("revize_notu") or "").strip()

    if not sender:
        return jsonify({"error": "Gönderen bilgisi gerekli."}), 400

    if not content and mail_id:
        try:
            mail = load_single_mail(folder, mail_config, mail_id)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        if not mail:
            return jsonify({"error": "Mail bulunamadı."}), 404
        sender = sender or mail.get("sender", "")
        subject = subject or mail.get("subject", "")
        content = mail.get("content", "")

    if not content:
        return jsonify({"error": "Mail içeriği bulunamadı."}), 400

    try:
        result = _normalize_ai_result(
            generate_ai_mail_reply(
                sender,
                subject,
                content,
                user_instruction=user_instruction,
                current_draft=current_draft,
                revize_notu=revize_notu,
                user=user,
            )
        )
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Yanıt oluşturulurken hata: {str(e)}"}), 500

    return jsonify({
        "draft": result["body"],
        "html_body": result.get("html_body") or "",
        "library_attachments": result.get("library_attachments") or [],
        "library_file_ids": result.get("library_file_ids") or [],
        "mail": {
            "id": mail_id,
            "sender": sender,
            "subject": subject,
            "content": content,
        },
    })


@mobile_api_bp.route("/mail/send-reply", methods=["POST"])
@require_api_user
def api_mail_send_reply(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

    mail_config, _active_account, _settings = _mail_context(user)
    if not mail_config:
        return jsonify({"error": "Mail hesabı bağlı değil."}), 400

    payload = request.get_json(silent=True) or {}
    sender = (payload.get("sender") or "").strip()
    subject = (payload.get("subject") or "").strip()
    final_reply = (payload.get("final_reply") or "").strip()
    cc_email = (payload.get("cc_email") or "").strip()
    bcc_email = (payload.get("bcc_email") or "").strip()

    if not sender:
        return jsonify({"error": "Alıcı gerekli."}), 400
    if not final_reply:
        return jsonify({"error": "Yanıt metni boş."}), 400

    try:
        send_reply_mail(
            mail_config,
            to_email=sender,
            subject=f"Re: {subject}" if subject else "Re:",
            body=final_reply,
            cc=cc_email,
            bcc=bcc_email,
        )
    except Exception as e:
        return jsonify({"error": f"E-posta gönderilirken hata: {str(e)}"}), 500

    return jsonify({
        "success": True,
        "message": f"{sender} adresine yanıt gönderildi.",
    })


@mobile_api_bp.route("/mail/ai-compose", methods=["POST"])
@require_api_user
def api_mail_ai_compose(user_id):
    payload = request.get_json(silent=True) or {}
    to_email = (payload.get("to_email") or "").strip()
    subject = (payload.get("subject") or "").strip()
    user_instruction = (payload.get("user_instruction") or "").strip()
    current_draft = (payload.get("current_draft") or "").strip()
    revize_notu = (payload.get("revize_notu") or "").strip()

    if not user_instruction and not revize_notu and not current_draft and not subject:
        return jsonify({
            "error": "AI için bir ipucu yazın. Örn: Toplantı daveti yaz, kısa ve resmi olsun.",
        }), 400

    try:
        user = find_user_by_id(user_id)
        result = _normalize_ai_result(
            generate_ai_new_mail(
                to_email=to_email,
                subject=subject,
                user_instruction=user_instruction,
                current_draft=current_draft,
                revize_notu=revize_notu,
                user=user,
            )
        )
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Taslak oluşturulurken hata: {e}"}), 500

    return jsonify({
        "draft": result["body"],
        "html_body": result.get("html_body") or "",
        "library_attachments": result.get("library_attachments") or [],
        "library_file_ids": result.get("library_file_ids") or [],
    })


@mobile_api_bp.route("/mail/send-new", methods=["POST"])
@require_api_user
def api_mail_send_new(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

    mail_config, _active_account, _settings = _mail_context(user)
    if not mail_config:
        return jsonify({"error": "Mail hesabı bağlı değil."}), 400

    payload = request.get_json(silent=True) or {}
    to_email = (payload.get("to_email") or "").strip()
    subject = (payload.get("subject") or "").strip()
    body = (payload.get("body") or payload.get("new_body") or "").strip()
    cc_email = (payload.get("cc_email") or "").strip()
    bcc_email = (payload.get("bcc_email") or "").strip()

    if not to_email:
        return jsonify({"error": "Alıcı gerekli."}), 400
    if not body:
        return jsonify({"error": "Mail metni boş."}), 400

    try:
        send_new_mail(
            mail_config,
            to_email=to_email,
            subject=subject,
            body=body,
            cc=cc_email,
            bcc=bcc_email,
        )
    except Exception as e:
        return jsonify({"error": f"E-posta gönderilirken hata: {str(e)}"}), 500

    return jsonify({
        "success": True,
        "message": f"{to_email} adresine mail gönderildi.",
    })


@mobile_api_bp.route("/mail/summary", methods=["POST"])
@require_api_user
def api_mail_summary(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

    payload = request.get_json(silent=True) or {}
    sender = (payload.get("sender") or "").strip()
    subject = (payload.get("subject") or "").strip()
    content = (payload.get("content") or "").strip()
    mail_id = (payload.get("mail_id") or "").strip()
    folder = (payload.get("folder") or "inbox").strip()
    create_reminders = bool(payload.get("create_reminders"))

    if not content and mail_id:
        mail_config, _active_account, _settings = _mail_context(user)
        if mail_config:
            try:
                mail = load_single_mail(folder, mail_config, mail_id)
                sender = sender or mail.get("sender", "")
                subject = subject or mail.get("subject", "")
                content = mail.get("content") or ""
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    if not content:
        return jsonify({"error": "Özetlenecek içerik yok."}), 400

    try:
        from services.mail_enrich_service import summarize_mail
        from services.calendar_service import create_events_from_actions

        summary = summarize_mail(sender, subject, content)
        created = []
        if create_reminders:
            actions = list(summary.get("reminders") or [])
            for item in summary.get("action_items") or []:
                actions.append({"title": item})
            created, _ = create_events_from_actions(user, actions, source_mail_id=mail_id)
        return jsonify({"summary": summary, "reminders_created": created})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mobile_api_bp.route("/calendar/events", methods=["GET"])
@require_api_user
def api_calendar_list(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404
    from services.calendar_service import list_events, upcoming_reminders
    return jsonify({
        "events": list_events(user),
        "reminders": upcoming_reminders(user),
    })


@mobile_api_bp.route("/files", methods=["GET"])
@require_api_user
def api_files_list(user_id):
    user = find_user_by_id(user_id)
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404
    from services.file_library_service import list_files
    return jsonify({"files": list_files(user)})
