package com.kipgpt.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.kipgpt.app.BuildConfig
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.SessionManager
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun SettingsScreen(
    apiClient: ApiClient,
    sessionManager: SessionManager,
    onBack: (() -> Unit)? = null,
    onLogout: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val baseUrl = remember { mutableStateOf(SessionManager.DEFAULT_BASE_URL) }
    val userEmail = remember { mutableStateOf<String?>(null) }
    val testing = remember { mutableStateOf(false) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        sessionManager.baseUrlFlow.collect { baseUrl.value = it }
    }

    LaunchedEffect(apiClient) {
        if (onLogout != null) {
            try {
                val me = apiClient.api.me()
                userEmail.value = me.email
            } catch (_: Exception) {
            }
        }
    }

    Scaffold(
        modifier = modifier,
        topBar = {
            if (onBack != null) {
                TopAppBar(
                    title = { Text("Ayarlar") },
                    navigationIcon = {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Geri")
                        }
                    },
                )
            }
        },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
        ) {
            if (onLogout == null) {
                Text("Ayarlar", style = MaterialTheme.typography.headlineSmall)
                Spacer(Modifier.height(8.dp))
            }

            if (!userEmail.value.isNullOrBlank()) {
                Text("Hesap", style = MaterialTheme.typography.titleMedium)
                Text(
                    userEmail.value!!,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.primary,
                )
                Spacer(Modifier.height(16.dp))
                HorizontalDivider()
                Spacer(Modifier.height(16.dp))
            }

            Text("Sunucu adresi", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = baseUrl.value,
                onValueChange = { baseUrl.value = it },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("http://10.0.2.2:5001/api/v1/") },
                singleLine = true,
            )
            Spacer(Modifier.height(8.dp))

            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(
                    selected = baseUrl.value == SessionManager.DEFAULT_BASE_URL,
                    onClick = { baseUrl.value = SessionManager.DEFAULT_BASE_URL },
                    label = { Text("Emülatör") },
                )
                FilterChip(
                    selected = baseUrl.value == SessionManager.RENDER_BASE_URL,
                    onClick = { baseUrl.value = SessionManager.RENDER_BASE_URL },
                    label = { Text("Render (Canlı)") },
                )
            }

            Spacer(Modifier.height(8.dp))
            Text(
                "Emülatör: 10.0.2.2 — Gerçek telefon: bilgisayarınızın yerel IP adresi",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "KipGPT sürümü: ${BuildConfig.VERSION_NAME}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(Modifier.height(16.dp))

            Button(
                onClick = {
                    scope.launch {
                        sessionManager.saveBaseUrl(baseUrl.value)
                        apiClient.updateBaseUrl(
                            if (baseUrl.value.endsWith("/")) baseUrl.value else "${baseUrl.value}/",
                        )
                        snackbar.showSnackbar("Sunucu adresi kaydedildi")
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Kaydet")
            }

            Spacer(Modifier.height(8.dp))
            OutlinedButton(
                onClick = {
                    scope.launch {
                        testing.value = true
                        try {
                            val normalized = if (baseUrl.value.endsWith("/")) {
                                baseUrl.value
                            } else {
                                "${baseUrl.value}/"
                            }
                            apiClient.updateBaseUrl(normalized)
                            if (onLogout != null) {
                                val me = apiClient.api.me()
                                userEmail.value = me.email
                                snackbar.showSnackbar("Bağlantı başarılı: ${me.email}")
                            } else {
                                snackbar.showSnackbar("Adres kaydedildi. Giriş yaparak test edin.")
                            }
                        } catch (e: Exception) {
                            snackbar.showSnackbar("Bağlantı hatası: ${e.message}")
                        } finally {
                            testing.value = false
                        }
                    }
                },
                enabled = !testing.value,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (testing.value) {
                    CircularProgressIndicator()
                } else {
                    Text("Bağlantıyı Test Et")
                }
            }

            if (onLogout != null) {
                Spacer(Modifier.height(16.dp))
                HorizontalDivider()
                Spacer(Modifier.height(16.dp))
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            sessionManager.clearToken()
                            apiClient.updateToken(null)
                            onLogout()
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Çıkış Yap")
                }
            }
        }
    }
}
