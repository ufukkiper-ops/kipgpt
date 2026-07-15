package com.kipgpt.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.SessionManager
import com.kipgpt.app.ui.LoginScreen
import com.kipgpt.app.ui.MainScreen
import com.kipgpt.app.ui.SettingsScreen
import com.kipgpt.app.ui.theme.KipGptTheme
import kotlinx.coroutines.flow.first

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val sessionManager = SessionManager(applicationContext)

        setContent {
            KipGptTheme {
                KipGptApp(sessionManager)
            }
        }
    }
}

@Composable
private fun KipGptApp(sessionManager: SessionManager) {
    val navController = rememberNavController()
    val startRoute = remember { mutableStateOf<String?>(null) }
    val tokenState = remember { mutableStateOf<String?>(null) }
    val baseUrlState = remember { mutableStateOf(SessionManager.DEFAULT_BASE_URL) }

    LaunchedEffect(Unit) {
        tokenState.value = sessionManager.tokenFlow.first()
        baseUrlState.value = sessionManager.baseUrlFlow.first()
        startRoute.value = if (tokenState.value.isNullOrBlank()) "login" else "main"
    }

    val apiClient = remember(tokenState.value, baseUrlState.value) {
        ApiClient(tokenState.value, baseUrlState.value)
    }

    val route = startRoute.value
    if (route == null) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    NavHost(navController = navController, startDestination = route) {
        composable("login") {
            LoginScreen(
                apiClient = apiClient,
                sessionManager = sessionManager,
                onLoggedIn = {
                    tokenState.value = sessionManager.tokenFlow.first()
                    navController.navigate("main") {
                        popUpTo("login") { inclusive = true }
                    }
                },
                onOpenSettings = { navController.navigate("settings_guest") },
            )
        }
        composable("main") {
            MainScreen(
                apiClient = apiClient,
                sessionManager = sessionManager,
                onLogout = {
                    tokenState.value = null
                    navController.navigate("login") {
                        popUpTo("main") { inclusive = true }
                    }
                },
            )
        }
        composable("settings_guest") {
            SettingsScreen(
                apiClient = apiClient,
                sessionManager = sessionManager,
                onBack = { navController.popBackStack() },
                onLogout = null,
            )
        }
    }
}
