package com.kipgpt.app.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.SessionManager
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    apiClient: ApiClient,
    sessionManager: SessionManager,
    onBack: () -> Unit,
    onLogout: () -> Unit,
) {
    val baseUrl = remember { mutableStateOf(SessionManager.DEFAULT_BASE_URL) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        sessionManager.baseUrlFlow.collect { baseUrl.value = it }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Ayarlar") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Geri")
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
            Text("Sunucu adresi")
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = baseUrl.value,
                onValueChange = { baseUrl.value = it },
                modifier = Modifier.fillMaxWidth(),
                placeholder = { Text("http://10.0.2.2:5001/api/v1/") },
                singleLine = true,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "Emülatör: http://10.0.2.2:5001/api/v1/\n" +
                    "Gerçek telefon: bilgisayar IP'niz, örn. http://192.168.1.10:5001/api/v1/",
            )
            Spacer(Modifier.height(16.dp))
            Button(
                onClick = {
                    scope.launch {
                        sessionManager.saveBaseUrl(baseUrl.value)
                        apiClient.updateBaseUrl(
                            if (baseUrl.value.endsWith("/")) baseUrl.value else "${baseUrl.value}/"
                        )
                        snackbar.showSnackbar("Sunucu adresi kaydedildi")
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Kaydet")
            }
            Spacer(Modifier.height(12.dp))
            Button(
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
