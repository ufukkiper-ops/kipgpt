import html


def render_file_badge(file_meta):
    if not file_meta:
        return ""

    name = html.escape(file_meta.get("name", "dosya"))
    icon = html.escape(file_meta.get("icon", "📎"))
    preview = file_meta.get("preview")

    if preview:
        safe_preview = html.escape(preview, quote=True)
        return (
            f'<div class="file-badge">'
            f'<img src="{safe_preview}" class="file-thumb" alt="{name}">'
            f'<span class="file-name">{name}</span>'
            f"</div>"
        )

    return (
        f'<div class="file-badge">'
        f'<span class="file-icon">{icon}</span>'
        f'<span class="file-name">{name}</span>'
        f"</div>"
    )


def format_message_body(content):
    text = html.escape(content or "")
    return text.replace("\n", "<br>")


def render_chat_list(chats, chat_titles, active_chat):
    result = ""
    chat_ids = list(chats.keys())
    chat_ids.reverse()

    for cid in chat_ids:
        title = chat_titles.get(cid, "Yeni Sohbet")
        active = "active" if cid == active_chat else ""
        safe_title = html.escape(title)
        safe_data = html.escape(title.lower(), quote=True)
        result += f"""
        <a class="chat-item {active}" href="/switch/{html.escape(cid, quote=True)}" data-title="{safe_data}">
            <span class="chat-item-title">{safe_title}</span>
        </a>
        """

    return result


def render_messages(gecmis):
    messages_html = ""

    for mesaj in gecmis:
        role = mesaj.get("role", "assistant")
        content = format_message_body(mesaj.get("content", ""))
        css = "msg msg-user" if role == "user" else "msg msg-bot"
        file_html = render_file_badge(mesaj.get("file"))
        extra_image = ""

        if role == "user":
            if not file_html and "image" in mesaj and mesaj["image"]:
                safe_src = html.escape(mesaj["image"], quote=True)
                extra_image = f'<br><img src="{safe_src}" class="msg-image" alt="">'
            messages_html += (
                f'<div class="{css}">'
                f'<div class="msg-label">Sen</div>'
                f'<div class="msg-text">{content}</div>'
                f"{file_html}{extra_image}"
                f"</div>"
            )
        else:
            if "image" in mesaj and mesaj["image"]:
                safe_src = html.escape(mesaj["image"], quote=True)
                extra_image = f'<br><img src="{safe_src}" class="msg-image" alt="">'
            messages_html += (
                f'<div class="{css}">'
                f'<div class="msg-bot-head">'
                f'<b class="bot-text msg-label">KipGPT</b>'
                f"</div>"
                f'<div class="msg-bot-text msg-text bot-text">{content}</div>'
                f"{file_html}{extra_image}"
                f"</div>"
            )

    return messages_html
