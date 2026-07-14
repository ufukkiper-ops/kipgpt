from routes.mail_page import mail_bp
from templates import render_chat_list
from chat import (
    get_client,
    ask_gpt,
    generate_chat_response,
    generate_chat_title,
    analyze_pdf,
    analyze_image
)
from users import (
    load_users,
    save_users,
    hash_password,
    check_password,
    ensure_users_file
)
from storage import load_data, save_data
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    session,
    jsonify,
)
import os
import json
import re
from routes.chat_routes import chat_bp
from chat import get_client
from mail import (
    get_inbox,
    get_sent,
    get_spam,
    get_trash,
    get_drafts,
    get_archive,
    send_reply_mail
)
ensure_users_file()

app = Flask(__name__)
app.register_blueprint(chat_bp)

app.register_blueprint(mail_bp)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "gizli123")

# --- DOSYA İŞLEMLERİ ---

DATA_FILE = "data.json"

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
                users.append({
    "username": username,
    "password": hash_password(password)
})
                save_users(users)
                return redirect(url_for("login"))
    # render registration form
    return render_template(
    "register.html",
    error=error,
    title="Kayıt Ol"
)

@app.route("/login", methods=["GET", "POST"])
def login():

    error = ""

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        users = load_users()

        for user in users:
            if (
    user["username"] == username
    and check_password(password, user["password"])
):
                session["user"] = username
                return redirect(url_for("index"))

        error = "Kullanıcı adı veya şifre hatalı."

    return render_template(
    "login.html",
    error=error,
    title="Giriş Yap"
)
      
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
    chat_titles = data[username].setdefault("chat_titles", {})
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

    folder = request.args.get("folder", "inbox")

    folder_menu = """
<div style="display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;">

<a class="btn btn-blue" href="/mail?folder=inbox">📥 Gelen</a>

<a class="btn btn-blue" href="/mail?folder=sent">📤 Gönderilen</a>

<a class="btn btn-blue" href="/mail?folder=spam">🚫 Spam</a>

<a class="btn btn-blue" href="/mail?folder=drafts">⭐ Taslaklar</a>

<a class="btn btn-blue" href="/mail?folder=trash">🗑 Çöp</a>

<a class="btn btn-blue" href="/mail?folder=archive">📦 Arşiv</a>

</div>
"""

    # Kullanıcının arama sorgusu (küçük harfe çevir ve baş/son boşlukları temizle)
    search = request.args.get("search", "").strip().lower()

    try:
        import inspect

        print("get_inbox objesi:", get_inbox)
        print("modülü:", get_inbox.__module__)
        print("imzası:", inspect.signature(get_inbox))

        if folder == "inbox":
            mailler = get_inbox(20)

        elif folder == "sent":
            mailler = get_sent(20)

        elif folder == "spam":
            mailler = get_spam(20)

        elif folder == "trash":
            mailler = get_trash(20)

        elif folder == "drafts":
            mailler = get_drafts(20)

        elif folder == "archive":
            mailler = get_archive(20)

        else:
            mailler = get_inbox(20)

    except Exception as e:
        error = str(e)
        mailler = []

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

                    ai_yaniti = ask_gpt(prompt)
                    
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
    
    print("MAIL SAYISI =", len(mailler))
    print(mailler[:1])

    if search:
        # ensure search is lowercase for comparisons
        s = search.lower()
        mailler = [
            m for m in mailler
            if (
                s in m.get("subject", "").lower()
                or s in m.get("sender", "").lower()
                or s in m.get("content", "").lower()
            )
        ]
    
    if mailler:
        for m in mailler:
            preview = (m.get("content", "")[:180] + "...") if len(m.get("content", "")) > 180 else m.get("content", "")
            mail_items_html += f"""
            <div class="user-box" style="margin-bottom:20px;background:#fff;border-left:4px solid #10b981;padding:15px;">
                <p><b>Kimden:</b> {m.get('sender_display','Bilinmiyor')}</p>
                <h3 style="margin:4px 0;color:#0f172a;font-size:17px;">
                {m.get('subject','Konu Yok')}
                </h3>
                <p style="color:#64748b;font-size:13px;">
                    {preview}
                </p>
                <form method="post" style="margin-top: 12px; display: flex; flex-direction: column; gap: 8px;">
                    <input type="hidden" name="islem" value="olustur">
                    <input type="hidden" name="sender" value="{m.get('sender', '')}">
                    <input type="hidden" name="subject" value="{m.get('subject', '')}">
                    <input type="hidden" name="content" value="{m.get('content', '')}">
                    
                    <input type="text" name="user_instruction" placeholder="Yapay zekaya not bırakın (Örn: Teklifi reddet, haftaya ertele...)" 

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

# Ensure variables exist before rendering (provide safe defaults if missing)
    error = locals().get("error") if "error" in locals() else None
    folder_menu = locals().get("folder_menu") if "folder_menu" in locals() else None
    folder = locals().get("folder") if "folder" in locals() else None
    search = locals().get("search") if "search" in locals() else None
    mail_items_html = locals().get("mail_items_html") if "mail_items_html" in locals() else ""

    # Render mail template into a variable (do not return here so subsequent routes remain reachable)
    return render_template(
    "mail.html",
    title="Mail",
    error=error,
    folder_menu=folder_menu,
    folder=folder,
    search=search,
    ai_preview_html=ai_preview_html,
    mail_items_html=mail_items_html,
)

@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session: return redirect(url_for("login"))
    username = session["user"]
    data = load_data()

    if username not in data or not isinstance(data[username], dict):
        data[username] = {"active_chat": "chat1", "chats": {"chat1": []}}

    active_chat = data[username].get("active_chat", "chat1")

    chats = data[username].setdefault("chats", {"chat1": []})

    chat_titles = data[username].setdefault("chat_titles", {})

    gecmis = chats.setdefault(active_chat, [])
    
    

    if request.method == "POST":
        action = request.form.get("action", "text")
        client = get_client()

        if client is None:
            return jsonify({
                "status": "error",
                "error": "Sunucuda OPENAI_API_KEY ayarlı değil."
            }), 400

        # ------------------ TEXT ------------------
        if action == "text":

            soru = request.form.get("soru", "").strip()

            if soru:

                gecmis.append({
                    "role": "user",
                    "content": soru
                })

                try:

                    cevap = generate_chat_response(
    [
        {
            "role": m["role"],
            "content": m["content"]
        }
        for m in gecmis
    ]
)
                    if active_chat not in chat_titles:

                        try:

                            chat_titles[active_chat] = generate_chat_title(soru)
                            print(chat_titles)
                            chat_list_html = ""

                
                        except Exception as e:
                            print("BAŞLIK HATASI:", e)
                            chat_titles[active_chat] = soru[:30]

                except Exception as e:

                    cevap = f"AI hatası: {e}"

                gecmis.append({
                    "role": "assistant",
                    "content": cevap
                })

                # append assistant response
                # (already appended above)

                data[username]["chats"][active_chat] = gecmis
                data[username]["chat_titles"] = chat_titles

                save_data(data)

                return jsonify({
                    "status": "success",
                    "answer": cevap
                })

        # ------------------ IMAGE / PDF ------------------
        elif action == "image":

            uploaded_file = request.files.get("image")

            if not uploaded_file or uploaded_file.filename == "":
                return jsonify({
                    "status": "error",
                    "error": "Dosya seçilmedi."
                })

            prompt = request.form.get(
                "image_prompt",
                ""
            ).strip() or "Bu dosyayı analiz et."

            try:

                # ---------- PDF ----------
                if uploaded_file.mimetype == "application/pdf":

                    cevap = analyze_pdf(
    uploaded_file,
    prompt
)

                    gecmis.append({
                        "role": "user",
                        "content": f"[PDF] {uploaded_file.filename}"
                    })

                # ---------- IMAGE ----------
                else:

                    cevap, image_data_url = analyze_image(
                        uploaded_file,
                        prompt
                    )

                    gecmis.append({
                        "role": "user",
                        "content": f"[RESİM] {prompt}",
                        "image": image_data_url
                    })

                    gecmis.append({
                        "role": "assistant",
                        "content": cevap
                    })
                    data[username]["chat_titles"] = chat_titles
                    data[username]["chats"][active_chat] = gecmis
                    save_data(data)

                return jsonify({
                    "status": "success",
                    "answer": cevap
                })

            except Exception as e:

                return jsonify({
                    "status": "error",
                    "error": str(e)
                })

    chat_list_html = render_chat_list(
    chats,
    chat_titles,
    active_chat
)

    messages_html = ""
    for mesaj in gecmis:
        role = mesaj.get("role", "assistant")
        content = mesaj.get("content", "")
        css = "msg msg-user" if role == "user" else "msg msg-bot"
        extra_image = ""

        if "image" in mesaj:
         extra_image = f'<br><img src="{mesaj["image"]}">'
        if role == "user":
            extra_image = f'<br><img src="{mesaj["image"]}">' if "image" in mesaj and mesaj["image"] else ""

            messages_html += f'<div class="{css}"><b>Sen:</b><br>{content}</div>'
        else:
            messages_html += f'<div class="{css}"><b class="bot-text">KipGPT:</b><br><span class="bot-text">{content}</span>{extra_image}</div>'
    

    return render_template(
    "chat.html",
    username=username,
    active_chat=active_chat,
    chat_list_html=chat_list_html,
    messages_html=messages_html,
    title="KipGPT",
)
if __name__ == "__main__":
    # Render'ın verdiği PORT'u kullan, yoksa 10000 kullan
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)