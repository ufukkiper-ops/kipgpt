package com.kipgpt.app.ui

import android.Manifest
import android.content.pm.PackageManager
import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.InsertDriveFile
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.ChatFileMeta
import com.kipgpt.app.data.ChatMessage
import com.kipgpt.app.data.ChatSummary
import com.kipgpt.app.data.SendRequest
import com.kipgpt.app.data.SpeechHelper
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

private const val MAX_CHAT_FILE_BYTES = 15L * 1024L * 1024L

private val CHAT_FILE_MIME_TYPES = arrayOf(
    "image/*",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/csv",
    "text/markdown",
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    apiClient: ApiClient,
    modifier: Modifier = Modifier,
) {
    val chats = remember { mutableStateListOf<ChatSummary>() }
    val messages = remember { mutableStateListOf<ChatMessage>() }
    val activeChatId = remember { mutableStateOf("") }
    val chatTitle = remember { mutableStateOf("KipGPT") }
    val input = remember { mutableStateOf("") }
    val loading = remember { mutableStateOf(false) }
    val sending = remember { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val speechHelper = remember { SpeechHelper(context) }
    val listening = remember { mutableStateOf(false) }
    val pendingVoiceStart = remember { mutableStateOf(false) }
    val pendingFile = remember { mutableStateOf<PendingChatFile?>(null) }

    DisposableEffect(speechHelper) {
        onDispose { speechHelper.shutdown() }
    }

    fun startVoiceInput(skipPermissionCheck: Boolean = false) {
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
            pendingVoiceStart.value = true
            return
        }
        listening.value = true
        val started = speechHelper.startListening(
            onResult = { transcript ->
                input.value = if (input.value.isBlank()) transcript else "${input.value} $transcript"
            },
            onError = { message ->
                scope.launch { snackbar.showSnackbar(message) }
            },
            onEnd = { listening.value = false },
        )
        if (!started) {
            listening.value = false
        }
    }

    val micPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) {
            if (pendingVoiceStart.value) {
                pendingVoiceStart.value = false
                startVoiceInput(skipPermissionCheck = true)
            }
        } else {
            pendingVoiceStart.value = false
            scope.launch { snackbar.showSnackbar("Mikrofon izni gerekli") }
        }
    }

    val filePickerLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument(),
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            try {
                val pending = withContext(Dispatchers.IO) {
                    readPendingChatFile(context, uri)
                }
                pendingFile.value = pending
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Dosya seçilemedi")
            }
        }
    }

    fun requestMicPermissionIfNeeded() {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            pendingVoiceStart.value = true
            micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        } else {
            startVoiceInput(skipPermissionCheck = true)
        }
    }

    fun loadChats(selectId: String? = null, showBlockingLoader: Boolean = false) {
        scope.launch {
            if (showBlockingLoader) {
                loading.value = true
            }
            try {
                val response = apiClient.api.chats()
                chats.clear()
                chats.addAll(response.chats)
                val target = selectId ?: response.active_chat
                if (target.isNotBlank()) {
                    activeChatId.value = target
                    val detail = apiClient.api.messages(target)
                    messages.clear()
                    messages.addAll(detail.messages)
                    chatTitle.value = detail.title
                }
            } catch (e: Exception) {
                snackbar.showSnackbar("Sohbetler yüklenemedi: ${e.message}")
            } finally {
                if (showBlockingLoader) {
                    loading.value = false
                }
            }
        }
    }

    suspend fun ensureActiveChat(): String {
        if (activeChatId.value.isNotBlank()) {
            return activeChatId.value
        }
        val created = apiClient.api.newChat()
        val newId = created["id"].orEmpty()
        if (newId.isBlank()) {
            throw IllegalStateException("Sohbet oluşturulamadı")
        }
        activeChatId.value = newId
        return newId
    }

    fun sendTextMessage(text: String) {
        scope.launch {
            sending.value = true
            messages.add(ChatMessage("user", text))
            input.value = ""
            try {
                val chatId = ensureActiveChat()
                val response = apiClient.api.sendMessage(chatId, SendRequest(text))
                messages.add(ChatMessage("assistant", response.answer))
                chatTitle.value = response.chat_title
                loadChats(chatId)
            } catch (e: Exception) {
                messages.removeLastOrNull()
                snackbar.showSnackbar("Gönderilemedi: ${e.message}")
            } finally {
                sending.value = false
            }
        }
    }

    fun sendFileMessage(pending: PendingChatFile, caption: String) {
        scope.launch {
            sending.value = true
            val displayText = caption.ifBlank { "[DOSYA] ${pending.name}" }
            messages.add(
                ChatMessage(
                    role = "user",
                    content = displayText,
                    file = ChatFileMeta(name = pending.name, type = pending.category),
                ),
            )
            input.value = ""
            pendingFile.value = null
            try {
                val chatId = ensureActiveChat()
                val mediaType = (pending.mime.ifBlank { "application/octet-stream" })
                    .toMediaTypeOrNull()
                val fileBody = pending.bytes.toRequestBody(mediaType)
                val part = MultipartBody.Part.createFormData("file", pending.name, fileBody)
                val textBody = caption.toRequestBody("text/plain".toMediaTypeOrNull())
                val response = apiClient.api.sendMessageWithFile(chatId, textBody, part)
                messages.add(
                    ChatMessage(
                        role = "assistant",
                        content = response.answer,
                    ),
                )
                chatTitle.value = response.chat_title
                loadChats(chatId)
            } catch (e: Exception) {
                messages.removeLastOrNull()
                snackbar.showSnackbar("Dosya gönderilemedi: ${e.message}")
            } finally {
                sending.value = false
            }
        }
    }

    LaunchedEffect(Unit) { loadChats(showBlockingLoader = true) }

    LaunchedEffect(messages.size, sending.value) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.lastIndex)
        }
    }

    ModalNavigationDrawer(
        modifier = modifier,
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet {
                Column(Modifier.padding(16.dp)) {
                    Text("Sohbetler", style = MaterialTheme.typography.titleLarge)
                    Text(
                        "Geçmiş konuşmalarınız",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                HorizontalDivider()
                chats.forEach { chat ->
                    val isActive = chat.id == activeChatId.value
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(
                                if (isActive) {
                                    MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.45f)
                                } else {
                                    Color.Transparent
                                },
                            )
                            .clickable {
                                scope.launch {
                                    drawerState.close()
                                    activeChatId.value = chat.id
                                    chatTitle.value = chat.title
                                    apiClient.api.activateChat(chat.id)
                                    val detail = apiClient.api.messages(chat.id)
                                    messages.clear()
                                    messages.addAll(detail.messages)
                                }
                            }
                            .padding(horizontal = 16.dp, vertical = 12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(modifier.weight(1f)) {
                            Text(
                                chat.title,
                                style = MaterialTheme.typography.titleSmall,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                            )
                            Text(
                                chat.preview.ifBlank { "Boş sohbet" },
                                style = MaterialTheme.typography.bodySmall,
                                maxLines = 1,
                                overflow = TextOverflow.Ellipsis,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        if (chat.message_count > 0) {
                            Text(
                                "${chat.message_count}",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(start = 8.dp),
                            )
                        }
                    }
                    HorizontalDivider()
                }
            }
        },
    ) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = {
                        Column {
                            Text(chatTitle.value, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text(
                                "KipGPT",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    },
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Default.Menu, contentDescription = "Menü")
                        }
                    },
                    actions = {
                        IconButton(onClick = {
                            scope.launch {
                                try {
                                    val created = apiClient.api.newChat()
                                    loadChats(created["id"])
                                } catch (e: Exception) {
                                    snackbar.showSnackbar(e.message ?: "Hata")
                                }
                            }
                        }) {
                            Icon(Icons.Default.Add, contentDescription = "Yeni sohbet")
                        }
                        if (activeChatId.value.isNotBlank()) {
                            IconButton(onClick = {
                                scope.launch {
                                    try {
                                        apiClient.api.clearChat(activeChatId.value)
                                        messages.clear()
                                        loadChats(activeChatId.value)
                                    } catch (e: Exception) {
                                        snackbar.showSnackbar(e.message ?: "Temizlenemedi")
                                    }
                                }
                            }) {
                                Icon(Icons.Default.Delete, contentDescription = "Temizle")
                            }
                        }
                    },
                )
            },
            snackbarHost = { SnackbarHost(snackbar) },
            bottomBar = {
                Surface(
                    tonalElevation = 3.dp,
                    shadowElevation = 6.dp,
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .windowInsetsPadding(WindowInsets.ime)
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                    ) {
                        pendingFile.value?.let { file ->
                            PendingFileChip(
                                name = file.name,
                                onClear = { pendingFile.value = null },
                            )
                            Spacer(Modifier.height(8.dp))
                        }
                        ChatStyleInputBar(
                            value = input.value,
                            onValueChange = { input.value = it },
                            placeholder = if (pendingFile.value != null) {
                                "Dosya için not ekleyin (isteğe bağlı)..."
                            } else {
                                "Mesaj yazın..."
                            },
                            enabled = !sending.value && !loading.value,
                            listening = listening.value,
                            sendEnabled = (
                                input.value.isNotBlank() || pendingFile.value != null
                                ) && !sending.value,
                            sending = sending.value,
                            onAttachClick = {
                                filePickerLauncher.launch(CHAT_FILE_MIME_TYPES)
                            },
                            onMicClick = {
                                if (listening.value) {
                                    speechHelper.stopListening()
                                    listening.value = false
                                } else {
                                    requestMicPermissionIfNeeded()
                                }
                            },
                            onSendClick = {
                                val text = input.value.trim()
                                val file = pendingFile.value
                                when {
                                    file != null -> sendFileMessage(file, text)
                                    text.isNotBlank() -> sendTextMessage(text)
                                }
                            },
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
            },
        ) { padding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
            ) {
                when {
                    loading.value -> {
                        CircularProgressIndicator(
                            modifier = Modifier.align(Alignment.Center),
                        )
                    }
                    messages.isEmpty() && !sending.value -> {
                        Column(
                            modifier = Modifier.align(Alignment.Center),
                            horizontalAlignment = Alignment.CenterHorizontally,
                        ) {
                            Text(
                                "Merhaba!",
                                style = MaterialTheme.typography.headlineSmall,
                            )
                            Spacer(Modifier.height(8.dp))
                            Text(
                                "Metin yazın veya PDF / görsel ekleyin.",
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                    else -> {
                        LazyColumn(
                            state = listState,
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(horizontal = 12.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                            contentPadding = PaddingValues(vertical = 4.dp),
                        ) {
                            items(messages) { message ->
                                ChatMessageBubble(message, speechHelper)
                            }
                            if (sending.value) {
                                item {
                                    Box(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(vertical = 4.dp),
                                        contentAlignment = Alignment.CenterStart,
                                    ) {
                                        AiThinkingStatus()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PendingFileChip(name: String, onClear: () -> Unit) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.secondaryContainer,
    ) {
        Row(
            modifier = Modifier.padding(start = 12.dp, end = 4.dp, top = 6.dp, bottom = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                Icons.Default.InsertDriveFile,
                contentDescription = null,
                modifier = Modifier.size(18.dp),
            )
            Text(
                name,
                modifier = Modifier
                    .padding(horizontal = 8.dp)
                    .widthIn(max = 220.dp),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodySmall,
            )
            IconButton(onClick = onClear, modifier = Modifier.size(28.dp)) {
                Icon(Icons.Default.Close, contentDescription = "Kaldır", modifier = Modifier.size(16.dp))
            }
        }
    }
}

private data class PendingChatFile(
    val name: String,
    val mime: String,
    val category: String,
    val bytes: ByteArray,
)

private fun readPendingChatFile(context: android.content.Context, uri: Uri): PendingChatFile {
    val resolver = context.contentResolver
    var name = "dosya"
    resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE), null, null, null)
        ?.use { cursor ->
            if (cursor.moveToFirst()) {
                val nameIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
                if (nameIndex >= 0) {
                    name = cursor.getString(nameIndex) ?: name
                }
                if (sizeIndex >= 0) {
                    val size = cursor.getLong(sizeIndex)
                    if (size > MAX_CHAT_FILE_BYTES) {
                        throw IllegalArgumentException("Dosya boyutu 15 MB sınırını aşıyor.")
                    }
                }
            }
        }

    val mime = resolver.getType(uri).orEmpty()
    val category = guessChatFileCategory(name, mime)
    if (category == "other") {
        throw IllegalArgumentException(
            "Desteklenmeyen dosya türü. PDF, JPG, PNG, Word, Excel, CSV veya TXT gönderin.",
        )
    }

    val bytes = resolver.openInputStream(uri)?.use { it.readBytes() }
        ?: throw IllegalArgumentException("Dosya okunamadı.")
    if (bytes.isEmpty()) {
        throw IllegalArgumentException("Boş dosya yüklenemez.")
    }
    if (bytes.size > MAX_CHAT_FILE_BYTES) {
        throw IllegalArgumentException("Dosya boyutu 15 MB sınırını aşıyor.")
    }

    return PendingChatFile(
        name = File(name).name,
        mime = mime.ifBlank { "application/octet-stream" },
        category = category,
        bytes = bytes,
    )
}

private fun guessChatFileCategory(filename: String, mime: String): String {
    val ext = filename.substringAfterLast('.', "").lowercase()
    val lowerMime = mime.lowercase()
    return when {
        lowerMime.startsWith("image/") || ext in setOf("jpg", "jpeg", "png", "gif", "webp", "bmp") -> "image"
        lowerMime == "application/pdf" || ext == "pdf" -> "pdf"
        ext in setOf("doc", "docx") || lowerMime.contains("word") -> "word"
        ext in setOf("xls", "xlsx", "csv") || lowerMime.contains("excel") || lowerMime.contains("spreadsheet") -> "excel"
        ext in setOf("txt", "md", "log") || lowerMime.startsWith("text/") -> "text"
        else -> "other"
    }
}
