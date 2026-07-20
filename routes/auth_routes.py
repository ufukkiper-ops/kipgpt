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
    if "user" in session:
        return redirect(url_for("mail.mail_page"))

    error = session.pop("auth_error", "")
    from services.oauth_mail import is_oauth_login_enabled

    google_enabled = is_oauth_login_enabled() and is_google_configured()

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
            # Istege bagli: kayit formunda "Gmail'i de bagla" secildiyse
            if google_enabled and request.form.get("link_gmail") == "1":
                session["mail_flash_success"] = (
                    "Hesabınız oluşturuldu. Gmail’i bağlamak için Google hesabınızı onaylayın."
                )
                return redirect(url_for("mail_oauth.oauth_start", provider="google"))
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
        try:
            from services.env_setup import save_google_credentials_from_json

            json_file = request.files.get("client_json")
            if json_file and json_file.filename:
                raw = json_file.read().decode("utf-8", errors="replace")
                save_google_credentials_from_json(raw, get_redirect_uri())
            else:
                client_id = request.form.get("client_id", "").strip()
                client_secret = request.form.get("client_secret", "").strip()
                if not client_id or not client_secret:
                    raise ValueError(
                        "Google Cloud’dan indirdiğiniz JSON dosyasını seçin "
                        "veya gerçek Client ID + Client Secret girin "
                        "(ekrandaki gri örnek yazılar geçerli değildir)."
                    )
                if "123456789-abc" in client_id or client_id.startswith("Gerçek"):
                    raise ValueError(
                        "Örnek Client ID girdiniz. Google Cloud Console’daki "
                        "gerçek ....apps.googleusercontent.com değerini yapıştırın."
                    )
                save_google_credentials(client_id, client_secret, get_redirect_uri())
            if next_action == "link_mail":
                return redirect(url_for("mail_oauth.oauth_start", provider="google"))
            return redirect(url_for("auth.google_auth_start", action=next_action))
        except Exception as e:
            error = str(e)

    from services.google_auth import get_mail_link_redirect_uri

    return render_template(
        "google_setup.html",
        error=error,
        success=success,
        next_action=next_action,
        redirect_uri=get_redirect_uri(),
        mail_redirect_uri=get_mail_link_redirect_uri(),
        title="Google Ayarları",
    )


@auth_bp.route("/auth/google")
def google_auth_start():
    from services.oauth_mail import OAUTH_LOGIN_DISABLED_MESSAGE, is_oauth_login_enabled

    action = request.args.get("action", "register")
    with_mail = request.args.get("with_mail") == "1" or action in {
        "link_mail",
        "register_mail",
        "login_mail",
    }
    if action == "register_mail":
        action = "register"
    elif action == "login_mail":
        action = "login"

    if not is_oauth_login_enabled():
        session["auth_error"] = OAUTH_LOGIN_DISABLED_MESSAGE
        target = url_for("auth.login") if action == "login" else url_for("auth.register")
        return redirect(target)

    if not is_google_configured():
        session["auth_error"] = (
            "Google girişi henüz kurulmadı. E-posta ve şifre ile giriş yapın."
        )
        target = url_for("auth.login") if action == "login" else url_for("auth.register")
        return redirect(target)

    try:
        force_picker = session.pop("oauth_force_picker", False)
        with_mail = with_mail or bool(session.pop("oauth_with_mail", False))
        authorization_url, state, code_verifier = build_authorization_url(
            action,
            force_picker,
            with_mail=with_mail,
        )
    except Exception as e:
        session["auth_error"] = str(e)
        return redirect(url_for("auth.register") if action == "register" else url_for("auth.login"))

    session["oauth_state"] = state
    session["oauth_code_verifier"] = code_verifier
    session["oauth_action"] = action
    session["oauth_with_mail"] = with_mail
    session.modified = True
    return redirect(authorization_url)


MOBILE_AUTH_HTML = """
<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Giriş tamam</title>
<style>
body{font-family:Segoe UI,Roboto,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.card{background:#1e293b;border-radius:16px;padding:28px;max-width:420px;text-align:center}
a{display:inline-block;margin-top:16px;background:#2563eb;color:#fff;text-decoration:none;padding:12px 18px;border-radius:20px;font-weight:600}
p{color:#94a3b8;line-height:1.5}
</style></head>
<body><div class="card">
<h1>{{ title }}</h1>
<p>{{ message }}</p>
{% if deep_link %}<a id="open-app" href="{{ deep_link }}">Uygulamaya dön</a>
<script>setTimeout(function(){ location.href={{ deep_link|tojson }}; }, 400);</script>{% endif %}
</div></body></html>
"""


