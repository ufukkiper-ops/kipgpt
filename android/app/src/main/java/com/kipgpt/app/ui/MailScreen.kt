package com.kipgpt.app.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Translate
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.MailFolder
import com.kipgpt.app.data.MailItem
import com.kipgpt.app.data.TranslateRequest
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MailScreen(
    apiClient: ApiClient,
    onBack: () -> Unit,
) {
    val folders = remember { mutableStateListOf<MailFolder>() }
    val mails = remember { mutableStateListOf<MailItem>() }
    val selectedFolder = remember { mutableStateOf("inbox") }
    val selectedMail = remember { mutableStateOf<MailItem?>(null) }
    val search = remember { mutableStateOf("") }
    val account = remember { mutableStateOf("") }
    val loading = remember { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    fun loadMails() {
        scope.launch {
            loading.value = true
            try {
                val response = apiClient.api.mails(
                    folder = selectedFolder.value,
                    search = search.value.ifBlank { null },
                )
                mails.clear()
                mails.addAll(response.mails)
                account.value = response.account
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Mailler yüklenemedi")
            } finally {
                loading.value = false
            }
        }
    }

    LaunchedEffect(Unit) {
        try {
            folders.clear()
            folders.addAll(apiClient.api.folders().folders)
        } catch (_: Exception) {
        }
        loadMails()
    }

    if (selectedMail.value != null) {
        MailDetailScreen(
            mail = selectedMail.value!!,
            apiClient = apiClient,
            onBack = { selectedMail.value = null },
        )
        return
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Mailler")
                        if (account.value.isNotBlank()) {
                            Text(
                                account.value,
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Geri")
                    }
                },
                actions = {
                    IconButton(onClick = { loadMails() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Yenile")
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                folders.take(5).forEach { folder ->
                    FilterChip(
                        selected = selectedFolder.value == folder.id,
                        onClick = {
                            selectedFolder.value = folder.id
                            loadMails()
                        },
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
            )

            Spacer(Modifier.height(8.dp))

            if (loading.value) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else if (mails.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Bu klasörde mail yok")
                }
            } else {
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

@Composable
private fun MailRow(mail: MailItem, onClick: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 12.dp),
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(
                mail.sender.ifBlank { mail.sender_display },
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            Text(mail.date, style = MaterialTheme.typography.bodySmall)
        }
        Text(
            mail.subject.ifBlank { "(Konu yok)" },
            fontWeight = FontWeight.Medium,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            mail.content.replace("\n", " ").take(100),
            style = MaterialTheme.typography.bodySmall,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MailDetailScreen(
    mail: MailItem,
    apiClient: ApiClient,
    onBack: () -> Unit,
) {
    val content = remember { mutableStateOf(mail.content) }
    val translatedLang = remember { mutableStateOf<String?>(null) }
    val loading = remember { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    fun translate(lang: String) {
        if (translatedLang.value == lang) {
            content.value = mail.content
            translatedLang.value = null
            return
        }
        scope.launch {
            loading.value = true
            try {
                val response = apiClient.api.translate(
                    TranslateRequest(mail.content, lang)
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

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(mail.subject.ifBlank { "(Konu yok)" }, maxLines = 1) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Geri")
                    }
                },
                actions = {
                    IconButton(onClick = { translate("tr") }) {
                        Icon(Icons.Default.Translate, contentDescription = "Çevir")
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
                .padding(16.dp),
        ) {
            Text(mail.sender_display.ifBlank { mail.sender }, fontWeight = FontWeight.SemiBold)
            Text(mail.date, style = MaterialTheme.typography.bodySmall)
            Spacer(Modifier.height(8.dp))

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("tr" to "TR", "en" to "EN", "de" to "DE").forEach { (code, label) ->
                    FilterChip(
                        selected = translatedLang.value == code,
                        onClick = { translate(code) },
                        label = { Text(label) },
                    )
                }
            }

            Spacer(Modifier.height(12.dp))

            if (loading.value) {
                CircularProgressIndicator()
            } else {
                Text(content.value)
            }

            if (mail.attachments.isNotEmpty()) {
                Spacer(Modifier.height(16.dp))
                Text("Ekler", fontWeight = FontWeight.SemiBold)
                mail.attachments.forEach { att ->
                    Text("• ${att.filename} (${att.size} bayt)")
                }
            }
        }
    }
}
