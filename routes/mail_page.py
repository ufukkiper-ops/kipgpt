from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_file, session, url_for
from io import BytesIO

from services.mail_accounts import (
    add_mail_account,
    get_active_account_id,
    list_accounts_for_ui,
    remove_mail_account,
    resolve_active_mail_config,
    set_active_account,
)
from services.mail_config import MAIL_PRESETS
from services.mail_settings import SENSITIVITY_PRESETS, get_mail_settings, save_mail_settings
from services.mail_contacts import (
    get_mail_contacts,
    remember_contacts_from_mails,
)
from services.translate_service import resolve_lang, supported_languages, translate_mail_content
from services.mail_ui import (
    FOLDERS,
    FOLDER_LABELS,
    download_mail_attachment,
    filter_mails,
    handle_mail_action,
    load_folder_mails,
    load_mail_css,
)
from users import find_user_by_id

mail_bp = Blueprint("mail", __name__)


def _get_user_and_mail():
    user = find_user_by_id(session.get("user"))
    if not user:
        return None, None, None, [], None

    mail_config, active_account = resolve_active_mail_config(user, session)
    accounts = list_accounts_for_ui(user)
    active_id = get_active_account_id(user, session)
    return user, mail_config, active_account, accounts, active_id


def _mail_url(folder="inbox", account_id=None, search=""):
    params = [f"folder={folder}"]
    if account_id:
        params.append(f"account={account_id}")
    if search:
        params.append(f"search={search}")
    return "/mail?" + "&".join(params)


@mail_bp.route("/mail-version")
def mail_version():
    return {
        "ui_version": "gmail-v71",
        "layout": "gmail-sidebar",
        "message": "Çoklu mail hesabı desteği",
    }


@mail_bp.route("/mail/attachment")
def mail_attachment():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    user, _, _, _, _ = _get_user_and_mail()
    if not user:
        return redirect(url_for("auth.login"))

    account_id = (request.args.get("account") or "").strip() or None
    mail_config, _ = resolve_active_mail_config(user, session, account_id)
    if not mail_config:
        return "Mail ayarları bulunamadı.", 400

    mail_id = request.args.get("mail_id", "")
    folder = request.args.get("folder", "inbox")
    try:
        index = int(request.args.get("index", "0"))
    except ValueError:
        return "Geçersiz ek numarası.", 400

    try:
        filename, mime, data = download_mail_attachment(
            mail_config, folder, mail_id, index
        )
    except Exception as e:
        return str(e), 404

    return send_file(
        BytesIO(data),
        mimetype=mime,
        as_attachment=True,
        download_name=filename,
    )


