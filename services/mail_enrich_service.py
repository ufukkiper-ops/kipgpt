"""AI helpers for mail summary, tables, charts, and library attachments."""

from __future__ import annotations

import json
import re
from html import escape

from services.chat_service import get_client, get_gpt_model, plain_text_response
from services.file_library_service import list_files, resolve_attachment_queries


SUMMARY_SYSTEM = """Sen profesyonel bir e-posta analisti asistanısın.
Yanıtını SADECE geçerli JSON olarak ver. Markdown veya açıklama ekleme."""

ENRICHED_MAIL_SYSTEM = """Sen profesyonel bir e-posta yazım asistanısın.
Kullanıcı talimatına göre e-posta gövdesi üretirsin.
İstenirse tablo ve grafik verisi de üretirsin.
Dosya eklenmesi istenirse kütüphanedeki dosya adlarına göre attach_queries doldurursun.
Yanıtını SADECE geçerli JSON olarak ver."""


def _extract_json(text):
    raw = (text or "").strip()
    if not raw:
        raise ValueError("AI boş yanıt döndürdü.")

    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise
        return json.loads(match.group(0))


def _ask_json(system_prompt, user_prompt):
    client = get_client()
    if client is None:
        raise RuntimeError("Sunucuda OPENAI_API_KEY ayarlı değil.")

    response = client.chat.completions.create(
        model=get_gpt_model(),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )
    content = response.choices[0].message.content
    return _extract_json(content)


def wants_enrichment(text):
    lower = (text or "").lower()
    keywords = (
        "tablo", "grafik", "chart", "table", "diagram",
        "ekle", "ek olarak", "dosya", "belge", "rapor ekle",
        "şunu ekle", "şu dosya", "kütüphane",
    )
    return any(k in lower for k in keywords)


def summarize_mail(sender, subject, content):
    prompt = f"""Aşağıdaki e-postayı analiz et ve JSON döndür:

{{
  "summary": "2-4 cümlelik özet",
  "interpretation": "Gönderenin amacı / tonu hakkında kısa yorum",
  "importance": "low|medium|high",
  "urgency": "low|medium|high",
  "action_items": ["yapılacak 1", "yapılacak 2"],
  "reminders": [{{"title": "hatırlatıcı başlığı", "when": "ISO8601 veya boş"}}],
  "suggested_reply": "kısa cevap önerisi"
}}

Kimden: {sender}
Konu: {subject}
İçerik:
{content}
"""
    data = _ask_json(SUMMARY_SYSTEM, prompt)
    action_items = data.get("action_items") or []
    if isinstance(action_items, str):
        action_items = [action_items]
    reminders = data.get("reminders") or []
    if not isinstance(reminders, list):
        reminders = []

    return {
        "summary": plain_text_response(str(data.get("summary") or "")).strip(),
        "interpretation": plain_text_response(str(data.get("interpretation") or "")).strip(),
        "importance": str(data.get("importance") or "medium").lower(),
        "urgency": str(data.get("urgency") or "medium").lower(),
        "action_items": [plain_text_response(str(x)).strip() for x in action_items if str(x).strip()],
        "reminders": reminders,
        "suggested_reply": plain_text_response(str(data.get("suggested_reply") or "")).strip(),
    }


def _library_catalog(user):
    files = list_files(user) if user else []
    if not files:
        return "(Kütüphanede dosya yok)"
    lines = []
    for item in files[:40]:
        note = f" — not: {item.get('note')}" if item.get("note") else ""
        lines.append(f"- {item.get('filename')}{note}")
    return "\n".join(lines)


def _table_to_text(table):
    if not table:
        return ""
    headers = table.get("headers") or []
    rows = table.get("rows") or []
    title = (table.get("title") or "").strip()
    lines = []
    if title:
        lines.append(title)
    if headers:
        lines.append(" | ".join(str(h) for h in headers))
        lines.append(" | ".join("---" for _ in headers))
    for row in rows:
        lines.append(" | ".join(str(c) for c in row))
    return "\n".join(lines)


def _table_to_html(table):
    if not table:
        return ""
    title = escape((table.get("title") or "").strip())
    headers = table.get("headers") or []
    rows = table.get("rows") or []
    parts = ['<div style="margin:16px 0;">']
    if title:
        parts.append(f'<p style="font-weight:600;margin:0 0 8px;">{title}</p>')
    parts.append(
        '<table style="border-collapse:collapse;width:100%;max-width:640px;'
        'font-family:Arial,sans-serif;font-size:13px;">'
    )
    if headers:
        parts.append("<thead><tr>")
        for header in headers:
            parts.append(
                f'<th style="border:1px solid #dadce0;padding:8px;background:#f1f3f4;'
                f'text-align:left;">{escape(str(header))}</th>'
            )
        parts.append("</tr></thead>")
    parts.append("<tbody>")
    for row in rows:
        parts.append("<tr>")
        cells = row if isinstance(row, (list, tuple)) else [row]
        for cell in cells:
            parts.append(
                f'<td style="border:1px solid #dadce0;padding:8px;">{escape(str(cell))}</td>'
            )
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts)


def _chart_to_text(chart):
    if not chart:
        return ""
    title = (chart.get("title") or "Grafik").strip()
    labels = chart.get("labels") or []
    values = chart.get("values") or []
    lines = [title]
    try:
        numeric = [float(v) for v in values]
    except (TypeError, ValueError):
        numeric = []
    max_v = max(numeric) if numeric else 0
    for index, label in enumerate(labels):
        value = values[index] if index < len(values) else ""
        bar = ""
        if max_v and index < len(numeric):
            width = int(round((numeric[index] / max_v) * 20))
            bar = "█" * max(width, 1)
        lines.append(f"{label}: {value} {bar}".rstrip())
    return "\n".join(lines)


