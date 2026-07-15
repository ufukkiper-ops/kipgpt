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
            tr: "Türkçe'ye çevir",
            en: "Translate to English",
            de: "Auf Deutsch übersetzen",
        };

        translateButtons.forEach(function (btn) {
            const lang = btn.dataset.lang;
            const isActive = lang === currentTranslationLang;
            btn.classList.toggle("active", isActive);
            btn.disabled = readerBody?.classList.contains("is-translating");
            btn.title = isActive
                ? "Orijinal metni göster"
                : (defaultTitles[lang] || "Çevir");
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
        bodyEl.textContent = "Çeviri hazırlanıyor...";

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
                readerFrom.textContent = (mail.sender_display || mail.sender || "") +
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

            if (!input.files.length) {
                clearAttachmentPreview(input, previewEl);
                return;
            }

            showAttachPreview(input.files[0], previewEl, input);
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

})();
