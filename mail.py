import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from openai import OpenAI

# 🔐 EMAIL VE SUNUCU AYARLARI
EMAIL = "seninmail@gmail.com"
PASSWORD = "app_password"  # 16 haneli Google Uygulama Şifreniz

IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def connect_mail():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")
    return mail

def get_last_mails(count=5):
    mail = connect_mail()
    _, messages = mail.search(None, "ALL")
    mail_ids = messages[0].split()

    result = []

    for i in reversed(mail_ids[-count:]):
        try:
            _, msg_data = mail.fetch(i, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subject, _ = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(errors="ignore")

            from_ = msg.get("From")

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            result.append({
                "id": i.decode(),
                "subject": subject,
                "sender": from_,
                "content": body[:1000]
            })
        except Exception as e:
            print(f"Bir mail ayrıştırılırken hata atlandı: {e}")
            continue

    return result

def analyze_mail(text):
    prompt = f"Bu maili analiz et:\n- önemli mi\n- kısa özet\n- yapılması gereken\n- cevap öner\n\nMail:\n{text}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def send_reply_mail(to_email, subject, body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        raise Exception(f"E-posta gönderilirken kritik hata: {str(e)}")