def render_file_badge(file_meta):
    if not file_meta:
        return ""

    name = file_meta.get("name", "dosya")
    icon = file_meta.get("icon", "📎")
    preview = file_meta.get("preview")

    if preview:
        return (
            f'<div class="file-badge">'
            f'<img src="{preview}" class="file-thumb" alt="{name}">'
            f'<span class="file-name">{name}</span>'
            f"</div>"
        )

    return (
        f'<div class="file-badge">'
        f'<span class="file-icon">{icon}</span>'
        f'<span class="file-name">{name}</span>'
        f"</div>"
    )


def render_chat_list(chats, chat_titles, active_chat):
    html = ""
    chat_ids = list(chats.keys())
    chat_ids.reverse()

    for cid in chat_ids:
        title = chat_titles.get(cid, "Yeni Sohbet")
        active = "active" if cid == active_chat else ""
        html += f"""
        <a class="chat-item {active}" href="/switch/{cid}" data-title="{title.lower()}">
            <span class="chat-item-title">{title}</span>
        </a>
        """

    return html


def render_messages(gecmis):
    messages_html = ""

    for mesaj in gecmis:
        role = mesaj.get("role", "assistant")
        content = mesaj.get("content", "")
        css = "msg msg-user" if role == "user" else "msg msg-bot"
        file_html = render_file_badge(mesaj.get("file"))
        extra_image = ""

        if role == "user":
            if not file_html and "image" in mesaj and mesaj["image"]:
                extra_image = f'<br><img src="{mesaj["image"]}" class="msg-image">'
            messages_html += (
                f'<div class="{css}"><b>Sen:</b><br>{content}'
                f'{file_html}{extra_image}</div>'
            )
        else:
            if "image" in mesaj:
                extra_image = f'<br><img src="{mesaj["image"]}" class="msg-image">'
            messages_html += (
                f'<div class="{css}"><b class="bot-text">KipGPT:</b><br>'
                f'<span class="bot-text">{content}</span>{file_html}{extra_image}</div>'
            )

    return messages_html
