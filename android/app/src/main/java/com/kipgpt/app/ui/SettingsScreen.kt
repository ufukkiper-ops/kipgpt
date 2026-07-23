package com.kipgpt.app.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    apiClient: ApiClient,
    sessionManager: SessionManager,
    onBack: (() -> Unit)? = null,
    onLogout: (() -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val userEmail = remember { mutableStateOf<String?>(null) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

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
                Spacer(modifier.height(8.dp))
            }

            if (!userEmail.value.isNullOrBlank()) {
                Text("Hesap", style = MaterialTheme.typography.titleMedium)
                Text(
                    userEmail.value!!,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.primary,
                )
                Spacer(modifier.height(16.dp))
                HorizontalDivider()
                Spacer(modifier.height(16.dp))
            }

            Text(
                "Sunucu adresi uygulamaya gömülüdür; tünel değişince yeni APK ile güncellenir.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(modifier.height(8.dp))
            Text(
                "KipGPT sürümü: ${BuildConfig.VERSION_NAME}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            if (onLogout != null) {
                Spacer(modifier.height(16.dp))
                HorizontalDivider()
                Spacer(modifier.height(16.dp))
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
