(function (global) {
    const SpeechRecognition = global.SpeechRecognition || global.webkitSpeechRecognition;
    const synth = global.speechSynthesis;

    let recognition = null;
    let listening = false;
    let activeMicButton = null;

    const ERROR_MESSAGES = {
        "not-allowed": "Mikrofon izni verilmedi. Tarayıcı adres çubuğundan mikrofona izin verin.",
        "service-not-allowed": "Mikrofon izni verilmedi. Tarayıcı ayarlarından izin verin.",
        "audio-capture": "Mikrofona erişilemiyor. Cihazda mikrofon olduğundan emin olun.",
        "network": "Ses tanıma için ağ bağlantısı gerekli.",
        "no-speech": "Konuşma algılanamadı. Tekrar deneyin.",
        "aborted": "Ses tanıma iptal edildi.",
        "not-supported": "Tarayıcınız sesli girişi desteklemiyor. Chrome kullanmayı deneyin.",
        "insecure": "Mikrofon yalnızca HTTPS veya localhost üzerinde çalışır.",
    };

    function isSecureEnough() {
        if (global.isSecureContext) return true;
        const host = (global.location && global.location.hostname) || "";
        return host === "localhost" || host === "127.0.0.1";
    }

    function isSpeechSupported() {
        return !!SpeechRecognition && isSecureEnough();
    }

    function isSpeakSupported() {
        return !!synth;
    }

    function stripForSpeech(text) {
        return String(text || "")
            .replace(/<[^>]+>/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    function setMicButtonState(button, active) {
        if (!button) return;
        button.classList.toggle("is-listening", active);
        button.setAttribute("aria-pressed", active ? "true" : "false");
    }

    function friendlyError(codeOrMessage) {
        const key = String(codeOrMessage || "").toLowerCase();
        return ERROR_MESSAGES[key] || ERROR_MESSAGES["not-supported"].replace(
            "desteklemiyor",
            "şu an kullanılamıyor (" + codeOrMessage + ")"
        );
    }

    function speak(text, options) {
        if (!synth || !text) return false;
        stopSpeaking();
        const utter = new SpeechSynthesisUtterance(stripForSpeech(text));
        utter.lang = (options && options.lang) || "tr-TR";
        utter.rate = (options && options.rate) || 1;
        synth.speak(utter);
        return true;
    }

    function stopSpeaking() {
        if (synth) synth.cancel();
    }

    function isSpeaking() {
        return !!synth && synth.speaking;
    }

    function stopListening() {
        if (recognition) {
            try {
                recognition.stop();
            } catch (_err) {
                /* ignore */
            }
        }
        listening = false;
        setMicButtonState(activeMicButton, false);
        activeMicButton = null;
    }

    function startListening(onResult, onError, onEnd, micButton) {
        if (!isSecureEnough()) {
            if (onError) onError(ERROR_MESSAGES.insecure);
            return false;
        }
        if (!SpeechRecognition) {
            if (onError) onError(ERROR_MESSAGES["not-supported"]);
            return false;
        }

        if (listening) {
            stopListening();
            return false;
        }

        recognition = new SpeechRecognition();
        recognition.lang = "tr-TR";
        recognition.interimResults = true;
        recognition.continuous = false;
        recognition.maxAlternatives = 1;
        activeMicButton = micButton || null;
        setMicButtonState(activeMicButton, true);
        listening = true;

        let finalTranscript = "";

        recognition.onresult = function (event) {
            let interim = "";
            for (let i = event.resultIndex; i < event.results.length; i += 1) {
                const piece = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += piece;
                } else {
                    interim += piece;
                }
            }
            if (onResult && (finalTranscript || interim)) {
                onResult((finalTranscript || interim).trim(), {
                    interim: !finalTranscript && !!interim,
                    final: !!finalTranscript,
                });
            }
        };

        recognition.onerror = function (event) {
            if (onError) onError(friendlyError(event.error || "Ses tanıma hatası"));
        };

        recognition.onend = function () {
            listening = false;
            setMicButtonState(activeMicButton, false);
            activeMicButton = null;
            if (onEnd) onEnd();
        };

        try {
            recognition.start();
            return true;
        } catch (err) {
            listening = false;
            setMicButtonState(activeMicButton, false);
            activeMicButton = null;
            if (onError) onError(friendlyError(err.message || "Mikrofon başlatılamadı"));
            return false;
        }
    }

    function bindMicToField(button, field, options) {
        if (!button || !field || button.dataset.kipMicBound === "1") return;
        button.dataset.kipMicBound = "1";

        button.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();

            if (!isSpeechSupported()) {
                window.alert(
                    isSecureEnough()
                        ? ERROR_MESSAGES["not-supported"]
                        : ERROR_MESSAGES.insecure
                );
                return;
            }

            if (listening && activeMicButton === button) {
                stopListening();
                return;
            }

            const append = !options || options.append !== false;
            const baseline = (field.value || "").trim();

            startListening(
                function (transcript, meta) {
                    const text = (transcript || "").trim();
                    if (!text) return;
                    if (meta && meta.interim) {
                        field.value = append && baseline
                            ? baseline + " " + text
                            : text;
                    } else {
                        field.value = append && baseline
                            ? baseline + " " + text
                            : text;
                    }
                    field.dispatchEvent(new Event("input", { bubbles: true }));
                    field.focus();
                },
                function (message) {
                    if (options && options.onError) {
                        options.onError(message);
                    } else {
                        window.alert(message);
                    }
                },
                null,
                button
            );
        });
    }

    function createSpeakButton(textProvider) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "speech-speak-btn";
        button.title = "Dinle";
        button.innerHTML = '<span class="material-icons-outlined">volume_up</span>';
        button.addEventListener("click", function () {
            if (isSpeaking()) {
                stopSpeaking();
                return;
            }
            const text = typeof textProvider === "function" ? textProvider() : textProvider;
            speak(text);
        });
        return button;
    }

    global.KipSpeech = {
        speak: speak,
        stopSpeaking: stopSpeaking,
        isSpeaking: isSpeaking,
        startListening: startListening,
        stopListening: stopListening,
        isListening: function () { return listening; },
        isSpeechSupported: isSpeechSupported,
        isSpeakSupported: isSpeakSupported,
        stripForSpeech: stripForSpeech,
        bindMicToField: bindMicToField,
        createSpeakButton: createSpeakButton,
    };
})(window);
