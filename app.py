import os
import sys
from datetime import timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

def _load_env_file() -> None:
    env_path = ROOT_DIR / ".env"
    if not env_path.is_file():
        return
    try:
        load_dotenv(env_path)
        return
    except UnicodeDecodeError:
        pass
    # PowerShell vs. UTF-8 karisimi: cp1254 ile oku, UTF-8'e cevir
    try:
        text = env_path.read_bytes().decode("cp1254")
        env_path.write_text(text, encoding="utf-8", newline="\n")
        load_dotenv(env_path)
    except Exception:
        load_dotenv(env_path, encoding="latin-1")


_load_env_file()

from services.env_setup import bootstrap_google_credentials
bootstrap_google_credentials()

from services.data_paths import ensure_data_dir
ensure_data_dir()

# Google OAuth localhost HTTP desteği
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from routes.auth_routes import auth_bp
from routes.chat_routes import chat_bp
from routes.mail_page import mail_bp
from routes.mail_oauth import mail_oauth_bp
from routes.mobile_api import mobile_api_bp
from routes.tools_routes import tools_bp
from services.security import allow_dev_quick_login, resolve_flask_secret_key
from users import ensure_dev_quick_user, ensure_dev_quick_mail_accounts, ensure_users_file


def create_app():
    ensure_users_file()
    if allow_dev_quick_login():
        ensure_dev_quick_user()
        ensure_dev_quick_mail_accounts()

    application = Flask(__name__)
    application.secret_key = resolve_flask_secret_key()
    application.config["TEMPLATES_AUTO_RELOAD"] = True
    # Oturum süre sınırı yok: çıkış yapılana kadar kalıcı (pratik üst sınır ~100 yıl)
    application.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=36500)
    application.config["SESSION_COOKIE_HTTPONLY"] = True
    application.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    public_base = (os.environ.get("PUBLIC_BASE_URL") or "").strip().lower()
    application.config["SESSION_COOKIE_SECURE"] = public_base.startswith("https://")
    # Render / reverse-proxy: https ve Host bilgisini dogru oku (OAuth callback icin kritik)
    application.wsgi_app = ProxyFix(application.wsgi_app, x_for=1, x_proto=1, x_host=1)

    application.register_blueprint(auth_bp)
    application.register_blueprint(chat_bp)
    application.register_blueprint(mail_bp)
    application.register_blueprint(mail_oauth_bp)
    application.register_blueprint(mobile_api_bp)
    application.register_blueprint(tools_bp)

    return application


app = create_app()


@app.get("/health")
def health():
    return {"ok": True, "service": "kipgpt"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    is_local = not os.environ.get("RENDER")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=is_local,
        use_reloader=is_local,
    )
