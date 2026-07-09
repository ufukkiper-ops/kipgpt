from mail import get_last_mails, analyze_mail, send_reply_mail
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

BASE_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="color-scheme" content="light">
    
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico?v=3">
    <link rel="shortcut icon" type="image/x-icon" href="/static/favicon.ico?v=3">
    <link rel="apple-touch-icon" sizes="192x192" href="/static/icon.png?v=3">
    <meta name="mobile-web-app-capable" content="yes">
    
    <title>KipGPT</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
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
        a { text-decoration: none; color: inherit; }
        .layout { display: flex; width: 100%; height: 100%; background-color: #ffffff !important; }
        .sidebar {
            width: 280px; background: #f8fafc !important; padding: 20px;
            border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; gap: 15px;
        }
        .sidebar h2 { margin: 0; font-size: 20px; font-weight: 600; color: #0284c7 !important; }
        .user-box { padding: 12px; background: #f1f5f9 !important; border-radius: 12px; font-size: 14px; border: 1px solid #e2e8f0; color: #334155 !important; }
        .new-chat { display: block; width: 100%; background: linear-gradient(135deg, #38bdf8, #0284c7) !important; color: white !important; text-align: center; padding: 12px; border-radius: 12px; font-weight: 600; transition: all 0.2s; }
        .new-chat:hover { opacity: 0.9; transform: translateY(-1px); }
        .chat-list { display: flex; flex-direction: column; gap: 8px; overflow-y: auto; flex: 1; }
        .chat-item { display: block; padding: 12px; border-radius: 10px; background: #f1f5f9 !important; font-size: 14px; border: 1px solid transparent; transition: all 0.2s; color: #334155 !important; }
        .chat-item:hover { background: #e2e8f0 !important; }
        .chat-item.active { background: #3b82f6 !important; border-color: #2563eb !important; color: white !important; }
        .main { flex: 1; display: flex; flex-direction: column; background-color: #ffffff !important; }
        .topbar { background: #f8fafc !important; padding: 15px 25px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; color: #334155 !important; }
        .right-buttons { display: flex; gap: 10px; }
        .btn { border: none; border-radius: 10px; padding: 10px 16px; cursor: pointer; font-weight: 500; transition: opacity 0.2s; }
        .btn:hover { opacity: 0.9; }
        .btn-blue { background: #38bdf8 !important; color: black !important; }
        .btn-red { background: #ef4444 !important; color: white !important; }
        .btn-green { background: #10b981 !important; color: white !important; }
        .messages { flex: 1; padding: 25px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; background-color: #ffffff !important; }
        .msg { max-width: 75%; padding: 14px 18px; border-radius: 16px; line-height: 1.6; white-space: pre-wrap; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
        .msg-user { background: #0284c7 !important; color: white !important; align-self: flex-end; border-bottom-right-radius: 4px; }
        .msg-user * { color: white !important; }
        .msg-bot { background-color: #f1f5f9 !important; color: #0f172a !important; align-self: flex-start; border-bottom-left-radius: 4px; border: 1px solid #e2e8f0; }
        .msg-bot, .msg-bot *, .bot-text, .messages .msg-bot * { color: #0f172a !important; }
        .msg img { max-width: 100%; border-radius: 10px; margin-top: 10px; }
        .bottom { padding: 20px; background: #f8fafc !important; border-top: 1px solid #e2e8f0; display: flex; flex-direction: column; gap: 10px; }
        .input-container { display: flex; background: #ffffff !important; border-radius: 14px; padding: 6px; align-items: center; border: 1px solid #cbd5e1; }
        .input-container input[type="text"] { flex: 1; background: transparent !important; border: none; padding: 10px 15px; color: #0f172a !important; font-size: 15px; outline: none; }
        .card { max-width: 400px; margin: 100px auto; background: #ffffff !important; padding: 30px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); color: #0f172a !important; }
        .card input { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #cbd5e1; background: #ffffff !important; border-radius: 10px; color: #0f172a !important; }
        .error { color: #7f1d1d !important; background: #fca5a5 !important; padding: 12px; border-radius: 10px; margin-bottom: 15px; font-size: 14px; }
        .image-bar { display: flex; gap: 10px; align-items: center; font-size: 13px; background: #f1f5f9 !important; padding: 8px 12px; border-radius: 10px; color: #334155 !important; }
        @media (max-width: 768px) { .sidebar { display: none; } }
    </style>
</head>
<body>
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

@app.route("/mail", methods=["GET", "POST"])
def mail_page():
    if "user" not in session: 
        return redirect(url_for("login"))
        
    error = ""
    success_message = ""
    ai_yaniti = ""
    secilen_mail = {}
    mailler = []

    try:
        mailler = get_last_mails(count=5) 
    except Exception as e:
        error = f"Mailler çekilirken hata oluştu: {str(e)}"

    if request.method == "POST":
        islem = request.form.get("islem")
        sender = request.form.get("sender")
        subject = request.form.get("subject")
        content = request.form.get("content")
        user_instruction = request.form.get("user_instruction", "").strip()
        current_draft = request.form.get("current_draft", "").strip()
        revize_notu = request.form.get("revize_notu", "").strip()
        
        if islem == "olustur":
            client = get_client()
            if client is None:
                error = "Sunucuda OPENAI_API_KEY ayarlı değil."
            else:
                try:
                    talimat_ekleme = f"\nKullanıcının Özel İsteği/Notu: {user_instruction}" if user_instruction else ""
                    prompt = f"""Gelen Mail Kimden: {sender}
Konu: {subject}
İçerik: {content}
{talimat_ekleme}

Yukarıdaki maili, kullanıcının özel isteğini dikkate alarak profesyonel, kibar ve çözüm odaklı şekilde Türkçe olarak yanıtla.

⚠️ KRİTİK KURAL: Yanıtında ASLA "İşte güncellenmiş mail", "Tabii ki yazıyorum", "Merhaba" (eğer maile ait değilse) gibi hiçbir giriş, açıklama veya kapanış cümlesi kurma. Sadece ve sadece KARŞI TARAFA GÖNDERİLECEK mail metnini yaz."""

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    ai_yaniti = response.choices[0].message.content.strip()
                    secilen_mail = {"sender": sender, "subject": subject, "content": content}
                except Exception as e:
                    error = f"Yanıt oluşturulurken hata: {str(e)}"
                    
        elif islem == "revize_et":
            client = get_client()
            if client is None:
                error = "Sunucuda OPENAI_API_KEY ayarlı değil."
            else:
                try:
                    prompt = f"""Gelen Mail Kimden: {sender}
Konu: {subject}
İçerik: {content}

Daha Önce Hazırlanan Taslak:
{current_draft}

Kullanıcının Taslağı Yeniden Düzenleme İsteği:
{revize_notu}

Yukarıdaki eski taslağı, kullanıcının yeni düzenleme isteği doğrultusunda güncelleyerek yeniden Türkçe olarak yaz.

⚠️ KRİTİK KURAL: Yanıtında ASLA "İsteğiniz üzerine düzelttim", "Şöyle değiştirdim" gibi hiçbir açıklama cümlesi yer almasın. Sadece ve sadece KARŞI TARAFA GÖNDERİLECEK olan nihai mail metnini döndür."""

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    ai_yaniti = response.choices[0].message.content.strip()
                    secilen_mail = {"sender": sender, "subject": subject, "content": content}
                except Exception as e:
                    error = f"Taslak yeniden düzenlenirken hata: {str(e)}"

        elif islem == "gonder":
            final_reply = request.form.get("final_reply")
            try:
                send_reply_mail(to_email=sender, subject=f"Re: {subject}", body=final_reply)
                success_message = f"{sender} adresine yanıt başarıyla postalandı!"
            except Exception as e:
                error = f"E-posta gönderilirken hata oluştu: {str(e)}"

    mail_items_html = ""
    if mailler:
        for m in mailler:
            mail_items_html += f"""
            <div class="user-box" style="margin-bottom: 20px; background: #ffffff !important; border-left: 4px solid #10b981; padding: 15px;">
                <p style="margin: 4px 0;"><b>Kimden:</b> {m.get('sender_display', 'Bilinmiyor')}</p>
                <p style="margin: 4px 0;"><b>Konu:</b> {m.get('subject', 'Konu Yok')}</p>
                <p style="background: #f8fafc; padding: 10px; border-radius: 8px; font-size: 13px; max-height: 120px; overflow-y: auto; margin-top: 8px;">{m.get('content', '')}</p>
                
                <form method="post" style="margin-top: 12px; display: flex; flex-direction: column; gap: 8px;">
                    <input type="hidden" name="islem" value="olustur">
                    <input type="hidden" name="sender" value="{m.get('sender', '')}">
                    <input type="hidden" name="subject" value="{m.get('subject', '')}">
                    <input type="hidden" name="content" value="{m.get('content', '')}">
                    
                    <input type="text" name="user_instruction" placeholder="Yapay zekaya not bırakın (Örn: Teklifi reddet...)" 
                           style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; box-sizing: border-box; background:#ffffff !important;">
                    
                    <button class="btn btn-blue" type="submit" style="padding: 8px 12px; font-size: 13px; align-self: flex-start;">🤖 KipGPT ile Yanıt Oluştur</button>
                </form>
            </div>
            """
    else:
        mail_items_html = "<p style='color:#64748b;'>Kutuda mail bulunamadı.</p>"

    # 🔄 Türkçe Karakterleri korumak için Güvenli JS Enjeksiyonlu Taslak Alanı
    ai_preview_html = ""
    if ai_yaniti:
        # Satır atlamalarını JavaScript dizesine güvenli taşımak için hazırlıyoruz
        js_safe_reply = ai_yaniti.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
        
        ai_preview_html = f"""
        <div class="user-box" style="margin-bottom: 25px; background: #f0fdf4 !important; border: 1px solid #bbf7d0; padding: 15px;">
            <h4 style="margin-top:0; color:#166534; margin-bottom: 8px;">🤖 KipGPT Taslak Yanıtı</h4>
            <p style="font-size:12px; color:#64748b; margin-bottom:8px;">Alıcı: {secilen_mail.get('sender')}</p>
            
            <form method="post" style="margin-bottom: 15px;">
                <input type="hidden" name="islem" value="gonder">
                <input type="hidden" name="sender" value="{secilen_mail.get('sender')}">
                <input type="hidden" name="subject" value="{secilen_mail.get('subject')}">
                
                <textarea id="aiDraftTextArea" name="final_reply" style="width:100%; height:150px; padding:10px; border-radius:8px; border:1px solid #cbd5e1; font-family:inherit; font-size:14px; margin-bottom:10px; box-sizing: border-box;"></textarea>
                <button class="btn btn-green" type="submit" style="width:100%; padding:10px; font-weight:600;">🚀 Yanıtı E-Posta Olarak Gönder</button>
            </form>
            
            <div style="background: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #cbd5e1;">
                <h5 style="margin: 0 0 8px 0; color: #334155; font-size: 13px;">🔄 Yanıtı Beğenmediniz mi? Yapay Zekaya Yeniden Düzenletin:</h5>
                <form method="post" style="display: flex; flex-direction: column; gap: 8px;">
                    <input type="hidden" name="islem" value="revize_et">
                    <input type="hidden" name="sender" value="{secilen_mail.get('sender')}">
                    <input type="hidden" name="subject" value="{secilen_mail.get('subject')}">
                    <input type="hidden" name="content" value="{secilen_mail.get('content')}">
                    <input type="hidden" id="aiCurrentDraftHidden" name="current_draft" value="">
                    
                    <input type="text" name="revize_notu" placeholder="Şu yönde yenile: (Örn: Daha resmi yaz...)" required
                           style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; box-sizing: border-box;">
                    <button class="btn btn-blue" type="submit" style="padding: 6px 12px; font-size: 12px; align-self: flex-start; background: #64748b !important;">Taslağı Güncelle</button>
                </form>
            </div>
            
            <script>
                (function() {{
                    var rawReply = `{js_safe_reply}`;
                    document.getElementById('aiDraftTextArea').value = rawReply;
                    document.getElementById('aiCurrentDraftHidden').value = rawReply;
                }})();
            </script>
        </div>
        """

    content_html = f"""
    <div class="layout" style="justify-content: center; overflow-y: auto; padding: 20px 15px;">
        <div class="card" style="max-width: 700px; margin: 0 auto; width: 100%; padding: 20px; box-sizing: border-box;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin:0; font-size:20px;">E-Posta Asistanı</h2>
                <a href="/"><button class="btn btn-blue" style="padding: 6px 12px; font-size: 13px;">Sohbete Dön</button></a>
            </div>
            
            {"<div class='error'>" + error + "</div>" if error else ""}
            {"<div class='error' style='background:#d1fae5 !important; color:#065f46 !important; border:1px solid #a7f3d0;'> " + success_message + "</div>" if success_message else ""}
            
            {ai_preview_html}

            <div style="margin-top: 10px;">
                <h3 style="font-size: 15px; color: #334155; margin-bottom:8px;">Son Gelen E-Postalar</h3>
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin-bottom: 15px;">
                {mail_items_html}
            </div>
        </div>
    </div>
    """
    
    from flask import make_response
    response = make_response(render_page(content_html))
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)