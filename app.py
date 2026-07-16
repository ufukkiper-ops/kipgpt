import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

from services.env_setup import bootstrap_google_credentials
bootstrap_google_credentials()

# Google OAuth localhost HTTP desteği
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

from flask import Flask

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
