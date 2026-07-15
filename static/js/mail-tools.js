(function () {
    const fileLibrary = JSON.parse(
        document.getElementById("file-library-data")?.textContent || "[]"
    );
    let libraryCache = Array.isArray(fileLibrary) ? fileLibrary.slice() : [];

    function openOverlay(overlay) {
        if (!overlay) return;
        overlay.hidden = false;
        document.body.classList.add("dialog-open");
    }

    function closeOverlay(overlay) {
        if (!overlay) return;
        overlay.hidden = true;
        if (!document.querySelector(".mail-dialog-overlay:not([hidden])")) {
            document.body.classList.remove("dialog-open");
        }
    }

    function formatWhen(value) {
        if (!value) return "Tarih yok";
        try {
            const date = new Date(value);
            if (Number.isNaN(date.getTime())) return value;
            return date.toLocaleString("tr-TR", {
                day: "2-digit",
                month: "short",
                hour: "2-digit",
                minute: "2-digit",
            });
        } catch (_err) {
            return value;
        }
    }

    function formatSize(bytes) {
        const size = Number(bytes) or 0;
        if (size < 1024) return size + " B";
        if (size < 1024 * 1024) return Math.round(size / 1024) + " KB";
        return (size / (1024 * 1024)).toFixed(1) + " MB";
    }

    /* -------- Calendar -------- */
    const calendarOverlay = document.getElementById("calendar-overlay");
    const calendarOpenBtn = document.getElementById("calendar-open-btn");
    const calendarClose = document.getElementById("calendar-close");
    const calendarList = document.getElementById("calendar-list");
    const calendarForm = document.getElementById("calendar-create-form");

    async function loadCalendar() {
        if (!calendarList) return;
        calendarList.innerHTML = "<p class='tool-empty'>Yükleniyor...</p>";
        try {
            const res = await fetch("/api/calendar/events");
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Takvim yüklenemedi");
            renderCalendar(data.events || []);
        } catch (err) {
            calendarList.innerHTML = `<p class="tool-empty">${err.message}</p>`;
        }
    }

    function renderCalendar(events) {
        if (!events.length) {
            calendarList.innerHTML = "<p class='tool-empty'>Henüz etkinlik yok.</p>";
            return;
        }
        calendarList.innerHTML = events.map(function (event) {
            const due = event.reminder_at || event.start;
            return (
                `<div class="tool-item${event.done ? " is-done" : ""}" data-id="${event.id}">` +
                `<div class="tool-item-main">` +
                `<strong>${escapeHtml(event.title || "")}</strong>` +
                `<span>${escapeHtml(formatWhen(due))}</span>` +
                (event.description ? `<small>${escapeHtml(event.description)}</small>` : "") +
                `</div>` +
                `<div class="tool-item-actions">` +
                `<button type="button" class="icon-btn cal-toggle" title="Tamamla">` +
                `<span class="material-icons-outlined">${event.done ? "undo" : "check"}</span></button>` +
                `<button type="button" class="icon-btn cal-delete" title="Sil">` +
                `<span class="material-icons-outlined">delete</span></button>` +
                `</div></div>`
            );
        }).join("");
    }

    if (calendarOpenBtn) {
        calendarOpenBtn.addEventListener("click", function () {
            openOverlay(calendarOverlay);
            loadCalendar();
        });
    }
    if (calendarClose) {
        calendarClose.addEventListener("click", function () {
            closeOverlay(calendarOverlay);
        });
    }
    if (calendarOverlay) {
        calendarOverlay.addEventListener("click", function (e) {
            if (e.target === calendarOverlay) closeOverlay(calendarOverlay);
        });
    }
    if (calendarForm) {
        calendarForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            const title = document.getElementById("calendar-title")?.value || "";
            const start = document.getElementById("calendar-start")?.value || "";
            const description = document.getElementById("calendar-desc")?.value || "";
            try {
                const res = await fetch("/api/calendar/events", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        title: title,
                        start: start ? new Date(start).toISOString() : null,
                        reminder_at: start ? new Date(start).toISOString() : null,
                        description: description,
                    }),
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || "Eklenemedi");
                calendarForm.reset();
                loadCalendar();
            } catch (err) {
                alert(err.message);
            }
        });
    }
    if (calendarList) {
        calendarList.addEventListener("click", async function (e) {
            const item = e.target.closest(".tool-item");
            if (!item) return;
            const id = item.dataset.id;
            if (e.target.closest(".cal-delete")) {
                if (!confirm("Bu etkinliği silmek istiyor musunuz?")) return;
                await fetch("/api/calendar/events/" + id, { method: "DELETE" });
                loadCalendar();
                return;
            }
            if (e.target.closest(".cal-toggle")) {
                const done = !item.classList.contains("is-done");
                await fetch("/api/calendar/events/" + id, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ done: done }),
                });
                loadCalendar();
            }
        });
    }

    /* -------- File library -------- */
    const filesOverlay = document.getElementById("files-overlay");
    const filesOpenBtn = document.getElementById("files-open-btn");
    const filesClose = document.getElementById("files-close");
    const filesList = document.getElementById("files-list");
    const filesForm = document.getElementById("files-upload-form");
    const composeLibrarySelect = document.getElementById("compose-library-select");
    const composeLibraryIds = document.getElementById("compose-library-ids");
    const composeLibraryChips = document.getElementById("compose-library-chips");
    const composeHtmlBody = document.getElementById("compose-html-body");

    function escapeHtml(text) {
        return String(text || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function renderFiles(files) {
        libraryCache = files.slice();
        refreshComposeLibrarySelect();
        if (!filesList) return;
        if (!files.length) {
            filesList.innerHTML = "<p class='tool-empty'>Henüz dosya yok.</p>";
            return;
        }
        filesList.innerHTML = files.map(function (file) {
            return (
                `<div class="tool-item" data-id="${file.id}">` +
                `<div class="tool-item-main">` +
                `<strong>${escapeHtml(file.filename)}</strong>` +
                `<span>${formatSize(file.size)}${file.note ? " · " + escapeHtml(file.note) : ""}</span>` +
                `</div>` +
                `<div class="tool-item-actions">` +
                `<a class="icon-btn" href="/api/files/${file.id}/download" title="İndir">` +
                `<span class="material-icons-outlined">download</span></a>` +
                `<button type="button" class="icon-btn file-delete" title="Sil">` +
                `<span class="material-icons-outlined">delete</span></button>` +
                `</div></div>`
            );
        }).join("");
    }

    function refreshComposeLibrarySelect() {
        if (!composeLibrarySelect) return;
        const selected = new Set(
            Array.from(composeLibrarySelect.selectedOptions || []).map(function (o) {
                return o.value;
            })
        );
        composeLibrarySelect.innerHTML = libraryCache.map(function (file) {
            const isSelected = selected.has(file.id) ? " selected" : "";
            return `<option value="${file.id}"${isSelected}>${escapeHtml(file.filename)}</option>`;
        }).join("");
        syncComposeLibraryHidden();
    }

    function syncComposeLibraryHidden() {
        if (!composeLibraryIds || !composeLibrarySelect) return;
        const ids = Array.from(composeLibrarySelect.selectedOptions || []).map(function (o) {
            return o.value;
        });
        composeLibraryIds.innerHTML = ids.map(function (id) {
            return `<input type="hidden" name="library_file_ids" value="${id}">`;
        }).join("");
        if (composeLibraryChips) {
            composeLibraryChips.innerHTML = ids.map(function (id) {
                const file = libraryCache.find(function (f) { return f.id === id; });
                const name = file ? file.filename : id;
                return `<span class="library-chip">${escapeHtml(name)}</span>`;
            }).join("");
        }
    }

    window.KipMailTools = {
        setComposeLibraryAttachments: function (attachments, htmlBody) {
            if (composeHtmlBody && typeof htmlBody === "string") {
                composeHtmlBody.value = htmlBody;
            }
            if (!composeLibrarySelect || !attachments) return;
            const ids = attachments.map(function (a) { return a.id; });
            Array.from(composeLibrarySelect.options).forEach(function (opt) {
                opt.selected = ids.indexOf(opt.value) !== -1;
            });
            syncComposeLibraryHidden();
            if (composeLibraryChips && attachments.length) {
                composeLibraryChips.innerHTML = attachments.map(function (a) {
                    return `<span class="library-chip">${escapeHtml(a.filename)} <em>AI</em></span>`;
                }).join("");
            }
        },
        getLibraryCache: function () { return libraryCache.slice(); },
    };

    async function loadFiles() {
        if (!filesList) return;
        filesList.innerHTML = "<p class='tool-empty'>Yükleniyor...</p>";
        try {
            const res = await fetch("/api/files");
            const data = await res.json();
            if (!res.ok) throw new Error(data.error || "Dosyalar yüklenemedi");
            renderFiles(data.files || []);
        } catch (err) {
            filesList.innerHTML = `<p class="tool-empty">${err.message}</p>`;
        }
    }

    if (filesOpenBtn) {
        filesOpenBtn.addEventListener("click", function () {
            openOverlay(filesOverlay);
            loadFiles();
        });
    }
    if (filesClose) {
        filesClose.addEventListener("click", function () {
            closeOverlay(filesOverlay);
        });
    }
    if (filesOverlay) {
        filesOverlay.addEventListener("click", function (e) {
            if (e.target === filesOverlay) closeOverlay(filesOverlay);
        });
    }
    if (composeLibrarySelect) {
        composeLibrarySelect.addEventListener("change", syncComposeLibraryHidden);
    }
    if (filesForm) {
        filesForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            const input = document.getElementById("files-upload-input");
            const note = document.getElementById("files-upload-note")?.value || "";
            if (!input || !input.files || !input.files[0]) {
                alert("Dosya seçin.");
                return;
            }
            const formData = new FormData();
            formData.append("file", input.files[0]);
            formData.append("note", note);
            try {
                const res = await fetch("/api/files", { method: "POST", body: formData });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || "Yükleme başarısız");
                filesForm.reset();
                loadFiles();
            } catch (err) {
                alert(err.message);
            }
        });
    }
    if (filesList) {
        filesList.addEventListener("click", async function (e) {
            const item = e.target.closest(".tool-item");
            if (!item || !e.target.closest(".file-delete")) return;
            if (!confirm("Dosyayı kütüphaneden silmek istiyor musunuz?")) return;
            await fetch("/api/files/" + item.dataset.id, { method: "DELETE" });
            loadFiles();
        });
    }

    /* -------- AI Summary -------- */
    const summaryBtn = document.getElementById("ai-summary-btn");
    const summaryBox = document.getElementById("mail-ai-summary");

    function importanceLabel(value) {
        const map = { low: "Düşük", medium: "Orta", high: "Yüksek" };
        return map[(value || "").toLowerCase()] || value || "-";
    }

    function renderSummary(summary, remindersCreated) {
        if (!summaryBox || !summary) return;
        const actions = (summary.action_items || []).map(function (item) {
            return `<li>${escapeHtml(item)}</li>`;
        }).join("");
        const reminderNote = remindersCreated && remindersCreated.length
            ? `<p class="summary-reminders">${remindersCreated.length} hatırlatıcı takvime eklendi.</p>`
            : "";
        summaryBox.innerHTML =
            `<div class="summary-card">` +
            `<div class="summary-head"><span class="material-icons-outlined">auto_awesome</span><strong>AI Özet & Yorum</strong></div>` +
            `<p>${escapeHtml(summary.summary || "")}</p>` +
            `<p class="summary-interp">${escapeHtml(summary.interpretation || "")}</p>` +
            `<div class="summary-meta">Önem: ${escapeHtml(importanceLabel(summary.importance))} · Aciliyet: ${escapeHtml(importanceLabel(summary.urgency))}</div>` +
            (actions ? `<ul class="summary-actions">${actions}</ul>` : "") +
            (summary.suggested_reply
                ? `<div class="summary-reply"><span>Önerilen yanıt</span><p>${escapeHtml(summary.suggested_reply)}</p></div>`
                : "") +
            reminderNote +
            `<div class="summary-actions-row">` +
            `<button type="button" class="action-btn" id="summary-add-reminders">Hatırlatıcı oluştur</button>` +
            `<button type="button" class="action-btn" id="summary-hide">Gizle</button>` +
            `</div></div>`;
        summaryBox.hidden = false;
        summaryBox.dataset.raw = JSON.stringify(summary);
    }

    if (summaryBtn) {
        summaryBtn.addEventListener("click", async function () {
            const mailId = document.body.dataset.activeMailId || "";
            const readerBody = document.getElementById("reader-body");
            const readerFrom = document.getElementById("reader-from");
            const readerSubject = document.getElementById("reader-subject");
            const content = (readerBody?.innerText || "").trim();
            if (!content) {
                alert("Önce bir mail seçin.");
                return;
            }
            summaryBtn.disabled = true;
            if (summaryBox) {
                summaryBox.hidden = false;
                summaryBox.innerHTML = "<div class='summary-card'>Özet hazırlanıyor...</div>";
            }
            try {
                const res = await fetch("/mail/ai-summary", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        mail_id: mailId,
                        folder: document.body.dataset.mailFolder || "inbox",
                        account: document.body.dataset.mailAccount || "",
                        sender: readerFrom?.textContent || "",
                        subject: readerSubject?.textContent || "",
                        content: content,
                        create_reminders: false,
                    }),
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || "Özet alınamadı");
                renderSummary(data.summary, data.reminders_created || []);
            } catch (err) {
                if (summaryBox) {
                    summaryBox.innerHTML = `<div class="summary-card">${escapeHtml(err.message)}</div>`;
                } else {
                    alert(err.message);
                }
            } finally {
                summaryBtn.disabled = false;
            }
        });
    }

    if (summaryBox) {
        summaryBox.addEventListener("click", async function (e) {
            if (e.target.id === "summary-hide") {
                summaryBox.hidden = true;
                return;
            }
            if (e.target.id === "summary-add-reminders") {
                let summary = null;
                try {
                    summary = JSON.parse(summaryBox.dataset.raw || "null");
                } catch (_err) {}
                if (!summary) return;
                const mailId = document.body.dataset.activeMailId || "";
                try {
                    const res = await fetch("/mail/ai-summary", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            mail_id: mailId,
                            sender: document.getElementById("reader-from")?.textContent || "",
                            subject: document.getElementById("reader-subject")?.textContent || "",
                            content: document.getElementById("reader-body")?.innerText || "",
                            create_reminders: true,
                        }),
                    });
                    const data = await res.json();
                    if (!res.ok) throw new Error(data.error || "Hatırlatıcı eklenemedi");
                    renderSummary(data.summary, data.reminders_created || []);
                    alert((data.reminders_created || []).length + " hatırlatıcı eklendi.");
                } catch (err) {
                    alert(err.message);
                }
            }
        });
    }

    // Hide summary when switching mails
    document.addEventListener("kipgpt:mail-opened", function () {
        if (summaryBox) {
            summaryBox.hidden = true;
            summaryBox.innerHTML = "";
        }
    });

    // Hydrate AI draft HTML body from JSON blob
    const aiHtmlField = document.getElementById("ai-html-body");
    const aiHtmlData = document.getElementById("ai-html-body-data");
    if (aiHtmlField && aiHtmlData) {
        try {
            aiHtmlField.value = JSON.parse(aiHtmlData.textContent || '""');
        } catch (_err) {
            aiHtmlField.value = "";
        }
    }
})();
