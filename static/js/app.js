const FILE_ICONS = {
    pdf: "📄",
    image: "🖼️",
    word: "📝",
    excel: "📊",
    text: "📃",
    other: "📎",
};

let selectedChatFile = null;
const MAX_CHAT_FILE_BYTES = 15 * 1024 * 1024;

function validateChatFile(file) {
    if (!file) return null;
    if (file.size > MAX_CHAT_FILE_BYTES) {
        return "Dosya boyutu 15 MB sınırını aşıyor.";
    }
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    const allowed = ["pdf", "jpg", "jpeg", "png", "gif", "webp", "bmp", "doc", "docx", "xls", "xlsx", "csv", "txt", "md", "log"];
    if (!allowed.includes(ext)) {
        return "Desteklenmeyen dosya türü. PDF, JPG, PNG, Word, Excel, CSV veya TXT gönderin.";
    }
    return null;
}

function showChatError(message) {
    const messages = document.querySelector(".messages");
    if (!messages) return;
    const div = document.createElement("div");
    div.className = "msg msg-bot";
    div.innerHTML =
        '<div class="msg-label">Hata</div>' +
        '<div class="msg-text">' + escapeHtml(message) + "</div>";
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

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
    if (file.type.startsWith("image/") || ["jpg", "jpeg", "png", "gif", "webp", "bmp"].includes(ext)) {
        type = "image";
    } else if (ext === "pdf") {
        type = "pdf";
    } else if (ext === "doc" || ext === "docx") {
        type = "word";
    } else if (ext === "xls" || ext === "xlsx" || ext === "csv") {
        type = "excel";
    } else if (ext === "txt" || ext === "md" || ext === "log") {
        type = "text";
    }

    return {
        name: file.name,
        type: type,
        icon: FILE_ICONS[type] || FILE_ICONS.other,
        preview: (file.type.startsWith("image/") || type === "image")
            ? URL.createObjectURL(file)
            : null,
    };
}

function appendMessage(role, text, fileMeta) {
    const messages = document.querySelector(".messages");
    if (!messages) return null;

    const div = document.createElement("div");
    div.className = role === "user" ? "msg msg-user" : "msg msg-bot";

    const label = role === "user" ? "Sen" : "KipGPT";
    const fileHtml = renderFileBadge(fileMeta);
    const bodyHtml = escapeHtml(text).replace(/\n/g, "<br>");

    if (role === "user") {
        div.innerHTML =
            `<div class="msg-label">${label}</div>` +
            `<div class="msg-text">${bodyHtml}</div>${fileHtml}`;
    } else {
        div.innerHTML =
            `<div class="msg-bot-head">` +
            `<b class="msg-label">${label}</b>` +
            (window.KipSpeech && KipSpeech.isSpeakSupported()
                ? `<button type="button" class="speech-speak-btn msg-speak-btn" title="Dinle">` +
                  `<span class="speech-speak-icon">🔊</span></button>`
                : "") +
            `</div>` +
            `<div class="msg-bot-text msg-text">${bodyHtml}</div>${fileHtml}`;

        const speakBtn = div.querySelector(".msg-speak-btn");
        if (speakBtn) {
            speakBtn.addEventListener("click", function () {
                if (KipSpeech.isSpeaking()) {
                    KipSpeech.stopSpeaking();
                    updateChatStopButton();
                    return;
                }
                KipSpeech.speak(text);
                updateChatStopButton();
            });
        }
    }

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
}

function createThinkingBubble() {
    const loading = document.createElement("div");
    loading.className = "msg msg-bot msg-thinking";
    loading.innerHTML =
        '<span class="msg-thinking-text">Düşünüyor</span>' +
        '<span class="msg-thinking-dots" aria-hidden="true">' +
        "<span>.</span><span>.</span><span>.</span>" +
        "</span>";

    let tick = 0;
    const labels = ["Düşünüyor", "Hazırlıyor"];
    const textEl = loading.querySelector(".msg-thinking-text");
    loading._thinkingTimer = setInterval(function () {
        tick += 1;
        if (textEl) {
            textEl.textContent = labels[tick % labels.length];
        }
    }, 1600);
    return loading;
}

function removeThinkingBubble(loading) {
    if (!loading) return;
    if (loading._thinkingTimer) {
        clearInterval(loading._thinkingTimer);
    }
    loading.remove();
}

