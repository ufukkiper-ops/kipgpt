from services.chat_service import get_client, get_gpt_model, plain_text_response

# ISO-ish codes -> display name (Turkish UI labels where common)
LANG_LABELS = {
    "tr": "Türkçe",
    "en": "İngilizce",
    "de": "Almanca",
    "fr": "Fransızca",
    "es": "İspanyolca",
    "it": "İtalyanca",
    "pt": "Portekizce",
    "ru": "Rusça",
    "ar": "Arapça",
    "fa": "Farsça",
    "zh": "Çince",
    "ja": "Japonca",
    "ko": "Korece",
    "hi": "Hintçe",
    "nl": "Felemenkçe",
    "pl": "Lehçe",
    "uk": "Ukraynaca",
    "ro": "Romence",
    "el": "Yunanca",
    "sv": "İsveççe",
    "no": "Norveççe",
    "da": "Danca",
    "fi": "Fince",
    "cs": "Çekçe",
    "hu": "Macarca",
    "bg": "Bulgarca",
    "hr": "Hırvatça",
    "sr": "Sırpça",
    "sk": "Slovakça",
    "sl": "Slovence",
    "lt": "Litvanca",
    "lv": "Letonca",
    "et": "Estonca",
    "he": "İbranice",
    "th": "Tayca",
    "vi": "Vietnamca",
    "id": "Endonezce",
    "ms": "Malayca",
    "tl": "Filipince",
    "bn": "Bengalce",
    "ur": "Urduca",
    "sw": "Svahili",
    "af": "Afrikaans",
    "sq": "Arnavutça",
    "ka": "Gürcüce",
    "hy": "Ermenice",
    "az": "Azerbaycan Türkçesi",
    "kk": "Kazakça",
    "uz": "Özbekçe",
    "tg": "Tacikçe",
    "ky": "Kırgızca",
    "mn": "Moğolca",
    "ne": "Nepalce",
    "si": "Sinhala",
    "ta": "Tamilce",
    "te": "Teluguca",
    "ml": "Malayalam",
    "kn": "Kannada",
    "mr": "Marathi",
    "gu": "Guceratça",
    "pa": "Pencapça",
    "am": "Amharca",
    "zu": "Zulu",
    "xh": "Xhosa",
    "ca": "Katalanca",
    "eu": "Baskça",
    "gl": "Galiçyaca",
    "is": "İzlandaca",
    "ga": "İrlandaca",
    "cy": "Galce",
    "mt": "Maltaca",
    "mk": "Makedonca",
    "bs": "Boşnakça",
    "me": "Karadağca",
    "be": "Belarusça",
    "my": "Burmaca",
    "km": "Kmerce",
    "lo": "Laoca",
}


def supported_languages():
    """Unique language list sorted by Turkish label."""
    items = []
    seen = set()
    for code, label in LANG_LABELS.items():
        key = code.split("-")[0]
        if key in seen:
            continue
        seen.add(key)
        items.append({"code": key, "label": label})
    items.sort(key=lambda x: x["label"].casefold())
    return items


def resolve_lang(target_lang):
    code = (target_lang or "").strip().lower().replace("_", "-")
    if not code:
        return None, None
    if code in LANG_LABELS:
        return code.split("-")[0], LANG_LABELS[code]
    base = code.split("-")[0]
    if base in LANG_LABELS:
        return base, LANG_LABELS[base]
    # Allow passing a display name
    for key, label in LANG_LABELS.items():
        if label.casefold() == code or label.casefold() == (target_lang or "").strip().casefold():
            return key.split("-")[0], label
    return None, None


def translate_mail_content(text, target_lang):
    code, lang_name = resolve_lang(target_lang)
    if not code or not lang_name:
        raise ValueError("Geçersiz hedef dil.")

    content = (text or "").strip()
    if not content:
        raise ValueError("Çevrilecek içerik yok.")

    client = get_client()
    if client is None:
        raise Exception("OPENAI_API_KEY bulunamadı.")

    prompt = f"""Önce aşağıdaki e-posta içeriğinin dilini algıla, sonra tamamını {lang_name} diline çevir.

Kurallar:
- Kaynak dili otomatik algıla; hedef dil {lang_name}.
- Kaynak dil zaten {lang_name} ise metni anlamlı şekilde aynı dilde düzgünleştirerek ver, "zaten bu dilde" gibi not yazma.
- Sadece çevrilmiş metni döndür.
- Açıklama, not, kaynak dil adı veya ek cümle ekleme.
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
