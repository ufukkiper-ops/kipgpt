package com.kipgpt.app.ui

import androidx.compose.foundation.background
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
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.ChatMessage
import com.kipgpt.app.data.ChatSummary
import com.kipgpt.app.data.SendRequest
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    apiClient: ApiClient,
    onOpenMail: () -> Unit,
    onOpenSettings: () -> Unit,
    onLogout: () -> Unit,
) {
    val chats = remember { mutableStateListOf<ChatSummary>() }
    val messages = remember { mutableStateListOf<ChatMessage>() }
    val activeChatId = remember { mutableStateOf("") }
    val chatTitle = remember { mutableStateOf("Kip Asistan") }
    val input = remember { mutableStateOf("") }
    val loading = remember { mutableStateOf(false) }
    val sending = remember { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val listState = rememberLazyListState()
    val scope = rememberCoroutineScope()

    fun loadChats(selectId: String? = null) {
        scope.launch {
            loading.value = true
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
                loading.value = false
            }
        }
    }

    LaunchedEffect(Unit) { loadChats() }

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.lastIndex)
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet {
                Text(
                    "Sohbetler",
                    modifier = Modifier.padding(16.dp),
                    style = MaterialTheme.typography.titleLarge,
                )
                chats.forEach { chat ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
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
                        Column(Modifier.weight(1f)) {
                            Text(chat.title, style = MaterialTheme.typography.titleSmall)
                            Text(
                                chat.preview.ifBlank { "Boş sohbet" },
                                style = MaterialTheme.typography.bodySmall,
                                maxLines = 1,
                            )
                        }
                    }
                }
            }
        },
    ) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text(chatTitle.value) },
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
                        IconButton(onClick = onOpenMail) {
                            Icon(Icons.Default.Email, contentDescription = "Mail")
                        }
                        IconButton(onClick = onOpenSettings) {
                            Icon(Icons.Default.Settings, contentDescription = "Ayarlar")
                        }
                    },
                )
            },
            snackbarHost = { SnackbarHost(snackbar) },
            floatingActionButton = {
                if (activeChatId.value.isNotBlank()) {
                    FloatingActionButton(
                        onClick = {
                            scope.launch {
                                try {
                                    apiClient.api.clearChat(activeChatId.value)
                                    messages.clear()
                                } catch (e: Exception) {
                                    snackbar.showSnackbar(e.message ?: "Temizlenemedi")
                                }
                            }
                        },
                    ) {
                        Icon(Icons.Default.Delete, contentDescription = "Temizle")
                    }
                }
            },
        ) { padding ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
            ) {
                if (loading.value) {
                    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                } else {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxWidth()
                            .padding(horizontal = 12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        item { Spacer(Modifier.height(4.dp)) }
                        items(messages) { message ->
                            MessageBubble(message)
                        }
                        item { Spacer(Modifier.height(4.dp)) }
                    }
                }

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    OutlinedTextField(
                        value = input.value,
                        onValueChange = { input.value = it },
                        modifier = Modifier.weight(1f),
                        placeholder = { Text("Mesaj yazın...") },
                        enabled = !sending.value,
                    )
                    Spacer(Modifier.padding(4.dp))
                    IconButton(
                        onClick = {
                            val text = input.value.trim()
                            if (text.isBlank() || activeChatId.value.isBlank()) return@IconButton
                            scope.launch {
                                sending.value = true
                                messages.add(ChatMessage("user", text))
                                input.value = ""
                                try {
                                    val response = apiClient.api.sendMessage(
                                        activeChatId.value,
                                        SendRequest(text),
                                    )
                                    messages.add(ChatMessage("assistant", response.answer))
                                    chatTitle.value = response.chat_title
                                    loadChats(activeChatId.value)
                                } catch (e: Exception) {
                                    snackbar.showSnackbar("Gönderilemedi: ${e.message}")
                                } finally {
                                    sending.value = false
                                }
                            }
                        },
                        enabled = !sending.value && input.value.isNotBlank(),
                    ) {
                        Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Gönder")
                    }
                }
            }
        }
    }
}

@Composable
private fun MessageBubble(message: ChatMessage) {
    val isUser = message.role == "user"
    val bg = if (isUser) MaterialTheme.colorScheme.primary else Color(0xFFE8EAED)
    val fg = if (isUser) Color.White else Color(0xFF202124)
    val align = if (isUser) Alignment.CenterEnd else Alignment.CenterStart

    Box(
        modifier = Modifier.fillMaxWidth(),
        contentAlignment = align,
    ) {
        Text(
            text = message.content,
            color = fg,
            modifier = Modifier
                .widthIn(max = 320.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(bg)
                .padding(horizontal = 14.dp, vertical = 10.dp),
        )
    }
}