@auth_bp.route("/auth/google/callback")
def google_auth_callback():
    from flask import current_app, render_template_string
    from services.api_auth import create_api_token
    from services.oauth_mail import pop_oauth_state

    error = request.args.get("error")
    state_q = (request.args.get("state") or "").strip()

    action = session.pop("oauth_action", None)
    with_mail = bool(session.pop("oauth_with_mail", False))
    state = session.pop("oauth_state", None)
    code_verifier = session.pop("oauth_code_verifier", None)
    mobile = False

    # Android / dosya tabanli state (session yok)
    if (not code_verifier or state != state_q) and state_q:
        saved = pop_oauth_state(state_q)
        if saved and saved.get("purpose") == "auth":
            code_verifier = saved.get("code_verifier")
            state = state_q
            action = saved.get("action") or "login"
            with_mail = bool(saved.get("with_mail"))
            mobile = bool(saved.get("mobile"))

    action = action or "register"

    def _fail_auth(message):
        if mobile:
            return render_template_string(
                MOBILE_AUTH_HTML,
                title="Giriş başarısız",
                message=message,
                deep_link=None,
            ), 400
        session["auth_error"] = message
        return redirect(url_for("auth.login") if action == "login" else url_for("auth.register"))

    if error:
        if error in ("login_required", "interaction_required", "consent_required") and not mobile:
            session["oauth_force_picker"] = True
            session["oauth_action"] = action
            session["oauth_with_mail"] = with_mail
            return redirect(
                url_for(
                    "auth.google_auth_start",
                    action=action,
                    with_mail="1" if with_mail else "0",
                )
            )
        return _fail_auth("Google bağlantısı iptal edildi.")

    if not state or not code_verifier:
        return _fail_auth("Oturum süresi doldu. Lütfen tekrar deneyin.")

    try:
        from services.google_auth import _has_gmail_scope
        from services.public_url import external_request_url

        flow = flow_for_callback(state, code_verifier, with_mail=with_mail)
        oauth_tokens = exchange_code_for_credentials(
            flow,
            external_request_url(request),
            require_mail_scope=with_mail,
        )
        email = fetch_google_email(oauth_tokens["access_token"])
        mail_linked = with_mail and _has_gmail_scope(oauth_tokens.get("scopes"))
    except Exception as e:
        return _fail_auth(f"Google bağlantısı başarısız: {e}")

    existing = find_user(email)

    try:
        if existing:
            link_google_mail_to_user(email, oauth_tokens, link_mail=mail_linked)
        elif action == "login":
            return _fail_auth("Bu Google hesabı kayıtlı değil. Önce kayıt olun.")
        else:
            create_google_user(email, oauth_tokens, link_mail=mail_linked)
    except Exception as e:
        return _fail_auth(f"Hesap oluşturulamadı: {e}")

    _init_user_data(email)

    if mobile:
        from urllib.parse import quote

        token = create_api_token(current_app.secret_key, email)
        deep_link = (
            f"kipgpt://oauth?token={quote(token)}&email={quote(email)}"
            f"&mail_linked={'1' if mail_linked else '0'}"
        )
        return render_template_string(
            MOBILE_AUTH_HTML,
            title="Giriş tamam",
            message=f"{email} hesabıyla giriş yapıldı."
            + (" Gmail bağlandı." if mail_linked else ""),
            deep_link=deep_link,
        )

    session["user"] = email
    if mail_linked:
        session["mail_flash_success"] = f"{email} ile giriş yapıldı; Gmail bağlandı."
    return redirect(url_for("mail.mail_page"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("mail.mail_page"))

    error = session.pop("auth_error", "")
    from services.oauth_mail import is_oauth_login_enabled

    google_enabled = is_oauth_login_enabled() and is_google_configured()

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
    user_id = session.get("user")
    if user_id:
        try:
            from services.oauth_mail import clear_user_oauth_tokens
            clear_user_oauth_tokens(user_id, revoke=True)
        except Exception:
            pass
    session.clear()
    return redirect(url_for("auth.login"))
