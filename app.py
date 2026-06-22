from flask import Flask, request, render_template_string, redirect, url_for, session
import os
import json
from openai import OpenAI

app = Flask(__name__)
app.secret_key = "gizli123"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# DOSYA YARDIMCI FONKSİYONLARI
# =========================
def load_users():
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_users(users):
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_data():
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# HTML
# =========================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Asistan</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0f172a;
            margin: 0;
            padding: 0;
            color: white;
        }
        .container {
            max-width: 700px;
            margin: auto;
            min-height: 100vh;
            background: #1e293b;
            display: flex;
            flex-direction: column;
        }
        .topbar {
            padding: 15px;
            background: #020617;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .messages {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
        }
        .msg-user {
            background: #0ea5e9;
            color: black;
            padding: 10px;
            border-radius: 10px;
            margin: 8px 0;
            text-align: right;
        }
        .msg-bot {
            background: #22c55e;
            color: black;
            padding: 10px;
            border-radius: 10px;
            margin: 8px 0;
            text-align: left;
        }
        .bottom {
            padding: 12px;
            background: #020617;
        }
        form {
            display: flex;
            gap: 8px;
        }
        input {
            flex: 1;
            padding: 12px;
            border-radius: 8px;
            border: none;
        }
        button {
            padding: 12px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        .btn-blue {
            background: #38bdf8;
        }
        .btn-red {
            background: #ef4444;
            color: white;
        }
        .card {
            max-width: 420px;
            margin: 70px auto;
            background: #1e293b;
            padding: 20px;
            border-radius: 12px;
        }
        .card input {
            width: 100%;
            margin-bottom: 10px;
            box-sizing: border-box;
        }
        a {
            color: #38bdf8;
            text-decoration: none;
        }
        .error {
            color: #f87171;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    %CONTENT%
</body>
</html>
"""


# =========================
# REGISTER
# =========================
@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == "" or password == "":
            error = "Kullanıcı adı ve şifre boş olamaz."
        else:
            users = load_users()

            for user in users:
                if user["username"] == username:
                    error = "Bu kullanıcı adı zaten var."
                    break

            if error == "":
                users.append({
                    "username": username,
                    "password": password
                })
                save_users(users)
                return redirect(url_for("login"))

    content = f"""
    <div class="card">
        <h2>Kayıt Ol</h2>
        <div class="error">{error}</div>
        <form method="post">
            <input name="username" placeholder="Kullanıcı adı">
            <input name="password" type="password" placeholder="Şifre">
            <button class="btn-blue" type="submit">Kayıt Ol</button>
        </form>
        <p>Zaten hesabın var mı? <a href="/login">Giriş Yap</a></p>
    </div>
    """
    return HTML.replace("%CONTENT%", content)


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        users = load_users()
        found = False

        for user in users:
            if user["username"] == username and user["password"] == password:
                session["user"] = username
                found = True
                break

        if found:
            return redirect(url_for("index"))
        else:
            error = "Kullanıcı adı veya şifre hatalı."

    content = f"""
    <div class="card">
        <h2>Giriş Yap</h2>
        <div class="error">{error}</div>
        <form method="post">
            <input name="username" placeholder="Kullanıcı adı">
            <input name="password" type="password" placeholder="Şifre">
            <button class="btn-blue" type="submit">Giriş Yap</button>
        </form>
        <p>Hesabın yok mu? <a href="/register">Kayıt Ol</a></p>
    </div>
    """
    return HTML.replace("%CONTENT%", content)


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# =========================
# CHAT ANA SAYFA
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    data = load_data()

    if username not in data:
        data[username] = []

    gecmis = data[username]

    if request.method == "POST":
        soru = request.form.get("soru", "").strip()

        if soru != "":
            gecmis.append({"role": "user", "content": soru})

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=gecmis
            )

            cevap = response.choices[0].message.content
            gecmis.append({"role": "assistant", "content": cevap})

            data[username] = gecmis
            save_data(data)

    messages_html = ""
    for mesaj in gecmis:
        if mesaj["role"] == "user":
            messages_html += f'<div class="msg-user"><b>Sen:</b> {mesaj["content"]}</div>'
        else:
            messages_html += f'<div class="msg-bot"><b>AI:</b> {mesaj["content"]}</div>'

    content = f"""
    <div class="container">
        <div class="topbar">
            <div><b>AI Asistan</b> — {username}</div>
            <div>
                <a href="/logout" style="color:white;">Çıkış Yap</a>
            </div>
        </div>

        <div class="messages">
            {messages_html}
        </div>

        <div class="bottom">
            <form method="post">
                <input name="soru" placeholder="Mesaj yaz..." autofocus>
                <button class="btn-blue" type="submit">Gönder</button>
            </form>

            <form method="post" action="/temizle" style="margin-top:10px;">
                <button class="btn-red" type="submit">Temizle</button>
            </form>
        </div>
    </div>
    """
    return HTML.replace("%CONTENT%", content)


# =========================
# TEMİZLE
# =========================
@app.route("/temizle", methods=["POST"])
def temizle():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    data = load_data()
    data[username] = []
    save_data(data)

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

