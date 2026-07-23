package com.kipgpt.app.ui

import android.Manifest
import android.content.Intent
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
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Summarize
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Translate
import androidx.compose.material.icons.outlined.StarOutline
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.ManageAccounts
import androidx.compose.material.icons.filled.MarkEmailRead
import androidx.compose.material.icons.filled.MarkEmailUnread
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.activity.compose.BackHandler
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.ListItem
import androidx.compose.material3.RadioButton
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
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
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.kipgpt.app.data.AddMailAccountRequest
import retrofit2.HttpException
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.AttachmentSaver
import com.kipgpt.app.data.LibraryAttachmentRef
import com.kipgpt.app.data.MailAccount
import com.kipgpt.app.data.MailAiComposeRequest
import com.kipgpt.app.data.MailAiReplyRequest
import com.kipgpt.app.data.MailAttachment
import com.kipgpt.app.data.MailFolder
import com.kipgpt.app.data.MailItem
import com.kipgpt.app.data.MailProviderPreset
import com.kipgpt.app.data.MarkMailReadRequest
import com.kipgpt.app.data.MarkMailUnreadRequest
import com.kipgpt.app.data.OAuthProviderStatus
import com.kipgpt.app.data.MailSaveDraftRequest
import com.kipgpt.app.data.MailSendNewRequest
import com.kipgpt.app.data.MailSendReplyRequest
import com.kipgpt.app.data.MailSummaryData
import com.kipgpt.app.data.MailSummaryRequest
import com.kipgpt.app.data.OutgoingAttachmentPayload
import com.kipgpt.app.data.SessionManager
import com.kipgpt.app.data.SpeechHelper
import com.kipgpt.app.data.TranslateRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MailScreen(
    apiClient: ApiClient,
    sessionManager: SessionManager,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val folders = remember { mutableStateListOf<MailFolder>() }
    val mails = remember { mutableStateListOf<MailItem>() }
    val mailAccounts = remember { mutableStateListOf<MailAccount>() }
    val providers = remember { mutableStateOf<Map<String, MailProviderPreset>>(emptyMap()) }
    val oauthProviders = remember { mutableStateOf<Map<String, OAuthProviderStatus>>(emptyMap()) }
    val awaitingOAuthReturn = remember { mutableStateOf(false) }
    val selectedFolder = remember { mutableStateOf("inbox") }
    val selectedMail = remember { mutableStateOf<MailItem?>(null) }
    val composing = remember { mutableStateOf(false) }
    val search = remember { mutableStateOf("") }
    val account = remember { mutableStateOf("") }
    val activeAccountId = remember { mutableStateOf<String?>(null) }
    val showAccountSheet = remember { mutableStateOf(false) }
    val showAddAccountDialog = remember { mutableStateOf(false) }
    val accountsLoading = remember { mutableStateOf(false) }
    val loading = remember { mutableStateOf(false) }
    val loadError = remember { mutableStateOf<String?>(null) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val accountSheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

    suspend fun syncActiveAccount(accountId: String) {
        apiClient.api.activateMailAccount(accountId)
        sessionManager.saveActiveMailAccount(accountId)
        activeAccountId.value = accountId
    }

    suspend fun loadAccountsNow() {
        accountsLoading.value = true
        try {
            val response = apiClient.api.mailAccounts()
            mailAccounts.clear()
            mailAccounts.addAll(response.accounts)
            providers.value = response.providers
            oauthProviders.value = response.oauth_providers

            val savedId = sessionManager.getActiveMailAccount()
            val targetId = when {
                savedId != null && response.accounts.any { it.id == savedId } -> savedId
                response.active_account_id != null -> response.active_account_id
                response.accounts.isNotEmpty() -> response.accounts.first().id
                else -> null
            }

            if (targetId != null && targetId != response.active_account_id) {
                syncActiveAccount(targetId)
            } else {
                activeAccountId.value = targetId
            }
        } catch (e: Exception) {
            snackbar.showSnackbar(e.message ?: "Hesaplar yüklenemedi")
        } finally {
            accountsLoading.value = false
        }
    }

    suspend fun loadMailsNow() {
        if (mailAccounts.isEmpty()) {
            mails.clear()
            loadError.value = "Mail hesabı bağlı değil. Hesap ekleyin."
            return
        }
        loading.value = true
        loadError.value = null
        try {
            val response = apiClient.api.mails(
                folder = selectedFolder.value,
                search = search.value.trim().ifBlank { null },
                account = activeAccountId.value,
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

    fun switchAccount(accountId: String) {
        scope.launch {
            try {
                syncActiveAccount(accountId)
                showAccountSheet.value = false
                loadMailsNow()
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Hesap değiştirilemedi")
            }
        }
    }

    fun deleteAccount(accountId: String) {
        scope.launch {
            try {
                val response = apiClient.api.deleteMailAccount(accountId)
                loadAccountsNow()
                if (response.active_account_id != null) {
                    sessionManager.saveActiveMailAccount(response.active_account_id)
                    activeAccountId.value = response.active_account_id
                } else {
                    sessionManager.saveActiveMailAccount(null)
                    activeAccountId.value = null
                }
                loadMailsNow()
                snackbar.showSnackbar("Hesap kaldırıldı")
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Hesap silinemedi")
            }
        }
    }

    LaunchedEffect(Unit) {
        try {
            folders.clear()
            folders.addAll(apiClient.api.folders().folders)
        } catch (_: Exception) {
        }
        loadAccountsNow()
    }

    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME && awaitingOAuthReturn.value) {
                awaitingOAuthReturn.value = false
                scope.launch {
                    loadAccountsNow()
                    loadMailsNow()
                    snackbar.showSnackbar("Hesaplar güncellendi")
                }
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    LaunchedEffect(activeAccountId.value, selectedFolder.value) {
        if (selectedMail.value == null && !composing.value && !accountsLoading.value) {
            loadMailsNow()
        }
    }

    if (showAddAccountDialog.value) {
        AddMailAccountDialog(
            providers = providers.value,
            oauthProviders = oauthProviders.value,
            saving = accountsLoading.value,
            onDismiss = { showAddAccountDialog.value = false },
            onOAuth = { providerKey ->
                scope.launch {
                    accountsLoading.value = true
                    try {
                        val response = apiClient.api.mailOAuthStart(providerKey)
                        val url = response.authorization_url
                        if (url.isBlank()) {
                            snackbar.showSnackbar("OAuth adresi alınamadı")
                            return@launch
                        }
                        awaitingOAuthReturn.value = true
                        showAddAccountDialog.value = false
                        showAccountSheet.value = false
                        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                        context.startActivity(intent)
                        snackbar.showSnackbar("Tarayıcıda giriş yapın; dönünce otomatik yenilenir")
                    } catch (e: HttpException) {
                        val msg = e.response()?.errorBody()?.string()?.let {
                            it.substringAfter("\"error\":\"").substringBefore("\"")
                        } ?: (e.message ?: "OAuth başlatılamadı")
                        snackbar.showSnackbar(msg)
                    } catch (e: Exception) {
                        snackbar.showSnackbar(e.message ?: "OAuth başlatılamadı")
                    } finally {
                        accountsLoading.value = false
                    }
                }
            },
            onSave = { request ->
                scope.launch {
                    accountsLoading.value = true
                    try {
                        val response = apiClient.api.addMailAccount(request)
                        mailAccounts.clear()
                        mailAccounts.addAll(apiClient.api.mailAccounts().accounts)
                        syncActiveAccount(response.active_account_id)
                        showAddAccountDialog.value = false
                        showAccountSheet.value = false
                        loadMailsNow()
                        snackbar.showSnackbar("Mail hesabı eklendi")
                    } catch (e: Exception) {
                        snackbar.showSnackbar(e.message ?: "Hesap eklenemedi")
                    } finally {
                        accountsLoading.value = false
                    }
                }
            },
        )
    }

    if (showAccountSheet.value) {
        ModalBottomSheet(
            onDismissRequest = { showAccountSheet.value = false },
            sheetState = accountSheetState,
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp)
                    .padding(bottom = 24.dp)
                    .navigationBarsPadding(),
            ) {
                Text(
                    "Mail Hesapları",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(8.dp))
                if (mailAccounts.isEmpty()) {
                    Text(
                        "Henüz mail hesabı yok. Gmail, Outlook veya diğer sağlayıcılar için hesap ekleyin.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Spacer(Modifier.height(12.dp))
                } else {
                    mailAccounts.forEach { item ->
                        ListItem(
                            headlineContent = {
                                Text(item.label.ifBlank { item.email })
                            },
                            supportingContent = { Text(item.email) },
                            leadingContent = {
                                RadioButton(
                                    selected = activeAccountId.value == item.id,
                                    onClick = { switchAccount(item.id) },
                                )
                            },
                            trailingContent = {
                                IconButton(onClick = { deleteAccount(item.id) }) {
                                    Icon(Icons.Default.Delete, contentDescription = "Hesabı kaldır")
                                }
                            },
                            modifier = Modifier.clickable { switchAccount(item.id) },
                        )
                    }
                }
                Button(
                    onClick = {
                        showAccountSheet.value = false
                        showAddAccountDialog.value = true
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Icon(Icons.Default.Add, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Hesap Ekle")
                }
            }
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
            activeAccountId = activeAccountId.value,
            onBack = { selectedMail.value = null },
            onReadStateChanged = { mailId, unread ->
                val idx = mails.indexOfFirst { it.id == mailId }
                if (idx >= 0) {
                    mails[idx] = mails[idx].copy(unread = unread)
                }
                selectedMail.value = selectedMail.value?.let {
                    if (it.id == mailId) it.copy(unread = unread) else it
                }
                if (!unread && selectedFolder.value == "unread") {
                    mails.removeAll { it.id == mailId }
                }
            },
            modifier = modifier,
        )
        return
    }

    val needsAccount = mailAccounts.isEmpty() ||
        loadError.value?.contains("Mail hesabı bağlı değil", ignoreCase = true) == true

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
                    IconButton(onClick = { showAccountSheet.value = true }) {
                        Icon(Icons.Default.ManageAccounts, contentDescription = "Mail hesapları")
                    }
                    IconButton(onClick = { loadMails() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Yenile")
                    }
                },
            )
        },
        floatingActionButton = {
            if (!needsAccount) {
                FloatingActionButton(onClick = { composing.value = true }) {
                    Icon(Icons.Default.Edit, contentDescription = "Yeni mail")
                }
            }
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            if (needsAccount) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.padding(24.dp),
                    ) {
                        Text(
                            "Mail hesabı bağlı değil",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.SemiBold,
                        )
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "Gmail, Outlook veya diğer IMAP/SMTP hesabınızı ekleyerek maillerinizi görüntüleyin.",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Spacer(Modifier.height(16.dp))
                        Button(onClick = { showAddAccountDialog.value = true }) {
                            Icon(Icons.Default.Add, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text("Mail Hesabı Ekle")
                        }
                    }
                }
                return@Column
            }

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
                                if (loadError.value?.contains("Mail hesabı bağlı değil", ignoreCase = true) == true) {
                                    Spacer(Modifier.height(8.dp))
                                    Button(onClick = { showAddAccountDialog.value = true }) {
                                        Text("Mail Hesabı Ekle")
                                    }
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
    val titleWeight = if (mail.unread) FontWeight.Bold else FontWeight.SemiBold
    val subjectWeight = if (mail.unread) FontWeight.SemiBold else FontWeight.Medium

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
                        fontWeight = titleWeight,
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
                if (mail.unread) {
                    Box(
                        modifier = Modifier
                            .padding(end = 6.dp)
                            .size(8.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.primary),
                    )
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
                    fontWeight = subjectWeight,
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
    activeAccountId: String? = null,
    onBack: () -> Unit,
    onReadStateChanged: (mailId: String, unread: Boolean) -> Unit = { _, _ -> },
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
            val full = apiClient.api.mailDetail(mail.id, folder, activeAccountId)
            mailState.value = full
            content.value = full.content
            translatedLang.value = null
            summary.value = null
            htmlBody.value = ""
            libraryAttachments.value = emptyList()
            if (full.unread || mail.unread) {
                try {
                    val markFolder = if (folder == "unread") "inbox" else folder
                    apiClient.api.markMailRead(
                        MarkMailReadRequest(
                            mail_id = full.id.ifBlank { mail.id },
                            folder = markFolder,
                            account = activeAccountId,
                        )
                    )
                    mailState.value = full.copy(unread = false)
                    onReadStateChanged(full.id.ifBlank { mail.id }, false)
                } catch (_: Exception) {
                    // Okundu işareti başarısız olsa da detay gösterilsin
                }
            }
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
                    val markFolder = if (folder == "unread") "inbox" else folder
                    IconButton(
                        onClick = {
                            scope.launch {
                                try {
                                    if (mailState.value.unread) {
                                        apiClient.api.markMailRead(
                                            MarkMailReadRequest(
                                                mail_id = mailState.value.id,
                                                folder = markFolder,
                                                account = activeAccountId,
                                            ),
                                        )
                                        mailState.value = mailState.value.copy(unread = false)
                                        onReadStateChanged(mailState.value.id, false)
                                        snackbar.showSnackbar("Okundu olarak işaretlendi")
                                    } else {
                                        apiClient.api.markMailUnread(
                                            MarkMailUnreadRequest(
                                                mail_id = mailState.value.id,
                                                folder = markFolder,
                                                account = activeAccountId,
                                            ),
                                        )
                                        mailState.value = mailState.value.copy(unread = true)
                                        onReadStateChanged(mailState.value.id, true)
                                        snackbar.showSnackbar("Okunmadı olarak işaretlendi")
                                    }
                                } catch (e: Exception) {
                                    snackbar.showSnackbar(e.message ?: "İşaretleme başarısız")
                                }
                            }
                        },
                        enabled = !detailLoading.value && mailState.value.id.isNotBlank(),
                    ) {
                        Icon(
                            if (mailState.value.unread) Icons.Default.MarkEmailRead else Icons.Default.MarkEmailUnread,
                            contentDescription = if (mailState.value.unread) {
                                "Okundu işaretle"
                            } else {
                                "Okunmadı işaretle"
                            },
                        )
                    }
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
                                if (speaking.value) Icons.Default.Stop else Icons.AutoMirrored.Filled.VolumeUp,
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
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                val markFolder = if (folder == "unread") "inbox" else folder
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            try {
                                apiClient.api.markMailRead(
                                    MarkMailReadRequest(
                                        mail_id = mailState.value.id,
                                        folder = markFolder,
                                        account = activeAccountId,
                                    ),
                                )
                                mailState.value = mailState.value.copy(unread = false)
                                onReadStateChanged(mailState.value.id, false)
                                snackbar.showSnackbar("Okundu olarak işaretlendi")
                            } catch (e: Exception) {
                                snackbar.showSnackbar(e.message ?: "İşaretleme başarısız")
                            }
                        }
                    },
                    enabled = !detailLoading.value && mailState.value.id.isNotBlank(),
                ) {
                    Icon(
                        Icons.Default.MarkEmailRead,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text("Okundu işaretle")
                }
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            try {
                                apiClient.api.markMailUnread(
                                    MarkMailUnreadRequest(
                                        mail_id = mailState.value.id,
                                        folder = markFolder,
                                        account = activeAccountId,
                                    ),
                                )
                                mailState.value = mailState.value.copy(unread = true)
                                onReadStateChanged(mailState.value.id, true)
                                snackbar.showSnackbar("Okunmadı olarak işaretlendi")
                            } catch (e: Exception) {
                                snackbar.showSnackbar(e.message ?: "İşaretleme başarısız")
                            }
                        }
                    },
                    enabled = !detailLoading.value && mailState.value.id.isNotBlank(),
                ) {
                    Icon(
                        Icons.Default.MarkEmailUnread,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text("Okunmadı")
                }
            }
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

    fun hasDraftContent(): Boolean {
        return toEmail.value.isNotBlank() ||
            subject.value.isNotBlank() ||
            body.value.isNotBlank() ||
            htmlBody.value.isNotBlank() ||
            libraryAttachments.value.isNotEmpty() ||
            pendingAttachment.value != null
    }

    fun saveDraftAndBack() {
        scope.launch {
            if (!hasDraftContent()) {
                onBack()
                return@launch
            }
            sending.value = true
            try {
                val response = apiClient.api.saveMailDraft(
                    MailSaveDraftRequest(
                        to_email = toEmail.value.trim(),
                        subject = subject.value.trim(),
                        body = body.value.trim(),
                        html_body = htmlBody.value,
                        library_file_ids = libraryAttachments.value.map { it.id },
                        attachment = pendingAttachment.value,
                    ),
                )
                if (response.saved) {
                    snackbar.showSnackbar("Taslak kaydedildi")
                }
                onBack()
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Taslak kaydedilemedi")
                // Kullanıcı tekrar deneyebilir; geri dönme
            } finally {
                sending.value = false
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
                    IconButton(
                        onClick = { saveDraftAndBack() },
                        enabled = !sending.value,
                    ) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Geri")
                    }
                },
                actions = {
                    IconButton(
                        onClick = { saveDraftAndBack() },
                        enabled = !sending.value && !aiLoading.value,
                    ) {
                        Icon(Icons.Default.Save, contentDescription = "Taslak kaydet")
                    }
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
        BackHandler(enabled = !sending.value) {
            saveDraftAndBack()
        }
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
                horizontalArrangement = Arrangement.spacedBy(6.dp, Alignment.End),
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                RoundAttachButton(
                    enabled = !sending.value && !aiLoading.value,
                    onClick = { attachPicker.launch(arrayOf("*/*")) },
                )
                RoundSendButton(
                    enabled = toEmail.value.isNotBlank() && body.value.isNotBlank(),
                    loading = sending.value,
                    onClick = { sendMail() },
                )
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddMailAccountDialog(
    providers: Map<String, MailProviderPreset>,
    oauthProviders: Map<String, OAuthProviderStatus>,
    saving: Boolean,
    onDismiss: () -> Unit,
    onOAuth: (String) -> Unit,
    onSave: (AddMailAccountRequest) -> Unit,
) {
    val providerKeys = providers.keys.toList().ifEmpty {
        listOf("gmail", "outlook", "yahoo", "custom")
    }
    val email = remember { mutableStateOf("") }
    val label = remember { mutableStateOf("") }
    val password = remember { mutableStateOf("") }
    val showPassword = remember { mutableStateOf(false) }
    val provider = remember { mutableStateOf(providerKeys.first()) }
    val providerMenuOpen = remember { mutableStateOf(false) }
    val imapServer = remember { mutableStateOf("") }
    val smtpServer = remember { mutableStateOf("") }
    val imapPort = remember { mutableStateOf("993") }
    val smtpPort = remember { mutableStateOf("587") }

    val selectedPreset = providers[provider.value]
    val providerLabel = selectedPreset?.label ?: provider.value
    val providerHint = selectedPreset?.hint ?: ""
    val isCustom = provider.value == "custom"
    LaunchedEffect(provider.value, selectedPreset) {
        if (!isCustom && selectedPreset != null) {
            imapServer.value = selectedPreset.imap_server
            smtpServer.value = selectedPreset.smtp_server
            imapPort.value = selectedPreset.imap_port.toString()
            smtpPort.value = selectedPreset.smtp_port.toString()
        }
    }

    AlertDialog(
        onDismissRequest = { if (!saving) onDismiss() },
        title = { Text("Mail Hesabı Ekle") },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                val googleReady = oauthProviders["google"]?.configured == true
                val microsoftReady = oauthProviders["microsoft"]?.configured == true
                val yahooReady = oauthProviders["yahoo"]?.configured == true
                val anyOAuth = googleReady || microsoftReady || yahooReady

                Text(
                    "Şifresiz bağla (önerilen)",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.SemiBold,
                )
                if (anyOAuth) {
                    if (googleReady) {
                        OutlinedButton(
                            onClick = { onOAuth("google") },
                            enabled = !saving,
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text("Gmail ile senkronize et")
                        }
                    }
                    if (microsoftReady) {
                        OutlinedButton(
                            onClick = { onOAuth("microsoft") },
                            enabled = !saving,
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text("Outlook ile bağla")
                        }
                    }
                    if (yahooReady) {
                        OutlinedButton(
                            onClick = { onOAuth("yahoo") },
                            enabled = !saving,
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text("Yahoo ile bağla")
                        }
                    }
                    Text(
                        "Google hesabınızı seçip izin verin — uygulama şifresi gerekmez.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                } else {
                    Text(
                        "Şifresiz Gmail şu an sunucuda kapalı (OAUTH_LOGIN_ENABLED). " +
                            "Şimdilik uygulama şifresi ile ekleyebilirsiniz.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                }

                Text(
                    "veya şifre / IMAP ile ekle",
                    style = MaterialTheme.typography.labelLarge,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(
                    "E-posta ve uygulama şifresi ile ekleyin",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                OutlinedTextField(
                    value = email.value,
                    onValueChange = { email.value = it },
                    label = { Text("E-posta") },
                    singleLine = true,
                    enabled = !saving,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = label.value,
                    onValueChange = { label.value = it },
                    label = { Text("Etiket (isteğe bağlı)") },
                    singleLine = true,
                    enabled = !saving,
                    modifier = Modifier.fillMaxWidth(),
                )
                ExposedDropdownMenuBox(
                    expanded = providerMenuOpen.value,
                    onExpandedChange = { providerMenuOpen.value = !providerMenuOpen.value },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    OutlinedTextField(
                        value = providerLabel,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Sağlayıcı") },
                        trailingIcon = {
                            ExposedDropdownMenuDefaults.TrailingIcon(expanded = providerMenuOpen.value)
                        },
                        modifier = Modifier
                            .menuAnchor(type = MenuAnchorType.PrimaryNotEditable)
                            .fillMaxWidth(),
                        enabled = !saving,
                    )
                    ExposedDropdownMenu(
                        expanded = providerMenuOpen.value,
                        onDismissRequest = { providerMenuOpen.value = false },
                    ) {
                        providerKeys.forEach { key ->
                            val itemLabel = providers[key]?.label ?: key
                            DropdownMenuItem(
                                text = { Text(itemLabel) },
                                onClick = {
                                    provider.value = key
                                    providerMenuOpen.value = false
                                },
                            )
                        }
                    }
                }
                if (providerHint.isNotBlank()) {
                    Text(
                        providerHint,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                OutlinedTextField(
                    value = password.value,
                    onValueChange = { password.value = it },
                    label = { Text("Şifre / Uygulama şifresi") },
                    singleLine = true,
                    enabled = !saving,
                    visualTransformation = if (showPassword.value) {
                        androidx.compose.ui.text.input.VisualTransformation.None
                    } else {
                        androidx.compose.ui.text.input.PasswordVisualTransformation()
                    },
                    trailingIcon = {
                        IconButton(onClick = { showPassword.value = !showPassword.value }) {
                            Icon(
                                if (showPassword.value) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                                contentDescription = if (showPassword.value) "Gizle" else "Göster",
                            )
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                )
                if (isCustom) {
                    OutlinedTextField(
                        value = imapServer.value,
                        onValueChange = { imapServer.value = it },
                        label = { Text("IMAP sunucu") },
                        singleLine = true,
                        enabled = !saving,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    OutlinedTextField(
                        value = smtpServer.value,
                        onValueChange = { smtpServer.value = it },
                        label = { Text("SMTP sunucu") },
                        singleLine = true,
                        enabled = !saving,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(
                            value = imapPort.value,
                            onValueChange = { imapPort.value = it },
                            label = { Text("IMAP port") },
                            singleLine = true,
                            enabled = !saving,
                            modifier = Modifier.weight(1f),
                        )
                        OutlinedTextField(
                            value = smtpPort.value,
                            onValueChange = { smtpPort.value = it },
                            label = { Text("SMTP port") },
                            singleLine = true,
                            enabled = !saving,
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    onSave(
                        AddMailAccountRequest(
                            account_email = email.value.trim(),
                            account_label = label.value.trim(),
                            mail_provider = provider.value,
                            mail_password = password.value,
                            imap_server = imapServer.value.trim(),
                            smtp_server = smtpServer.value.trim(),
                            imap_port = imapPort.value.trim(),
                            smtp_port = smtpPort.value.trim(),
                        ),
                    )
                },
                enabled = !saving && email.value.isNotBlank() && password.value.isNotBlank(),
            ) {
                if (saving) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp))
                } else {
                    Text("Ekle")
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !saving) {
                Text("İptal")
            }
        },
    )
}
