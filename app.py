# mail modülünü en üstte içe aktarıyoruz
from mail import get_last_mails, analyze_mail
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
import os
import json
import base64
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "gizli123")

USERS_FILE = "users.json"
DATA_FILE = "data.json"


def ensure_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


def load_users():
    ensure_files()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def load_data():
    ensure_files()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def image_file_to_data_url(file_storage):
    mime_type = file_storage.mimetype or "image/jpeg"
    raw = file_storage.read()
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


# Arka plan tamamen beyaz (#ffffff) olarak güncellendi, yazı renkleri siyah yapıldı.
BASE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Asistan</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        * { box-sizing: border-box; font-family: 'Inter', sans-serif; }
        body {
            background-color: #ffffff !important;
            color: #000000 !important;
        }
        a { text-decoration: none; color: inherit; }
        .layout {
            display: flex;
            width: 100%;
            height: 100%;
        }
        .sidebar {
            width: 280px;
            background: #f8fafc;
            padding: 20px;
            border-right: 1px solid #e2e8f0;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .sidebar h2 {
            margin: 0;
            font-size: 20px;
            font-weight: 600;
            color: #0284c7;
        }
        .user-box {
            padding: 12px;
            background: #f1f5f9;
            border-radius: 12px;
            font-size: 14px;
            border: 1px solid #e2e8f0;
            color: #334155;
        }
        .new-chat {
            display: block;
            width: 100%;
            background: linear-gradient(135deg, #38bdf8, #0284c7);
            color: white;
            text-align: center;
            padding: 12px;
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.2s;
        }
        .new-chat:hover { opacity: 0.9; transform: translateY(-1px); }
        .chat-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            overflow-y: auto;
            flex: 1;
        }
        .chat-item {
            display: block;
            padding: 12px;
            border-radius: 10px;
            background: #f1f5f9;
            font-size: 14px;
            border: 1px solid transparent;
            transition: all 0.2s;
            color: #334155;
        }
        .chat-item:hover { background: #e2e8f0; }
        .chat-item.active {
            background: #3b82f6;
            border-color: #2563eb;
            color: white;
        }
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: #ffffff;
        }
        .topbar {
            background: #f8fafc;
            padding: 15px 25px;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #334155;
        }
        .right-buttons {
            display: flex;
            gap: 10px;
        }
        .btn {
            border: none;
            border-radius: 10px;
            padding: 10px 16px;
            cursor: pointer;
            font-weight: 500;
            transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.9; }
        .btn-blue { background: #38bdf8; color: black; }
        .btn-red { background: #ef4444; color: white; }
        .btn-green { background: #10b981; color: white; }
        
        .messages {
            flex: 1;
            padding: 25px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
            background: #ffffff;
        }
        .msg {
            max-width: 75%;
            padding: 14px 18px;
            border-radius: 16px;
            line-height: 1.6;
            white-space: pre-wrap;
            font-size: 15px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }
        .msg-user {
            background: #0284c7;
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        .msg-bot {
            background: #f1f5f9;
            color: #1e293b;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
            border: 1px solid #e2e8f0;
        }
        .msg img {
            max-width: 100%;
            border-radius: 10px;
            margin-top: 10px;
        }
        .bottom {
            padding: 20px;
            background: #f8fafc;
            border-top: 1px solid #e2e8f0;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .input-container {
            display: flex;
            background: #ffffff;
            border-radius: 14px;
            padding: 6px;
            align-items: center;
            border: 1px solid #cbd5e1;
        }
        .input-container input[type="text"] {
            flex: 1;
            background: transparent;
            border: none;
            padding: 10px 15px;
            color: #1e293b;
            font-size: 15px;
            outline: none;
        }
        .card {
            max-width: 400px;
            margin: 100px auto;
            background: #ffffff;
            padding: 30px;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05);
            color: #1e293b;
        }
        .card input {
            width: 100%;
            padding: 12px;
            margin-bottom: 15px;
            border: 1px solid #cbd5e1;
            background: #ffffff;
            border-radius: 10px;
            color: #1e293b;
        }
        .error {
            color: #7f1d1d;
            background: #fca5a5;
            padding: 12px;
            border-radius: 10px;
            margin-bottom: 15px;
            font-size: 14px;
        }
        .image-bar {
            display: flex;
            gap: 10px;
            align-items: center;
            font-size: 13px;
            background: #f1f5f9;
            padding: 8px 12px;
            border-radius: 10px;
            color: #334155;
        }
        @media (max-width: 768px) {
            .sidebar { display: none; }
        }
    </style>
</head>
<body>
{{ content|safe }}

<script>
    // Sayfa yüklendiğinde mesajları en aşağı kaydır
    const msgDiv = document.querySelector('.messages');
    if(msgDiv) msgDiv.scrollTop = msgDiv.scrollHeight;

    // AJAX/Fetch ile Sayfa Yenilenmeden Anlık Mesaj Gönderme Teknolojisi
    async function sendTextMessage(event) {
        event.preventDefault();
        const input = document.getElementById('chat-input');
        const msg = input.value.trim();
        if(!msg) return;

        input.value = '';

        // Kullanıcı mesajını ekrana ekle
        appendMessage('user', msg);

        try {
            const formData = new FormData();
            formData.append('action', 'text');
            formData.append('soru', msg);

            const response = await fetch('/', { method: 'POST', body: formData });
            const data = await response.json();

            if(data.status === 'success') {
                appendMessage('bot', data.answer);
            } else {
                appendMessage('bot', 'Bir hata oluştu: ' + data.error);
            }
        } catch(e) {
            appendMessage('bot', 'Bağlantı hatası gerçekleşti.');
        }
    }

    function appendMessage(role, text) {
        const messagesContainer = document.querySelector('.messages');
        const msgHtml = document.createElement('div');
        msgHtml.className = role === 'user' ? 'msg msg-user' : 'msg msg-bot';
        msgHtml.innerHTML = `<b>${role === 'user' ? 'Sen' : 'AI'}:</b><br>${text}`;
        messagesContainer.appendChild(msgHtml);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
</script>
</body>
</html>
"""


def render_page(content):
    return render_template_string(BASE_HTML, content=content)


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
                    error = "Bu kullanıcı adı zaten kullanılıyor."
                    break

            if error == "":
                users.append({"username": username, "password": password})
                save_users(users)
                return redirect(url_for("login"))

    content = f"""
    <div class="card">
        <h2>Kayıt Ol</h2>
        {"<div class='error'>" + error + "</div>" if error else ""}
        <form method="post">
            <input name="username" placeholder="Kullanıcı adı">
            <input name="password" type="password" placeholder="Şifre">
            <button class="btn btn-blue" type="submit" style="width:100%;">Kayıt Ol</button>
        </form>
        <p style="font-size:14px; text-align:center;">Zaten hesabın var mı? <a href="/login" style="color:#0284c7;">Giriş Yap</a></p>
    </div>
    """
    return render_page(content)


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
        {"<div class='error'>" + error + "</div>" if error else ""}
        <form method="post">
            <input name="username" placeholder="Kullanıcı adı">
            <input name="password" type="password" placeholder="Şifre">
            <button class="btn btn-blue" type="submit" style="width:100%;">Giriş Yap</button>
        </form>
        <p style="font-size:14px; text-align:center;">Hesabın yok mu? <a href="/register" style="color:#0284c7;">Kayıt Ol</a></p>
    </div>
    """
    return render_page(content)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/new_chat")
def new_chat():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    data = load_data()

    if username not in data or not isinstance(data[username], dict):
        data[username] = {"active_chat": "chat1", "chats": {"chat1": []}}

    chats = data[username].setdefault("chats", {"chat1": []})
    
    new_id = f"chat{len(chats) + 1}"
    chats[new_id] = []
    data[username]["active_chat"] = new_id

    save_data(data)
    return redirect(url_for("index"))


@app.route("/switch/<chat_id>")
def switch_chat(chat_id):
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    data = load_data()

    if username in data and "chats" in data[username] and chat_id in data[username]["chats"]:
        data[username]["active_chat"] = chat_id
        save_data(data)

    return redirect(url_for("index"))


@app.route("/clear_chat", methods=["POST"])
def clear_chat():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    data = load_data()

    if username in data:
        active_chat = data[username].get("active_chat", "chat1")
        if active_chat in data[username]["chats"]:
            data[username]["chats"][active_chat] = []
            save_data(data)

    return redirect(url_for("index"))


@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    data = load_data()

    if username not in data or not isinstance(data[username], dict):
        data[username] = {"active_chat": "chat1", "chats": {"chat1": []}}

    active_chat = data[username].get("active_chat", "chat1")
    chats = data[username].setdefault("chats", {"chat1": []})
    gecmis = chats.setdefault(active_chat, [])

    if request.method == "POST":
        action = request.form.get("action", "text")
        client = get_client()

        if client is None:
            return jsonify({"status": "error", "error": "Sunucuda OPENAI_API_KEY ayarlı değil."}), 400

        # TEXT MESAJI (AJAX Desteği ile Akıcı Hale Getirildi)
        if action == "text":
            soru = request.form.get("soru", "").strip()
            if soru != "":
                gecmis.append({"role": "user", "content": soru})
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": m["role"], "content": m["content"]} for m in gecmis]
                    )
                    cevap = response.choices[0].message.content
                except Exception as e:
                    cevap = f"AI hatası: {str(e)}"

                gecmis.append({"role": "assistant", "content": cevap})
                data[username]["chats"][active_chat] = gecmis
                data[username]["chats"][active_chat] = gecmis
                save_data(data)
                
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or True:
                    return jsonify({"status": "success", "answer": cevap})

        # GÖRSEL ANALİZİ (Doğru OpenAI API Standardına Güncellendi)
        elif action == "image":
            uploaded_file = request.files.get("image")
            prompt = request.form.get("image_prompt", "").strip() or "Bu resmi detaylı yorumla."

            if uploaded_file and uploaded_file.filename != "":
                try:
                    image_data_url = image_file_to_data_url(uploaded_file)
                    gecmis.append({
                        "role": "user",
                        "content": f"[RESİM] {prompt}",
                        "image": image_data_url
                    })

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": image_data_url}}
                                ]
                            }
                        ]
                    )
                    cevap = response.choices[0].message.content
                    gecmis.append({"role": "assistant", "content": cevap})
                    data[username]["chats"][active_chat] = gecmis
                    save_data(data)
                except Exception as e:
                    print(f"Hata: {e}")
                
                return redirect(url_for("index"))

    # HTML render kısımları
    chat_list_html = "".join([
        f'<a class="chat-item {"active" if cid == active_chat else ""}" href="/switch/{cid}">{cid}</a>'
        for cid in chats.keys()
    ])

    messages_html = ""
    for mesaj in gecmis:
        role = mesaj.get("role", "assistant")
        content = mesaj.get("content", "")
        css = "msg msg-user" if role == "user" else "msg msg-bot"
        title = "Sen" if role == "user" else "AI"
        extra_image = f'<br><img src="{mesaj["image"]}">' if "image" in mesaj and mesaj["image"] else ""

        messages_html += f'<div class="{css}"><b>{title}:</b><br>{content}{extra_image}</div>'

    content = f"""
    <div class="layout">
        <div class="sidebar">
            <h2>AI Asistan</h2>
            <div class="user-box"><b>Kullanıcı:</b> {username}</div>
            <a class="new-chat" href="/new_chat">+ Yeni Sohbet</a>
            <div class="chat-list">{chat_list_html}</div>
        </div>

        <div class="main">
            <div class="topbar">
                <div><b>Aktif Sohbet:</b> {active_chat}</div>
                <div class="right-buttons">
                    <a href="/mail"><button class="btn btn-green">📧 Mailler</button></a>
                    <form method="post" action="/clear_chat" style="margin:0;">
                        <button class="btn btn-red" type="submit">Temizle</button>
                    </form>
                    <a href="/logout"><button class="btn btn-blue">Çıkış</button></a>
                </div>
            </div>

            <div class="messages">{messages_html}</div>

            <div class="bottom">
                <form class="input-container" onsubmit="sendTextMessage(event)">
                    <input id="chat-input" type="text" placeholder="Mesajınızı buraya yazın..." autofocus>
                    <button class="btn btn-blue" type="submit">Gönder</button>
                </form>

                <form class="image-bar" method="post" enctype="multipart/form-data">
                    <input type="hidden" name="action" value="image">
                    <input type="file" name="image" accept="image/*" required style="color:#1e293b; font-size:12px;">
                    <input type="text" name="image_prompt" placeholder="Resim sorusu..." style="background:#ffffff; border:1px solid #cbd5e1; padding:5px; color:#1e293b; border-radius:5px;">
                    <button class="btn btn-green" type="submit" style="padding:5px 10px; font-size:12px;">Resmi Yorumlat</button>
                </form>
            </div>
        </div>
    </div>
    """
    return render_page(content)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)