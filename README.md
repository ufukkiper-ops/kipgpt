# KipGPT

AI destekli mail asistanı. Gmail için **Google OAuth 2.0 + Gmail API**, diğer sağlayıcılar için OAuth/IMAP.

## Özellikler

- Birden fazla Gmail, Outlook/Yahoo ve özel IMAP hesabı (uygulama şifresi ile)
- Access / refresh token şifreli saklama (önceden OAuth ile bağlanmış hesaplar için)
- Gmail API / IMAP: gelen kutusu, detay, gönder, taslak, yıldızlı, okunmamış, spam, çöp, arama
- AI özet ve cevap önerileri (OpenAI)
- **Not:** Gmail / Outlook / Yahoo otomatik (OAuth) girişi varsayılan olarak kapalıdır. Hesap ekleme e-posta + uygulama şifresi ile yapılır.

## Kurulum (yerel)

### Masaüstü uygulaması (Windows / Linux)

```bat
desktop\start.bat
```

veya:

```bash
./desktop/start.sh
```

Ayrıntılar: [desktop/README.md](desktop/README.md) — Windows `.exe` derleme ve Microsoft Store notları dahil.

### 1. Bağımlılıklar

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Google Cloud Console

1. [Google Cloud Console](https://console.cloud.google.com/) → proje oluştur
2. **APIs & Services → Enable APIs** → **Gmail API** aç
3. **OAuth consent screen** (External) yapılandır; test kullanıcı ekle
4. **Credentials → Create OAuth client ID** (Web application)
5. Authorized redirect URIs:
   - `http://127.0.0.1:5001/auth/google/callback` (giriş/kayıt)
   - `http://127.0.0.1:5001/mail/oauth/google/callback` (Gmail bağlama)

### 3. `.env`

```bash
copy .env.example .env
```

Zorunlu alanlar:

```env
FLASK_SECRET_KEY=uzun-rastgele-deger
# veya: SECRET_KEY=...

GOOGLE_CLIENT_ID=....apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
GOOGLE_REDIRECT_URI=http://127.0.0.1:5001/auth/google/callback
GOOGLE_MAIL_REDIRECT_URI=http://127.0.0.1:5001/mail/oauth/google/callback

OPENAI_API_KEY=sk-...   # AI özet / cevap için
```

### 4. Çalıştır

```bash
python app.py
# veya start.bat
```

Aç: `http://127.0.0.1:5001/login` → Mail → **Hesap Ekle** (e-posta + uygulama şifresi)

> Gmail / Outlook / Yahoo OAuth (şifresiz) giriş kapalıdır. Yeniden açmak için `OAUTH_LOGIN_ENABLED=1` ortam değişkenini ekleyin.

## Render deploy

1. Repo’yu Render’a bağla (`render.yaml` hazır)
2. Environment değişkenleri:
   - `FLASK_SECRET_KEY` (güçlü)
   - `PUBLIC_BASE_URL=https://kip-asistan.onrender.com`
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI=https://kip-asistan.onrender.com/auth/google/callback`
   - `GOOGLE_MAIL_REDIRECT_URI=https://kip-asistan.onrender.com/mail/oauth/google/callback`
   - `OPENAI_API_KEY`
3. Google Console’a **aynı Render redirect URI’lerini** ekle
4. Kalıcı disk önerilir (`users.json` / `data/` için); yoksa redeploy’da hesaplar silinebilir

## Önemli route’lar

| Route | Açıklama |
|-------|----------|
| `GET /mail/oauth/google/start` | Gmail OAuth başlat |
| `GET /mail/oauth/google/callback` | Token al, hesabı kaydet |
| `GET/POST /mail` | Mail UI (klasör, arama, AI, gönder) |
| `POST /mail/save-draft` | Taslak (Gmail API drafts) |
| `POST /api/v1/mail/*` | Android / mobil API |
| `GET /logout` | Oturum + OAuth token temizliği |

## Mimari notlar

- Google hesapları: `services/gmail_api.py` (resmi `google-api-python-client`)
- Outlook / Yahoo / uygulama şifresi: IMAP/SMTP (`mail.py`)
- Token yenileme: `services/google_auth.py` → `get_fresh_access_token`
- OAuth state: `data/oauth_states.json` (çoklu worker uyumlu)

## Güvenlik

- Production’da zayıf `FLASK_SECRET_KEY` reddedilir
- Mail secret’ları Fernet ile şifrelenir (`MAIL_CREDENTIALS_KEY` opsiyonel)
- `.env` ve `google_client_secret.json` git’e eklenmez
