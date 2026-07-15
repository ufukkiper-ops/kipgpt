(function () {

    const READ_KEY = "kipgpt_read_mails";

    const mailsData = JSON.parse(
        document.getElementById("mails-data")?.textContent || "[]"
    );

    const mailMap = {};
    mailsData.forEach(function (m) {
        mailMap[m.id] = m;
    });

    const list = document.getElementById("gmail-list");
    const readerEmpty = document.getElementById("reader-empty");
    const readerContent = document.getElementById("reader-content");
    const aiDraftView = document.getElementById("ai-draft-view");
    const readerSubject = document.getElementById("reader-subject");
    const readerFrom = document.getElementById("reader-from");
    const readerDate = document.getElementById("reader-date");
    const readerAvatar = document.getElementById("reader-avatar");
    const readerBody = document.getElementById("reader-body");
    const readerThread = document.getElementById("reader-thread");
    const readerAttachments = document.getElementById("reader-attachments");
    const translateButtons = document.querySelectorAll(".translate-btn");
    const currentFolder = document.body.dataset.mailFolder || "inbox";
    const currentAccount = document.body.dataset.mailAccount || "";

    function buildAttachmentUrl(mail, att) {
        let url = "/mail/attachment?mail_id=" + encodeURIComponent(mail.id) +
            "&index=" + encodeURIComponent(att.index) +
            "&folder=" + encodeURIComponent(currentFolder);
        if (currentAccount) {
            url += "&account=" + encodeURIComponent(currentAccount);
        }
        return url;
    }

    function formatAttachmentSize(bytes) {
        const size = Number(bytes) || 0;
        if (size < 1024) return size + " B";
        if (size < 1024 * 1024) return Math.round(size / 1024) + " KB";
        return (size / (1024 * 1024)).toFixed(1) + " MB";
    }
    const aiPanel = document.getElementById("ai-panel");
    const aiMailId = document.getElementById("ai-mail-id");
    const aiSender = document.getElementById("ai-sender");
    const aiSubject = document.getElementById("ai-subject");
    const aiContent = document.getElementById("ai-content");
    const replyBtn = document.getElementById("reply-btn");
    const aiReplyBtn = document.getElementById("ai-reply-btn");
    const manualReplyPanel = document.getElementById("manual-reply-panel");
    const manualReplySender = document.getElementById("manual-reply-sender");
    const manualReplySubject = document.getElementById("manual-reply-subject");
    const manualReplyTo = document.getElementById("manual-reply-to");
    const manualReplyBody = document.getElementById("manual-reply-body");
    const manualReplyCancel = document.getElementById("manual-reply-cancel");
    const selectAll = document.getElementById("select-all");
    const sidebar = document.getElementById("gmail-sidebar");
    const menuBtn = document.querySelector(".menu-btn");
    const composeBtn = document.getElementById("compose-btn");
    const composeOverlay = document.getElementById("compose-overlay");
    const composeClose = document.getElementById("compose-close");
    const readerBack = document.getElementById("reader-back");
    const gmailReader = document.getElementById("gmail-reader");

    function getReadSet() {
        try {
            return new Set(JSON.parse(localStorage.getItem(READ_KEY) || "[]"));
        } catch (e) {
            return new Set();
        }
    }

    function saveReadSet(readSet) {
        localStorage.setItem(READ_KEY, JSON.stringify(Array.from(readSet)));
    }

    function markAsRead(mailId) {
        if (!mailId) return;

        const readSet = getReadSet();
        readSet.add(mailId);
        saveReadSet(readSet);

        const row = document.querySelector('[data-mail-id="' + mailId + '"]');
        if (row) {
            row.classList.remove("unread");
            row.classList.add("read");
        }
    }

    function applyReadState() {
        const readSet = getReadSet();

        document.querySelectorAll(".gmail-row").forEach(function (row) {
            const mailId = row.dataset.mailId;

            if (readSet.has(mailId)) {
                row.classList.add("read");
                row.classList.remove("unread");
            } else {
                row.classList.add("unread");
                row.classList.remove("read");
            }
        });
    }

    const aiDraftData = JSON.parse(
        document.getElementById("ai-draft-data")?.textContent || "null"
    );

    let currentOriginalContent = "";
    let currentTranslationLang = null;
    const translationCache = {};

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text || "";
        return div.innerHTML;
    }

    function escapeAttr(text) {
        return String(text || "")
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;");
    }

    function getActiveBodyElement() {
        if (readerThread && !readerThread.hidden) {
            const latest = readerThread.querySelector(".thread-msg.is-latest .thread-msg-body");
            if (latest) return latest;
        }
        return readerBody;
    }

    function setReaderBody(text, translated) {
        const target = getActiveBodyElement();
        if (!target) return;
        target.textContent = text || "(İçerik yok)";
        target.classList.toggle("is-translated", Boolean(translated));
    }

    function updateTranslateButtons() {
        const defaultTitles = {
            tr: "Dili algıla ve Türkçe'ye çevir",
            en: "Detect language and translate to English",
            de: "Sprache erkennen und ins Deutsche übersetzen",
        };

        translateButtons.forEach(function (btn) {
            const lang = btn.dataset.lang;
            const isActive = lang === currentTranslationLang;
            btn.classList.toggle("active", isActive);
            btn.disabled = readerBody?.classList.contains("is-translating");
            btn.title = isActive
                ? "Orijinal metni göster"
                : (defaultTitles[lang] || "Dili algıla ve çevir");
        });
    }

    function showOriginalContent() {
        currentTranslationLang = null;
        setReaderBody(currentOriginalContent, false);
        updateTranslateButtons();
    }

    function resetTranslationState(content) {
        currentOriginalContent = content || "";
        currentTranslationLang = null;
        Object.keys(translationCache).forEach(function (key) {
            delete translationCache[key];
        });
        setReaderBody(currentOriginalContent, false);
        updateTranslateButtons();
    }

    async function translateMail(targetLang) {
        const bodyEl = getActiveBodyElement();
        if (!currentOriginalContent || !bodyEl) return;

        if (currentTranslationLang === targetLang) {
            showOriginalContent();
            return;
        }

        if (translationCache[targetLang]) {
            currentTranslationLang = targetLang;
            setReaderBody(translationCache[targetLang], true);
            updateTranslateButtons();
            return;
        }

        bodyEl.classList.add("is-translating");
        updateTranslateButtons();

        const previousText = bodyEl.textContent;
        bodyEl.textContent = "Dil algılanıyor, çeviri hazırlanıyor...";

        try {
            const response = await fetch("/mail/translate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    text: currentOriginalContent,
                    target_lang: targetLang,
                }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "Çeviri yapılamadı.");
            }

            translationCache[targetLang] = data.translated || "";
            currentTranslationLang = targetLang;
            setReaderBody(translationCache[targetLang], true);
        } catch (err) {
            currentTranslationLang = null;
            setReaderBody(previousText, false);
            alert(err.message || "Çeviri sırasında hata oluştu.");
        } finally {
            bodyEl.classList.remove("is-translating");
            updateTranslateButtons();
        }
    }

    translateButtons.forEach(function (btn) {
        btn.addEventListener("click", function () {
            translateMail(btn.dataset.lang);
        });
    });

    function renderMessageAttachments(mail, container) {
        if (!container) return;
        const attachments = mail.attachments || [];
        if (!attachments.length) {
            container.innerHTML = "";
            container.hidden = true;
            return;
        }

        let html = '<div class="mail-attachments-title">Ekler (' + attachments.length + ')</div><div class="mail-attachments-list">';
        attachments.forEach(function (att) {
            const url = buildAttachmentUrl(mail, att);
            const safeName = escapeHtml(att.filename || "ek");
            const downloadName = escapeAttr(att.filename || "ek");
            const sizeLabel = att.size ? formatAttachmentSize(att.size) : "";
            if (att.is_image && att.preview) {
                html += '<a class="mail-attach-item" href="' + url + '" download="' + downloadName + '" title="İndir: ' + safeName + '">' +
                    '<img src="' + att.preview + '" class="mail-attach-thumb" alt="' + safeName + '">' +
                    '<span class="mail-attach-meta"><span class="mail-attach-name">' + safeName + '</span>' +
                    (sizeLabel ? '<span class="mail-attach-size">' + sizeLabel + '</span>' : '') + '</span>' +
                    '<span class="material-icons-outlined mail-attach-download">download</span></a>';
            } else {
                html += '<a class="mail-attach-item" href="' + url + '" download="' + downloadName + '" title="İndir: ' + safeName + '">' +
                    '<span class="mail-attach-icon material-icons-outlined">attach_file</span>' +
                    '<span class="mail-attach-meta"><span class="mail-attach-name">' + safeName + '</span>' +
                    (sizeLabel ? '<span class="mail-attach-size">' + sizeLabel + '</span>' : '') + '</span>' +
                    '<span class="material-icons-outlined mail-attach-download">download</span></a>';
            }
        });
        html += "</div>";
        container.innerHTML = html;
        container.hidden = false;
    }

    function renderAttachments(mail) {
        if (!readerAttachments) return;
        renderMessageAttachments(mail, readerAttachments);
    }

    function buildThreadAttachmentsHtml(mail) {
        const attachments = mail.attachments || [];
        if (!attachments.length) return "";

        let html = '<div class="thread-msg-attachments"><div class="mail-attachments-list">';
        attachments.forEach(function (att) {
            const url = buildAttachmentUrl(mail, att);
            const safeName = escapeHtml(att.filename || "ek");
            const downloadName = escapeAttr(att.filename || "ek");
            const sizeLabel = att.size ? formatAttachmentSize(att.size) : "";
            if (att.is_image && att.preview) {
                html += '<a class="mail-attach-item mail-attach-item-compact" href="' + url + '" download="' + downloadName + '" title="İndir: ' + safeName + '">' +
                    '<img src="' + att.preview + '" class="mail-attach-thumb" alt="' + safeName + '">' +
                    '<span class="mail-attach-name">' + safeName + '</span>' +
                    (sizeLabel ? '<span class="mail-attach-size">' + sizeLabel + '</span>' : '') +
                    '<span class="material-icons-outlined mail-attach-download">download</span></a>';
            } else {
                html += '<a class="mail-attach-item mail-attach-item-compact" href="' + url + '" download="' + downloadName + '" title="İndir: ' + safeName + '">' +
                    '<span class="mail-attach-icon material-icons-outlined">attach_file</span>' +
                    '<span class="mail-attach-name">' + safeName + '</span>' +
                    (sizeLabel ? '<span class="mail-attach-size">' + sizeLabel + '</span>' : '') +
                    '<span class="material-icons-outlined mail-attach-download">download</span></a>';
            }
        });
        html += "</div>";
        html += "</div>";
        return html;
    }

    function renderThreadView(mail) {
        if (!readerThread) return false;

        const messages = (mail.thread_messages || []).filter(Boolean);
        if (messages.length <= 1) {
            readerThread.hidden = true;
            readerThread.innerHTML = "";
            if (readerBody) readerBody.hidden = false;
            return false;
        }

        const latest = messages[0];
        const older = messages.slice(1);
        let html = "";

        html += '<article class="thread-msg is-latest is-expanded" data-mail-id="' + escapeHtml(latest.id) + '">';
        html += '<div class="thread-msg-header thread-msg-header-static">';
        html += '<span class="thread-msg-avatar">' + escapeHtml((latest.sender_display || latest.sender || "?").charAt(0).toUpperCase()) + "</span>";
        html += '<div class="thread-msg-meta">';
        html += '<span class="thread-msg-from">' + escapeHtml(latest.sender_display || latest.sender || "") + "</span>";
        html += '<span class="thread-msg-date">' + escapeHtml(latest.date || "") + "</span>";
        html += "</div></div>";
        html += '<div class="thread-msg-body">' + escapeHtml(latest.content || "(İçerik yok)") + "</div>";
        html += buildThreadAttachmentsHtml(latest);
        html += "</article>";

        if (older.length) {
            html += '<div class="thread-older-label">';
            html += '<span class="material-icons-outlined">forum</span>';
            html += "Önceki mesajlar (" + older.length + ")";
            html += "</div>";

            older.forEach(function (msg) {
                const snippet = (msg.content || "").replace(/\s+/g, " ").trim().slice(0, 120);
                html += '<article class="thread-msg is-collapsed" data-mail-id="' + escapeHtml(msg.id) + '">';
                html += '<button type="button" class="thread-msg-header" aria-expanded="false">';
                html += '<span class="thread-msg-avatar">' + escapeHtml((msg.sender_display || msg.sender || "?").charAt(0).toUpperCase()) + "</span>";
                html += '<div class="thread-msg-meta">';
                html += '<span class="thread-msg-from">' + escapeHtml(msg.sender_display || msg.sender || "") + "</span>";
                html += '<span class="thread-msg-date">' + escapeHtml(msg.date || "") + "</span>";
                if (snippet) {
                    html += '<span class="thread-msg-snippet">' + escapeHtml(snippet) + "</span>";
                }
                html += "</div>";
                html += '<span class="material-icons-outlined thread-msg-toggle">expand_more</span>';
                html += "</button>";
                html += '<div class="thread-msg-body" hidden>' + escapeHtml(msg.content || "(İçerik yok)") + "</div>";
                html += buildThreadAttachmentsHtml(msg);
                html += "</article>";
            });
        }

        readerThread.innerHTML = html;
        readerThread.hidden = false;
        if (readerBody) {
            readerBody.hidden = true;
            readerBody.textContent = "";
        }
        if (readerAttachments) {
            readerAttachments.innerHTML = "";
            readerAttachments.hidden = true;
        }
        return true;
    }

    function bindThreadToggleEvents() {
        if (!readerThread) return;

        readerThread.querySelectorAll(".thread-msg-header:not(.thread-msg-header-static)").forEach(function (btn) {
            btn.addEventListener("click", function () {
                const article = btn.closest(".thread-msg");
                if (!article) return;

                const expanded = article.classList.toggle("is-expanded");
                article.classList.toggle("is-collapsed", !expanded);
                btn.setAttribute("aria-expanded", expanded ? "true" : "false");

                const body = article.querySelector(".thread-msg-body");
                if (body) body.hidden = !expanded;

                const icon = btn.querySelector(".thread-msg-toggle");
                if (icon) {
                    icon.textContent = expanded ? "expand_less" : "expand_more";
                }
            });
        });
    }

    function hideDraftView() {
        if (aiDraftView) aiDraftView.hidden = true;
    }

    function showDraftView() {
        if (readerEmpty) readerEmpty.hidden = true;
        if (readerContent) readerContent.hidden = true;
        if (aiDraftView) aiDraftView.hidden = false;
        if (gmailReader) gmailReader.classList.add("reader-active");
    }

    function isDraftMail(mail) {
        if (!aiDraftData || !aiDraftData.yanit || !aiDraftData.mail || !mail) {
            return false;
        }

        const draft = aiDraftData.mail;

        if (draft.id && mail.id && draft.id === mail.id) {
            return true;
        }

        return draft.sender === mail.sender && draft.subject === mail.subject;
    }

    function closeMail() {
        if (gmailReader) gmailReader.classList.remove("reader-active");
        document.querySelectorAll(".gmail-row.selected").forEach(function (row) {
            row.classList.remove("selected");
        });
        hideDraftView();
        if (readerContent) readerContent.hidden = true;
        if (readerEmpty) readerEmpty.hidden = false;
        if (aiPanel) aiPanel.hidden = true;
        if (manualReplyPanel) manualReplyPanel.hidden = true;
        if (readerThread) {
            readerThread.hidden = true;
            readerThread.innerHTML = "";
        }
        if (readerBody) readerBody.hidden = false;
    }

    function formatThreadParticipants(mail) {
        const messages = mail.thread_messages || [];
        const names = [];
        const seen = new Set();

        messages.forEach(function (msg) {
            const raw = (msg.sender_display || msg.sender || "").trim();
            if (!raw) return;
            const key = raw.toLowerCase();
            if (seen.has(key)) return;
            seen.add(key);
            names.push(raw);
        });

        if (names.length <= 1) {
            return names[0] || mail.sender_display || mail.sender || "";
        }
        if (names.length === 2) {
            return names[0] + " ve " + names[1];
        }
        return names[0] + ", " + names[1] + " ve " + (names.length - 2) + " kişi daha";
    }

    function openMail(mail) {
        if (!mail) return;

        document.querySelectorAll(".gmail-row.selected").forEach(function (row) {
            row.classList.remove("selected");
        });

        const row = document.querySelector('[data-mail-id="' + mail.id + '"]');
        if (row) row.classList.add("selected");

        markAsRead(mail.id);
        (mail.thread_ids || []).forEach(function (id) {
            markAsRead(id);
        });

        if (isDraftMail(mail)) {
            showDraftView();
            return;
        }

        hideDraftView();

        if (gmailReader) gmailReader.classList.add("reader-active");
        if (readerEmpty) readerEmpty.hidden = true;

        if (readerContent) {
            readerContent.hidden = false;

            if (readerSubject) readerSubject.textContent = mail.subject || "Konu yok";
            if (readerAvatar) {
                readerAvatar.textContent = (mail.sender_display || "?").charAt(0).toUpperCase();
            }

            const isThread = renderThreadView(mail);
            if (!isThread) {
                if (readerBody) {
                    resetTranslationState(mail.content || "");
                } else {
                    currentOriginalContent = mail.content || "";
                }
                renderAttachments(mail);
            } else {
                const latest = (mail.thread_messages || [])[0] || mail;
                resetTranslationState(latest.content || "");
                bindThreadToggleEvents();
            }

            if (aiMailId) aiMailId.value = mail.id || "";
            if (aiSender) aiSender.value = mail.sender || "";
            if (aiSubject) aiSubject.value = mail.subject || "";
            if (aiContent) aiContent.value = currentOriginalContent;
            if (aiPanel) aiPanel.hidden = true;
            if (manualReplyPanel) manualReplyPanel.hidden = true;
            if (manualReplySender) manualReplySender.value = mail.sender || "";
            if (manualReplySubject) manualReplySubject.value = mail.subject || "";
            currentSenderDisplay = mail.sender_display || mail.sender || "";
            if (manualReplyTo) manualReplyTo.value = currentSenderDisplay;
            if (manualReplyBody) manualReplyBody.value = "";

            if (readerFrom && mail.thread_count > 1) {
                readerFrom.textContent = formatThreadParticipants(mail) +
                    " · " + mail.thread_count + " mesaj";
            } else if (readerFrom) {
                readerFrom.textContent = mail.sender_display || mail.sender || "";
            }
            if (readerDate) readerDate.textContent = mail.date || "";
        }
    }

    if (list) {
        list.addEventListener("click", function (e) {
            const starBtn = e.target.closest(".star-btn");
            if (starBtn) {
                e.stopPropagation();
                starBtn.classList.toggle("starred");
                const icon = starBtn.querySelector(".material-icons-outlined");
                if (icon) {
                    icon.textContent = starBtn.classList.contains("starred")
                        ? "star"
                        : "star_border";
                }
                return;
            }

            if (e.target.closest(".checkbox-wrap")) {
                e.stopPropagation();
                return;
            }

            const row = e.target.closest(".gmail-row");
            if (!row) return;

            const mail = mailMap[row.dataset.mailId];
            openMail(mail);
        });

        list.addEventListener("keydown", function (e) {
            if (e.key !== "Enter" && e.key !== " ") return;
            const row = e.target.closest(".gmail-row");
            if (!row) return;
            e.preventDefault();
            openMail(mailMap[row.dataset.mailId]);
        });
    }

    function hideReplyPanels() {
        if (aiPanel) aiPanel.hidden = true;
        if (manualReplyPanel) manualReplyPanel.hidden = true;
    }

    let currentSenderDisplay = "";

    function showManualReplyPanel() {
        hideReplyPanels();
        if (!manualReplyPanel) return;
        manualReplyPanel.hidden = false;
        if (manualReplySender && aiSender) {
            manualReplySender.value = aiSender.value || "";
        }
        if (manualReplySubject && aiSubject) {
            manualReplySubject.value = aiSubject.value || "";
        }
        if (manualReplyTo) {
            manualReplyTo.value = currentSenderDisplay || aiSender?.value || "";
        }
        manualReplyPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
        if (manualReplyBody) manualReplyBody.focus();
    }

    function showAiReplyPanel() {
        hideReplyPanels();
        if (!aiPanel) return;
        aiPanel.hidden = false;
        aiPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
        const textarea = document.getElementById("ai-user-instruction") ||
            aiPanel.querySelector('textarea[name="user_instruction"]');
        if (textarea) textarea.focus();
    }

    const AI_THINKING_LABELS = ["Düşünüyor", "Hazırlıyor"];
    let aiThinkingTimer = null;

    function startAiThinking(statusEl) {
        if (!statusEl) return;
        statusEl.hidden = false;
        const textEl = statusEl.querySelector(".ai-thinking-text");
        let tick = 0;
        if (textEl) {
            textEl.textContent = AI_THINKING_LABELS[0];
        }
        if (aiThinkingTimer) {
            clearInterval(aiThinkingTimer);
        }
        aiThinkingTimer = setInterval(function () {
            tick += 1;
            if (textEl) {
                textEl.textContent = AI_THINKING_LABELS[tick % AI_THINKING_LABELS.length];
            }
        }, 1600);
    }

    function bindAiFormThinking(form, statusEl) {
        if (!form) return;
        form.addEventListener("submit", function () {
            startAiThinking(statusEl);
            form.classList.add("is-ai-busy");
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.style.pointerEvents = "none";
                submitBtn.style.opacity = "0.7";
            }
        });
    }

    bindAiFormThinking(
        document.getElementById("ai-generate-form"),
        document.getElementById("ai-thinking"),
    );
    bindAiFormThinking(
        document.getElementById("ai-revise-form"),
        document.getElementById("ai-revise-thinking"),
    );

    if (replyBtn) {
        replyBtn.addEventListener("click", showManualReplyPanel);
    }

    if (aiReplyBtn) {
        aiReplyBtn.addEventListener("click", showAiReplyPanel);
    }

    if (manualReplyCancel) {
        manualReplyCancel.addEventListener("click", function () {
            if (manualReplyPanel) manualReplyPanel.hidden = true;
            if (manualReplyBody) manualReplyBody.value = "";
        });
    }

    const manualReplyCcToggle = document.getElementById("manual-reply-cc-toggle");
    const manualReplyExtraFields = document.getElementById("manual-reply-extra-fields");
    bindCcToggle(manualReplyCcToggle, manualReplyExtraFields);

    const aiReviseForm = document.getElementById("ai-revise-form");
    const aiDraftEditor = document.getElementById("ai-draft-editor");
    const aiCurrentDraft = document.getElementById("ai-current-draft");
    if (aiReviseForm && aiDraftEditor && aiCurrentDraft) {
        aiReviseForm.addEventListener("submit", function () {
            aiCurrentDraft.value = aiDraftEditor.value;
        });
    }

    if (readerBack) {
        readerBack.addEventListener("click", closeMail);
    }

    if (selectAll) {
        selectAll.addEventListener("change", function () {
            document.querySelectorAll(".mail-check").forEach(function (cb) {
                cb.checked = selectAll.checked;
            });
            syncCheckedRows();
        });
    }

    function syncCheckedRows() {
        const checks = document.querySelectorAll(".mail-check");
        const checked = document.querySelectorAll(".mail-check:checked");

        if (selectAll && checks.length) {
            selectAll.checked = checked.length === checks.length;
            selectAll.indeterminate = checked.length > 0 && checked.length < checks.length;
        }

        document.querySelectorAll(".gmail-row").forEach(function (row) {
            const isChecked = Boolean(row.querySelector(".mail-check")?.checked);
            row.classList.toggle("checked", isChecked);
        });
    }

    if (list) {
        list.addEventListener("change", function (e) {
            if (e.target.classList.contains("mail-check")) {
                syncCheckedRows();
            }
        });
    }

    if (menuBtn && sidebar) {
        menuBtn.addEventListener("click", function () {
            sidebar.classList.toggle("open");
        });
    }

    if (composeClose && composeOverlay) {
        composeClose.addEventListener("click", function () {
            composeOverlay.hidden = true;
        });

        composeOverlay.addEventListener("click", function (e) {
            if (e.target === composeOverlay) {
                composeOverlay.hidden = true;
            }
        });
    }

    const composeFilePreview = document.getElementById("compose-file-preview");
    const composeFileInput = document.getElementById("compose-file");
    const composeCcToggle = document.getElementById("compose-cc-toggle");
    const composeExtraFields = document.getElementById("compose-extra-fields");
    const composeToInput = document.getElementById("compose-to-email");
    const composeContactPanel = document.getElementById("compose-contact-panel");
    const composeContactList = document.getElementById("compose-contact-list");
    const mailContacts = JSON.parse(
        document.getElementById("mail-contacts-data")?.textContent || "[]"
    );
    const replyCcToggle = document.getElementById("reply-cc-toggle");
    const replyExtraFields = document.getElementById("reply-extra-fields");

    function bindCcToggle(button, fields) {
        if (!button || !fields) return;
        button.addEventListener("click", function () {
            const willShow = fields.hidden;
            fields.hidden = !willShow;
            button.classList.toggle("active", willShow);
        });
    }

    bindCcToggle(composeCcToggle, composeExtraFields);
    bindCcToggle(replyCcToggle, replyExtraFields);

    function filterContacts(query) {
        const value = (query || "").trim().toLowerCase();
        if (!value) {
            return mailContacts.slice(0, 8);
        }
        return mailContacts.filter(function (contact) {
            return (
                contact.email.toLowerCase().includes(value) ||
                (contact.name || "").toLowerCase().includes(value)
            );
        }).slice(0, 8);
    }

    function renderComposeContacts(query) {
        if (!composeContactList || !composeContactPanel) return;

        const matches = filterContacts(query);
        if (!matches.length) {
            composeContactPanel.hidden = true;
            composeContactList.innerHTML = "";
            return;
        }

        composeContactPanel.hidden = false;
        composeContactList.innerHTML = matches.map(function (contact) {
            const label = contact.name && contact.name !== contact.email
                ? contact.name
                : contact.email;
            return (
                `<button type="button" class="compose-contact-item" data-email="${contact.email}" title="${contact.email}">` +
                `<span class="compose-contact-name">${label}</span>` +
                `<span class="compose-contact-email">${contact.email}</span>` +
                `</button>`
            );
        }).join("");

        composeContactList.querySelectorAll(".compose-contact-item").forEach(function (btn) {
            btn.addEventListener("click", function () {
                if (!composeToInput) return;
                const email = btn.dataset.email || "";
                const current = composeToInput.value.trim();
                if (!current) {
                    composeToInput.value = email;
                } else if (!current.toLowerCase().includes(email.toLowerCase())) {
                    composeToInput.value = current.replace(/,\s*$/, "") + ", " + email;
                }
                composeToInput.focus();
                renderComposeContacts(composeToInput.value);
            });
        });
    }

    if (composeToInput) {
        composeToInput.addEventListener("focus", function () {
            renderComposeContacts(composeToInput.value);
        });
        composeToInput.addEventListener("input", function () {
            renderComposeContacts(composeToInput.value);
        });
    }

    if (composeBtn && composeOverlay) {
        composeBtn.addEventListener("click", function () {
            composeOverlay.hidden = false;
            renderComposeContacts(composeToInput?.value || "");
            if (composeToInput) {
                composeToInput.focus();
            }
        });
    }

    const composeAiPanel = document.getElementById("compose-ai-panel");
    const composeAiToggle = document.getElementById("compose-ai-toggle");
    const composeAiCancel = document.getElementById("compose-ai-cancel");
    const composeAiGenerate = document.getElementById("compose-ai-generate");
    const composeAiInstruction = document.getElementById("compose-ai-instruction");
    const composeAiThinking = document.getElementById("compose-ai-thinking");
    const composeSubject = document.getElementById("compose-subject");
    const composeBody = document.getElementById("compose-body");
    let composeAiBusy = false;

    function setComposeAiBusy(busy) {
        composeAiBusy = busy;
        if (composeAiGenerate) {
            composeAiGenerate.style.opacity = busy ? "0.7" : "";
            composeAiGenerate.style.pointerEvents = busy ? "none" : "";
        }
        if (composeAiToggle) {
            composeAiToggle.disabled = busy;
        }
        if (composeAiThinking) {
            if (busy) {
                startAiThinking(composeAiThinking);
            } else {
                composeAiThinking.hidden = true;
                if (aiThinkingTimer) {
                    clearInterval(aiThinkingTimer);
                    aiThinkingTimer = null;
                }
            }
        }
    }

    if (composeAiToggle && composeAiPanel) {
        composeAiToggle.addEventListener("click", function () {
            composeAiPanel.hidden = !composeAiPanel.hidden;
            if (!composeAiPanel.hidden && composeAiInstruction) {
                composeAiInstruction.focus();
            }
        });
    }

    if (composeAiCancel && composeAiPanel) {
        composeAiCancel.addEventListener("click", function () {
            composeAiPanel.hidden = true;
        });
    }

    if (composeAiGenerate) {
        composeAiGenerate.addEventListener("click", async function () {
            if (composeAiBusy) return;
            const instruction = (composeAiInstruction?.value || "").trim();
            const currentBody = (composeBody?.value || "").trim();
            const subject = (composeSubject?.value || "").trim();
            const toEmail = (composeToInput?.value || "").trim();

            if (!instruction && !currentBody && !subject) {
                alert("AI için bir ipucu yazın. Örn: Toplantı daveti yaz, kısa ve resmi olsun.");
                if (composeAiInstruction) composeAiInstruction.focus();
                return;
            }

            setComposeAiBusy(true);
            try {
                const payload = {
                    to_email: toEmail,
                    subject: subject,
                    user_instruction: currentBody ? "" : instruction,
                    current_draft: currentBody,
                    revize_notu: currentBody
                        ? (instruction || "Taslağı iyileştir, daha net ve profesyonel yaz.")
                        : "",
                };
                const response = await fetch("/mail/ai-compose", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || "Taslak oluşturulamadı.");
                }
                if (composeBody) {
                    composeBody.value = data.draft || "";
                    composeBody.focus();
                }
                if (composeAiInstruction) {
                    composeAiInstruction.value = "";
                }
            } catch (err) {
                alert(err.message || "AI taslağı oluşturulurken hata oluştu.");
            } finally {
                setComposeAiBusy(false);
            }
        });
    }

    function clearAttachmentPreview(input, previewEl) {
        if (input) {
            input.value = "";
        }
        if (previewEl) {
            if (previewEl.dataset.objectUrl) {
                URL.revokeObjectURL(previewEl.dataset.objectUrl);
                delete previewEl.dataset.objectUrl;
            }
            previewEl.innerHTML = "";
            previewEl.hidden = true;
        }
    }

    function showAttachPreview(file, previewEl, input) {
        if (!previewEl || !file) return;

        if (previewEl.dataset.objectUrl) {
            URL.revokeObjectURL(previewEl.dataset.objectUrl);
        }

        let mediaHtml = "";
        if (file.type.startsWith("image/")) {
            const url = URL.createObjectURL(file);
            previewEl.dataset.objectUrl = url;
            mediaHtml =
                `<img src="${url}" class="attach-preview-thumb" alt="${file.name}">`;
        } else {
            mediaHtml = `<span class="attach-preview-icon">📎</span>`;
        }

        previewEl.innerHTML =
            `<div class="attach-preview-card">` +
            `<button type="button" class="attach-remove-btn" aria-label="Eki kaldır">` +
            `<span class="material-icons-outlined">close</span>` +
            `</button>` +
            mediaHtml +
            `<span class="attach-preview-name">${file.name}</span>` +
            `</div>`;

        const removeBtn = previewEl.querySelector(".attach-remove-btn");
        if (removeBtn) {
            removeBtn.addEventListener("click", function (e) {
                e.preventDefault();
                e.stopPropagation();
                clearAttachmentPreview(input, previewEl);
            });
        }

        previewEl.hidden = false;
    }

    document.querySelectorAll(".mail-attach-input").forEach(function (input) {
        input.addEventListener("change", function () {
            const previewId = input.id === "compose-file"
                ? "compose-file-preview"
                : input.id === "manual-reply-file"
                    ? "manual-reply-attach-preview"
                    : "reply-attach-preview";
            const previewEl = document.getElementById(previewId);
            const file = input.files && input.files[0];

            if (!file) {
                clearAttachmentPreview(input, previewEl);
                return;
            }

            if (file.size > 15 * 1024 * 1024) {
                window.alert("Dosya boyutu 15 MB sınırını aşıyor.");
                clearAttachmentPreview(input, previewEl);
                return;
            }

            showAttachPreview(file, previewEl, input);
        });
    });

    document.querySelectorAll(".attach-btn").forEach(function (label) {
        label.addEventListener("click", function (e) {
            const input = label.querySelector(".mail-attach-input");
            if (!input) return;
            // Some browsers ignore label->hidden file input; force picker.
            if (e.target === input) return;
            e.preventDefault();
            input.click();
        });
    });

    const settingsBtn = document.getElementById("settings-btn");
    const settingsOverlay = document.getElementById("settings-overlay");
    const settingsClose = document.getElementById("settings-close");
    const spamSensitivity = document.getElementById("spam-sensitivity");
    const sensitivityHint = document.getElementById("sensitivity-hint");
    const customThresholdWrap = document.getElementById("custom-threshold-wrap");
    const spamThreshold = document.getElementById("spam-threshold");
    const thresholdValue = document.getElementById("threshold-value");
    const sensitivityData = JSON.parse(
        document.getElementById("sensitivity-data")?.textContent || "{}"
    );

    function updateSensitivityUI() {
        if (!spamSensitivity) return;
        const key = spamSensitivity.value;
        const preset = sensitivityData[key] || {};
        if (sensitivityHint) {
            sensitivityHint.textContent = preset.hint || "";
        }
        if (customThresholdWrap) {
            customThresholdWrap.hidden = key !== "custom";
        }
    }

    if (spamSensitivity) {
        spamSensitivity.addEventListener("change", updateSensitivityUI);
        updateSensitivityUI();
    }

    if (spamThreshold && thresholdValue) {
        spamThreshold.addEventListener("input", function () {
            thresholdValue.textContent = spamThreshold.value;
        });
    }

    function bindDialogClose(overlay, closeBtn, cancelBtn) {
        if (!overlay) return;

        function closeDialog() {
            overlay.hidden = true;
            document.body.classList.remove("dialog-open");
        }

        function openDialog() {
            overlay.hidden = false;
            document.body.classList.add("dialog-open");
        }

        if (closeBtn) {
            closeBtn.addEventListener("click", closeDialog);
        }

        if (cancelBtn) {
            cancelBtn.addEventListener("click", closeDialog);
        }

        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) {
                closeDialog();
            }
        });

        return { openDialog, closeDialog };
    }

    const settingsDialog = bindDialogClose(
        settingsOverlay,
        settingsClose,
        document.getElementById("settings-cancel")
    );

    if (settingsBtn && settingsDialog) {
        settingsBtn.addEventListener("click", function () {
            settingsDialog.openDialog();
        });
    }

    const accountAddBtn = document.getElementById("account-add-btn");
    const accountOverlay = document.getElementById("account-overlay");
    const accountClose = document.getElementById("account-close");
    const accountProvider = document.getElementById("account_provider");
    const accountProviderHint = document.getElementById("account-provider-hint");
    const accountCustomFields = document.getElementById("account-custom-fields");
    const providerData = JSON.parse(
        document.getElementById("provider-data")?.textContent || "{}"
    );

    function updateAccountProviderUI() {
        if (!accountProvider) return;
        const preset = providerData[accountProvider.value] || {};
        if (accountProviderHint) {
            accountProviderHint.textContent = preset.hint || "";
        }
        if (accountCustomFields) {
            accountCustomFields.hidden = accountProvider.value !== "custom";
        }
    }

    if (accountProvider) {
        accountProvider.addEventListener("change", updateAccountProviderUI);
        updateAccountProviderUI();
    }

    const accountDialog = bindDialogClose(
        accountOverlay,
        accountClose,
        document.getElementById("account-cancel")
    );

    if (accountAddBtn && accountDialog) {
        accountAddBtn.addEventListener("click", function () {
            accountDialog.openDialog();
        });
    }

    document.addEventListener("keydown", function (e) {
        if (e.key !== "Escape") return;
        if (settingsOverlay && !settingsOverlay.hidden) {
            settingsDialog?.closeDialog();
        }
        if (accountOverlay && !accountOverlay.hidden) {
            accountDialog?.closeDialog();
        }
    });

    const spamBtn = document.getElementById("spam-btn");
    const spamForm = document.getElementById("spam-form");
    const spamMailId = document.getElementById("spam-mail-id");
    const unspamBtn = document.getElementById("unspam-btn");
    const unspamActionBtn = document.getElementById("unspam-action-btn");
    const unspamForm = document.getElementById("unspam-form");
    const unspamMailId = document.getElementById("unspam-mail-id");
    const unspamMailIds = document.getElementById("unspam-mail-ids");
    const listUnspamBtn = document.getElementById("list-unspam-btn");
    const restoreTrashBtn = document.getElementById("restore-trash-btn");
    const restoreTrashActionBtn = document.getElementById("restore-trash-action-btn");
    const restoreTrashForm = document.getElementById("restore-trash-form");
    const restoreTrashMailId = document.getElementById("restore-trash-mail-id");
    const restoreTrashMailIds = document.getElementById("restore-trash-mail-ids");
    const listRestoreTrashBtn = document.getElementById("list-restore-trash-btn");
    const listRecoverAllBtn = document.getElementById("list-recover-all-btn");
    const recoverAllForm = document.getElementById("recover-all-form");

    function getCheckedMailIds() {
        const ids = [];
        document.querySelectorAll(".gmail-row .mail-check:checked").forEach(function (cb) {
            const row = cb.closest(".gmail-row");
            if (!row) return;

            const threadIds = (row.dataset.threadIds || "")
                .split(",")
                .map(function (value) { return value.trim(); })
                .filter(Boolean);

            const targetIds = threadIds.length ? threadIds : [row.dataset.mailId].filter(Boolean);
            targetIds.forEach(function (id) {
                if (id && !ids.includes(id)) {
                    ids.push(id);
                }
            });
        });
        return ids;
    }

    function getMailIdsForAction() {
        const checkedIds = getCheckedMailIds();
        if (checkedIds.length) {
            return checkedIds;
        }
        const selectedRow = document.querySelector(".gmail-row.selected");
        if (selectedRow) {
            const threadIds = (selectedRow.dataset.threadIds || "")
                .split(",")
                .map(function (value) { return value.trim(); })
                .filter(Boolean);
            if (threadIds.length) {
                return threadIds;
            }
            if (selectedRow.dataset.mailId) {
                return [selectedRow.dataset.mailId];
            }
        }
        if (aiMailId?.value) {
            const openMail = mailMap[aiMailId.value];
            if (openMail?.thread_ids?.length) {
                return openMail.thread_ids;
            }
            return [aiMailId.value];
        }
        return [];
    }

    function updateFolderActions() {
        const isSpamFolder = currentFolder === "spam";
        const isTrashFolder = currentFolder === "trash";

        if (spamBtn) {
            spamBtn.hidden = isSpamFolder || isTrashFolder;
        }
        if (unspamBtn) unspamBtn.hidden = !isSpamFolder;
        if (unspamActionBtn) unspamActionBtn.hidden = !isSpamFolder;
        if (listUnspamBtn) listUnspamBtn.hidden = !isSpamFolder;
        if (restoreTrashBtn) restoreTrashBtn.hidden = !isTrashFolder;
        if (restoreTrashActionBtn) restoreTrashActionBtn.hidden = !isTrashFolder;
        if (listRestoreTrashBtn) listRestoreTrashBtn.hidden = !isTrashFolder;
    }

    function submitMailMove(form, singleInput, bulkInput, confirmMessage) {
        const ids = getMailIdsForAction();
        if (!ids.length || !form) {
            alert("Lütfen en az bir mail seçin.");
            return;
        }

        const message = confirmMessage.replace("{count}", String(ids.length));
        if (!confirm(message)) return;

        if (bulkInput) {
            bulkInput.value = ids.join(",");
        }
        if (singleInput) {
            singleInput.value = ids.length === 1 ? ids[0] : "";
        }
        form.submit();
    }

    updateFolderActions();

    if (spamBtn && spamForm && spamMailId) {
        spamBtn.addEventListener("click", function () {
            submitMailMove(
                spamForm,
                spamMailId,
                null,
                "Seçili mail spam klasörüne taşınsın mı?"
            );
        });
    }

    function bindRestoreAction(button, form, singleInput, bulkInput, message) {
        if (!button || !form) return;
        button.addEventListener("click", function () {
            submitMailMove(form, singleInput, bulkInput, message);
        });
    }

    bindRestoreAction(
        unspamBtn,
        unspamForm,
        unspamMailId,
        unspamMailIds,
        "{count} mail spam değil olarak işaretlensin ve gelen kutusuna taşınsın mı?"
    );
    bindRestoreAction(
        unspamActionBtn,
        unspamForm,
        unspamMailId,
        unspamMailIds,
        "{count} mail spam değil olarak işaretlensin ve gelen kutusuna taşınsın mı?"
    );
    bindRestoreAction(
        listUnspamBtn,
        unspamForm,
        unspamMailId,
        unspamMailIds,
        "{count} mail spam değil olarak işaretlensin ve gelen kutusuna taşınsın mı?"
    );
    bindRestoreAction(
        restoreTrashBtn,
        restoreTrashForm,
        restoreTrashMailId,
        restoreTrashMailIds,
        "{count} mail çöp kutusundan geri alınsın ve gelen kutusuna taşınsın mı?"
    );
    bindRestoreAction(
        restoreTrashActionBtn,
        restoreTrashForm,
        restoreTrashMailId,
        restoreTrashMailIds,
        "{count} mail çöp kutusundan geri alınsın ve gelen kutusuna taşınsın mı?"
    );
    bindRestoreAction(
        listRestoreTrashBtn,
        restoreTrashForm,
        restoreTrashMailId,
        restoreTrashMailIds,
        "{count} mail çöp kutusundan geri alınsın ve gelen kutusuna taşınsın mı?"
    );

    if (listRecoverAllBtn && recoverAllForm) {
        listRecoverAllBtn.addEventListener("click", function () {
            if (!confirm(
                "Spam ve çöp kutusundaki TÜM mailler gelen kutusuna geri alınsın mı?"
            )) {
                return;
            }
            recoverAllForm.submit();
        });
    }

    applyReadState();

    if (aiDraftData && aiDraftData.yanit) {
        showDraftView();

        const draftMail = aiDraftData.mail;
        const draftId = draftMail?.id || mailsData.find(function (m) {
            return m.sender === draftMail.sender && m.subject === draftMail.subject;
        })?.id;

        if (draftId) {
            markAsRead(draftId);
            const row = document.querySelector('[data-mail-id="' + draftId + '"]');
            if (row) row.classList.add("selected");
        }
    }

    setupMobilePullRefresh();

    function setupMobilePullRefresh() {
        if (!window.matchMedia("(max-width: 768px)").matches) {
            return;
        }

        const listPanel = document.querySelector(".gmail-list-panel");
        const mailList = document.getElementById("gmail-list");
        if (!listPanel || !mailList) {
            return;
        }

        let indicator = listPanel.querySelector(".pull-refresh-indicator");
        if (!indicator) {
            indicator = document.createElement("div");
            indicator.className = "pull-refresh-indicator";
            indicator.innerHTML =
                '<span class="material-icons-outlined pull-refresh-icon">refresh</span>' +
                '<span class="pull-refresh-text">Yenilemek için bırakın</span>';
            listPanel.insertBefore(indicator, mailList);
        }

        let startY = 0;
        let pulling = false;
        let pullDistance = 0;
        let refreshing = false;
        const threshold = 72;

        function getActiveScrollTarget() {
            if (refreshing) {
                return null;
            }

            if (gmailReader && gmailReader.classList.contains("reader-active")) {
                if (readerBody && !readerBody.hidden && readerBody.scrollTop <= 0) {
                    return readerBody;
                }
                if (readerThread && !readerThread.hidden && readerThread.scrollTop <= 0) {
                    return readerThread;
                }
                return null;
            }

            return mailList.scrollTop <= 0 ? mailList : null;
        }

        function resetIndicator() {
            indicator.classList.remove("is-visible", "is-ready", "is-refreshing");
            indicator.style.removeProperty("--pull-offset");
            const text = indicator.querySelector(".pull-refresh-text");
            if (text) {
                text.textContent = "Yenilemek için bırakın";
            }
            pullDistance = 0;
        }

        document.addEventListener("touchstart", function (e) {
            if (!getActiveScrollTarget()) {
                pulling = false;
                return;
            }
            startY = e.touches[0].clientY;
            pulling = true;
            pullDistance = 0;
        }, { passive: true });

        document.addEventListener("touchmove", function (e) {
            if (!pulling) {
                return;
            }

            const target = getActiveScrollTarget();
            if (!target) {
                pulling = false;
                resetIndicator();
                return;
            }

            pullDistance = e.touches[0].clientY - startY;
            if (pullDistance <= 0) {
                resetIndicator();
                return;
            }

            e.preventDefault();
            const offset = Math.min(pullDistance * 0.45, 72);
            indicator.classList.add("is-visible");
            indicator.classList.toggle("is-ready", pullDistance >= threshold);
            indicator.style.setProperty("--pull-offset", offset + "px");
        }, { passive: false });

        document.addEventListener("touchend", function () {
            if (!pulling) {
                return;
            }
            pulling = false;

            if (pullDistance >= threshold && !refreshing) {
                refreshing = true;
                indicator.classList.add("is-refreshing");
                const text = indicator.querySelector(".pull-refresh-text");
                if (text) {
                    text.textContent = "Yenileniyor...";
                }
                window.location.reload();
                return;
            }

            resetIndicator();
        }, { passive: true });
    }

    setupSpeechControls();

    function setupSpeechControls() {
        const micPairs = [
            ["manual-reply-mic", "manual-reply-body"],
            ["ai-instruction-mic", "ai-user-instruction"],
            ["ai-draft-mic", "ai-draft-editor"],
            ["compose-mic", "compose-body"],
            ["compose-ai-mic", "compose-ai-instruction"],
        ];

        function bindAllMics() {
            if (!window.KipSpeech) return;
            micPairs.forEach(function (pair) {
                const button = document.getElementById(pair[0]);
                const field = document.getElementById(pair[1]);
                if (button && field) {
                    KipSpeech.bindMicToField(button, field, { append: true });
                }
            });
        }

        if (!window.KipSpeech) {
            // speech.js async/cache miss fallback
            window.setTimeout(bindAllMics, 300);
        }

        const readerSpeakBtn = document.getElementById("reader-speak-btn");
        const readerStopBtn = document.getElementById("reader-stop-speak-btn");

        function getReadableMailText() {
            const activeBody = getActiveBodyElement();
            if (activeBody) {
                return KipSpeech.stripForSpeech(activeBody.textContent || "");
            }
            return KipSpeech.stripForSpeech(currentOriginalContent || "");
        }

        function updateReaderStopButton() {
            if (!readerStopBtn || !window.KipSpeech) return;
            readerStopBtn.hidden = !KipSpeech.isSpeaking();
        }

        if (readerSpeakBtn) {
            readerSpeakBtn.addEventListener("click", function () {
                if (!window.KipSpeech) {
                    window.alert("Sesli okuma yüklenemedi. Sayfayı yenileyin.");
                    return;
                }
                if (KipSpeech.isSpeaking()) {
                    KipSpeech.stopSpeaking();
                    updateReaderStopButton();
                    return;
                }
                const text = getReadableMailText();
                if (!text) return;
                KipSpeech.speak(text);
                updateReaderStopButton();
                window.setTimeout(updateReaderStopButton, 300);
            });
        }

        if (readerStopBtn) {
            readerStopBtn.addEventListener("click", function () {
                if (!window.KipSpeech) return;
                KipSpeech.stopSpeaking();
                updateReaderStopButton();
            });
        }

        bindAllMics();

        // Re-bind when panels open (in case nodes were added later)
        [aiReplyBtn, replyBtn, composeBtn, composeAiToggle].forEach(function (btn) {
            if (!btn) return;
            btn.addEventListener("click", function () {
                window.setTimeout(bindAllMics, 50);
            });
        });
    }

    const chatBubblePanel = document.getElementById("chat-bubble-panel");
    const chatBubbleFrame = document.getElementById("chat-bubble-frame");
    const chatBubbleFab = document.getElementById("chat-bubble-fab");
    const chatBubbleOpen = document.getElementById("chat-bubble-open");
    const chatBubbleClose = document.getElementById("chat-bubble-close");
    let chatBubbleLoaded = false;
    const CHAT_BUBBLE_POS_KEY = "kipgpt_chat_bubble_pos";
    let bubbleDragMoved = false;

    function clampBubblePosition(left, top, size) {
        const maxLeft = Math.max(8, window.innerWidth - size - 8);
        const maxTop = Math.max(8, window.innerHeight - size - 8);
        return {
            left: Math.min(Math.max(8, left), maxLeft),
            top: Math.min(Math.max(8, top), maxTop),
        };
    }

    function applyBubblePosition(left, top) {
        if (!chatBubbleFab) return;
        const size = chatBubbleFab.offsetWidth || 56;
        const pos = clampBubblePosition(left, top, size);
        chatBubbleFab.style.left = pos.left + "px";
        chatBubbleFab.style.top = pos.top + "px";
        chatBubbleFab.style.right = "auto";
        chatBubbleFab.style.bottom = "auto";
        positionChatPanel();
        return pos;
    }

    function saveBubblePosition(left, top) {
        try {
            localStorage.setItem(CHAT_BUBBLE_POS_KEY, JSON.stringify({ left: left, top: top }));
        } catch (e) {}
    }

    function restoreBubblePosition() {
        if (!chatBubbleFab) return;
        try {
            const raw = localStorage.getItem(CHAT_BUBBLE_POS_KEY);
            if (!raw) return;
            const saved = JSON.parse(raw);
            if (typeof saved.left === "number" && typeof saved.top === "number") {
                applyBubblePosition(saved.left, saved.top);
            }
        } catch (e) {}
    }

    function positionChatPanel() {
        if (!chatBubblePanel || !chatBubbleFab || chatBubblePanel.hidden) return;
        if (window.innerWidth <= 640) {
            chatBubblePanel.style.left = "0px";
            chatBubblePanel.style.right = "0px";
            chatBubblePanel.style.top = "auto";
            chatBubblePanel.style.bottom = "0px";
            return;
        }

        const fabRect = chatBubbleFab.getBoundingClientRect();
        const panelWidth = Math.min(420, window.innerWidth - 24);
        const panelHeight = Math.min(640, window.innerHeight - 24);
        let left = fabRect.right - panelWidth;
        let top = fabRect.top - panelHeight - 12;

        if (top < 8) {
            top = fabRect.bottom + 12;
        }
        if (left < 8) {
            left = 8;
        }
        if (left + panelWidth > window.innerWidth - 8) {
            left = window.innerWidth - panelWidth - 8;
        }
        if (top + panelHeight > window.innerHeight - 8) {
            top = Math.max(8, window.innerHeight - panelHeight - 8);
        }

        chatBubblePanel.style.left = left + "px";
        chatBubblePanel.style.top = top + "px";
        chatBubblePanel.style.right = "auto";
        chatBubblePanel.style.bottom = "auto";
        chatBubblePanel.style.width = panelWidth + "px";
        chatBubblePanel.style.height = panelHeight + "px";
    }

    function openChatBubble() {
        if (!chatBubblePanel) return;
        chatBubblePanel.hidden = false;
        if (chatBubbleFab) {
            chatBubbleFab.classList.add("is-open");
        }
        if (chatBubbleFrame && !chatBubbleLoaded) {
            chatBubbleFrame.src = "/chat?embed=1";
            chatBubbleLoaded = true;
        }
        positionChatPanel();
    }

    function closeChatBubble() {
        if (!chatBubblePanel) return;
        chatBubblePanel.hidden = true;
        if (chatBubbleFab) {
            chatBubbleFab.classList.remove("is-open");
        }
    }

    function toggleChatBubble() {
        if (!chatBubblePanel) return;
        if (chatBubblePanel.hidden) {
            openChatBubble();
        } else {
            closeChatBubble();
        }
    }

    function enableChatBubbleDrag() {
        if (!chatBubbleFab) return;

        let dragging = false;
        let startX = 0;
        let startY = 0;
        let originLeft = 0;
        let originTop = 0;

        function onPointerDown(e) {
            if (e.button !== undefined && e.button !== 0) return;
            dragging = true;
            bubbleDragMoved = false;
            chatBubbleFab.classList.add("is-dragging");
            const rect = chatBubbleFab.getBoundingClientRect();
            originLeft = rect.left;
            originTop = rect.top;
            startX = e.clientX;
            startY = e.clientY;
            chatBubbleFab.setPointerCapture?.(e.pointerId);
            e.preventDefault();
        }

        function onPointerMove(e) {
            if (!dragging) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
                bubbleDragMoved = true;
            }
            applyBubblePosition(originLeft + dx, originTop + dy);
        }

        function onPointerUp(e) {
            if (!dragging) return;
            dragging = false;
            chatBubbleFab.classList.remove("is-dragging");
            try {
                chatBubbleFab.releasePointerCapture?.(e.pointerId);
            } catch (err) {}
            const rect = chatBubbleFab.getBoundingClientRect();
            const pos = applyBubblePosition(rect.left, rect.top);
            saveBubblePosition(pos.left, pos.top);
        }

        chatBubbleFab.addEventListener("pointerdown", onPointerDown);
        window.addEventListener("pointermove", onPointerMove);
        window.addEventListener("pointerup", onPointerUp);
        window.addEventListener("pointercancel", onPointerUp);

        chatBubbleFab.addEventListener("click", function (e) {
            if (bubbleDragMoved) {
                e.preventDefault();
                e.stopPropagation();
                bubbleDragMoved = false;
                return;
            }
            toggleChatBubble();
        });

        window.addEventListener("resize", function () {
            const rect = chatBubbleFab.getBoundingClientRect();
            const pos = applyBubblePosition(rect.left, rect.top);
            saveBubblePosition(pos.left, pos.top);
            positionChatPanel();
        });
    }

    restoreBubblePosition();
    enableChatBubbleDrag();

    if (chatBubbleOpen) {
        chatBubbleOpen.addEventListener("click", openChatBubble);
    }
    if (chatBubbleClose) {
        chatBubbleClose.addEventListener("click", closeChatBubble);
    }

})();
