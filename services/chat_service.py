import os
import base64
import re

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader
from openai import OpenAI

from services.file_service import (
    build_file_meta,
    extract_file_text,
    get_file_category,
    image_to_data_url,
)


DEFAULT_GPT_MODEL = "gpt-5.6"

CHAT_SYSTEM_PROMPT = """Sen Kip Asistan adında yardımcı bir Türkçe yapay zeka asistanısın.

Kurallar:
- Türkçe dil bilgisi, imla ve noktalama kurallarına titizlikle uy.
- Cümleleri düzgün kur; gereksiz tekrar ve dağınık ifadelerden kaçın.
- Kullanıcı bir konu anlattığında gelişi güzel cevap verme; önce ne anlatıldığını anla, bağlama uygun yanıt ver.
- Soru sorulduysa doğrudan yanıtla; talimat verildiyse talimatı yerine getir.
- Net, anlaşılır ve profesyonel bir üslup kullan.

Biçimlendirme (çok önemli):
- Markdown KULLANMA: **, *, ###, `, # gibi işaretler yazma.
- Kalın yazı, başlık işaretleri veya yıldızlı vurgu yapma.
- Önce 1-2 cümlelik kısa özet yaz.
- Detayları sade madde listesi halinde ver; her madde "- " ile başlasın.
- Alt gruplar gerekiyorsa "Temel bilgiler:", "Sonuçlar:" gibi düz metin etiket kullan, altına maddeler yaz.
- Sayısal değerleri normal metin içinde yaz (örnek: Fosfor oranı: %0,038).
- Gereksiz uzunluk yapma; okunması kolay, sade Türkçe tercih et."""


def plain_text_response(text):
    if not text:
        return text

    cleaned = text
    cleaned = re.sub(r"^#{1,6}\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"__(.+?)__", r"\1", cleaned)
    cleaned = re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", cleaned)
    cleaned = re.sub(r"`(.+?)`", r"\1", cleaned)
    return cleaned.strip()


def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def image_file_to_data_url(file_storage):
    return image_to_data_url(file_storage)


def pdf_to_text(file_storage):
    reader = PdfReader(file_storage)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text


def ask_gpt(prompt):
    client = get_client()
    if client is None:
        raise Exception("OPENAI_API_KEY bulunamadı.")

    response = client.chat.completions.create(
        model=DEFAULT_GPT_MODEL,
        messages=[
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return plain_text_response(response.choices[0].message.content)


def generate_chat_response(messages):
    client = get_client()
    if client is None:
        raise Exception("OPENAI_API_KEY bulunamadı.")

    api_messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    for msg in messages:
        api_messages.append({"role": msg["role"], "content": msg["content"]})

    response = client.chat.completions.create(
        model=DEFAULT_GPT_MODEL,
        messages=api_messages,
    )
    return plain_text_response(response.choices[0].message.content)


def generate_chat_title(soru):
    client = get_client()
    if client is None:
        raise Exception("OPENAI_API_KEY bulunamadı.")

    response = client.chat.completions.create(
        model=DEFAULT_GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "En fazla 4 kelimelik bir sohbet başlığı oluştur. Emoji kullanabilirsin. Sadece başlığı yaz.",
            },
            {"role": "user", "content": soru},
        ],
    )
    return response.choices[0].message.content.strip()


def analyze_uploaded_file(uploaded_file, prompt):
    filename = uploaded_file.filename or "dosya"
    mimetype = uploaded_file.mimetype or ""
    category = get_file_category(filename, mimetype)

    if category == "image":
        preview = image_to_data_url(uploaded_file)
        client = get_client()
        if client is None:
            raise Exception("OPENAI_API_KEY bulunamadı.")

        response = client.chat.completions.create(
            model=DEFAULT_GPT_MODEL,
            messages=[
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": preview}},
                    ],
                },
            ],
        )
        answer = plain_text_response(response.choices[0].message.content)
        return answer, build_file_meta(filename, category, preview)

    text, category = extract_file_text(uploaded_file, filename, mimetype)
    if not text:
        raise ValueError("Dosyadan metin çıkarılamadı.")

    full_prompt = (
        f"{prompt}\n\n"
        f"Dosya adı: {filename}\n"
        f"Dosya türü: {category}\n\n"
        f"Dosya içeriği:\n\n{text}"
    )
    answer = ask_gpt(full_prompt)
    return answer, build_file_meta(filename, category)


def analyze_pdf(uploaded_file, prompt):
    text = pdf_to_text(uploaded_file)
    return ask_gpt(f"{prompt}\n\nPDF İçeriği:\n\n{text}")


def analyze_image(uploaded_file, prompt):
    image_data_url = image_to_data_url(uploaded_file)
    client = get_client()
    if client is None:
        raise Exception("OPENAI_API_KEY bulunamadı.")

    response = client.chat.completions.create(
        model=DEFAULT_GPT_MODEL,
        messages=[
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
    )
    return plain_text_response(response.choices[0].message.content), image_data_url
