package com.kipgpt.app.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.SessionManager

@Composable
fun MainScreen(
    apiClient: ApiClient,
    sessionManager: SessionManager,
    onLogout: () -> Unit,
) {
    // 0 = Mail (giriş sonrası varsayılan), 1 = Sohbet, 2 = Ayarlar
    val selectedTab = rememberSaveable { mutableIntStateOf(0) }

    Scaffold(
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    selected = selectedTab.intValue == 0,
                    onClick = { selectedTab.intValue = 0 },
                    icon = { Icon(Icons.Default.Email, contentDescription = "Mail") },
                    label = { Text("Mail") },
                )
                NavigationBarItem(
                    selected = selectedTab.intValue == 1,
                    onClick = { selectedTab.intValue = 1 },
                    icon = { Icon(Icons.AutoMirrored.Filled.Chat, contentDescription = "Sohbet") },
                    label = { Text("Sohbet") },
                )
                NavigationBarItem(
                    selected = selectedTab.intValue == 2,
                    onClick = { selectedTab.intValue = 2 },
                    icon = { Icon(Icons.Default.Settings, contentDescription = "Ayarlar") },
                    label = { Text("Ayarlar") },
                )
            }
        },
    ) { padding ->
        when (selectedTab.intValue) {
            0 -> MailScreen(
                apiClient = apiClient,
                modifier = Modifier.fillMaxSize().padding(padding),
            )
            1 -> ChatScreen(
                apiClient = apiClient,
                modifier = Modifier.fillMaxSize().padding(padding),
            )
            else -> SettingsScreen(
                apiClient = apiClient,
                sessionManager = sessionManager,
                onLogout = onLogout,
                modifier = Modifier.fillMaxSize().padding(padding),
            )
        }
    }
}
