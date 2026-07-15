package com.kipgpt.app.ui

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Event
import androidx.compose.material.icons.filled.Folder
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
    // 0 Mail, 1 Takvim, 2 Dosyalar, 3 Sohbet, 4 Ayarlar
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
                    icon = { Icon(Icons.Default.Event, contentDescription = "Takvim") },
                    label = { Text("Takvim") },
                )
                NavigationBarItem(
                    selected = selectedTab.intValue == 2,
                    onClick = { selectedTab.intValue = 2 },
                    icon = { Icon(Icons.Default.Folder, contentDescription = "Dosyalar") },
                    label = { Text("Dosyalar") },
                )
                NavigationBarItem(
                    selected = selectedTab.intValue == 3,
                    onClick = { selectedTab.intValue = 3 },
                    icon = { Icon(Icons.AutoMirrored.Filled.Chat, contentDescription = "Sohbet") },
                    label = { Text("Sohbet") },
                )
                NavigationBarItem(
                    selected = selectedTab.intValue == 4,
                    onClick = { selectedTab.intValue = 4 },
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
            1 -> CalendarScreen(
                apiClient = apiClient,
                modifier = Modifier.fillMaxSize().padding(padding),
            )
            2 -> FileLibraryScreen(
                apiClient = apiClient,
                modifier = Modifier.fillMaxSize().padding(padding),
            )
            3 -> ChatScreen(
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
