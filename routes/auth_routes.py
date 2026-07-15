from flask import Blueprint, redirect, render_template, request, session, url_for

from services.env_setup import save_google_credentials
from services.google_auth import (
    build_authorization_url,
    exchange_code_for_credentials,
    fetch_google_email,
    flow_for_callback,
    get_redirect_uri,
    is_google_configured,
)
from storage import load_data, save_data
from users import (
    authenticate_local_user,
    create_google_user,
    email_exists,
    find_user,
    get_user_id,
    hash_password,
    is_valid_email,
    link_google_mail_to_user,
    load_users,
    save_users,
    ensure_dev_quick_user,
)

auth_bp = Blueprint("auth", __name__)


def _init_user_data(email):
    data = load_data()
    if email not in data:
        data[email] = {
            "active_chat": "chat1",
            "chats": {"chat1": []},
            "chat_titles": {},
        }
        save_data(data)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    error = session.pop("auth_error", "")
    google_enabled = is_google_configured()

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        password2 = request.form.get("password2", "").strip()

        if not email or not password:
            error = "E-posta ve şifre boş olamaz."
        elif not is_valid_email(email):
            error = "Geçerli bir e-posta adresi girin."
        elif password != password2:
            error = "Şifreler eşleşmiyor."
        elif email_exists(email):
            error = "Bu e-posta adresi zaten kayıtlı."
        else:
            users = load_users()
            users.append({
                "email": email,
                "username": email,
                "password": hash_password(password),
                "auth_provider": "local",
                "mail_accounts": [],
            })
            save_users(users)
            _init_user_data(email)
            session["user"] = email
            return redirect(url_for("mail.mail_page"))

    return render_template(
        "register.html",
        error=error,
        google_enabled=google_enabled,
        title="Kayıt Ol",
    )


@auth_bp.route("/google-ayar", methods=["GET", "POST"])
def google_setup():
    error = ""
    success = False
    next_action = request.args.get("next", request.form.get("next", "register"))

    if request.method == "POST":
        client_id = request.form.get("client_id", "").strip()
        client_secret = request.form.get("client_secret", "").strip()
        try:
            if not client_id or not client_secret:
                raise ValueError("Client ID ve Client Secret gerekli.")
            save_google_credentials(client_id, client_secret, get_redirect_uri())
            return redirect(url_for("auth.google_auth_start", action=next_action))
        except Exception as e:
            error = str(e)

    return render_template(
        "google_setup.html",
        error=error,
        success=success,
        next_action=next_action,
        redirect_uri=get_redirect_uri(),
        title="Google Ayarları",
    )


@auth_bp.route("/auth/google")
def google_auth_start():
    action = request.args.get("action", "register")

    if not is_google_configured():
        session["auth_error"] = (
            "Google girişi henüz kurulmadı. E-posta ve şifre ile giriş yapın."
        )
        target = url_for("auth.login") if action == "login" else url_for("auth.register")
        return redirect(target)

    try:
        force_picker = session.pop("oauth_force_picker", False)
        authorization_url, state, code_verifier = build_authorization_url(action, force_picker)
    except Exception as e:
        session["auth_error"] = str(e)
        return redirect(url_for("auth.register") if action == "register" else url_for("auth.login"))

    session["oauth_state"] = state
    session["oauth_code_verifier"] = code_verifier
    session["oauth_action"] = action
    session.modified = True
    return redirect(authorization_url)


@auth_bp.route("/auth/google/callback")
def google_auth_callback():
    action = session.pop("oauth_action", "register")
    error = request.args.get("error")

    if error:
        if error in ("login_required", "interaction_required", "consent_required"):
            session["oauth_force_picker"] = True
            session["oauth_action"] = action
            return redirect(url_for("auth.google_auth_start", action=action))
        session["auth_error"] = "Google bağlantısı iptal edildi."
        return redirect(url_for("auth.login") if action == "login" else url_for("auth.register"))

    state = session.pop("oauth_state", None)
    code_verifier = session.pop("oauth_code_verifier", None)

    if not state or not code_verifier:
        session["auth_error"] = "Oturum süresi doldu. Lütfen tekrar deneyin."
        return redirect(url_for("auth.login") if action == "login" else url_for("auth.register"))

    try:
        flow = flow_for_callback(state, code_verifier)
        oauth_tokens = exchange_code_for_credentials(flow, request.url)
        email = fetch_google_email(oauth_tokens["access_token"])
    except Exception as e:
        session["auth_error"] = f"Google bağlantısı başarısız: {e}"
        return redirect(url_for("auth.login") if action == "login" else url_for("auth.register"))

    existing = find_user(email)

    if existing:
        link_google_mail_to_user(email, oauth_tokens)
    elif action == "login":
        session["auth_error"] = "Bu Google hesabı kayıtlı değil. Önce kayıt olun."
        return redirect(url_for("auth.register"))
    else:
        create_google_user(email, oauth_tokens)

    _init_user_data(email)
    session["user"] = email
    return redirect(url_for("mail.mail_page"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = session.pop("auth_error", "")
    google_enabled = is_google_configured()

    if request.method == "POST":
        identifier = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        user = authenticate_local_user(identifier, password)

        if user:
            _init_user_data(get_user_id(user))
            session["user"] = get_user_id(user)
            return redirect(url_for("mail.mail_page"))
        else:
            error = "E-posta veya şifre hatalı."

    return render_template(
        "login.html",
        error=error,
        google_enabled=google_enabled,
        title="Giriş Yap",
    )


@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("auth.login"))
