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
    remember_contacts_from_fields,
    remember_contacts_from_mails,
)
from services.translate_service import translate_mail_content
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
        "ui_version": "gmail-v39",
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

    if target_lang not in ("tr", "en", "de"):
        return jsonify({"error": "Geçersiz dil seçimi."}), 400

    try:
        translated = translate_mail_content(text, target_lang)
        return jsonify({
            "translated": translated,
            "target_lang": target_lang,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@mail_bp.route("/mail", methods=["GET", "POST"])
def mail_page():
    if "user" not in session:
        return redirect(url_for("auth.login"))

    error = ""
    success_message = ""
    ai_yaniti = ""
    secilen_mail = {}

    folder = request.args.get("folder", "inbox")
    search = request.args.get("search", "").strip().lower()
    folder_label = FOLDER_LABELS.get(folder, "Gelen Kutusu")

    user = find_user_by_id(session.get("user"))
    if not user:
        return redirect(url_for("auth.login"))

    requested_account = request.args.get("account") or request.form.get("account_id")
    if requested_account:
        set_active_account(user, session, requested_account)
        user = find_user_by_id(session.get("user"))

    if request.method == "POST":
        islem = request.form.get("islem", "")

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
                success_message = "Mail hesabı silindi."
                return redirect(_mail_url(folder, next_id))
            except Exception as e:
                error = str(e)

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
            mailler, mail_meta = load_folder_mails(
                folder, mail_config, settings=mail_settings
            )
            spam_moved = mail_meta.get("spam_moved", 0)
        except Exception as e:
            error = str(e) if not error else error
    elif not mail_accounts:
        error = error or "Henüz mail hesabı yok. Sol menüden + ile mail hesabı ekleyin."
    elif not error:
        error = "Seçili mail hesabına bağlanılamadı. Bilgileri kontrol edin."

    if request.method == "POST" and request.form.get("islem") not in (
        "hesap_ekle", "hesap_sil", "hesap_degistir", "ayar_kaydet"
    ):
        if not mail_config:
            error = error or "Mail ayarları bulunamadı."
        else:
            error, success_message, ai_yaniti, secilen_mail = handle_mail_action(
                request.form, mail_config, request.files, user=user
            )
            if success_message and request.form.get("islem") in (
                "spam", "spam_cikar", "cop_kurtar", "tumunu_geri_al"
            ):
                folder = "inbox"
                try:
                    mailler, mail_meta = load_folder_mails(
                folder, mail_config, settings=mail_settings
            )
                    spam_moved = mail_meta.get("spam_moved", 0)
                except Exception as e:
                    error = str(e)

    if spam_moved and not success_message:
        success_message = f"{spam_moved} spam mail otomatik olarak spam klasörüne taşındı."

    mailler = filter_mails(mailler, search)
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
        secilen_mail=secilen_mail,
        mailler=mailler,
        mail_css=mail_css,
        mail_accounts=mail_accounts,
        active_account_id=active_account_id,
        active_account=active_account,
        providers=MAIL_PRESETS,
        mail_settings=mail_settings,
        sensitivity_presets=SENSITIVITY_PRESETS,
        mail_contacts=mail_contacts,
        ui_version="gmail-v39",
    )
