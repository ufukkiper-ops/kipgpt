from functools import wraps

from flask import current_app, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

# Telefon oturumu: çıkış yapılana kadar (web ile aynı; ~100 yıl pratik üst sınır)
TOKEN_MAX_AGE = 36500 * 24 * 3600


def _serializer(secret_key):
    return URLSafeTimedSerializer(secret_key, salt="kipgpt-mobile")


def create_api_token(secret_key, user_id):
    return _serializer(secret_key).dumps({"user": user_id})


def verify_api_token(secret_key, token):
    if not token:
        return None
    try:
        data = _serializer(secret_key).loads(token, max_age=TOKEN_MAX_AGE)
        return (data.get("user") or "").strip() or None
    except (BadSignature, SignatureExpired):
        return None


def get_bearer_token():
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.headers.get("X-Auth-Token", "").strip() or None


def require_api_user(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = get_bearer_token()
        user_id = verify_api_token(current_app.secret_key, token)
        if not user_id:
            return jsonify({"error": "Giriş gerekli."}), 401
        return view(user_id, *args, **kwargs)

    return wrapper