@mail_bp.route("/mail/translate", methods=["POST"])
def mail_translate():
    if "user" not in session:
        return jsonify({"error": "Giriş gerekli."}), 401

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    target_lang = (data.get("target_lang") or "").strip().lower()

    if not text:
        return jsonify({"error": "Çevrilecek içerik yok."}), 400

    code, _label = resolve_lang(target_lang)
    if not code:
        return jsonify({"error": "Geçersiz dil seçimi."}), 400

    try:
        translated = translate_mail_content(text, code)
        return jsonify({
            "translated": translated,
            "target_lang": code,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mail_bp.route("/mail/languages", methods=["GET"])
def mail_languages():
    if "user" not in session:
        return jsonify({"error": "Giriş gerekli."}), 401
    return jsonify({"languages": supported_languages()})


@mail_bp.route("/mail/ai-compose", methods=["POST"])
def mail_ai_compose():
    if "user" not in session:
        return jsonify({"error": "Giriş gerekli."}), 401

    user = find_user_by_id(session.get("user"))
    data = request.get_json(silent=True) or {}
    to_email = (data.get("to_email") or "").strip()
    subject = (data.get("subject") or data.get("new_subject") or "").strip()
    user_instruction = (data.get("user_instruction") or "").strip()
    current_draft = (data.get("current_draft") or "").strip()
    revize_notu = (data.get("revize_notu") or "").strip()

    if not user_instruction and not revize_notu and not current_draft and not subject:
        return jsonify({
            "error": "AI için bir ipucu yazın. Örn: Toplantı daveti yaz, kısa ve resmi olsun.",
        }), 400

    try:
        from services.mail_ui import generate_ai_new_mail, _normalize_ai_result

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
        return jsonify({
            "draft": result["body"],
            "html_body": result.get("html_body") or "",
            "library_attachments": result.get("library_attachments") or [],
            "library_file_ids": result.get("library_file_ids") or [],
            "table": result.get("table"),
            "chart": result.get("chart"),
        })
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Taslak oluşturulurken hata: {e}"}), 500


@mail_bp.route("/mail/save-draft", methods=["POST"])
def mail_save_draft():
    if "user" not in session:
        return jsonify({"error": "Giriş gerekli."}), 401

    user, mail_config, _active, _accounts, _active_id = _get_user_and_mail()
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 401
    if not mail_config:
        return jsonify({"error": "Mail hesabı bağlı değil."}), 400

    data = request.get_json(silent=True) or {}
    form = request.form if request.form else {}

    def _get(key, default=""):
        if key in data and data.get(key) is not None:
            return data.get(key)
        return form.get(key, default)

    to_email = str(_get("to_email") or "").strip()
    cc_email = str(_get("cc_email") or "").strip()
    bcc_email = str(_get("bcc_email") or "").strip()
    subject = str(_get("subject") or _get("new_subject") or "").strip()
    body = str(
        _get("body") or _get("new_body") or _get("final_reply") or ""
    ).strip()
    html_body = str(_get("html_body") or "").strip()

    try:
        from services.mail_ui import _collect_outgoing_attachments, save_outgoing_draft

        attachments = _collect_outgoing_attachments(form, request.files, user)
        library_ids = data.get("library_file_ids") if isinstance(data.get("library_file_ids"), list) else None
        if library_ids is None:
            raw_ids = str(_get("library_file_ids") or "").strip()
            library_ids = [part.strip() for part in raw_ids.split(",") if part.strip()] if raw_ids else []
        if library_ids:
            from services.file_library_service import load_attachments
            attachments.extend(load_attachments(user, library_ids))

        saved, message = save_outgoing_draft(
            mail_config,
            to_email=to_email,
            subject=subject,
            body=body,
            cc=cc_email,
            bcc=bcc_email,
            html_body=html_body,
            attachments=attachments,
        )
        return jsonify({"success": True, "saved": saved, "message": message})
    except Exception as e:
        return jsonify({"error": f"Taslak kaydedilirken hata: {e}"}), 500


@mail_bp.route("/mail/mark-read", methods=["POST"])
def mail_mark_read():
    if "user" not in session:
        return jsonify({"error": "Oturum gerekli."}), 401

    user = find_user_by_id(session.get("user"))
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

    data = request.get_json(silent=True) or {}
    mail_ids = data.get("mail_ids") or []
    if isinstance(mail_ids, str):
        mail_ids = [part.strip() for part in mail_ids.split(",") if part.strip()]
    single = (data.get("mail_id") or "").strip()
    if single and single not in mail_ids:
        mail_ids.append(single)

    folder = (data.get("folder") or request.args.get("folder") or "inbox").strip() or "inbox"
    account_id = (data.get("account") or request.args.get("account") or "").strip() or None
    if account_id:
        set_active_account(user, session, account_id)
        user = find_user_by_id(session.get("user")) or user

    mail_config, _active = resolve_active_mail_config(user, session, account_id)
    if not mail_config:
        return jsonify({"error": "Mail hesabı bağlı değil."}), 400

    try:
        from mail import mark_mails_as_read
        from services.mail_ui import get_imap_folder_name

        imap_folder = get_imap_folder_name(folder, mail_config)
        expand_threads = bool(data.get("expand_threads", True))
        marked = mark_mails_as_read(mail_config, imap_folder, mail_ids, expand_threads=expand_threads)
        return jsonify({
            "ok": True,
            "marked": marked,
            "requested": len([str(x).strip() for x in mail_ids if str(x).strip()]),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@mail_bp.route("/mail/mark-unread", methods=["POST"])
def mail_mark_unread():
    if "user" not in session:
        return jsonify({"error": "Oturum gerekli."}), 401

    user = find_user_by_id(session.get("user"))
    if not user:
        return jsonify({"error": "Kullanıcı bulunamadı."}), 404

    data = request.get_json(silent=True) or {}
    mail_ids = data.get("mail_ids") or []
    if isinstance(mail_ids, str):
        mail_ids = [part.strip() for part in mail_ids.split(",") if part.strip()]
    single = (data.get("mail_id") or "").strip()
    if single and single not in mail_ids:
        mail_ids.append(single)

    folder = (data.get("folder") or request.args.get("folder") or "inbox").strip() or "inbox"
    account_id = (data.get("account") or request.args.get("account") or "").strip() or None
    if account_id:
        set_active_account(user, session, account_id)
        user = find_user_by_id(session.get("user")) or user

    mail_config, _active = resolve_active_mail_config(user, session, account_id)
    if not mail_config:
        return jsonify({"error": "Mail hesabı bağlı değil."}), 400

    try:
        from mail import mark_mails_as_unread
        from services.mail_ui import get_imap_folder_name

        imap_folder = get_imap_folder_name(folder, mail_config)
        expand_threads = bool(data.get("expand_threads", True))
        marked = mark_mails_as_unread(mail_config, imap_folder, mail_ids, expand_threads=expand_threads)
        return jsonify({"ok": True, "marked": marked})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@mail_bp.route("/mail", methods=["GET", "POST"])
def mail_page():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    error = ""
    success_message = ""
    ai_yaniti = ""
    secilen_mail = {}
    ai_meta = {}

    folder = request.args.get("folder", "inbox")
    search = request.args.get("search", "").strip().lower()
    folder_label = FOLDER_LABELS.get(folder, "Gelen Kutusu")

    user = find_user_by_id(session.get("user"))
    if not user:
        return redirect(url_for("auth.login"))

    error = session.pop("mail_flash_error", "") or error
    success_message = session.pop("mail_flash_success", "") or success_message

    islem = request.form.get("islem", "") if request.method == "POST" else ""
    # Silme formundaki account_id hedef hesaptır; aktif hesap yapma.
    requested_account = request.args.get("account")
    if not requested_account and islem not in {"hesap_sil", "hesap_ekle"}:
        requested_account = request.form.get("account_id")
    if requested_account:
        set_active_account(user, session, requested_account)
        user = find_user_by_id(session.get("user"))

    if request.method == "POST":
        if islem == "hesap_ekle":
            try:
                new_account = add_mail_account(user, request.form)
                set_active_account(user, session, new_account["id"])
                success_message = f"{new_account['email']} hesabı eklendi."
                return redirect(_mail_url(folder, new_account["id"]))
            except Exception as e:
                error = str(e)

        elif islem == "hesap_sil":
            account_id = request.form.get("account_id", "").strip()
            try:
                next_id = remove_mail_account(user, account_id)
                set_active_account(user, session, next_id)
                session["mail_flash_success"] = "Mail hesabı silindi."
                return redirect(_mail_url(folder, next_id or None))
            except Exception as e:
                session["mail_flash_error"] = str(e)
                return redirect(_mail_url(folder, get_active_account_id(user, session), search))

        elif islem == "hesap_degistir":
            account_id = request.form.get("account_id", "").strip()
            if set_active_account(user, session, account_id):
                return redirect(_mail_url(folder, account_id, search))

        elif islem == "ayar_kaydet":
            user_id = (user.get("email") or user.get("username") or "").strip()
            try:
                save_mail_settings(user_id, request.form)
                success_message = "Mail ayarları kaydedildi."
                return redirect(_mail_url(folder, get_active_account_id(user, session), search))
            except Exception as e:
                error = str(e)

    user, mail_config, active_account, mail_accounts, active_account_id = _get_user_and_mail()
    mail_settings = get_mail_settings(user)

    mailler = []
    spam_moved = 0
    if mail_config:
        try:
            user_id = (user.get("email") or user.get("username") or "").strip()
            mailler, mail_meta = load_folder_mails(
                folder,
                mail_config,
                settings=mail_settings,
                search=search,
                user_id=user_id,
            )
            spam_moved = mail_meta.get("spam_moved", 0)
            if mail_meta.get("error") and not error:
                error = mail_meta["error"]
        except Exception as e:
            error = str(e) if not error else error
    elif not mail_accounts:
        error = error or "Henüz mail hesabı yok. Sol menüden + ile Gmail hesabı ekleyin."
    elif not error:
        error = "Seçili mail hesabına bağlanılamadı. Bilgileri kontrol edin."

    if request.method == "POST" and request.form.get("islem") not in (
        "hesap_ekle", "hesap_sil", "hesap_degistir", "ayar_kaydet"
    ):
        if not mail_config:
            error = error or "Mail ayarları bulunamadı."
        else:
            error, success_message, ai_yaniti, secilen_mail, ai_meta = handle_mail_action(
                request.form, mail_config, request.files, user=user
            )
            if success_message and request.form.get("islem") in (
                "spam", "spam_cikar", "cop_kurtar", "tumunu_geri_al"
            ):
                folder = "inbox"
                # Spam Değil sonrası güncel trusted_senders ile yeniden yükle
                if request.form.get("islem") == "spam_cikar":
                    user = find_user_by_id(session.get("user")) or user
                    mail_settings = get_mail_settings(user)
                try:
                    user_id = (user.get("email") or user.get("username") or "").strip()
                    mailler, mail_meta = load_folder_mails(
                        folder,
                        mail_config,
                        settings=mail_settings,
                        search=search,
                        user_id=user_id,
                    )
                    spam_moved = mail_meta.get("spam_moved", 0)
                    if mail_meta.get("error") and not error:
                        error = mail_meta["error"]
                except Exception as e:
                    error = str(e) if not error else error

    # Gmail API zaten sunucu tarafında aradıysa tekrar filtreleme
    from services.gmail_api import is_gmail_api_config
    if search and not is_gmail_api_config(mail_config):
        mailler = filter_mails(mailler, search)

    if spam_moved and not success_message:
        success_message = f"{spam_moved} spam mail otomatik olarak spam klasörüne taşındı."

    mail_contacts = get_mail_contacts(user) if user else []
    if user and mailler:
        remember_contacts_from_mails(
            user,
            mailler,
            own_email=(mail_config or {}).get("email"),
        )
        user = find_user_by_id(session.get("user"))
        mail_contacts = get_mail_contacts(user)

    folder_label = FOLDER_LABELS.get(folder, folder_label)
    mail_css = load_mail_css(current_app.root_path)

    from services.calendar_service import upcoming_reminders
    from services.file_library_service import list_files

    calendar_reminders = upcoming_reminders(user) if user else []
    file_library = list_files(user) if user else []

    from services.oauth_mail import oauth_provider_status

    return render_template(
        "mail.html",
        title="Mail",
        error=error,
        success_message=success_message,
        folders=FOLDERS,
        folder_label=folder_label,
        folder=folder,
        search=search,
        ai_yaniti=ai_yaniti,
        ai_meta=ai_meta or {},
        secilen_mail=secilen_mail,
        mailler=mailler,
        mail_css=mail_css,
        mail_accounts=mail_accounts,
        active_account_id=active_account_id,
        active_account=active_account,
        providers=MAIL_PRESETS,
        oauth_providers=oauth_provider_status(),
        mail_settings=mail_settings,
        sensitivity_presets=SENSITIVITY_PRESETS,
        mail_contacts=mail_contacts,
        calendar_reminders=calendar_reminders,
        file_library=file_library,
        translate_languages=supported_languages(),
        ui_version="gmail-v71",
    )
