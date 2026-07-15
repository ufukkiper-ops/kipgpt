import re


SUBJECT_PREFIX_RE = re.compile(
    r"^(re|fwd|fw|yanit|yanıt|cevap|ilet|aw)\s*:\s*",
    re.I,
)


def normalize_subject(subject):
    value = (subject or "").strip()
    while True:
        cleaned = SUBJECT_PREFIX_RE.sub("", value).strip()
        if cleaned == value:
            break
        value = cleaned
    return value.lower()


def build_conversation_key(mail):
    thread_id = (mail.get("thread_id") or "").strip()
    if thread_id:
        return f"thread:{thread_id}"

    subject = normalize_subject(mail.get("subject", ""))
    sender = (mail.get("sender") or "").strip().lower()
    return f"conv:{subject}|{sender}"


def group_mails_by_thread(mailler):
    if not mailler:
        return []

    groups = {}
    order = []

    for mail in mailler:
        key = build_conversation_key(mail)
        if key not in groups:
            groups[key] = {
                "messages": [],
            }
            order.append(key)
        groups[key]["messages"].append(mail)

    grouped = []
    for key in order:
        messages = groups[key]["messages"]
        primary = messages[0]
        thread_ids = [m["id"] for m in messages]
        combined_content = "\n\n".join(
            f"--- {m.get('date', '')} | {m.get('sender_display', m.get('sender', ''))} ---\n{m.get('content', '')}"
            for m in messages
            if m.get("content")
        )

        grouped.append({
            **primary,
            "thread_id": primary.get("thread_id") or key,
            "thread_ids": thread_ids,
            "thread_count": len(messages),
            "thread_messages": messages,
            "content": combined_content or primary.get("content", ""),
        })

    return grouped


def expand_selected_mail_ids(mailler, selected_ids):
    selected_set = {str(mail_id).strip() for mail_id in selected_ids if str(mail_id).strip()}
    if not selected_set or not mailler:
        return list(selected_set)

    thread_keys = set()
    for mail in mailler:
        mail_id = mail.get("id")
        thread_ids = mail.get("thread_ids") or []
        if mail_id in selected_set or any(tid in selected_set for tid in thread_ids):
            thread_keys.add(build_conversation_key(mail))

    if not thread_keys:
        return list(selected_set)

    expanded = []
    seen = set()
    for mail in mailler:
        if build_conversation_key(mail) not in thread_keys:
            continue
        for mail_id in mail.get("thread_ids") or [mail.get("id")]:
            if mail_id and mail_id not in seen:
                seen.add(mail_id)
                expanded.append(mail_id)

    return expanded or list(selected_set)
