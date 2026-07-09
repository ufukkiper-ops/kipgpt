from flask import Flask, request, render_template_string, redirect, url_for, session, make_response
import os, json
from mail import get_last_mails, send_reply_mail, analyze_mail 

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "gizli123")

def render_page(content):
    # UTF-8 karakter desteği için charset ekliyoruz
    BASE_HTML = """
    <!DOCTYPE html>
    <html lang="tr"><head><meta charset="UTF-8"><title>KipGPT</title></head>
    <body>{{ content|safe }}</body></html>"""
    return render_template_string(BASE_HTML, content=content)

# --- ANA SAYFA (index) ---
@app.route("/", methods=["GET", "POST"])
def index():
    if "user" not in session: return redirect(url_for("login"))
    return render_page("<h1>Hoş geldin!</h1><a href='/mail'>Mail Kutusu</a> | <a href='/logout'>Çıkış</a>")

# --- GİRİŞ VE KAYIT ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["user"] = request.form.get("username")
        return redirect(url_for("index"))
    return render_page("<form method='post'><input name='username' placeholder='Kullanıcı'><button>Giriş</button></form>")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# --- MAİL ROTALARI ---
@app.route("/mail", methods=["GET", "POST"])
def mail():
    if "user" not in session: return redirect(url_for("login"))
    
    # Mail işleme fonksiyonlarını burada çağırıyoruz
    mailler = get_last_mails(count=5)
    content = "<h2>Gelen Kutusu</h2>"
    for m in mailler:
        content += f"<div>{m.get('subject', 'Konu Yok')}</div>"
    
    response = make_response(render_page(content))
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5001)), debug=True)