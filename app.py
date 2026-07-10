from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify
import os
import json
import base64
import re
from openai import OpenAI
from mail import get_last_mails, send_reply_mail 
def save_users(users):
    """Kullanıcı verilerini JSON dosyasına kaydeder."""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "gizli123")

# --- DOSYA İŞLEMLERİ ---
USERS_FILE = "users.json"
DATA_FILE = "data.json"

def ensure_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f: json.dump([], f, ensure_ascii=False, indent=2)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump({}, f, ensure_ascii=False, indent=2)

ensure_files()

def load_users():
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return []

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key) if api_key else None
BASE_HTML = """
<!DOCTYPE html>
<html lang="tr"><head><meta charset="UTF-8"><title>KipGPT</title>
<style>
    body { font-family: 'Inter', sans-serif; margin: 0; background: #fff; }
    .layout { display: flex; width: 100%; height: 100vh; }
    .card { max-width: 700px; margin: 40px auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 16px; }
    .btn { border: none; border-radius: 10px; padding: 10px 16px; cursor: pointer; }
    .btn-blue { background: #38bdf8; }
    .btn-green { background: #10b981; color: white; }
    .error { color: #7f1d1d; background: #fca5a5; padding: 10px; border-radius: 10px; margin-bottom: 10px; }
</style>
<script>
async function sendTextMessage(event) {
    event.preventDefault();

    const input = document.getElementById("chat-input");
    const message = input.value.trim();

    if (!message) return;

    const formData = new FormData();
    formData.append("action", "text");
    formData.append("soru", message);

    try {
        const response = await fetch("/", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (data.status === "success") {
            location.reload();
        } else {
            alert(data.error || "Bir hata oluştu.");
        }

    } catch (e) {
        alert("Sunucuya bağlanılamadı.");
        console.error(e);
    }

    input.value = "";
}
</script>
</head><body>{{ content|safe }}</body></html>
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
    # render registration form
    content = '''
    <div class="card">
        <h2>Kayıt Ol</h2>
        <form method="post">
            <input name="username" placeholder="Kullanıcı adı">
            <input name="password" type="password" placeholder="Şifre">
            <button class="btn btn-blue" type="submit" style="width:100%;">Kayıt Ol</button>
        </form>
        <p style="font-size:14px; text-align:center;">Zaten hesabın var mı? <a href="/login" style="color:#0284c7;">Giriş Yap</a></p>
    </div>
    '''
    return render_page(content)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        users = load_users()
        if any(u["username"] == username and u["password"] == password for u in users):
            session["user"] = username
            return redirect(url_for("mail_page"))
    return render_page('<div class="card"><h2>Giriş</h2><form method="post"><input name="username" placeholder="Kullanıcı"><input name="password" type="password" placeholder="Şifre"><button type="submit">Giriş</button></form></div>')
      
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
    if "user" not in session: return redirect(url_for("login"))
    error = "" 
    success_message = ""
    ai_yaniti = ""
    secilen_mail = {}
    

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
        user_instruction = request.form.get("user_instruction", "").strip() # Kullanıcının özel talimatı
        user_instruction = request.form.get("user_instruction", "").strip()
        current_draft = request.form.get("current_draft", "").strip() # Mevcut taslak metni
        revize_notu = request.form.get("revize_notu", "").strip()     # Yeniden düzenleme notu

        if islem == "olustur":
            client = get_client()
            if client is None:
                error = "Sunucuda OPENAI_API_KEY ayarlı değil."
            else:
                try:
                    # Yapay zekaya hem gelen maili hem de senin özel talimatını gönderiyoruz:
                    talimat_ekleme = f"\nKullanıcının Özel İsteği/Notu: {user_instruction}" if user_instruction else ""
                    
                    prompt = f"""Gelen Mail Kimden: {sender}
Konu: {subject}
İçerik: {content}
{talimat_ekleme}

