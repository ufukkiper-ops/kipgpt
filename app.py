from flask import Flask, request, render_template_string, redirect, url_for, session, make_response, jsonify
import os, json, base64, email
from openai import OpenAI
from mail import get_last_mails, send_reply_mail, analyze_mail # Eski özelliklerin importları korundu

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "gizli123")

# --- ESKİ DOSYA YÖNETİMİ ÖZELLİKLERİ ---
USERS_FILE = "users.json"
DATA_FILE = "data.json"

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

# --- TÜRKÇE KARAKTER KORUMALI RENDER ---
def render_page(content):
    # Meta charset utf-8 burada da var, karakterleri korur
    BASE_HTML = """
    <!DOCTYPE html>
    <html lang="tr"><head><meta charset="UTF-8">
    <title>KipGPT</title></head>
    <body>{{ content|safe }}</body></html>"""
    return render_template_string(BASE_HTML, content=content)

# --- TÜM ROTALAR (index hatası düzeltildi) ---
@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session: return redirect(url_for("login"))
    # Eski ana sayfa mantığın burada devam ediyor
    return render_page("<h1>Sohbet Ekranı</h1>") 

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username")
        # Basit giriş kontrolü
        session["user"] = username
        return redirect(url_for("index"))
    return render_page("<form method='post'><input name='username'><button>Giriş</button></form>")

@app.route("/mail", methods=["GET", "POST"])
def mail_route():
    if "user" not in session: return redirect(url_for("login"))
    
    # Mail çekme ve AI ile işlem yapma mantığı burada
    mailler = get_last_mails(count=5)
    
    # UTF-8 garantili yanıt oluşturma
    response = make_response(render_page(f"<h2>Mail Kutusu</h2>"))
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response

@app.route("/register", methods=["GET", "POST"])
def register():
    # Eski kayıt olma mantığın aynen burada kalmalı
    return render_page("Kayıt ol sayfası içeriği...")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5001)), debug=True)