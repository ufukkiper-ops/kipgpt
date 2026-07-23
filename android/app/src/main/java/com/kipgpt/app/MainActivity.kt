package com.kipgpt.app

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.kipgpt.app.data.ApiClient
import com.kipgpt.app.data.SessionManager
import com.kipgpt.app.ui.LoginScreen
import com.kipgpt.app.ui.MainScreen
import com.kipgpt.app.ui.theme.KipGptTheme
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val oauthUriState = mutableStateOf<Uri?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        oauthUriState.value = intent?.data.takeIf { it?.scheme == "kipgpt" && it.host == "oauth" }

        val app = application as KipGptApplication

        setContent {
            KipGptTheme {
                val pendingOAuthUri by oauthUriState
                KipGptApp(
                    sessionManager = app.sessionManager,
                    pendingOAuthUri = pendingOAuthUri,
                    onOAuthConsumed = { oauthUriState.value = null },
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        oauthUriState.value = intent.data.takeIf { it?.scheme == "kipgpt" && it.host == "oauth" }
    }
}

@Composable
private fun KipGptApp(
    sessionManager: SessionManager,
    pendingOAuthUri: Uri?,
    onOAuthConsumed: () -> Unit,
) {
    val viewModel: MainViewModel = viewModel(
        factory = MainViewModel.Factory(sessionManager),
    )
    val authState by viewModel.authState.collectAsState()
    val baseUrl by viewModel.baseUrl.collectAsState()
    val scope = rememberCoroutineScope()

    val token = (authState as? AuthState.LoggedIn)?.token
    val apiClient = remember(token, baseUrl) {
        ApiClient(token, baseUrl)
    }

    LaunchedEffect(pendingOAuthUri) {
        val uri = pendingOAuthUri ?: return@LaunchedEffect
        val oauthToken = uri.getQueryParameter("token").orEmpty()
        val email = uri.getQueryParameter("email").orEmpty()
        if (oauthToken.isNotBlank()) {
            sessionManager.saveToken(oauthToken, email.ifBlank { null })
        }
        onOAuthConsumed()
    }

    when {
        authState is AuthState.Loading -> {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        }
        authState is AuthState.LoggedOut -> {
            LoginScreen(
                apiClient = apiClient,
                sessionManager = sessionManager,
                onLoggedIn = { },
            )
        }
        authState is AuthState.LoggedIn -> {
            MainScreen(
                apiClient = apiClient,
                sessionManager = sessionManager,
                onLogout = {
                    scope.launch {
                        viewModel.logout()
                    }
                },
            )
        }
    }
}