function enhanceExistingBotMessages() {
    if (!window.KipSpeech || !KipSpeech.isSpeakSupported()) return;

    document.querySelectorAll(".msg-bot:not(.msg-thinking)").forEach(function (msg) {
        if (msg.querySelector(".msg-speak-btn")) return;

        const textEl =
            msg.querySelector(".msg-bot-text") ||
            msg.querySelector(".msg-text") ||
            msg.querySelector(".bot-text:last-of-type");
        let text = textEl ? textEl.textContent : msg.textContent;
        text = (text || "").replace(/^Kip(?:GPT| Asistan):\s*/i, "").trim();
        if (!text) return;

        let head = msg.querySelector(".msg-bot-head");
        if (!head) {
            head = document.createElement("div");
            head.className = "msg-bot-head";
            const label = document.createElement("b");
            label.className = "msg-label bot-text";
            label.textContent = "KipGPT";
            head.appendChild(label);
            msg.insertBefore(head, msg.firstChild);
        }

        if (!head.querySelector(".msg-speak-btn")) {
            const speakBtn = document.createElement("button");
            speakBtn.type = "button";
            speakBtn.className = "speech-speak-btn msg-speak-btn";
            speakBtn.title = "Dinle";
            speakBtn.innerHTML = '<span class="speech-speak-icon">🔊</span>';
            speakBtn.addEventListener("click", function () {
                if (KipSpeech.isSpeaking()) {
                    KipSpeech.stopSpeaking();
                    updateChatStopButton();
                    return;
                }
                KipSpeech.speak(text);
                updateChatStopButton();
            });
            head.appendChild(speakBtn);
        }

        if (textEl && !textEl.classList.contains("msg-bot-text")) {
            textEl.classList.add("msg-bot-text", "msg-text");
        }
    });
}

function updateChatStopButton() {
    const stopBtn = document.getElementById("chat-stop-speak-btn");
    if (!stopBtn || !window.KipSpeech) return;
    stopBtn.hidden = !KipSpeech.isSpeaking();
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

function updateChatSendState() {
    const chatInput = document.getElementById("chat-input");
    const chatSendBtn = document.querySelector(".chat-send-btn");
    if (!chatInput || !chatSendBtn) return;
    chatSendBtn.disabled = !chatInput.value.trim() && !selectedChatFile;
}

function clearSelectedFilePreview() {
    const bar = document.getElementById("file-preview-bar");
    const content = document.getElementById("file-preview-content");
    const fileInput = document.getElementById("file-input");

    selectedChatFile = null;
    if (content) content.innerHTML = "";
    if (bar) bar.hidden = true;
    if (fileInput) fileInput.value = "";
    updateChatSendState();
}

function bindChatPage() {
    const chatForm = document.getElementById("chat-form");
    const chatSearch = document.getElementById("chat-search");
    const chatList = document.getElementById("chat-list");
    const fileInput = document.getElementById("file-input");
    const fileUploadBtn = document.getElementById("file-upload-btn");
    const clearBtn = document.getElementById("file-preview-clear");

    clearSelectedFilePreview();

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
            if (!fileInput.files.length) {
                clearSelectedFilePreview();
                return;
            }
            const file = fileInput.files[0];
            const validationError = validateChatFile(file);
            if (validationError) {
                showChatError(validationError);
                clearSelectedFilePreview();
                return;
            }
            selectedChatFile = file;
            showSelectedFilePreview(selectedChatFile);
            updateChatSendState();
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", clearSelectedFilePreview);
    }

    const chatMicBtn = document.getElementById("chat-mic-btn");
    const chatInput = document.getElementById("chat-input");

    if (chatInput) {
        chatInput.addEventListener("input", updateChatSendState);
        updateChatSendState();
    }

    if (chatMicBtn && chatInput && window.KipSpeech) {
        KipSpeech.bindMicToField(chatMicBtn, chatInput, { append: true });
    }

    const chatStopBtn = document.getElementById("chat-stop-speak-btn");
    if (chatStopBtn && window.KipSpeech) {
        chatStopBtn.addEventListener("click", function () {
            KipSpeech.stopSpeaking();
            updateChatStopButton();
        });
    }

    enhanceExistingBotMessages();

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

    if (file) {
        const validationError = validateChatFile(file);
        if (validationError) {
            showChatError(validationError);
            return;
        }
    }

    const messages = document.querySelector(".messages");
    const previewMeta = file ? getFileMetaFromFile(file) : null;
    const displayText = message || (file ? `[DOSYA] ${file.name}` : "");

    appendMessage("user", displayText, previewMeta);

    const loading = createThinkingBubble();
    messages.appendChild(loading);
    messages.scrollTop = messages.scrollHeight;

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
    updateChatSendState();

    try {
        const response = await fetch("/chat", {
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
            removeThinkingBubble(loading);
            appendMessage("bot", data.answer, data.file || null);
            if (data.chat_title) {
                updateActiveChatTitle(data.chat_title);
            }
            clearSelectedFilePreview();
        } else {
            removeThinkingBubble(loading);
            showChatError(data.error || "Bilinmeyen hata");
        }
    } catch (e) {
        removeThinkingBubble(loading);
        showChatError(e.message || "Bağlantı hatası");
        console.error(e);
    }

    messages.scrollTop = messages.scrollHeight;
}
