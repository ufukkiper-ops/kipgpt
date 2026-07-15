package com.kipgpt.app.ui

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import android.util.Base64
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Summarize
import androidx.compose.material.icons.filled.VolumeUp
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Translate
import androidx.compose.material.icons.outlined.StarOutline
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.AttachmentSaver
import com.kipgpt.app.data.LibraryAttachmentRef
import com.kipgpt.app.data.MailAiComposeRequest
import com.kipgpt.app.data.MailAiReplyRequest
import com.kipgpt.app.data.MailAttachment
import com.kipgpt.app.data.MailFolder
import com.kipgpt.app.data.MailItem
import com.kipgpt.app.data.MailSendNewRequest
import com.kipgpt.app.data.MailSendReplyRequest
import com.kipgpt.app.data.MailSummaryData
import com.kipgpt.app.data.MailSummaryRequest
import com.kipgpt.app.data.OutgoingAttachmentPayload
import com.kipgpt.app.data.SpeechHelper
import com.kipgpt.app.data.TranslateRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MailScreen(
    apiClient: ApiClient,
    modifier: Modifier = Modifier,
) {
    val folders = remember { mutableStateListOf<MailFolder>() }
    val mails = remember { mutableStateListOf<MailItem>() }
    val selectedFolder = remember { mutableStateOf("inbox") }
    val selectedMail = remember { mutableStateOf<MailItem?>(null) }
    val composing = remember { mutableStateOf(false) }
    val search = remember { mutableStateOf("") }
    val account = remember { mutableStateOf("") }
    val loading = remember { mutableStateOf(false) }
    val loadError = remember { mutableStateOf<String?>(null) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    suspend fun loadMailsNow() {
        loading.value = true
        loadError.value = null
        try {
            val response = apiClient.api.mails(
                folder = selectedFolder.value,
                search = search.value.trim().ifBlank { null },
            )
            mails.clear()
            mails.addAll(response.mails)
            account.value = response.account
        } catch (e: Exception) {
            val msg = e.message ?: "Mailler yüklenemedi"
            loadError.value = msg
            snackbar.showSnackbar(msg)
        } finally {
            loading.value = false
        }
    }

    fun loadMails() {
        scope.launch { loadMailsNow() }
    }

    LaunchedEffect(Unit) {
        try {
            folders.clear()
            folders.addAll(apiClient.api.folders().folders)
        } catch (_: Exception) {
        }
    }

    LaunchedEffect(selectedFolder.value) {
        if (selectedMail.value == null && !composing.value) {
            loadMailsNow()
        }
    }

    if (composing.value) {
        ComposeMailScreen(
            apiClient = apiClient,
            onBack = { composing.value = false },
            onSent = {
                composing.value = false
                loadMails()
            },
            modifier = modifier,
        )
        return
    }

    if (selectedMail.value != null) {
        MailDetailScreen(
            mail = selectedMail.value!!,
            folder = selectedFolder.value,
            apiClient = apiClient,
            onBack = { selectedMail.value = null },
            modifier = modifier,
        )
        return
    }

    Scaffold(
        modifier = modifier,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Mailler")
                        if (account.value.isNotBlank()) {
                            Text(
                                account.value,
                                style = MaterialTheme.typography.bodySmall,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                    }
                },
                actions = {
                    IconButton(onClick = { loadMails() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Yenile")
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { composing.value = true }) {
                Icon(Icons.Default.Edit, contentDescription = "Yeni mail")
            }
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            LazyRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(folders, key = { it.id }) { folder ->
                    FilterChip(
                        selected = selectedFolder.value == folder.id,
                        onClick = { selectedFolder.value = folder.id },
                        label = { Text(folder.label) },
                    )
                }
            }

            OutlinedTextField(
                value = search.value,
                onValueChange = { search.value = it },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp),
                placeholder = { Text("Mail ara...") },
                singleLine = true,
                trailingIcon = {
                    IconButton(onClick = { loadMails() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Ara")
                    }
                },
            )

            Spacer(Modifier.height(8.dp))

            PullToRefreshBox(
                isRefreshing = loading.value,
                onRefresh = { loadMails() },
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
            ) {
                when {
                    loading.value && mails.isEmpty() -> {
                        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                CircularProgressIndicator()
                                if (loadError.value != null) {
                                    Spacer(Modifier.height(12.dp))
                                    Text(loadError.value!!, color = MaterialTheme.colorScheme.error)
                                }
                            }
                        }
                    }
                    loadError.value != null && mails.isEmpty() -> {
                        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text(loadError.value!!, color = MaterialTheme.colorScheme.error)
                                Spacer(Modifier.height(12.dp))
                                OutlinedButton(onClick = { loadMails() }) {
                                    Text("Tekrar dene")
                                }
                            }
                        }
                    }
                    mails.isEmpty() -> {
                        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Text(
                                "Bu klasörde mail yok",
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                    else -> {
                        LazyColumn(modifier = Modifier.fillMaxSize()) {
                            items(mails, key = { it.id }) { mail ->
                                MailRow(mail) { selectedMail.value = mail }
                                HorizontalDivider()
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun MailRow(mail: MailItem, onClick: () -> Unit) {
    val senderName = formatSenderName(mail)
    val senderEmail = formatSenderEmail(mail)
    val senderInitial = senderName.firstOrNull()?.uppercaseChar()?.toString() ?: "?"

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.Top,
    ) {
        Box(
            modifier = Modifier
                .padding(top = 2.dp, end = 12.dp)
                .size(42.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primary),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                senderInitial,
                color = Color.White,
                fontWeight = FontWeight.SemiBold,
                style = MaterialTheme.typography.titleMedium,
            )
        }

        Column(Modifier.weight(1f)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        senderName,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        style = MaterialTheme.typography.titleSmall,
                    )
                    if (senderEmail.isNotBlank() && senderEmail != senderName) {
                        Text(
                            senderEmail,
                            style = MaterialTheme.typography.bodySmall,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                if (mail.starred) {
                    Icon(
                        Icons.Default.Star,
                        contentDescription = "Yıldızlı",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(horizontal = 6.dp),
                    )
                }
                Text(mail.date, style = MaterialTheme.typography.bodySmall)
            }

            Spacer(Modifier.height(4.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    mail.subject.ifBlank { "(Konu yok)" },
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f, fill = false),
                )
                if (mail.thread_count > 1) {
                    Text(
                        "${mail.thread_count} mesaj",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(start = 6.dp),
                    )
                }
            }

            Text(
                mail.content.replace("\n", " ").take(120),
                style = MaterialTheme.typography.bodySmall,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            if (mail.attachments.isNotEmpty()) {
                Row(
                    modifier = Modifier.padding(top = 4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        Icons.Default.AttachFile,
                        contentDescription = null,
                        modifier = Modifier.padding(end = 4.dp),
                        tint = MaterialTheme.colorScheme.primary,
                    )
                    Text(
                        "${mail.attachments.size} ek",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MailDetailScreen(
    mail: MailItem,
    folder: String,
    apiClient: ApiClient,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val mailState = remember { mutableStateOf(mail) }
    val content = remember { mutableStateOf(mail.content) }
    val translatedLang = remember { mutableStateOf<String?>(null) }
    val selectedLang = remember { mutableStateOf("tr") }
    val langMenuOpen = remember { mutableStateOf(false) }
    val languages = remember {
        mutableStateOf(
            listOf(
                "tr" to "Türkçe",
                "en" to "İngilizce",
                "de" to "Almanca",
                "fr" to "Fransızca",
                "es" to "İspanyolca",
                "it" to "İtalyanca",
                "pt" to "Portekizce",
                "ru" to "Rusça",
                "ar" to "Arapça",
                "zh" to "Çince",
                "ja" to "Japonca",
                "ko" to "Korece",
                "nl" to "Felemenkçe",
                "pl" to "Lehçe",
                "uk" to "Ukraynaca",
                "hi" to "Hintçe",
                "az" to "Azerbaycan Türkçesi",
            )
        )
    }
    val loading = remember { mutableStateOf(false) }
    val detailLoading = remember { mutableStateOf(true) }
    val downloadingIndex = remember { mutableStateOf<Int?>(null) }
    val speaking = remember { mutableStateOf(false) }
    val showAiPanel = remember { mutableStateOf(false) }
    val aiInstruction = remember { mutableStateOf("") }
    val aiDraft = remember { mutableStateOf("") }
    val reviseNote = remember { mutableStateOf("") }
    val aiLoading = remember { mutableStateOf(false) }
    val sendingReply = remember { mutableStateOf(false) }
    val listeningInstruction = remember { mutableStateOf(false) }
    val listeningRevise = remember { mutableStateOf(false) }
    val pendingVoiceTarget = remember { mutableStateOf<String?>(null) }
    val htmlBody = remember { mutableStateOf("") }
    val libraryAttachments = remember { mutableStateOf<List<LibraryAttachmentRef>>(emptyList()) }
    val summary = remember { mutableStateOf<MailSummaryData?>(null) }
    val summaryLoading = remember { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val speechHelper = remember { SpeechHelper(context) }

    fun startVoiceInputFor(
        target: String,
        skipPermissionCheck: Boolean = false,
        launchPermission: (String) -> Unit = {},
    ) {
        if (!speechHelper.isListenAvailable()) {
            scope.launch {
                snackbar.showSnackbar("Ses tanıma yok. Google uygulamasını güncelleyin.")
            }
            return
        }
        if (!skipPermissionCheck &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            pendingVoiceTarget.value = target
            launchPermission(Manifest.permission.RECORD_AUDIO)
            return
        }

        val setListening = { active: Boolean ->
            when (target) {
                "instruction" -> listeningInstruction.value = active
                "revise" -> listeningRevise.value = active
            }
        }
        val appendText = { transcript: String ->
            when (target) {
                "instruction" -> {
                    aiInstruction.value = if (aiInstruction.value.isBlank()) {
                        transcript
                    } else {
                        "${aiInstruction.value} $transcript"
                    }
                }
                "revise" -> {
                    reviseNote.value = if (reviseNote.value.isBlank()) {
                        transcript
                    } else {
                        "${reviseNote.value} $transcript"
                    }
                }
            }
        }

        setListening(true)
        val started = speechHelper.startListening(
            onResult = appendText,
            onError = { message -> scope.launch { snackbar.showSnackbar(message) } },
            onEnd = { setListening(false) },
        )
        if (!started) {
            setListening(false)
        }
    }

    val startVoiceUpdated = rememberUpdatedState<(String, Boolean) -> Unit> { target, skip ->
        startVoiceInputFor(target, skipPermissionCheck = skip)
    }

    val micPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        val target = pendingVoiceTarget.value
        pendingVoiceTarget.value = null
        if (granted && target != null) {
            startVoiceUpdated.value(target, true)
        } else if (!granted) {
            scope.launch { snackbar.showSnackbar("Mikrofon izni gerekli") }
        }
    }

    fun requestVoiceInput(target: String) {
        startVoiceInputFor(
            target = target,
            skipPermissionCheck = false,
            launchPermission = { perm -> micPermissionLauncher.launch(perm) },
        )
    }

    LaunchedEffect(mail.id, folder) {
        detailLoading.value = true
        try {
            val full = apiClient.api.mailDetail(mail.id, folder)
            mailState.value = full
            content.value = full.content
            translatedLang.value = null
            summary.value = null
            htmlBody.value = ""
            libraryAttachments.value = emptyList()
        } catch (e: Exception) {
            snackbar.showSnackbar(e.message ?: "Mail yüklenemedi")
        } finally {
            detailLoading.value = false
        }
    }

    LaunchedEffect(Unit) {
        try {
            val response = apiClient.api.mailLanguages()
            if (response.languages.isNotEmpty()) {
                languages.value = response.languages.map { it.code to it.label }
                if (languages.value.none { it.first == selectedLang.value }) {
                    selectedLang.value = languages.value.first().first
                }
            }
        } catch (_: Exception) {
            // keep fallback language list
        }
    }

    DisposableEffect(speechHelper) {
        onDispose { speechHelper.shutdown() }
    }

    fun downloadAttachment(att: MailAttachment) {
        scope.launch {
            downloadingIndex.value = att.index
            try {
                val savedName = withContext(Dispatchers.IO) {
                    val body = apiClient.api.downloadAttachment(
                        mailId = mailState.value.id,
                        index = att.index,
                        folder = folder,
                    )
                    body.use { response ->
                        val bytes = response.bytes()
                        AttachmentSaver.saveToDownloads(
                            context = context,
                            filename = att.filename,
                            bytes = bytes,
                            mime = att.mime,
                        )
                    }
                }
                snackbar.showSnackbar("İndirildi: $savedName")
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Ek indirilemedi")
            } finally {
                downloadingIndex.value = null
            }
        }
    }

    fun translate(lang: String) {
        if (translatedLang.value == lang) {
            content.value = mailState.value.content
            translatedLang.value = null
            return
        }
        scope.launch {
            loading.value = true
            try {
                val response = apiClient.api.translate(
                    TranslateRequest(mailState.value.content, lang),
                )
                content.value = response.translated
                translatedLang.value = lang
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Çeviri hatası")
            } finally {
                loading.value = false
            }
        }
    }

    fun generateAiReply(revise: Boolean = false) {
        scope.launch {
            aiLoading.value = true
            try {
                val detail = mailState.value
                val response = apiClient.api.generateMailAiReply(
                    MailAiReplyRequest(
                        mail_id = detail.id,
                        folder = folder,
                        sender = detail.sender,
                        subject = detail.subject,
                        content = detail.content,
                        user_instruction = if (revise) "" else aiInstruction.value.trim(),
                        current_draft = if (revise) aiDraft.value else "",
                        revize_notu = if (revise) reviseNote.value.trim() else "",
                    ),
                )
                aiDraft.value = response.draft
                htmlBody.value = response.html_body
                libraryAttachments.value = response.library_attachments
                reviseNote.value = ""
                if (response.library_attachments.isNotEmpty()) {
                    snackbar.showSnackbar(
                        "Kütüphane eki: " + response.library_attachments.joinToString { it.filename },
                    )
                }
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "AI yanıt oluşturulamadı")
            } finally {
                aiLoading.value = false
            }
        }
    }

    fun sendAiReply() {
        val draft = aiDraft.value.trim()
        if (draft.isBlank()) {
            scope.launch { snackbar.showSnackbar("Yanıt metni boş") }
            return
        }
        scope.launch {
            sendingReply.value = true
            try {
                val detail = mailState.value
                val response = apiClient.api.sendMailReply(
                    MailSendReplyRequest(
                        sender = detail.sender,
                        subject = detail.subject,
                        final_reply = draft,
                        html_body = htmlBody.value,
                        library_file_ids = libraryAttachments.value.map { it.id },
                    ),
                )
                snackbar.showSnackbar(response.message)
                showAiPanel.value = false
                aiDraft.value = ""
                aiInstruction.value = ""
                htmlBody.value = ""
                libraryAttachments.value = emptyList()
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Yanıt gönderilemedi")
            } finally {
                sendingReply.value = false
            }
        }
    }

    Scaffold(
        modifier = modifier,
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        mailState.value.subject.ifBlank { "(Konu yok)" },
                        maxLines = 1,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Geri")
                    }
                },
                actions = {
                    if (speechHelper.isSpeakAvailable()) {
                        IconButton(onClick = {
                            if (speechHelper.isSpeaking()) {
                                speechHelper.stopSpeaking()
                                speaking.value = false
                            } else {
                                speechHelper.speak(content.value)
                                speaking.value = true
                            }
                        }) {
                            Icon(
                                if (speaking.value) Icons.Default.Stop else Icons.Default.VolumeUp,
                                contentDescription = "Maili dinle",
                            )
                        }
                    }
                    IconButton(onClick = { translate(selectedLang.value) }) {
                        Icon(Icons.Default.Translate, contentDescription = "Çevir")
                    }
                    IconButton(
                        onClick = {
                            scope.launch {
                                summaryLoading.value = true
                                try {
                                    val detail = mailState.value
                                    val response = apiClient.api.mailSummary(
                                        MailSummaryRequest(
                                            mail_id = detail.id,
                                            folder = folder,
                                            sender = detail.sender,
                                            subject = detail.subject,
                                            content = detail.content,
                                            create_reminders = false,
                                        ),
                                    )
                                    summary.value = response.summary
                                } catch (e: Exception) {
                                    snackbar.showSnackbar(e.message ?: "Özet alınamadı")
                                } finally {
                                    summaryLoading.value = false
                                }
                            }
                        },
                        enabled = !summaryLoading.value && !detailLoading.value,
                    ) {
                        Icon(Icons.Default.Summarize, contentDescription = "AI Özet")
                    }
                    IconButton(onClick = {
                        showAiPanel.value = !showAiPanel.value
                        if (!showAiPanel.value) {
                            aiDraft.value = ""
                            reviseNote.value = ""
                            htmlBody.value = ""
                            libraryAttachments.value = emptyList()
                        }
                    }) {
                        Icon(Icons.Default.AutoAwesome, contentDescription = "AI ile yanıtla")
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp)
                .navigationBarsPadding(),
        ) {
            val detail = mailState.value
            val senderName = formatSenderName(detail)
            val senderEmail = formatSenderEmail(detail)
            val senderInitial = senderName.firstOrNull()?.uppercaseChar()?.toString() ?: "?"

            Row(verticalAlignment = Alignment.Top) {
                Box(
                    modifier = Modifier
                        .padding(end = 12.dp)
                        .size(48.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        senderInitial,
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold,
                        style = MaterialTheme.typography.titleLarge,
                    )
                }
                Column(Modifier.weight(1f)) {
                    Text(
                        senderName,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                    if (senderEmail.isNotBlank()) {
                        Text(
                            senderEmail,
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    Text(
                        detail.date,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 2.dp),
                    )
                }
                if (detail.starred) {
                    Icon(Icons.Default.Star, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                } else {
                    Icon(Icons.Outlined.StarOutline, contentDescription = null)
                }
            }

            Spacer(Modifier.height(12.dp))
            Text(
                detail.subject.ifBlank { "(Konu yok)" },
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Medium,
            )
            Spacer(Modifier.height(8.dp))

            Text(
                "Dili algıla ve çevir:",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(6.dp))
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                val selectedLabel = languages.value.firstOrNull { it.first == selectedLang.value }?.second
                    ?: selectedLang.value
                ExposedDropdownMenuBox(
                    expanded = langMenuOpen.value,
                    onExpandedChange = { langMenuOpen.value = !langMenuOpen.value },
                    modifier = Modifier.weight(1f),
                ) {
                    OutlinedTextField(
                        value = selectedLabel,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Dil") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = langMenuOpen.value) },
                        modifier = Modifier
                            .menuAnchor(type = MenuAnchorType.PrimaryNotEditable)
                            .fillMaxWidth(),
                        enabled = !loading.value && !detailLoading.value,
                    )
                    ExposedDropdownMenu(
                        expanded = langMenuOpen.value,
                        onDismissRequest = { langMenuOpen.value = false },
                    ) {
                        languages.value.forEach { (code, label) ->
                            DropdownMenuItem(
                                text = { Text(label) },
                                onClick = {
                                    selectedLang.value = code
                                    langMenuOpen.value = false
                                },
                            )
                        }
                    }
                }
                Button(
                    onClick = { translate(selectedLang.value) },
                    enabled = !loading.value && !detailLoading.value,
                ) {
                    Icon(Icons.Filled.Translate, contentDescription = null)
                    Spacer(Modifier.size(6.dp))
                    Text(if (translatedLang.value == selectedLang.value) "Orijinal" else "Çevir")
                }
            }

            Spacer(Modifier.height(12.dp))

            if (detailLoading.value || loading.value) {
                if (loading.value && !detailLoading.value) {
                    Text(
                        "Dil algılanıyor, çeviri hazırlanıyor...",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(bottom = 8.dp),
                    )
                }
                CircularProgressIndicator()
            } else {
                Text(content.value, style = MaterialTheme.typography.bodyLarge)
            }

            if (summaryLoading.value) {
                Spacer(Modifier.height(12.dp))
                Text("AI özet hazırlanıyor...", color = MaterialTheme.colorScheme.primary)
            }

            summary.value?.let { s ->
                Spacer(Modifier.height(16.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.45f),
                    ),
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text("AI Özet & Yorum", fontWeight = FontWeight.SemiBold)
                        Spacer(Modifier.height(8.dp))
                        Text(s.summary)
                        if (s.interpretation.isNotBlank()) {
                            Spacer(Modifier.height(6.dp))
                            Text(
                                s.interpretation,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        Spacer(Modifier.height(6.dp))
                        Text(
                            "Önem: ${s.importance} · Aciliyet: ${s.urgency}",
                            style = MaterialTheme.typography.bodySmall,
                        )
                        if (s.action_items.isNotEmpty()) {
                            Spacer(Modifier.height(8.dp))
                            s.action_items.forEach { item ->
                                Text("• $item")
                            }
                        }
                        if (s.suggested_reply.isNotBlank()) {
                            Spacer(Modifier.height(8.dp))
                            Text("Önerilen yanıt", fontWeight = FontWeight.Medium)
                            Text(s.suggested_reply)
                        }
                        Spacer(Modifier.height(10.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = {
                                scope.launch {
                                    try {
                                        val detail = mailState.value
                                        val response = apiClient.api.mailSummary(
                                            MailSummaryRequest(
                                                mail_id = detail.id,
                                                folder = folder,
                                                sender = detail.sender,
                                                subject = detail.subject,
                                                content = detail.content,
                                                create_reminders = true,
                                            ),
                                        )
                                        summary.value = response.summary
                                        snackbar.showSnackbar(
                                            "${response.reminders_created.size} hatırlatıcı eklendi",
                                        )
                                    } catch (e: Exception) {
                                        snackbar.showSnackbar(e.message ?: "Hatırlatıcı eklenemedi")
                                    }
                                }
                            }) {
                                Text("Hatırlatıcı oluştur")
                            }
                            OutlinedButton(onClick = { summary.value = null }) {
                                Text("Gizle")
                            }
                        }
                    }
                }
            }

            if (detail.attachments.isNotEmpty()) {
                Spacer(Modifier.height(16.dp))
                Text("Ekler (${detail.attachments.size})", fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(8.dp))
                detail.attachments.forEach { att ->
                    OutlinedButton(
                        onClick = { downloadAttachment(att) },
                        enabled = downloadingIndex.value == null,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp),
                    ) {
                        if (downloadingIndex.value == att.index) {
                            CircularProgressIndicator(modifier = Modifier.height(18.dp))
                        } else {
                            Icon(Icons.Default.Download, contentDescription = null)
                        }
                        Spacer(Modifier.width(8.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                att.filename.ifBlank { "ek" },
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                formatSize(att.size),
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                }
            }

            if (showAiPanel.value) {
                Spacer(Modifier.height(20.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.35f),
                    ),
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text(
                            "KipGPT ile Yanıt",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "İpucu yazabilir veya boş bırakıp doğrudan yanıt oluşturabilirsiniz.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Spacer(Modifier.height(12.dp))

                        if (aiLoading.value) {
                            AiThinkingStatus()
                            Spacer(Modifier.height(12.dp))
                        }

                        if (aiDraft.value.isBlank()) {
                            InlineInputActionBar(
                                value = aiInstruction.value,
                                onValueChange = { aiInstruction.value = it },
                                placeholder = "İpucu / talimat (isteğe bağlı)",
                                enabled = !aiLoading.value && !detailLoading.value,
                                minLines = 2,
                                maxLines = 4,
                                trailingContent = {
                                    RoundMicButton(
                                        listening = listeningInstruction.value,
                                        enabled = !aiLoading.value && !detailLoading.value,
                                        onClick = {
                                            if (listeningInstruction.value) {
                                                speechHelper.stopListening()
                                                listeningInstruction.value = false
                                            } else {
                                                requestVoiceInput("instruction")
                                            }
                                        },
                                    )
                                    RoundActionButton(
                                        icon = Icons.Default.AutoAwesome,
                                        contentDescription = "Yanıt Oluştur",
                                        enabled = !aiLoading.value && !detailLoading.value,
                                        loading = aiLoading.value,
                                        onClick = { generateAiReply() },
                                    )
                                },
                            )
                        } else {
                            OutlinedTextField(
                                value = aiDraft.value,
                                onValueChange = { aiDraft.value = it },
                                modifier = Modifier.fillMaxWidth(),
                                label = { Text("Yanıt taslağı") },
                                minLines = 8,
                            )
                            if (libraryAttachments.value.isNotEmpty()) {
                                Spacer(Modifier.height(8.dp))
                                Text(
                                    "Kütüphane ekleri",
                                    style = MaterialTheme.typography.labelMedium,
                                )
                                Spacer(Modifier.height(4.dp))
                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                                ) {
                                    libraryAttachments.value.forEach { item ->
                                        AssistChip(
                                            onClick = {},
                                            label = { Text(item.filename) },
                                        )
                                    }
                                }
                            }
                            Spacer(Modifier.height(12.dp))
                            InlineInputActionBar(
                                value = reviseNote.value,
                                onValueChange = { reviseNote.value = it },
                                placeholder = "AI ile güncelle...",
                                enabled = !aiLoading.value && !sendingReply.value,
                                minLines = 1,
                                maxLines = 3,
                                trailingContent = {
                                    RoundMicButton(
                                        listening = listeningRevise.value,
                                        enabled = !aiLoading.value && !sendingReply.value,
                                        onClick = {
                                            if (listeningRevise.value) {
                                                speechHelper.stopListening()
                                                listeningRevise.value = false
                                            } else {
                                                requestVoiceInput("revise")
                                            }
                                        },
                                    )
                                    RoundActionButton(
                                        icon = Icons.Default.Refresh,
                                        contentDescription = "Güncelle",
                                        enabled = reviseNote.value.isNotBlank(),
                                        loading = aiLoading.value,
                                        onClick = { generateAiReply(revise = true) },
                                        tonal = true,
                                    )
                                    RoundSendButton(
                                        enabled = aiDraft.value.isNotBlank(),
                                        loading = sendingReply.value,
                                        onClick = { sendAiReply() },
                                    )
                                },
                            )
                            Spacer(Modifier.height(8.dp))
                            OutlinedButton(
                                onClick = {
                                    aiDraft.value = ""
                                    reviseNote.value = ""
                                },
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Text("Yeniden oluştur")
                            }
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ComposeMailScreen(
    apiClient: ApiClient,
    onBack: () -> Unit,
    onSent: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val toEmail = remember { mutableStateOf("") }
    val subject = remember { mutableStateOf("") }
    val body = remember { mutableStateOf("") }
    val aiInstruction = remember { mutableStateOf("") }
    val showAiPanel = remember { mutableStateOf(false) }
    val aiLoading = remember { mutableStateOf(false) }
    val sending = remember { mutableStateOf(false) }
    val listening = remember { mutableStateOf(false) }
    val htmlBody = remember { mutableStateOf("") }
    val libraryAttachments = remember { mutableStateOf<List<LibraryAttachmentRef>>(emptyList()) }
    val pendingAttachmentName = remember { mutableStateOf<String?>(null) }
    val pendingAttachment = remember { mutableStateOf<OutgoingAttachmentPayload?>(null) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val speechHelper = remember { SpeechHelper(context) }

    val attachPicker = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            try {
                val (filename, bytes, mime) = withContext(Dispatchers.IO) {
                    readUriBytes(context.contentResolver, uri)
                }
                if (bytes.size > 15 * 1024 * 1024) {
                    snackbar.showSnackbar("Dosya 15 MB sınırını aşıyor")
                    return@launch
                }
                pendingAttachmentName.value = filename
                pendingAttachment.value = OutgoingAttachmentPayload(
                    filename = filename,
                    mimetype = mime,
                    data_base64 = Base64.encodeToString(bytes, Base64.NO_WRAP),
                )
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Dosya okunamadı")
            }
        }
    }

    DisposableEffect(speechHelper) {
        onDispose { speechHelper.shutdown() }
    }

    fun generateAiCompose() {
        scope.launch {
            val instruction = aiInstruction.value.trim()
            val currentBody = body.value.trim()
            if (instruction.isBlank() && currentBody.isBlank() && subject.value.isBlank()) {
                snackbar.showSnackbar("AI için bir ipucu yazın")
                return@launch
            }
            aiLoading.value = true
            try {
                val response = apiClient.api.generateMailAiCompose(
                    MailAiComposeRequest(
                        to_email = toEmail.value.trim(),
                        subject = subject.value.trim(),
                        user_instruction = if (currentBody.isBlank()) instruction else "",
                        current_draft = currentBody,
                        revize_notu = if (currentBody.isNotBlank()) {
                            instruction.ifBlank { "Taslağı iyileştir, daha net ve profesyonel yaz." }
                        } else {
                            ""
                        },
                    ),
                )
                body.value = response.draft
                htmlBody.value = response.html_body
                libraryAttachments.value = response.library_attachments
                aiInstruction.value = ""
                if (response.library_attachments.isNotEmpty()) {
                    snackbar.showSnackbar(
                        "Kütüphane eki: " + response.library_attachments.joinToString { it.filename },
                    )
                }
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "AI taslağı oluşturulamadı")
            } finally {
                aiLoading.value = false
            }
        }
    }

    fun sendMail() {
        scope.launch {
            val to = toEmail.value.trim()
            val text = body.value.trim()
            if (to.isBlank()) {
                snackbar.showSnackbar("Alıcı gerekli")
                return@launch
            }
            if (text.isBlank()) {
                snackbar.showSnackbar("Mail metni boş")
                return@launch
            }
            sending.value = true
            try {
                val response = apiClient.api.sendNewMail(
                    MailSendNewRequest(
                        to_email = to,
                        subject = subject.value.trim(),
                        body = text,
                        html_body = htmlBody.value,
                        library_file_ids = libraryAttachments.value.map { it.id },
                        attachment = pendingAttachment.value,
                    ),
                )
                snackbar.showSnackbar(response.message)
                onSent()
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Gönderilemedi")
            } finally {
                sending.value = false
            }
        }
    }

    Scaffold(
        modifier = modifier,
        topBar = {
            TopAppBar(
                title = { Text("Yeni İleti") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Geri")
                    }
                },
                actions = {
                    IconButton(
                        onClick = { showAiPanel.value = !showAiPanel.value },
                        enabled = !aiLoading.value && !sending.value,
                    ) {
                        Icon(Icons.Default.AutoAwesome, contentDescription = "AI ile yaz")
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp)
                .navigationBarsPadding(),
        ) {
            OutlinedTextField(
                value = toEmail.value,
                onValueChange = { toEmail.value = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Kime") },
                singleLine = true,
                enabled = !sending.value,
            )
            Spacer(Modifier.height(10.dp))
            OutlinedTextField(
                value = subject.value,
                onValueChange = { subject.value = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Konu") },
                singleLine = true,
                enabled = !sending.value,
            )
            Spacer(Modifier.height(10.dp))
            OutlinedTextField(
                value = body.value,
                onValueChange = { body.value = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("Mesaj") },
                minLines = 8,
                enabled = !sending.value && !aiLoading.value,
            )

            if (libraryAttachments.value.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                Text("Kütüphane ekleri", style = MaterialTheme.typography.labelMedium)
                Spacer(Modifier.height(4.dp))
                Row(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                ) {
                    libraryAttachments.value.forEach { item ->
                        AssistChip(onClick = {}, label = { Text(item.filename) })
                    }
                }
            }

            if (pendingAttachmentName.value != null) {
                Spacer(Modifier.height(8.dp))
                AssistChip(
                    onClick = {
                        pendingAttachmentName.value = null
                        pendingAttachment.value = null
                    },
                    label = { Text("Ek: ${pendingAttachmentName.value} (kaldır)") },
                )
            }

            if (showAiPanel.value) {
                Spacer(Modifier.height(16.dp))
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.35f),
                    ),
                ) {
                    Column(Modifier.padding(16.dp)) {
                        Text(
                            "KipGPT ile Mail Yaz",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "İpucu yazın; tablo/grafik veya “teklif.pdf ekle” diyebilirsiniz.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Spacer(Modifier.height(12.dp))
                        if (aiLoading.value) {
                            AiThinkingStatus()
                            Spacer(Modifier.height(12.dp))
                        }
                        InlineInputActionBar(
                            value = aiInstruction.value,
                            onValueChange = { aiInstruction.value = it },
                            placeholder = "Örn: Toplantı daveti, kısa ve resmi",
                            enabled = !aiLoading.value && !sending.value,
                            minLines = 2,
                            maxLines = 4,
                            trailingContent = {
                                RoundMicButton(
                                    listening = listening.value,
                                    enabled = !aiLoading.value && !sending.value && speechHelper.isListenAvailable(),
                                    onClick = {
                                        if (listening.value) {
                                            speechHelper.stopListening()
                                            listening.value = false
                                        } else {
                                            listening.value = true
                                            val started = speechHelper.startListening(
                                                onResult = { transcript ->
                                                    aiInstruction.value = if (aiInstruction.value.isBlank()) {
                                                        transcript
                                                    } else {
                                                        "${aiInstruction.value} $transcript"
                                                    }
                                                },
                                                onError = { message ->
                                                    scope.launch { snackbar.showSnackbar(message) }
                                                },
                                                onEnd = { listening.value = false },
                                            )
                                            if (!started) listening.value = false
                                        }
                                    },
                                )
                                RoundActionButton(
                                    icon = Icons.Default.AutoAwesome,
                                    contentDescription = "AI ile Yaz",
                                    enabled = !aiLoading.value && !sending.value,
                                    loading = aiLoading.value,
                                    onClick = { generateAiCompose() },
                                )
                            },
                        )
                    }
                }
            }

            Spacer(Modifier.height(16.dp))
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                OutlinedButton(
                    onClick = { attachPicker.launch(arrayOf("*/*")) },
                    enabled = !sending.value && !aiLoading.value,
                    modifier = Modifier.weight(1f),
                ) {
                    Icon(Icons.Default.AttachFile, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Dosya ekle")
                }
                Button(
                    onClick = { sendMail() },
                    enabled = !sending.value && !aiLoading.value,
                    modifier = Modifier.weight(1f),
                ) {
                    if (sending.value) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                    } else {
                        Text("Gönder")
                    }
                }
            }
        }
    }
}

private fun formatSize(bytes: Int): String {
    if (bytes < 1024) return "$bytes B"
    if (bytes < 1024 * 1024) return "${bytes / 1024} KB"
    return "${bytes / (1024 * 1024)} MB"
}

private fun formatSenderName(mail: MailItem): String {
    val raw = mail.sender_display.ifBlank { mail.sender }.trim()
    val nameMatch = Regex("^\"?([^\"<]+)\"?\\s*<").find(raw)
    if (nameMatch != null) {
        return nameMatch.groupValues[1].trim()
    }
    if (raw.contains("@") && !raw.contains(" ")) {
        return raw.substringBefore("@")
    }
    return raw.ifBlank { "Bilinmeyen gönderen" }
}

private fun formatSenderEmail(mail: MailItem): String {
    val raw = mail.sender_display.ifBlank { mail.sender }.trim()
    val emailMatch = Regex("<([^>]+)>").find(raw)
    if (emailMatch != null) {
        return emailMatch.groupValues[1].trim()
    }
    return mail.sender.trim().takeIf { it.contains("@") } ?: raw.takeIf { it.contains("@") } ?: ""
}