Yukarıdaki maili, varsa kullanıcının özel isteğini/notunu dikkate alarak profesyonel, kibar ve çözüm odaklı şekilde Türkçe olarak yanıtla."""

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    ai_yaniti = response.choices[0].message.content
                    secilen_mail = {"sender": sender, "subject": subject, "content": content}
                except Exception as e:
                    error = f"Yanıt oluşturulurken hata: {str(e)}"

        elif islem == "revize_et":
            # 🔄 MEVCUT TASLAĞI YENİDEN DÜZENLEME AŞAMASI
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

Lütfen daha önce hazırlanan taslağı, kullanıcının yeni düzenleme isteği doğrultusunda güncelleyerek yeniden Türkçe olarak yaz."""

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    ai_yaniti = response.choices[0].message.content
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
                    
                    <input type="text" name="user_instruction" placeholder="Yapay zekaya not bırakın (Örn: Teklifi reddet, haftaya ertele...)" 
                    <input type="text" name="user_instruction" placeholder="Yapay zekaya not bırakın (Örn: Teklifi reddet...)" 
                           style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; box-sizing: border-box; background:#ffffff !important;">
                    
                    <button class="btn btn-blue" type="submit" style="padding: 8px 12px; font-size: 13px; align-self: flex-start;">🤖 KipGPT ile Yanıt Oluştur</button>
                </form>
            </div>
            """
    else:
        mail_items_html = "<p style='color:#64748b;'>Kutuda mail bulunamadı.</p>"

    # 📝 Yapay zeka yanıt taslağı ekranı ve interaktif REVİZE ETME modülü
    ai_preview_html = ""
    if ai_yaniti:
        ai_preview_html = f"""
        <div class="user-box" style="margin-bottom: 25px; background: #f0fdf4 !important; border: 1px solid #bbf7d0; padding: 15px;">
            <meta charset="UTF-8">
            <h4 style="margin-top:0; color:#166534; margin-bottom: 8px;">🤖 KipGPT Taslak Yanıtı</h4>
            <p style="font-size:12px; color:#64748b; margin-bottom:8px;">Alıcı: {secilen_mail.get('sender')}</p>
            <form method="post">
            
            <form method="post" style="margin-bottom: 15px;">
                <input type="hidden" name="islem" value="gonder">
                <input type="hidden" name="sender" value="{secilen_mail.get('sender')}">
                <input type="hidden" name="subject" value="{secilen_mail.get('subject')}">
                <textarea name="final_reply" style="width:100%; height:150px; padding:10px; border-radius:8px; border:1px solid #cbd5e1; font-family:inherit; font-size:14px; margin-bottom:10px; box-sizing: border-box;">{ai_yaniti}</textarea>
                <button class="btn btn-green" type="submit" style="width:100%; padding:10px; font-weight:600;">🚀 Yanıtı E-Posta Olarak Gönder</button>
            </form>
            
            <div style="background: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #cbd5e1;">
                <h5 style="margin: 0 0 8px 0; color: #334155; font-size: 13px;">🔄 Yanıtı Beğenmediniz mi? Yapay Zekaya Yeniden Düzenletin:</h5>
                <form method="post" style="display: flex; flex-direction: column; gap: 8px;">
                    <input type="hidden" name="islem" value="revize_et">
                    <input type="hidden" name="sender" value="{secilen_mail.get('sender')}">
                    <input type="hidden" name="subject" value="{secilen_mail.get('subject')}">
                    <input type="hidden" name="content" value="{secilen_mail.get('content')}">
                    <input type="hidden" name="current_draft" value="{ai_yaniti}">
                    
                    <input type="text" name="revize_notu" placeholder="Şu yönde yenile: (Örn: Daha kısa yaz, toplantı saatini 14:00 yap...)" required
                           style="width: 100%; padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; box-sizing: border-box;">
                    <button class="btn btn-blue" type="submit" style="padding: 6px 12px; font-size: 12px; align-self: flex-start; background: #64748b !important;">Taslağı Güncelle</button>
                </form>
            </div>
        </div>
        """

    content_html = f"""
    <div class="layout" style="justify-content: center; overflow-y: auto; padding: 20px 15px;">
        <meta charset="UTF-8">
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
    return render_page(content_html)
def image_file_to_data_url(file_storage):
    """Gelen resmi base64 formatına çevirir."""
    mime_type = file_storage.mimetype or "image/jpeg"
    raw = file_storage.read()
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"
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
    <form
        class="input-container"
        onsubmit="sendTextMessage(event)"
        enctype="multipart/form-data">

        <label for="file-input"
               style="cursor:pointer;font-size:28px;color:#3b82f6;font-weight:bold;padding:0 5px;">+</label>

        <input id="file-input"
               type="file"
               name="image"
               accept="image/*,application/pdf"
               style="display:none;">

        <input type="hidden"
               name="action"
               value="text">

        <input id="chat-input"
               type="text"
               name="soru"
               placeholder="Mesajınızı yazın..."
               autocomplete="off"
               autofocus>

        <button class="btn btn-blue" type="submit">Gönder</button>

    </form>
</div>
        </div>
    </div>
    """
    return render_page(content)

if __name__ == "__main__":
    # Render'ın verdiği PORT'u kullan, yoksa 10000 kullan
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)