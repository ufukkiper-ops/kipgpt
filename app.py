from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
import os, json, base64, email, re
from email.header import decode_header
from openai import OpenAI
from mail import get_last_mails, analyze_mail, send_reply_mail, connect_mail

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "gizli123")

USERS_FILE = "users.json"
DATA_FILE = "data.json"

# --- Senin Fonksiyonların ---
def ensure_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump([], f, ensure_ascii=False, indent=2)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump({}, f, ensure_ascii=False, indent=2)

def load_users():
    ensure_files()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return []

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump(users, f, ensure_ascii=False, indent=2)

def load_data():
    ensure_files()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key) if api_key else None

# --- Senin CSS'in ile Birlikte BASE_HTML ---
BASE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>KipGPT</title>
    <style>
        :root { color-scheme: light !important; --background-color: #ffffff !important; --text-color: #0f172a !important; }
        * { box-sizing: border-box; font-family: 'Inter', sans-serif; }
        html, body { margin: 0; padding: 0; background-color: #ffffff !important; color: #0f172a !important; }
        .card { max-width: 400px; margin: 100px auto; background: #ffffff !important; padding: 30px; border-radius: 16px; border: 1px solid #e2e8f0; }
        .btn-blue { background: #38bdf8 !important; color: white !important; border: none; padding: 10px; width: 100%; border-radius: 10px; cursor: pointer; }
        .error { color: #7f1d1d !important; background: #fca5a5 !important; padding: 10px; border-radius: 10px; margin-bottom: 10px; }
    </style>
</head>
<body>{{ content|safe }}</body>
</html>
"""

def render_page(content):
    return render_template_string(BASE_HTML, content=content)

# --- DÜZELTİLMİŞ ROTALAR ---

@app.route("/", methods=["GET", "POST"])
def home():
    if "user" not in session: return redirect(url_for("login"))
    return render_page("<h1>Hoş geldin!</h1><a href='/mail_kutusu'>Mail Kutusuna Git</a>")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        users = load_users()
        if any(u["username"] == username and u["password"] == password for u in users):
            session["user"] = username
            return redirect(url_for("home"))
        error = "Hatalı giriş."
    return render_page(f"<div class='card'><h2>Giriş</h2>{f'<div class=\"error\">{error}</div>' if error else ''}<form method='post'><input name='username' placeholder='Kullanıcı'><input name='password' type='password' placeholder='Şifre'><button class='btn-blue'>Giriş</button></form></div>")

@app.route("/mail_kutusu")
def mail_kutusu():
    if "user" not in session: return redirect(url_for("login"))
    mailler = get_last_mails(count=5)
    content = "<h2>Gelen Kutusu</h2>"
    for m in mailler:
        content += f"<div style='border:1px solid #ccc; padding:10px; margin:5px;'>{m.get('subject', 'Konu Yok')}</div>"
    return render_page(content)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5001)))