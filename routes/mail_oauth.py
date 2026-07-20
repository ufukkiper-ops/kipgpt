"""Şifresiz mail hesabı bağlama: Gmail / Outlook / Yahoo OAuth."""

from flask import Blueprint, redirect, render_template_string, request, session, url_for

from services.oauth_mail import (
    OAUTH_PROVIDERS,
    oauth_provider_status,
    pop_oauth_state,
    save_oauth_state,
    upsert_oauth_mail_account,
)
from users import find_user_by_id

mail_oauth_bp = Blueprint("mail_oauth", __name__)

SUCCESS_HTML = """
<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hesap bağlandı</title>
<style>
body{font-family:Segoe UI,Roboto,sans-serif;background:#f6f8fc;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
.card{background:#fff;border-radius:16px;padding:28px;max-width:420px;box-shadow:0 8px 28px rgba(0,0,0,.08);text-align:center}
h1{font-size:20px;margin:0 0 8px}p{color:#5f6368;line-height:1.5}
a{display:inline-block;margin-top:16px;background:#1a73e8;color:#fff;text-decoration:none;padding:10px 18px;border-radius:20px;font-weight:600}
</style></head>
<body><div class="card">
<h1>Mail hesabı bağlandı</h1>
<p><strong>{{ email }}</strong> hesabı KipGPT ile senkronize edildi. Uygulamaya veya mail sayfasına dönebilirsiniz.</p>
<a href="/mail">Maillere git</a>
</div></body></html>
"""


def _require_user():
    user_id = session.get("user")
    user = find_user_by_id(user_id) if user_id else None
    return user_id, user


def _fail(message, mobile=False):
    if mobile:
        return render_template_string(
            SUCCESS_HTML.replace("bağlandı", "bağlanamadı").replace(
                "hesabı KipGPT ile senkronize edildi", message
            ),
            email="",
        ), 400
    session["mail_flash_error"] = message
    return redirect(url_for("mail.mail_page"))


@mail_oauth_bp.route("/mail/oauth/<provider>/start")
def oauth_start(provider):
    from services.oauth_mail import OAUTH_LOGIN_DISABLED_MESSAGE, is_oauth_login_enabled

    if not is_oauth_login_enabled():
        return _fail(OAUTH_LOGIN_DISABLED_MESSAGE)

    provider = (provider or "").strip().lower()
    if provider not in OAUTH_PROVIDERS:
        return _fail("Geçersiz sağlayıcı.")

    user_id, user = _require_user()
    if not user:
        return redirect(url_for("auth.login"))

    status = oauth_provider_status().get(provider) or {}
    if not status.get("configured"):
        return _fail(
            f"{status.get('label', provider)} OAuth henüz yapılandırılmadı. "
            "Yönetici ortam değişkenlerini eklemeli."
        )

    label = (request.args.get("label") or "").strip()
    mobile = request.args.get("mobile") == "1"

    from services.public_url import mail_oauth_redirect_uri

    redirect_uri = mail_oauth_redirect_uri(provider, request)

    try:
        if provider == "google":
            from services.google_auth import build_authorization_url

            authorization_url, state, code_verifier = build_authorization_url(
                action="link_mail",
                force_account_picker=True,
                redirect_uri=redirect_uri,
            )
        elif provider == "microsoft":
            from services.microsoft_auth import build_authorization_url

            authorization_url, state, code_verifier = build_authorization_url(
                redirect_uri=redirect_uri,
            )
        else:
            from services.yahoo_auth import build_authorization_url

            authorization_url, state, code_verifier = build_authorization_url(
                redirect_uri=redirect_uri,
            )
    except Exception as exc:
        return _fail(str(exc), mobile=mobile)

    save_oauth_state(
        state,
        {
            "user_id": user_id,
            "provider": provider,
            "code_verifier": code_verifier,
            "label": label,
            "mobile": mobile,
            "redirect_uri": redirect_uri,
        },
    )
    session["oauth_mail_state"] = state
    session.modified = True
    return redirect(authorization_url)


@mail_oauth_bp.route("/mail/oauth/google/callback")
def oauth_google_callback():
    return _handle_callback("google")


@mail_oauth_bp.route("/mail/oauth/microsoft/callback")
def oauth_microsoft_callback():
    return _handle_callback("microsoft")


@mail_oauth_bp.route("/mail/oauth/yahoo/callback")
def oauth_yahoo_callback():
    return _handle_callback("yahoo")


def _handle_callback(provider):
    error = request.args.get("error")
    state = request.args.get("state") or ""
    code = request.args.get("code") or ""
    saved = pop_oauth_state(state) if state else None
    mobile = bool((saved or {}).get("mobile"))

    if error:
        return _fail("Bağlantı iptal edildi veya reddedildi.", mobile=mobile)
    if not saved or saved.get("provider") != provider:
        return _fail("Oturum süresi doldu. Lütfen tekrar bağlayın.", mobile=mobile)

    user_id = saved.get("user_id")
    if not find_user_by_id(user_id):
        return _fail("Kullanıcı bulunamadı.", mobile=mobile)

    redirect_uri = saved.get("redirect_uri") or ""

    try:
        if provider == "google":
            from services.google_auth import (
                exchange_code_for_credentials,
                fetch_google_email,
                flow_for_callback,
            )
            from services.public_url import external_request_url, mail_oauth_redirect_uri

            flow = flow_for_callback(
                state,
                saved.get("code_verifier"),
                redirect_uri=redirect_uri or mail_oauth_redirect_uri("google", request),
            )
            tokens = exchange_code_for_credentials(
                flow,
                external_request_url(request),
                require_mail_scope=True,
            )
            email = fetch_google_email(tokens["access_token"])
            provider_key = "google_oauth"
        elif provider == "microsoft":
            from services.microsoft_auth import (
                exchange_code_for_tokens,
                fetch_microsoft_email,
            )
            from services.public_url import mail_oauth_redirect_uri

            tokens = exchange_code_for_tokens(
                code,
                saved.get("code_verifier") or "",
                redirect_uri=redirect_uri or mail_oauth_redirect_uri("microsoft", request),
            )
            email = fetch_microsoft_email(tokens["access_token"], tokens.get("id_token") or "")
            provider_key = "microsoft_oauth"
        else:
            from services.yahoo_auth import exchange_code_for_tokens, fetch_yahoo_email
            from services.public_url import mail_oauth_redirect_uri

            tokens = exchange_code_for_tokens(
                code,
                saved.get("code_verifier") or "",
                redirect_uri=redirect_uri or mail_oauth_redirect_uri("yahoo", request),
            )
            email = fetch_yahoo_email(tokens["access_token"])
            provider_key = "yahoo_oauth"

        if not tokens.get("refresh_token"):
            return _fail(
                "Yenileme jetonu alınamadı. Google/Microsoft/Yahoo uygulamasında "
                "offline erişimi açıp tekrar deneyin.",
                mobile=mobile,
            )

        account = upsert_oauth_mail_account(
            user_id,
            email=email,
            provider_key=provider_key,
            tokens=tokens,
            label=saved.get("label") or email,
        )
    except Exception as exc:
        return _fail(f"Bağlantı başarısız: {exc}", mobile=mobile)

    if mobile:
        return render_template_string(SUCCESS_HTML, email=account["email"])

    session["mail_flash_success"] = f"{account['email']} hesabı bağlandı ve senkronize edildi."
    return redirect(url_for("mail.mail_page", account=account["id"]))
