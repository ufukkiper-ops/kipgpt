# Gerekli kütüphaneleri ekliyoruz
from mail import get_last_mails, analyze_mail
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
import os
import json
import base64
from openai import OpenAI
from pypdf import PdfReader
import docx

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

# --- YENİ: DOKÜMAN OKUMA FONKSİYONLARI ---
def read_pdf(file_storage):
    try:
        reader = PdfReader(file_storage)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text.strip()
    except Exception as e:
        return f"[PDF Okuma Hatası: {str(e)}]"

def read_docx(file_storage):
    try:
        doc = docx.Document(file_storage)
        text = []
        for para in doc.paragraphs:
            text.append(para.text)
        return "\n".join(text).strip()
    except Exception as e:
        return f"[Word Okuma Hatası: {str(e)}]"
# -----------------------------------------

BASE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light">
    
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <link rel="shortcut icon" type="image/x-icon" href="/static/favicon.ico">
    
    <link rel="apple-touch-icon" sizes="192x192" href="/static/icon.png">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    
    <title>AI Asistan</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght=300;400;500;600&display=swap" rel="stylesheet">
    <style>
        /* CSS kodların aynen kalıyor... */
        :root {
            color-scheme: light !important;
            --background-color: #ffffff !important;
            --text-color: #0f172a !important;
        }
        * { box-sizing: border-box; font-family: 'Inter', sans-serif; }
        html, body {
            margin: 0; padding: 0;
            background-color: #ffffff !important;
            color: #0f172a !important;
            display: flex; height: 100vh; overflow: hidden;
        }
{{ content|safe }}
<script>
    const msgDiv = document.querySelector('.messages');
    if(msgDiv) msgDiv.scrollTop = msgDiv.scrollHeight;

    async function sendTextMessage(event) {
        event.preventDefault();
        const input = document.getElementById('chat-input');
        const msg = input.value.trim();
        if(!msg) return;

        input.value = '';
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
        if(role === 'user') {
            msgHtml.innerHTML = '<b>Sen:</b><br>' + text;
        } else {
            msgHtml.innerHTML = '<b class="bot-text">AI:</b><br><span class="bot-text">' + text + '</span>';
        }
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
    if "user" not in session: return redirect(url_for("login"))
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
    if "user" not in session: return redirect(url_for("login"))
    username = session["user"]
    data = load_data()
    if username in data and "chats" in data[username] and chat_id in data[username]["chats"]:
        data[username]["active_chat"] = chat_id
        save_data(data)
    return redirect(url_for("index"))

@app.route("/clear_chat", methods=["POST"])
def clear_chat():
    if "user" not in session: return redirect(url_for("login"))
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
    if "user" not in session: return redirect(url_for("login"))
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
                save_data(data)
                return jsonify({"status": "success", "answer": cevap})

        elif action == "image":  # Bu alan artık genel dosya/resim yükleme alanı oldu
            uploaded_file = request.files.get("image")
            prompt = request.form.get("image_prompt", "").strip() or "Bu dosyayı detaylı incele ve yorumla."

            if uploaded_file and uploaded_file.filename != "":
                filename = uploaded_file.filename.lower()
                
                try:
                    # --- RESİM Mİ DOKÜMAN MI KONTROLÜ ---
                    if filename.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                        # Gelen dosya resim ise vision modeline gönderiyoruz
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

                    elif filename.endswith('.pdf'):
                        # Gelen dosya PDF ise metni çıkarıyoruz
                        pdf_text = read_pdf(uploaded_file)
                        tam_soru = f"Kullanıcı bir PDF dokümanı yükledi. Sorusu: {prompt}\n\nDoküman İçeriği:\n{pdf_text}"
                        gecmis.append({"role": "user", "content": f"[DOKÜMAN - {uploaded_file.filename}] {prompt}"})
                        
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": tam_soru}]
                        )
                        cevap = response.choices[0].message.content
                        gecmis.append({"role": "assistant", "content": cevap})

                    elif filename.endswith(('.docx', '.doc')):
                        # Gelen dosya Word ise metni çıkarıyoruz
                        docx_text = read_docx(uploaded_file)
                        tam_soru = f"Kullanıcı bir Word dokümanı yükledi. Sorusu: {prompt}\n\nDoküman İçeriği:\n{docx_text}"
                        gecmis.append({"role": "user", "content": f"[DOKÜMAN - {uploaded_file.filename}] {prompt}"})
                        
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": tam_soru}]
                        )
                        cevap = response.choices[0].message.content
                        gecmis.append({"role": "assistant", "content": cevap})
                    
                    else:
                        cevap = "Desteklenmeyen dosya formatı. Lütfen Resim, PDF veya Word dosyası yükleyin."
                        gecmis.append({"role": "assistant", "content": cevap})

                    data[username]["chats"][active_chat] = gecmis
                    save_data(data)
                except Exception as e:
                    print(f"Hata: {e}")
                
                return redirect(url_for("index"))

    chat_list_html = "".join([
        f'<a class="chat-item {"active" if cid == active_chat else ""}" href="/switch/{cid}">{cid}</a>'
        for cid in chats.keys()
    ])

    messages_html = ""
    for mesaj in gecmis:
        role = mesaj.get("role", "assistant")
        content = mesaj.get("content", "")
        css = "msg msg-user" if role == "user" else "msg msg-bot"
        if role == "user":
            messages_html += f'<div class="{css}"><b>Sen:</b><br>{content}</div>'
        else:
            extra_image = f'<br><img src="{mesaj["image"]}">' if "image" in mesaj and mesaj["image"] else ""
            messages_html += f'<div class="{css}"><b class="bot-text">AI:</b><br><span class="bot-text">{content}</span>{extra_image}</div>'

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
                    <input type="file" name="image" accept="image/*,.pdf,.docx" required style="color:#0f172a; font-size:12px;">
                    <input type="text" name="image_prompt" placeholder="Dosya ile ilgili sorunuz..." style="background:#ffffff; border:1px solid #cbd5e1; padding:5px; color:#0f172a; border-radius:5px;">
                    <button class="btn btn-green" type="submit" style="padding:5px 10px; font-size:12px;">Dosyayı Yorumlat</button>
                </form>
            </div>
        </div>
    </div>
    """
    return render_page(content)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)