package com.kipgpt.app.ui

import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.material.icons.automirrored.filled.Undo
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.CalendarCreateRequest
import com.kipgpt.app.data.CalendarEvent
import com.kipgpt.app.data.CalendarUpdateRequest
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CalendarScreen(
    apiClient: ApiClient,
    modifier: Modifier = Modifier,
) {
    val events = remember { mutableStateOf<List<CalendarEvent>>(emptyList()) }
    val loading = remember { mutableStateOf(true) }
    val refreshing = remember { mutableStateOf(false) }
    val title = remember { mutableStateOf("") }
    val description = remember { mutableStateOf("") }
    val whenText = remember { mutableStateOf("") }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    fun formatWhen(raw: String?): String {
        if (raw.isNullOrBlank()) return "Tarih yok"
        return try {
            val instant = Instant.parse(raw)
            DateTimeFormatter.ofPattern("dd MMM yyyy HH:mm")
                .withZone(ZoneId.systemDefault())
                .format(instant)
        } catch (_: Exception) {
            raw
        }
    }

    fun load(showSpinner: Boolean = true) {
        scope.launch {
            if (showSpinner) loading.value = true
            try {
                val response = apiClient.api.calendarEvents()
                events.value = response.events
            } catch (e: Exception) {
                snackbar.showSnackbar(e.message ?: "Takvim yüklenemedi")
            } finally {
                loading.value = false
                refreshing.value = false
            }
        }
    }

    LaunchedEffect(Unit) { load() }

    Scaffold(
        modifier = modifier,
        topBar = { TopAppBar(title = { Text("Takvim") }) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = refreshing.value,
            onRefresh = {
                refreshing.value = true
                load(showSpinner = false)
            },
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp),
            ) {
                OutlinedTextField(
                    value = title.value,
                    onValueChange = { title.value = it },
                    label = { Text("Başlık") },
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = whenText.value,
                    onValueChange = { whenText.value = it },
                    label = { Text("Tarih (ör. 2026-07-20T14:00:00Z)") },
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = description.value,
                    onValueChange = { description.value = it },
                    label = { Text("Açıklama") },
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(8.dp))
                Button(
                    onClick = {
                        scope.launch {
                            val t = title.value.trim()
                            if (t.isBlank()) {
                                snackbar.showSnackbar("Başlık gerekli")
                                return@launch
                            }
                            try {
                                val whenIso = whenText.value.trim().ifBlank { null }
                                apiClient.api.createCalendarEvent(
                                    CalendarCreateRequest(
                                        title = t,
                                        description = description.value.trim(),
                                        start = whenIso,
                                        reminder_at = whenIso,
                                    ),
                                )
                                title.value = ""
                                description.value = ""
                                whenText.value = ""
                                load(showSpinner = false)
                            } catch (e: Exception) {
                                snackbar.showSnackbar(e.message ?: "Eklenemedi")
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Hatırlatıcı ekle")
                }

                Spacer(Modifier.height(16.dp))

                when {
                    loading.value -> CircularProgressIndicator()
                    events.value.isEmpty() -> Text("Henüz etkinlik yok.")
                    else -> LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        items(events.value, key = { it.id }) { event ->
                            Card(modifier = Modifier.fillMaxWidth()) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(12.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            event.title,
                                            style = MaterialTheme.typography.titleMedium,
                                        )
                                        Text(
                                            formatWhen(event.reminder_at ?: event.start),
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                        if (event.description.isNotBlank()) {
                                            Text(event.description, style = MaterialTheme.typography.bodyMedium)
                                        }
                                        if (event.done) {
                                            Text("Tamamlandı", color = MaterialTheme.colorScheme.primary)
                                        }
                                    }
                                    Row {
                                        IconButton(onClick = {
                                            scope.launch {
                                                try {
                                                    apiClient.api.updateCalendarEvent(
                                                        event.id,
                                                        CalendarUpdateRequest(done = !event.done),
                                                    )
                                                    load(showSpinner = false)
                                                } catch (e: Exception) {
                                                    snackbar.showSnackbar(e.message ?: "Güncellenemedi")
                                                }
                                            }
                                        }) {
                                            Icon(
                                                if (event.done) Icons.AutoMirrored.Filled.Undo else Icons.Filled.Check,
                                                contentDescription = "Tamamla",
                                            )
                                        }
                                        IconButton(onClick = {
                                            scope.launch {
                                                try {
                                                    apiClient.api.deleteCalendarEvent(event.id)
                                                    load(showSpinner = false)
                                                } catch (e: Exception) {
                                                    snackbar.showSnackbar(e.message ?: "Silinemedi")
                                                }
                                            }
                                        }) {
                                            Icon(Icons.Filled.Delete, contentDescription = "Sil")
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
}
