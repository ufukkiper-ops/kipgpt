from flask import Blueprint, current_app, jsonify, request, send_file
from io import BytesIO

from services.api_auth import create_api_token, require_api_user
from services.mail_accounts import list_accounts_for_ui, resolve_active_mail_config
from services.mail_settings import get_mail_settings
from services.mail_ui import FOLDERS, download_mail_attachment, filter_mails, load_folder_mails
from services.translate_service import translate_mail_content
from services.chat_service import generate_chat_response, generate_chat_title, get_client
from storage import load_data, save_data
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
        }
    return item


def _serialize_mail(mail):
    attachments = []
    for att in mail.get("attachments") or []:
        attachments.append({
            "index": att.get("index", 0),
            "filename": att.get("filename", ""),
            "mime": att.get("mime", ""),
            "size": att.get("size", 0),
            "is_image": bool(att.get("is_image")),
        })

    return {
        "id": mail.get("id", ""),
        "subject": mail.get("subject", ""),
        "sender": mail.get("sender", ""),
        "sender_display": mail.get("sender_display", ""),
        "date": mail.get("date", ""),
        "content": mail.get("content", ""),
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
    new_id = f"chat{len(chats) + 1}"
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
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Mesaj boş olamaz."}), 400

    if get_client() is None:
        return jsonify({"error": "Sunucuda OPENAI_API_KEY ayarlı değil."}), 400

    data = _user_chat_data(user_id)
    chats = data[user_id].setdefault("chats", {})
    if chat_id not in chats:
        return jsonify({"error": "Sohbet bulunamadı."}), 404

    gecmis = chats[chat_id]
    gecmis.append({"role": "user", "content": text})

    try:
        answer = generate_chat_response([
            {"role": m["role"], "content": m["content"]}
            for m in gecmis
        ])
    except Exception as e:
        return jsonify({"error": f"AI hatası: {e}"}), 500

    gecmis.append({"role": "assistant", "content": answer})
    titles = data[user_id].setdefault("chat_titles", {})
    if chat_id not in titles:
        try:
            titles[chat_id] = generate_chat_title(text)
        except Exception:
            titles[chat_id] = text[:30]

    data[user_id]["active_chat"] = chat_id
    save_data(data)

    return jsonify({
        "answer": answer,
        "chat_title": titles.get(chat_id, "Yeni Sohbet"),
        "messages": [_serialize_message(m) for m in gecmis[-2:]],
    })


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
    count = settings.get("inbox_fetch_count", 100)

    try:
        mailler, meta = load_folder_mails(folder, mail_config, count=count, settings=settings)
        mailler = filter_mails(mailler, search)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "folder": folder,
        "account": active_account.get("email") if active_account else "",
        "mails": [_serialize_mail(m) for m in mailler],
        "meta": meta,
    })


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
    if target_lang not in ("tr", "en", "de"):
        return jsonify({"error": "Geçersiz dil."}), 400

    try:
        translated = translate_mail_content(text, target_lang)
        return jsonify({"translated": translated, "target_lang": target_lang})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