def _chart_to_html(chart):
    if not chart:
        return ""
    title = escape((chart.get("title") or "Grafik").strip())
    labels = chart.get("labels") or []
    values = chart.get("values") or []
    try:
        numeric = [float(v) for v in values]
    except (TypeError, ValueError):
        numeric = [0] * len(values)
    max_v = max(numeric) if numeric else 1

    parts = [
        '<div style="margin:16px 0;font-family:Arial,sans-serif;font-size:13px;">',
        f'<p style="font-weight:600;margin:0 0 10px;">{title}</p>',
        '<table style="width:100%;max-width:640px;border-collapse:collapse;">',
    ]
    for index, label in enumerate(labels):
        value = values[index] if index < len(values) else ""
        pct = int(round((numeric[index] / max_v) * 100)) if max_v else 0
        pct = max(min(pct, 100), 4 if numeric and numeric[index] else 0)
        parts.append("<tr>")
        parts.append(
            f'<td style="padding:4px 8px 4px 0;white-space:nowrap;width:120px;">{escape(str(label))}</td>'
        )
        parts.append('<td style="padding:4px 0;width:70%;">')
        parts.append(
            f'<div style="background:#1a73e8;height:14px;width:{pct}%;'
            f'border-radius:3px;"></div>'
        )
        parts.append("</td>")
        parts.append(
            f'<td style="padding:4px 0 4px 8px;white-space:nowrap;">{escape(str(value))}</td>'
        )
        parts.append("</tr>")
    parts.append("</table></div>")
    return "".join(parts)


def _plain_to_html(text):
    safe = escape(text or "")
    return "<br>".join(safe.splitlines())


def build_html_body(body_text, table=None, chart=None):
    parts = [
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;line-height:1.5;color:#202124;">',
        f"<div>{_plain_to_html(body_text)}</div>",
    ]
    table_html = _table_to_html(table)
    chart_html = _chart_to_html(chart)
    if table_html:
        parts.append(table_html)
    if chart_html:
        parts.append(chart_html)
    parts.append("</div>")
    return "".join(parts)


def build_plain_body(body_text, table=None, chart=None):
    chunks = [plain_text_response(body_text or "").strip()]
    table_text = _table_to_text(table)
    chart_text = _chart_to_text(chart)
    if table_text:
        chunks.append("\n" + table_text)
    if chart_text:
        chunks.append("\n" + chart_text)
    return "\n\n".join(c for c in chunks if c).strip()


def generate_enriched_mail(
    user,
    *,
    mode="compose",
    sender="",
    to_email="",
    subject="",
    content="",
    user_instruction="",
    current_draft="",
    revize_notu="",
):
    instruction = (revize_notu or user_instruction or "").strip()
    catalog = _library_catalog(user)

    context = ""
    if mode == "reply":
        context = f"""Gelen mail:
Kimden: {sender}
Konu: {subject}
İçerik:
{content}
"""
    else:
        context = f"""Yeni mail:
Alıcı: {to_email or "(belirtilmedi)"}
Konu: {subject or "(belirtilmedi)"}
"""

    prompt = f"""{context}

Kullanıcı talimatı (öncelikli):
{instruction or "(yok)"}

Mevcut taslak:
{current_draft or "(boş)"}

Kullanıcı dosya kütüphanesi:
{catalog}

JSON şeması:
{{
  "body": "gönderilecek düz metin e-posta gövdesi (tablo/grafik metni hariç)",
  "table": null veya {{"title":"...","headers":["..."],"rows":[["..."]]}},
  "chart": null veya {{"title":"...","type":"bar","labels":["..."],"values":[1,2]}},
  "attach_queries": ["kütüphaneden eklenecek dosya adı veya anahtar kelime"]
}}

Kurallar:
- body zorunlu; Türkçe, profesyonel, gönderilebilir düz metin.
- Kullanıcı tablo isterse table doldur; istemezse null.
- Kullanıcı grafik isterse chart doldur (bar); istemezse null.
- Kullanıcı 'şu dosyayı ekle' derse attach_queries içine kütüphanedeki en yakın adları yaz.
- Kütüphanede yoksa attach_queries boş bırak.
- Markdown yazma. Sadece JSON döndür.
"""

    data = _ask_json(ENRICHED_MAIL_SYSTEM, prompt)
    body = plain_text_response(str(data.get("body") or "")).strip()
    if not body and current_draft:
        body = current_draft

    table = data.get("table") if isinstance(data.get("table"), dict) else None
    chart = data.get("chart") if isinstance(data.get("chart"), dict) else None
    queries = data.get("attach_queries") or []
    if isinstance(queries, str):
        queries = [queries]
    queries = [str(q).strip() for q in queries if str(q).strip()]

    # Also scan instruction for explicit filenames if model missed them
    if user and instruction:
        for item in list_files(user):
            name = item.get("filename") or ""
            stem = name.rsplit(".", 1)[0]
            if name and name.lower() in instruction.lower():
                queries.append(name)
            elif stem and len(stem) > 3 and stem.lower() in instruction.lower():
                queries.append(name)

    matches = resolve_attachment_queries(user, queries) if user else []
    plain = build_plain_body(body, table=table, chart=chart)
    html = build_html_body(body, table=table, chart=chart) if (table or chart) else ""

    return {
        "body": plain,
        "html_body": html,
        "table": table,
        "chart": chart,
        "library_attachments": matches,
        "library_file_ids": [m["id"] for m in matches],
        "attach_queries": queries,
    }
