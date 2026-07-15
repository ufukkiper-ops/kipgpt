from services.chat_service import get_client, get_gpt_model, plain_text_response

LANG_LABELS = {
    "tr": "Türkçe",
    "en": "English",
    "de": "Deutsch",
}


def translate_mail_content(text, target_lang):
    if target_lang not in LANG_LABELS:
        raise ValueError("Geçersiz hedef dil.")

    content = (text or "").strip()
    if not content:
        raise ValueError("Çevrilecek içerik yok.")

    client = get_client()
    if client is None:
        raise Exception("OPENAI_API_KEY bulunamadı.")

    lang_name = LANG_LABELS[target_lang]
    prompt = f"""Aşağıdaki e-posta içeriğinin tamamını {lang_name} diline çevir.

Kurallar:
- Sadece çevrilmiş metni döndür.
- Açıklama, not veya ek cümle ekleme.
- Markdown kullanma.
- Paragraf ve satır düzenini koru.
- İsimleri, e-posta adreslerini ve URL'leri olduğu gibi bırak.

E-posta içeriği:

{content[:14000]}"""

    response = client.chat.completions.create(
        model=get_gpt_model(),
        messages=[{"role": "user", "content": prompt}],
    )
    translated = response.choices[0].message.content or ""
    return plain_text_response(translated)
