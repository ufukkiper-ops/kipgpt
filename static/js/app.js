const FILE_ICONS = {
    pdf: "📄",
    image: "🖼️",
    word: "📝",
    excel: "📊",
    text: "📃",
    other: "📎",
};

let selectedChatFile = null;

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function renderFileBadge(fileMeta) {
    if (!fileMeta) return "";

    const name = escapeHtml(fileMeta.name || "dosya");
    const icon = fileMeta.icon || FILE_ICONS[fileMeta.type] || FILE_ICONS.other;

    if (fileMeta.preview) {
        return (
            `<div class="file-badge">` +
            `<img src="${fileMeta.preview}" class="file-thumb" alt="${name}">` +
            `<span class="file-name">${name}</span>` +
            `</div>`
        );
    }

    return (
        `<div class="file-badge">` +
        `<span class="file-icon">${icon}</span>` +
        `<span class="file-name">${name}</span>` +
        `</div>`
    );
}

function getFileMetaFromFile(file) {
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    let type = "other";
    if (file.type.startsWith("image/")) type = "image";
    else if (ext === "pdf") type = "pdf";
    else if (ext === "doc" || ext === "docx") type = "word";
    else if (ext === "xls" || ext === "xlsx" || ext === "csv") type = "excel";
    else if (ext === "txt") type = "text";

    return {
        name: file.name,
        type: type,
        icon: FILE_ICONS[type] || FILE_ICONS.other,
        preview: file.type.startsWith("image/") ? URL.createObjectURL(file) : null,
    };
}

function appendMessage(role, text, fileMeta) {
    const messages = document.querySelector(".messages");
    if (!messages) return null;

    const div = document.createElement("div");
    div.className = role === "user" ? "msg msg-user" : "msg msg-bot";

    const label = role === "user" ? "Sen" : "Kip Asistan";
    const fileHtml = renderFileBadge(fileMeta);
    div.innerHTML = `<b>${label}:</b><br>${escapeHtml(text).replace(/\n/g, "<br>")}${fileHtml}`;

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
}

function updateActiveChatTitle(title) {
    const el = document.querySelector(".active-chat-title b");
    if (el && title) {
        el.textContent = title;
    }

    const activeItem = document.querySelector(".chat-item.active .chat-item-title");
    if (activeItem && title) {
        activeItem.textContent = title;
    }
}

function showSelectedFilePreview(file) {
    const bar = document.getElementById("file-preview-bar");
    const content = document.getElementById("file-preview-content");
    if (!bar || !content || !file) return;

    content.innerHTML = renderFileBadge(getFileMetaFromFile(file));
    bar.hidden = false;
}

function clearSelectedFilePreview() {
    const bar = document.getElementById("file-preview-bar");
    const content = document.getElementById("file-preview-content");
    const fileInput = document.getElementById("file-input");

    selectedChatFile = null;
    if (content) content.innerHTML = "";
    if (bar) bar.hidden = true;
    if (fileInput) fileInput.value = "";
}

function bindChatPage() {
    const chatForm = document.getElementById("chat-form");
    const chatSearch = document.getElementById("chat-search");
    const chatList = document.getElementById("chat-list");
    const fileInput = document.getElementById("file-input");
    const fileUploadBtn = document.getElementById("file-upload-btn");
    const clearBtn = document.getElementById("file-preview-clear");

    if (!chatForm) return;

    if (chatSearch && chatList) {
        chatSearch.addEventListener("input", function () {
            const query = chatSearch.value.trim().toLowerCase();
            chatList.querySelectorAll(".chat-item").forEach(function (item) {
                const title = (item.dataset.title || item.textContent || "").toLowerCase();
                item.style.display = !query || title.includes(query) ? "" : "none";
            });
        });
    }

    if (fileUploadBtn && fileInput) {
        fileUploadBtn.addEventListener("click", function () {
            fileInput.click();
        });
    }

    if (fileInput) {
        fileInput.addEventListener("change", function () {
            if (fileInput.files.length > 0) {
                selectedChatFile = fileInput.files[0];
                showSelectedFilePreview(selectedChatFile);
            } else {
                clearSelectedFilePreview();
            }
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", clearSelectedFilePreview);
    }

    chatForm.addEventListener("submit", sendTextMessage);
}

document.addEventListener("DOMContentLoaded", bindChatPage);

async function sendTextMessage(event) {
    event.preventDefault();

    const input = document.getElementById("chat-input");
    const message = input.value.trim();
    const file = selectedChatFile;

    if (!message && !file) {
        return;
    }

    const messages = document.querySelector(".messages");
    const previewMeta = file ? getFileMetaFromFile(file) : null;
    const displayText = message || (file ? `[DOSYA] ${file.name}` : "");

    appendMessage("user", displayText, previewMeta);

    const loading = document.createElement("div");
    loading.className = "msg msg-bot";
    loading.innerHTML = "<b>Kip Asistan:</b><br><i>Kip Asistan düşünüyor...</i>";
    messages.appendChild(loading);

    const formData = new FormData();

    if (file) {
        formData.set("action", "file");
        formData.append("file", file, file.name);
        formData.append("image_prompt", message || "Bu dosyayı detaylı analiz et ve Türkçe yorumla.");
        if (message) formData.append("soru", message);
    } else {
        formData.set("action", "text");
        formData.append("soru", message);
    }

    input.value = "";

    try {
        const response = await fetch("/", {
            method: "POST",
            body: formData,
        });

        let data;
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
            data = await response.json();
        } else {
            throw new Error("Sunucudan geçersiz yanıt alındı. Oturumu yenileyip tekrar deneyin.");
        }

        if (data.status === "success") {
            loading.innerHTML = "<b>Kip Asistan:</b><br>" + escapeHtml(data.answer).replace(/\n/g, "<br>");
            if (data.chat_title) {
                updateActiveChatTitle(data.chat_title);
            }
            clearSelectedFilePreview();
        } else {
            loading.innerHTML = "<b>Hata:</b><br>" + escapeHtml(data.error || "Bilinmeyen hata");
        }
    } catch (e) {
        loading.innerHTML = "<b>Hata:</b><br>" + escapeHtml(e.message || "Bağlantı hatası");
        console.error(e);
    }

    messages.scrollTop = messages.scrollHeight;
}
